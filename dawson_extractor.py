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

    API_ENVIRONMENTS = {
        'blue': "https://public-api-blue.dawson.ustaxcourt.gov",
        'green': "https://public-api-green.dawson.ustaxcourt.gov"
    }

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

        # Set API environment (blue or green)
        api_env = config.get('api_environment', 'green')
        self.base_url = self.API_ENVIRONMENTS.get(api_env, self.API_ENVIRONMENTS['green'])

        # Create output directory with run-specific subfolder
        base_output_dir = Path(config.get('output_dir', 'downloads'))
        base_output_dir.mkdir(exist_ok=True)

        # Create subfolder named with document types and timestamp
        doc_types = config.get('document_types', ['Order'])
        timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')

        # Use shorter name if too many types (avoid filesystem name length limits)
        if len(doc_types) > 5:
            run_folder_name = f"batch_{len(doc_types)}_types_{timestamp}"
        else:
            types_str = '_'.join(t.lower().replace(' ', '_') for t in doc_types)
            run_folder_name = f"{types_str}_{timestamp}"

        self.base_output_dir = base_output_dir
        self.output_dir = base_output_dir / run_folder_name
        self.output_dir.mkdir(exist_ok=True)

        # Statistics
        self.stats = {
            'orders_downloaded': 0,
            'orders_skipped': 0,
            'api_calls': 0,
            'errors': 0,
            'start_time': datetime.now()
        }

        # Track existing documents to avoid duplicates
        self.existing_docs = self._scan_existing_documents()

    def _scan_existing_documents(self) -> set:
        """Scan all subfolders in base output directory for already downloaded documents."""
        existing = set()
        # Scan all subfolders and root for existing PDFs
        for pdf_file in self.base_output_dir.glob("**/*.pdf"):
            # Extract document_id from filename: {docket}_{document_id}_{date}.pdf
            parts = pdf_file.stem.split('_')
            if len(parts) >= 2:
                # Document ID is the second part (UUID format)
                doc_id = parts[1]
                existing.add(doc_id)
        if existing:
            print(f"Found {len(existing)} existing documents in {self.base_output_dir}")
        return existing

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
        url = f"{self.base_url}{endpoint}"
        self.stats['api_calls'] += 1

        try:
            self._rate_limit()
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            # Try to get more detailed error message from response
            error_detail = ""
            try:
                error_detail = f": {e.response.text}"
            except:
                pass
            print(f"HTTP Error for {endpoint}: {e}{error_detail}")
            self.stats['errors'] += 1
            return None
        except requests.exceptions.RequestException as e:
            print(f"Error making request to {endpoint}: {e}")
            self.stats['errors'] += 1
            return None

    def search_orders(self, keyword: str = "order") -> List[str]:
        """
        Search for court documents and return unique docket numbers.

        Args:
            keyword: Search keyword for documents

        Returns:
            List of unique docket numbers
        """
        print(f"Searching for documents with keyword: '{keyword}'...")

        params = {
            "keyword": keyword,
            "dateRange": "allDates",
            "limit": 5000
        }
        data = self._make_request("/public-api/order-search", params=params)

        if not data:
            print("Failed to retrieve search results")
            return []

        # Extract unique docket numbers from results
        docket_numbers = set()
        results = data.get('results', [])

        # Get allowed document types from config
        allowed_types = self.config.get('document_types', ['Order'])

        for item in results:
            docket_number = item.get('docketNumber')
            document_type = item.get('documentType', '')

            # Check if document type matches
            if docket_number and self._matches_document_type(document_type, allowed_types):
                docket_numbers.add(docket_number)

        print(f"Found {len(docket_numbers)} unique dockets with matching documents")
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

    def _matches_document_type(self, document_type: str, allowed_types: List[str]) -> bool:
        """
        Check if a document type matches the allowed types.

        Args:
            document_type: The document type to check
            allowed_types: List of allowed type patterns

        Returns:
            True if document_type matches any allowed type
        """
        match_mode = self.config.get('match_mode', 'substring')

        if match_mode == 'exact':
            return any(
                doc_type.lower() == document_type.lower()
                for doc_type in allowed_types
            )
        else:  # substring (default)
            return any(
                doc_type.lower() in document_type.lower()
                for doc_type in allowed_types
            )

    def filter_court_orders(self, case_data: Dict) -> List[Dict]:
        """
        Filter docket entries for configured document types.

        Args:
            case_data: Case details from API

        Returns:
            List of matching document entries
        """
        documents = []

        # Get allowed document types from config
        allowed_types = self.config.get('document_types', ['Order'])

        docket_entries = case_data.get('docketEntries', [])
        for entry in docket_entries:
            document_type = entry.get('documentType', '')
            is_sealed = entry.get('isSealed', False)
            document_id = entry.get('docketEntryId')

            # Check if document type matches
            matches_type = self._matches_document_type(document_type, allowed_types)

            # Only include public documents that match configured types
            if matches_type and not is_sealed and document_id:
                documents.append({
                    'docket_number': case_data.get('docketNumber'),
                    'docket_entry_id': document_id,
                    'document_type': document_type,
                    'description': entry.get('description', ''),
                    'filed_date': entry.get('filingDate', 'Unknown')
                })

        return documents

    def download_document(self, docket_number: str, document_id: str,
                         metadata: Dict) -> str:
        """
        Download a court order PDF.

        Args:
            docket_number: Case docket number
            document_id: Document entry ID
            metadata: Document metadata for naming

        Returns:
            'downloaded' if successful, 'skipped' if already exists, 'error' if failed
        """
        # Check if document already exists
        if document_id in self.existing_docs:
            self.stats['orders_skipped'] += 1
            return 'skipped'

        # Get download URL
        endpoint = f"/public-api/{docket_number}/{document_id}/public-document-download-url"
        response = self._make_request(endpoint)

        if not response or 'url' not in response:
            print(f"Failed to get download URL for {docket_number}/{document_id}")
            return 'error'

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

            # Add to existing docs set to prevent re-downloading in same session
            self.existing_docs.add(document_id)

            # Save metadata
            metadata_file = filepath.with_suffix('.json')
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)

            return 'downloaded'

        except Exception as e:
            print(f"Error downloading document: {e}")
            self.stats['errors'] += 1
            return 'error'

    def extract_orders(self, num_orders: int):
        """
        Main extraction process (incremental - skips existing documents).

        Args:
            num_orders: Total number of documents desired (will download delta)
        """
        existing_count = len(self.existing_docs)
        needed = max(0, num_orders - existing_count)
        min_per_type = self.config.get('min_per_type', 0)
        document_types = self.config.get('document_types', ['Order'])

        # Track counts per document type
        type_counts = {doc_type: 0 for doc_type in document_types}

        print(f"\n=== DAWSON Document Extractor ===")
        print(f"Target: {num_orders} total documents")
        print(f"Document types: {', '.join(document_types)}")
        if min_per_type > 0:
            print(f"Minimum per type: {min_per_type}")
        print(f"Existing: {existing_count} documents")
        print(f"To download: {needed} new documents")
        print(f"Output: {self.output_dir}")
        print(f"Rate limit: {self.config.get('rate_limit_delay', 1.0)}s between requests\n")

        if needed == 0:
            print("Already have enough documents. Nothing to download.")
            self._print_summary()
            return

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

        def needs_type(doc_type: str) -> bool:
            """Check if we still need more of this document type."""
            if min_per_type <= 0:
                return True
            # Find matching configured type (case-insensitive)
            for configured_type in document_types:
                if configured_type.lower() == doc_type.lower():
                    return type_counts.get(configured_type, 0) < min_per_type
            return True

        def all_minimums_met() -> bool:
            """Check if all document types have met their minimums."""
            if min_per_type <= 0:
                return True
            return all(count >= min_per_type for count in type_counts.values())

        while orders_collected < needed and docket_index < len(unique_dockets):
            docket = unique_dockets[docket_index]
            docket_index += 1

            print(f"\n[{docket_index}/{len(unique_dockets)}] Processing docket: {docket}")

            # Get case details
            case_data = self.get_case_details(docket)
            if not case_data:
                continue

            # Filter for configured document types
            documents = self.filter_court_orders(case_data)

            if not documents:
                print(f"  No matching documents found in docket {docket}")
                continue

            # If minimums not met, prioritize under-represented types
            if not all_minimums_met():
                documents = [doc for doc in documents if needs_type(doc['document_type'])]
                if not documents:
                    continue

            print(f"  Found {len(documents)} matching document(s)")

            # Download documents from this docket
            for order in documents:
                if orders_collected >= needed:
                    break

                # Skip if we don't need this type anymore (when filling minimums)
                if not all_minimums_met() and not needs_type(order['document_type']):
                    continue

                result = self.download_document(
                    order['docket_number'],
                    order['docket_entry_id'],
                    order
                )

                if result == 'downloaded':
                    orders_collected += 1
                    # Track type counts
                    for configured_type in document_types:
                        if configured_type.lower() == order['document_type'].lower():
                            type_counts[configured_type] = type_counts.get(configured_type, 0) + 1
                            break
                    print(f"  Progress: {orders_collected}/{needed} new downloads")
                elif result == 'skipped':
                    pass  # Already exists, silently skip

        # Print summary with type breakdown
        self._print_summary(type_counts)

    def _print_summary(self, type_counts: Optional[Dict[str, int]] = None):
        """Print extraction summary statistics."""
        duration = (datetime.now() - self.stats['start_time']).total_seconds()
        total_docs = len(self.existing_docs)

        print("\n" + "="*50)
        print("EXTRACTION COMPLETE")
        print("="*50)
        print(f"New documents downloaded: {self.stats['orders_downloaded']}")
        print(f"Documents skipped (already existed): {self.stats['orders_skipped']}")
        print(f"Total documents in library: {total_docs}")
        if type_counts:
            print(f"\nDownloaded by type:")
            for doc_type, count in type_counts.items():
                print(f"  {count:4d}  {doc_type}")
        print(f"Total API calls: {self.stats['api_calls']}")
        print(f"Errors: {self.stats['errors']}")
        print(f"Duration: {duration:.1f} seconds")
        print(f"Output directory: {self.output_dir.absolute()}")
        print("="*50)

    def discover_document_types(self) -> Dict[str, int]:
        """
        Query API with broad searches to discover all document types.

        Returns:
            Dict mapping document type names to occurrence counts
        """
        print("\n=== DAWSON Document Type Discovery ===\n")

        # Keywords to search - covers major document categories
        discovery_keywords = [
            "order", "motion", "decision", "opinion", "petition",
            "dismissal", "closing", "brief", "memorandum", "notice",
            "stipulation", "response", "reply", "objection", "report"
        ]

        type_counts: Dict[str, int] = {}

        for keyword in discovery_keywords:
            print(f"Searching with keyword: '{keyword}'...")

            params = {
                "keyword": keyword,
                "dateRange": "allDates",
                "limit": 5000
            }
            data = self._make_request("/public-api/order-search", params=params)

            if not data:
                continue

            results = data.get('results', [])
            for item in results:
                doc_type = item.get('documentType', '')
                if doc_type:
                    type_counts[doc_type] = type_counts.get(doc_type, 0) + 1

        # Save catalog
        catalog = {
            "discovered_at": datetime.now().isoformat(),
            "total_types": len(type_counts),
            "types": dict(sorted(type_counts.items(), key=lambda x: -x[1]))
        }

        catalog_path = Path("document_types_catalog.json")
        with open(catalog_path, 'w') as f:
            json.dump(catalog, f, indent=2)

        print(f"\n{'='*50}")
        print(f"DISCOVERY COMPLETE")
        print(f"{'='*50}")
        print(f"Document types found: {len(type_counts)}")
        print(f"Catalog saved to: {catalog_path.absolute()}")
        print(f"Total API calls: {self.stats['api_calls']}")
        print(f"\nTop 10 document types:")
        for doc_type, count in list(catalog['types'].items())[:10]:
            print(f"  {count:5d}  {doc_type}")
        print(f"{'='*50}")

        return type_counts

    def list_document_types(self):
        """Display discovered document types from catalog."""
        catalog_path = Path("document_types_catalog.json")

        if not catalog_path.exists():
            print("No document type catalog found.")
            print("Run with --discover first to catalog document types from the API.")
            return

        with open(catalog_path, 'r') as f:
            catalog = json.load(f)

        print(f"\n=== DAWSON Document Types ===")
        print(f"Discovered: {catalog.get('discovered_at', 'Unknown')}")
        print(f"Total types: {catalog.get('total_types', 0)}")
        print(f"\n{'Count':>6}  Type")
        print("-" * 50)

        for doc_type, count in catalog.get('types', {}).items():
            print(f"{count:6d}  {doc_type}")

        print("-" * 50)
        print("\nTo use exact matching, add types to config.json document_types list")
        print("and set match_mode to 'exact'.")


def load_config(config_file: str = 'config.json') -> Dict:
    """Load configuration from file or use defaults."""

    default_config = {
        'num_orders': 10,
        'document_types': ['Order'],
        'match_mode': 'substring',
        'api_environment': 'green',
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
    import argparse

    parser = argparse.ArgumentParser(
        description='DAWSON Court Document Extractor',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s                  Download documents using config.json settings
  %(prog)s 25               Download 25 documents
  %(prog)s --discover       Discover and catalog all document types from API
  %(prog)s --list-types     List all discovered document types
        '''
    )
    parser.add_argument('num_orders', nargs='?', type=int,
                        help='Number of documents to download (overrides config)')
    parser.add_argument('--discover', action='store_true',
                        help='Discover document types from API and save to catalog')
    parser.add_argument('--list-types', action='store_true',
                        help='List all discovered document types')

    args = parser.parse_args()

    # Load configuration
    config = load_config()

    # Override num_orders if provided
    if args.num_orders is not None:
        config['num_orders'] = args.num_orders

    # Create extractor
    extractor = DAWSONExtractor(config)

    # Handle different modes
    if args.discover:
        extractor.discover_document_types()
    elif args.list_types:
        extractor.list_document_types()
    else:
        extractor.extract_orders(config['num_orders'])


if __name__ == '__main__':
    main()
