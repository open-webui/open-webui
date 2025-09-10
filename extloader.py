import fitz  # PyMuPDF
import base64
import logging
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the FastAPI application
app = FastAPI(
    title="External Content Processing Engine",
    description="An API to extract text and images from documents for OpenWebUI.",
    version="1.0.0"
)

@app.put("/process")
async def process_document(request: Request):
    """
    Processes an uploaded document to extract text and, optionally, images.

    This endpoint expects the raw binary data of a file in the request body.
    It reads custom headers to determine how to process the file.

    Headers:
        - X-Filename (str): The original name of the file.
        - X-Extract-Images (str): Should be 'true' to enable image extraction.

    Returns:
        JSONResponse: A JSON object containing the extracted content.
    """
    logger.info("Received request to /process endpoint.")
    logger.info("=== DOCUMENT PROCESSING REQUEST RECEIVED ===")
    logger.info(f"All headers: {dict(request.headers)}")
    # Get file data and headers from the incoming request
    file_bytes = await request.body()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file content received."
        )

    filename = request.headers.get("x-filename", "unknown_file")
    extract_images_flag = request.headers.get("x-extract-images", "false").lower()
    logger.info(f"Raw X-Extract-Images header: {request.headers.get('x-extract-images')}")
    logger.info(f"Processed extract_images_flag: {extract_images_flag}")
    logger.info(f"Will extract images: {extract_images_flag == 'true'}")

    logger.info(f"Processing file: {filename}")
    logger.info(f"Image extraction enabled: {extract_images_flag == 'true'}")

    base64_images = []
    full_text = ""

    try:
        # Open the PDF from the in-memory byte stream
        doc = fitz.open(stream=file_bytes, filetype="pdf")

        # 1. Extract all text content from the document
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            full_text += page.get_text() + "\n\n"

        # 2. Extract images if the flag is set
        if extract_images_flag == 'true':
            logger.info("Starting image extraction...")
            # Iterate through all objects in the PDF to find images
            for page_num in range(len(doc)):
                image_list = doc.get_page_images(page_num, full=True)
                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]

                    # Encode the image bytes to a Base64 string with a data URI prefix
                    encoded_string = base64.b64encode(image_bytes).decode("utf-8")
                    data_uri = f"data:image/{image_ext};base64,{encoded_string}"
                    base64_images.append(data_uri)
            logger.info(f"Extracted {len(base64_images)} images.")

        # Prepare the final JSON response payload
        response_payload = {
            "page_content": full_text.strip(),
            "metadata": {
                "source": filename,
                "page_count": doc.page_count,
            },
            "images": base64_images,
        }

        return JSONResponse(content=response_payload)

    except Exception as e:
        logger.error(f"Failed to process PDF '{filename}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing the PDF: {e}",
        )

@app.get("/")
def read_root():
    """A simple root endpoint to confirm the server is running."""
    return {"status": "ok", "message": "Content Processing Engine is running."}
