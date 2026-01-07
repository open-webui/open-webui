# Docling OCR Page Extraction

This document describes the page extraction feature for Docling OCR integration in Open WebUI, which enables document-level citations with page numbers.

## Overview

The Docling OCR page extraction feature allows Open WebUI to process documents and extract page-level text content with metadata. This enables:
- **Page-specific citations**: Reference specific pages in documents
- **Accurate page numbering**: Display correct page numbers in citations
- **Enhanced searchability**: Search within specific pages of documents
- **Better user experience**: Navigate directly to cited pages

## Configuration

### Environment Variable

Set the following environment variable to enable/disable page extraction:

```bash
DOCLING_EXTRACT_PAGES=true
```

- **Default**: `true`
- **Values**: `true` or `false`

### Web UI Configuration

You can also configure this setting through the Open WebUI admin interface:

1. Navigate to **Settings** → **Retrieval** → **Content Extraction**
2. Find the **Docling** section
3. Toggle **Extract Pages** to enable or disable page extraction
4. Save your changes

## How It Works

### Page Extraction Process

1. **Document Upload**: When a document is uploaded, Open WebUI sends it to the Docling OCR service
2. **Multi-format Processing**: The service processes the document and returns both JSON and markdown formats
3. **Page Parsing**: The JSON format contains structured page information with text provenance
4. **Document Chunking**: Each page becomes a separate document chunk with metadata
5. **Vector Storage**: Chunks are stored in the vector database with page metadata

### Metadata Structure

Each page-level document includes the following metadata:

```json
{
  "page": 0,              // 0-based page index
  "page_label": 1,        // 1-based page label for display
  "total_pages": 10,      // Total number of pages in document
  "file_name": "doc.pdf", // Original filename
  "file_size": 1024000,   // File size in bytes
  "processing_engine": "docling",
  "content_length": 1500  // Length of page content
}
```

### API Integration

The DoclingLoader class handles the page extraction:

```python
# Initialize with page extraction enabled
loader = DoclingLoader(
    url="http://docling:5001",
    api_key="your-api-key",
    file_path="/path/to/document.pdf",
    extract_pages=True  # Enable page extraction
)

# Load documents (returns list of page-level documents)
documents = loader.load()
```

## Citation Display

When page extraction is enabled, citations in the chat interface will show:

- **Page numbers**: "Page 3 of 10" instead of just the document name
- **Page navigation**: Click to jump to the specific page
- **Contextual information**: Show surrounding page content

### Example Citation

```
[PDF Document: User Manual.pdf - Page 5 of 25]

"The advanced settings panel provides access to configuration options
for power users, including custom themes, API endpoints, and
performance tuning parameters..."
```

## Technical Details

### JSON Format Processing

The page extraction relies on Docling's JSON output format, which includes:

- **Page information**: Dimensions, orientation, and page numbers
- **Text provenance**: Which text belongs to which page
- **Bounding boxes**: Position information for text elements
- **Content hierarchy**: Structure information for better context

### Fallback Mechanism

If page extraction fails or is disabled, the system falls back to:

1. **Single document mode**: Treat the entire document as one text block
2. **Markdown processing**: Use the markdown output format
3. **Basic metadata**: Include only filename and processing engine

### Error Handling

The system gracefully handles various error scenarios:

- **API errors**: Falls back to markdown processing
- **Malformed JSON**: Logs warning and continues with fallback
- **Missing page data**: Creates empty page documents or skips
- **Network issues**: Retries with exponential backoff

## Performance Considerations

### Processing Time

- **Page extraction**: Adds ~10-20% processing time for typical documents
- **Large documents**: May take longer for documents with many pages
- **Caching**: Results are cached to avoid reprocessing

### Storage Impact

- **Metadata overhead**: ~200 bytes per page for metadata
- **Document chunks**: More chunks increases vector database size
- **Memory usage**: Slightly higher memory usage during processing

### Optimization Tips

1. **Enable for relevant documents**: Use for documents where page citations matter
2. **Monitor storage**: Watch vector database size with large document collections
3. **Configure timeouts**: Adjust API timeouts for large documents
4. **Use caching**: Enable caching to improve performance

## Troubleshooting

### Common Issues

#### Page Numbers Not Showing

**Symptoms**: Citations show document name but no page numbers.

**Causes**:
- `DOCLING_EXTRACT_PAGES` is set to `false`
- Docling API returned error or malformed JSON
- Document type doesn't support page extraction

**Solutions**:
1. Check the configuration setting
2. Review the application logs for errors
3. Verify Docling service is running and accessible
4. Test with a simple PDF document

#### Incorrect Page Numbers

**Symptoms**: Page numbers are wrong or don't match the original document.

**Causes**:
- Document has complex page numbering (Roman numerals, etc.)
- Front matter affecting page count
- Docling OCR processing issues

**Solutions**:
1. Check if the document has non-standard page numbering
2. Verify the original document page layout
3. Consider using the page label instead of page index for display

#### Processing Failures

**Symptoms**: Documents fail to process or show errors.

**Causes**:
- Docling API not accessible
- API key authentication issues
- Network connectivity problems
- Document format not supported

**Solutions**:
1. Verify Docling service status: `curl http://docling:5001/health`
2. Check API key configuration
3. Test network connectivity to Docling service
4. Review document format compatibility

### Debugging

Enable debug logging to troubleshoot issues:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Key log messages to watch for:
- `Docling extracted X pages from document`
- `Failed to extract pages from Docling JSON`
- `Error calling Docling API`

## API Reference

### DoclingLoader Class

```python
class DoclingLoader:
    def __init__(self, url, api_key=None, file_path=None, 
                 mime_type=None, params=None, extract_pages=True):
        """
        Initialize the DoclingLoader.
        
        Args:
            url (str): Base URL of the Docling service
            api_key (str, optional): API key for authentication
            file_path (str): Path to the document file
            mime_type (str, optional): MIME type of the document
            params (dict, optional): Additional parameters for the Docling API
            extract_pages (bool): Whether to extract individual pages
        """
    
    def load(self) -> list[Document]:
        """Load and process the document."""
    
    def _extract_pages_from_json(self, json_content: dict) -> list[Document]:
        """Extract page-level documents from JSON content."""
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `DOCLING_EXTRACT_PAGES` | bool | true | Enable page-level extraction |
| `DOCLING_SERVER_URL` | str | http://docling:5001 | Docling service URL |
| `DOCLING_API_KEY` | str | "" | API key for authentication |
| `DOCLING_PARAMS` | dict | {} | Additional API parameters |

## Migration Guide

### Upgrading from Previous Versions

1. **No breaking changes**: Existing configurations continue to work
2. **New feature**: Page extraction is enabled by default
3. **Configuration**: Add new environment variable if you want to disable it

### Disabling Page Extraction

If you encounter issues or want to revert to the previous behavior:

```bash
# Set environment variable
export DOCLING_EXTRACT_PAGES=false

# Or update through the UI
# Settings → Retrieval → Content Extraction → Docling → Extract Pages: Off
```

## Contributing

### Development Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Run tests: `python -m pytest tests/test_docling_page_extraction.py`
3. Start development server: `python -m open_webui.main`

### Testing

Run the test suite to verify functionality:

```bash
# Run all tests
python -m pytest tests/test_docling_page_extraction.py -v

# Run specific test
python -m pytest tests/test_docling_page_extraction.py::TestDoclingPageExtraction::test_extract_pages_from_json_success -v
```

### Code Style

Follow the existing code style and conventions:
- Use type hints for all function signatures
- Add comprehensive docstrings
- Include error handling and logging
- Write unit tests for new features

## Support

For issues or questions about the Docling page extraction feature:

1. Check the [troubleshooting guide](#troubleshooting)
2. Review the [Open WebUI documentation](https://docs.openwebui.com/)
3. Search [GitHub issues](https://github.com/open-webui/open-webui/issues)
4. Create a new issue with detailed information

## Changelog

### Version [Current]

- **Added**: Page extraction for Docling OCR
- **Added**: Configuration option `DOCLING_EXTRACT_PAGES`
- **Added**: Page metadata in document chunks
- **Added**: Unit tests for page extraction
- **Added**: Documentation and troubleshooting guide

### Future Enhancements

- Support for custom page numbering schemes
- Enhanced page preview in citations
- Page-level search within documents
- Export页面的批注和标记功能