# DAWSON Court Order Extractor

Efficiently extracts court order PDFs from the DAWSON (U.S. Tax Court) public API system.

## Features

- **Efficient API Usage**: Built-in rate limiting to avoid overloading the DAWSON API
- **Random Sampling**: Pulls orders from random dockets to ensure variety
- **Configurable**: Easy-to-use configuration file for customization
- **Metadata Tracking**: Saves metadata alongside each PDF for reference
- **Progress Monitoring**: Real-time progress updates and summary statistics
- **Error Handling**: Robust error handling with detailed logging

## Prerequisites

- Python 3.7 or higher
- Internet connection

## Installation

1. Clone or download this repository

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

Run with default settings (10 court orders):
```bash
python dawson_extractor.py
```

### Specify Number of Orders

Download a specific number of court orders:
```bash
python dawson_extractor.py 25
```

This will download 25 court order PDFs from random dockets.

### Configuration

Edit `config.json` to customize behavior:

```json
{
  "num_orders": 10,
  "rate_limit_delay": 1.0,
  "output_dir": "downloads",
  "search_keywords": ["order"]
}
```

**Configuration Options:**

- `num_orders`: Default number of orders to download (can be overridden via command line)
- `rate_limit_delay`: Delay in seconds between API requests (default: 1.0)
  - Increase this value to be more conservative (e.g., 2.0 for 2 seconds)
  - Decrease for faster extraction (not recommended below 0.5)
- `output_dir`: Directory where PDFs and metadata will be saved
- `search_keywords`: List of keywords to search for orders (e.g., ["order", "decision"])

## How It Works

The extractor uses an efficient multi-step process:

1. **Search Phase**: Searches for court orders using the DAWSON public API order-search endpoint
2. **Random Sampling**: Randomly shuffles docket numbers to ensure variety
3. **Filtering**: For each docket, retrieves case details and filters for:
   - Documents classified as "court orders"
   - Public (not sealed) documents
   - PDF format documents
4. **Download**: Downloads the filtered documents with rate limiting
5. **Metadata**: Saves JSON metadata alongside each PDF for reference

## Output Structure

Downloaded files are saved in the configured output directory:

```
downloads/
├── 12345-20_docketEntryId_2024-01-15.pdf
├── 12345-20_docketEntryId_2024-01-15.json
├── 67890-21_docketEntryId_2024-02-20.pdf
└── 67890-21_docketEntryId_2024-02-20.json
```

Each PDF has an accompanying JSON file with metadata:
- Docket number
- Document type
- Filed date
- Description

## Rate Limiting & API Etiquette

This tool implements rate limiting to be respectful of the DAWSON public API:

- Default delay: 1 second between API requests
- Configurable via `rate_limit_delay` in config.json
- Uses persistent session for connection pooling efficiency
- Includes proper User-Agent header

**Recommendations:**
- For large extractions (100+ orders), consider increasing `rate_limit_delay` to 2.0 seconds
- Run during off-peak hours if extracting significant amounts of data
- Monitor for any API errors and adjust delay if needed

## Statistics & Monitoring

The tool provides real-time feedback:
- Progress indicators showing current docket and order count
- Summary statistics at completion:
  - Total orders downloaded
  - Total API calls made
  - Error count
  - Total duration
  - Output directory location

## Error Handling

The tool gracefully handles common errors:
- Network timeouts
- Missing documents
- Sealed or restricted documents
- Invalid docket numbers
- API rate limit errors

Errors are logged but don't stop the extraction process.

## API Endpoints Used

This tool uses the following DAWSON public API endpoints:

- `GET /public-api/order-search` - Search for court orders
- `GET /public-api/cases/{docketNumber}` - Retrieve case details
- `GET /public-api/{docketNumber}/{key}/public-document-download-url` - Get document download URL

## Limitations

- Only accesses **public** documents (sealed documents are filtered out)
- Requires documents to be properly classified in the system
- Subject to DAWSON API availability and rate limits
- Does not authenticate, so only public data is accessible

## Troubleshooting

**No documents found:**
- Try different search keywords in `config.json`
- Check if the DAWSON API is accessible: https://api.dawson.ustaxcourt.gov/public-api/health

**Too many errors:**
- Increase `rate_limit_delay` in config.json
- Check internet connection
- Verify DAWSON API status

**Slow downloads:**
- This is expected with rate limiting enabled
- Decrease `rate_limit_delay` at your own risk
- Consider running overnight for large extractions

## Legal & Ethical Considerations

- This tool only accesses **public** court records
- Be respectful of the DAWSON system and implement appropriate rate limiting
- Intended for research, educational, and legitimate legal purposes
- Follow all applicable laws and terms of service
- The DAWSON system is operated by the U.S. Tax Court

## Resources

- DAWSON System: https://www.ustaxcourt.gov/dawson/
- DAWSON GitHub Repository: https://github.com/ustaxcourt/ef-cms
- U.S. Tax Court: https://www.ustaxcourt.gov/

## License

This tool is provided as-is for educational and research purposes.

## Contributing

Contributions are welcome! Please ensure any modifications maintain:
- Proper rate limiting
- Error handling
- Clear documentation
- Respectful API usage

## Support

For issues with:
- This extractor tool: Open an issue in this repository
- DAWSON system itself: Contact dawson.support@ustaxcourt.gov
- DAWSON API: See https://github.com/ustaxcourt/ef-cms
