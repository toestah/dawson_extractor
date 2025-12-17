#!/usr/bin/env python3
"""
DAWSON Court Order Extractor

This script efficiently extracts court order PDFs from the DAWSON
(U.S. Tax Court) public API system.
"""

import requests
import json
import time
import random
import os
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime


class DAWSONExtractor:
    """Efficiently extracts court orders from DAWSON public API."""

    BASE_URL = "https://public-api-blue.dawson.ustaxcourt.gov"

    def __init__(self, config: Dict):
        """
        Initialize the extractor with configuration.

        Args:
            config: Configuration dictionary with settings
        """
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'DAWSON-Extractor/1.0 (Educational/Research)'
        })

        # Create output directory
        self.output_dir = Path(config.get('output_dir', 'downloads'))
        self.output_dir.mkdir(exist_ok=True)

        # Statistics
        self.stats = {
            'orders_downloaded': 0,
            'api_calls': 0,
            'errors': 0,
            'start_time': datetime.now()
        }

    def _rate_limit(self):
        """Implement rate limiting between API calls."""
        delay = self.config.get('rate_limit_delay', 1.5)
        time.sleep(delay)

    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Make an API request with error handling.

        Args:
            endpoint: API endpoint path
            params: Query parameters

        Returns:
            JSON response or None if error
        """
        url = f"{self.BASE_URL}{endpoint}"
        self.stats['api_calls'] += 1

        try:
            self._rate_limit()
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error making request to {endpoint}: {e}")
            self.stats['errors'] += 1
            return None

    def search_orders(self, keyword: str = "order") -> List[str]:
        """
        Search for court orders and return unique docket numbers.

        Args:
            keyword: Search keyword for orders

        Returns:
            List of unique docket numbers
        """
        print(f"Searching for orders with keyword: '{keyword}'...")

        params = {
            "keyword": keyword,
            "dateRange": "allDates",
            "limit": 5000
        }
        data = self._make_request("/public-api/order-search", params=params)

        if not data:
            print("Failed to retrieve order search results")
            return []

        # Extract unique docket numbers from results
        docket_numbers = set()
        results = data.get('results', [])

        for item in results:
            docket_number = item.get('docketNumber')
            if docket_number and item.get('documentType') == 'Order':
                docket_numbers.add(docket_number)

        print(f"Found {len(docket_numbers)} unique dockets with orders")
        return list(docket_numbers)

    def get_case_details(self, docket_number: str) -> Optional[Dict]:
        """
        Get detailed case information including docket entries.

        Args:
            docket_number: Case docket number

        Returns:
            Case details or None if error
        """
        return self._make_request(f"/public-api/cases/{docket_number}")

    def filter_court_orders(self, case_data: Dict) -> List[Dict]:
        """
        Filter docket entries for court orders that are PDFs.

        Args:
            case_data: Case details from API

        Returns:
            List of court order entries
        """
        orders = []

        docket_entries = case_data.get('docketEntries', [])
        for entry in docket_entries:
            # Check if it's an order and if there's a document
            event_code = entry.get('eventCode', '')
            document_type = entry.get('documentType', '')
            is_sealed = entry.get('isSealed', False)
            document_id = entry.get('docketEntryId')

            # Look for order-related document types
            is_order = (
                'order' in document_type.lower() or
                'O' in event_code  # Order event codes often contain 'O'
            )

            # Only include public PDFs
            if is_order and not is_sealed and document_id:
                orders.append({
                    'docket_number': case_data.get('docketNumber'),
                    'docket_entry_id': document_id,
                    'document_type': document_type,
                    'description': entry.get('description', ''),
                    'filed_date': entry.get('filingDate', 'Unknown')
                })

        return orders

    def download_document(self, docket_number: str, document_id: str,
                         metadata: Dict) -> bool:
        """
        Download a court order PDF.

        Args:
            docket_number: Case docket number
            document_id: Document entry ID
            metadata: Document metadata for naming

        Returns:
            True if successful, False otherwise
        """
        # Get download URL
        endpoint = f"/public-api/{docket_number}/{document_id}/public-document-download-url"
        response = self._make_request(endpoint)

        if not response or 'url' not in response:
            print(f"Failed to get download URL for {docket_number}/{document_id}")
            return False

        download_url = response['url']

        # Create filename
        safe_docket = docket_number.replace('/', '_')
        filed_date = metadata.get('filed_date', 'Unknown').split('T')[0]
        filename = f"{safe_docket}_{document_id}_{filed_date}.pdf"
        filepath = self.output_dir / filename

        # Download the PDF
        try:
            self._rate_limit()
            pdf_response = self.session.get(download_url, timeout=60)
            pdf_response.raise_for_status()

            # Save to file
            with open(filepath, 'wb') as f:
                f.write(pdf_response.content)

            print(f"Downloaded: {filename}")
            self.stats['orders_downloaded'] += 1

            # Save metadata
            metadata_file = filepath.with_suffix('.json')
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)

            return True

        except Exception as e:
            print(f"Error downloading document: {e}")
            self.stats['errors'] += 1
            return False

    def extract_orders(self, num_orders: int):
        """
        Main extraction process.

        Args:
            num_orders: Number of orders to download
        """
        print(f"\n=== DAWSON Court Order Extractor ===")
        print(f"Target: {num_orders} court orders")
        print(f"Output: {self.output_dir}")
        print(f"Rate limit: {self.config.get('rate_limit_delay', 1.0)}s between requests\n")

        # Step 1: Search for orders
        search_keywords = self.config.get('search_keywords', ['order'])
        all_dockets = []

        for keyword in search_keywords:
            dockets = self.search_orders(keyword)
            all_dockets.extend(dockets)

        # Get unique dockets
        unique_dockets = list(set(all_dockets))

        if not unique_dockets:
            print("No dockets found. Exiting.")
            return

        # Step 2: Randomly shuffle to get random dockets
        random.shuffle(unique_dockets)

        print(f"\nProcessing {len(unique_dockets)} unique dockets...")

        # Step 3: Process dockets until we have enough orders
        orders_collected = 0
        docket_index = 0

        while orders_collected < num_orders and docket_index < len(unique_dockets):
            docket = unique_dockets[docket_index]
            docket_index += 1

            print(f"\n[{docket_index}/{len(unique_dockets)}] Processing docket: {docket}")

            # Get case details
            case_data = self.get_case_details(docket)
            if not case_data:
                continue

            # Filter for court orders
            orders = self.filter_court_orders(case_data)

            if not orders:
                print(f"  No court orders found in docket {docket}")
                continue

            print(f"  Found {len(orders)} court order(s)")

            # Download orders from this docket
            for order in orders:
                if orders_collected >= num_orders:
                    break

                success = self.download_document(
                    order['docket_number'],
                    order['docket_entry_id'],
                    order
                )

                if success:
                    orders_collected += 1
                    print(f"  Progress: {orders_collected}/{num_orders}")

        # Print summary
        self._print_summary()

    def _print_summary(self):
        """Print extraction summary statistics."""
        duration = (datetime.now() - self.stats['start_time']).total_seconds()

        print("\n" + "="*50)
        print("EXTRACTION COMPLETE")
        print("="*50)
        print(f"Orders downloaded: {self.stats['orders_downloaded']}")
        print(f"Total API calls: {self.stats['api_calls']}")
        print(f"Errors: {self.stats['errors']}")
        print(f"Duration: {duration:.1f} seconds")
        print(f"Output directory: {self.output_dir.absolute()}")
        print("="*50)


def load_config(config_file: str = 'config.json') -> Dict:
    """Load configuration from file or use defaults."""

    default_config = {
        'num_orders': 10,
        'rate_limit_delay': 1.0,
        'output_dir': 'downloads',
        'search_keywords': ['order']
    }

    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                user_config = json.load(f)
                default_config.update(user_config)
                print(f"Loaded configuration from {config_file}")
        except Exception as e:
            print(f"Error loading config file: {e}")
            print("Using default configuration")
    else:
        print(f"Config file not found. Using defaults.")

    return default_config


def main():
    """Main entry point."""
    # Load configuration
    config = load_config()

    # Allow command-line override of num_orders
    import sys
    if len(sys.argv) > 1:
        try:
            config['num_orders'] = int(sys.argv[1])
        except ValueError:
            print(f"Invalid number: {sys.argv[1]}")
            print("Usage: python dawson_extractor.py [num_orders]")
            sys.exit(1)

    # Create extractor and run
    extractor = DAWSONExtractor(config)
    extractor.extract_orders(config['num_orders'])


if __name__ == '__main__':
    main()
