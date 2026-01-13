# DAWSON Document Extractor

Efficiently extracts court documents (orders, closings, dismissals, etc.) from the DAWSON (U.S. Tax Court) public API system.

## Features

- **Document Type Discovery**: Query the API to discover all available document types
- **Exact or Substring Matching**: Choose precise type matching or flexible substring matching
- **Minimum Per Type**: Ensure balanced extraction with minimum counts per document type
- **API Environment Switching**: Seamlessly switch between blue/green API environments
- **Incremental Downloads**: Automatically skips already downloaded documents
- **Random Sampling**: Pulls documents from random dockets to ensure variety
- **Rate Limiting**: Built-in delays to respect the DAWSON API
- **Metadata Tracking**: Saves JSON metadata alongside each PDF

## Prerequisites

- Python 3.7 or higher
- Internet connection

## Installation

1. Clone or download this repository

2. Create a virtual environment and install dependencies:
```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

3. Create your configuration file:
```bash
cp config.json.example config.json
```

4. Edit `config.json` to customize document types and other settings

## Usage

### Basic Usage

```bash
# Download documents using config.json settings
./venv/bin/python dawson_extractor.py

# Download a specific number of documents
./venv/bin/python dawson_extractor.py 50
```

### Document Type Discovery

Before downloading, discover what document types exist in DAWSON:

```bash
# Query API and catalog all document types
./venv/bin/python dawson_extractor.py --discover

# List discovered document types
./venv/bin/python dawson_extractor.py --list-types
```

This creates `document_types_catalog.json` with all available types and their frequencies, enabling precise filtering with exact matching.

### Configuration

Edit `config.json` to customize behavior:

```json
{
  "num_orders": 100,
  "document_types": [
    "Order of Dismissal for Lack of Jurisdiction",
    "Order and Decision",
    "Order of Dismissal"
  ],
  "match_mode": "exact",
  "min_per_type": 5,
  "api_environment": "green",
  "rate_limit_delay": 1.0,
  "output_dir": "downloads",
  "search_keywords": ["dismissal", "decision"]
}
```

**Configuration Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `num_orders` | Total documents to download (can override via CLI) | 10 |
| `document_types` | List of document types to filter | `["Order"]` |
| `match_mode` | `"exact"` for precise matching, `"substring"` for partial matching | `"substring"` |
| `min_per_type` | Minimum documents required per type (0 to disable) | 0 |
| `api_environment` | `"green"` or `"blue"` - switch if one is down | `"green"` |
| `rate_limit_delay` | Seconds between API requests | 1.0 |
| `output_dir` | Base directory for downloads | `"downloads"` |
| `search_keywords` | Keywords for API search (should match document_types) | `["order"]` |

### Matching Modes

**Substring matching** (default): Flexible matching where "dismissal" matches "Order of Dismissal", "Order of Dismissal for Lack of Jurisdiction", etc.

**Exact matching**: Precise matching using exact type names from the API. Run `--discover` first to see available types, then use exact names in `document_types`.

### Minimum Per Type

Set `min_per_type` to ensure balanced extraction. The tool will prioritize under-represented types until all minimums are met, then fill the remainder randomly.

Example: With 4 document types and `min_per_type: 5`, the first 20 downloads will ensure at least 5 of each type.

## How It Works

1. **Search Phase**: Queries the DAWSON order-search API with configured keywords
2. **Random Sampling**: Shuffles docket numbers for variety
3. **Filtering**: For each docket, filters for matching document types (public, unsealed)
4. **Priority Download**: If `min_per_type` is set, prioritizes under-represented types
5. **Download**: Fetches PDFs with rate limiting, saves metadata JSON alongside
6. **Deduplication**: Skips documents already in any subfolder of output directory

## Output Structure

Each run creates a timestamped subfolder:

```
downloads/
├── order_of_dismissal_2024-01-15_143022/
│   ├── 12345-20_uuid_2024-01-15.pdf
│   ├── 12345-20_uuid_2024-01-15.json
│   └── ...
└── order_and_decision_2024-01-16_091500/
    ├── 67890-21_uuid_2024-02-20.pdf
    ├── 67890-21_uuid_2024-02-20.json
    └── ...
```

Each PDF has an accompanying JSON file with metadata:
- Docket number
- Document type
- Filed date
- Description

## API Endpoints

The tool uses two API environments (configurable via `api_environment`):
- `https://public-api-green.dawson.ustaxcourt.gov` (default)
- `https://public-api-blue.dawson.ustaxcourt.gov`

Endpoints:
- `GET /public-api/order-search` - Search for court documents
- `GET /public-api/cases/{docketNumber}` - Retrieve case details
- `GET /public-api/{docketNumber}/{key}/public-document-download-url` - Get download URL

## Troubleshooting

**No documents found:**
- Run `--discover` to see available document types
- Use exact type names with `match_mode: "exact"`
- Try switching `api_environment` between "green" and "blue"

**API errors (500):**
- One API environment may be down for deployment
- Switch `api_environment` in config.json

**Too many errors:**
- Increase `rate_limit_delay` to 2.0 or higher
- Check internet connection

## Legal & Ethical Considerations

- This tool only accesses **public** court records
- Be respectful of the DAWSON system with appropriate rate limiting
- Intended for research, educational, and legitimate legal purposes
- The DAWSON system is operated by the U.S. Tax Court

## Resources

- DAWSON System: https://www.ustaxcourt.gov/dawson/
- DAWSON GitHub Repository: https://github.com/ustaxcourt/ef-cms
- U.S. Tax Court: https://www.ustaxcourt.gov/

## License

This tool is provided as-is for educational and research purposes.
