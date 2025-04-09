# the key where we store our metadata in the database as JSON.
# If you change this, you must also change it in the frontend.
# For this, it's best to look for the current string and replace it.
# This is in an extra file so that the import works and does not cause a circular import.
EXTRA_MIDDLEWARE_METADATA_KEY = "middleware_metadata"

# Configuration for the GeminiLoader
LITELLM_GEMINI_NAME = "gemini-2.0-flash"
GEMINI_PDF_EXCTRACTION_PROMPT = """
These are pages from a PDF document. Extract all text content while preserving the structure.
Pay special attention to tables, columns, headers, and any structured content and accurately
represent the structure in correct markdown.
Maintain paragraph breaks and formatting.

For tables:
1. Maintain the table structure using markdown table format
2. Preserve all column headers and row labels
3. Ensure numerical data is accurately captured

For multi-column layouts:
1. Process columns from left to right
2. Clearly separate content from different columns

For charts and graphs:
1. Clearly mark that a chart or graph is present
2. Describe the chart type

Preserve all headers, footers, and page numbers.
Ignore footnotes.

Do not wrap the output text in ```markdown ... ``` wrappers. Assume this being done for you.

"""
