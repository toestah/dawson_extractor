# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DAWSON Document Extractor - A Python tool for extracting court documents (orders, closings, dismissals, etc.) from the DAWSON (U.S. Tax Court) public API system.

## Commands

### Setup
```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
cp config.json.example config.json
```

### Run
```bash
# Download using config.json settings
./venv/bin/python dawson_extractor.py

# Override document count
./venv/bin/python dawson_extractor.py 50

# Discover all document types from API
./venv/bin/python dawson_extractor.py --discover

# List discovered document types
./venv/bin/python dawson_extractor.py --list-types
```

## Architecture

Single-file Python application (`dawson_extractor.py`) with no tests.

### Key Class: `DAWSONExtractor`

**Core Methods:**
- `_make_request()` - API calls with rate limiting and error handling
- `_matches_document_type()` - Supports `substring` or `exact` matching via `match_mode` config
- `search_orders()` - Queries order-search API, returns docket numbers
- `filter_court_orders()` - Filters docket entries by configured document types
- `download_document()` - Fetches PDF, saves with JSON metadata
- `extract_orders()` - Main extraction loop with `min_per_type` support

**Discovery Methods:**
- `discover_document_types()` - Catalogs all types from API to `document_types_catalog.json`
- `list_document_types()` - Displays discovered types from catalog

**Utility Methods:**
- `_scan_existing_documents()` - Scans all subfolders for existing document IDs (deduplication)
- `_print_summary()` - Shows extraction stats with per-type breakdown

### API Endpoints

Uses `api_environment` config (`green` default, `blue` fallback):
- `https://public-api-green.dawson.ustaxcourt.gov`
- `https://public-api-blue.dawson.ustaxcourt.gov`

Endpoints:
- `GET /public-api/order-search` - Search documents by keyword
- `GET /public-api/cases/{docketNumber}` - Get case details and docket entries
- `GET /public-api/{docketNumber}/{key}/public-document-download-url` - Get download URL

### Configuration (`config.json`)

Settings loaded via `load_config()` with fallback defaults:

| Key | Description | Default |
|-----|-------------|---------|
| `num_orders` | Target document count | 10 |
| `document_types` | List of types to filter | `["Order"]` |
| `match_mode` | `"substring"` or `"exact"` | `"substring"` |
| `min_per_type` | Minimum docs per type (0=disabled) | 0 |
| `api_environment` | `"green"` or `"blue"` | `"green"` |
| `rate_limit_delay` | Seconds between API calls | 1.0 |
| `output_dir` | Base directory for downloads | `"downloads"` |
| `search_keywords` | Keywords for order-search API | `["order"]` |

### Output Structure

Each run creates a timestamped subfolder: `{output_dir}/{types}_{timestamp}/`

Files: `{docket}_{documentId}_{date}.pdf` with matching `.json` metadata

### Key Files

- `dawson_extractor.py` - Main application
- `config.json` - User configuration (gitignored)
- `config.json.example` - Configuration template
- `document_types_catalog.json` - Discovery output (gitignored)
