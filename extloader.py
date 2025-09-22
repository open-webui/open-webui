import fitz  # PyMuPDF
import base64
import logging
import os
import tempfile
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from langchain_community.document_loaders import AzureAIDocumentIntelligenceLoader
from azure.identity import DefaultAzureCredential

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
    """
    logger.info("Received request to /process endpoint.")
    logger.info("=== DOCUMENT PROCESSING REQUEST RECEIVED ===")
    logger.info(f"All headers: {dict(request.headers)}")
    
    file_bytes = await request.body()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file content received."
        )

    filename = request.headers.get("x-filename", "unknown_file")
    file_ext = os.path.splitext(filename)[1].lower()
    
    # Extract image flag - EXACTLY like the original working version
    extract_images_flag = request.headers.get("x-extract-images", "false").lower()
    
    # Debug logging
    logger.info(f"=== DEBUG: filename='{filename}', file_ext='{file_ext}'")
    logger.info(f"Raw X-Extract-Images header: {request.headers.get('x-extract-images')}")
    logger.info(f"Processed extract_images_flag: {extract_images_flag}")
    logger.info(f"Will extract images: {extract_images_flag == 'true'}")
    logger.info(f"Will take PDF path: {file_ext == '.pdf'}")
    logger.info(f"File size: {len(file_bytes)} bytes")

    base64_images = []
    full_text = ""
    page_count = 0

    # PDF processing - use original working logic
    if file_ext == ".pdf":
        logger.info("Taking PDF processing path with PyMuPDF")
        try:
            # Open the PDF from the in-memory byte stream - EXACTLY like original
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            page_count = doc.page_count
            
            # 1. Extract all text content from the document - EXACTLY like original
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                full_text += page.get_text() + "\n\n"

            # 2. Extract images if the flag is set - EXACTLY like original
            if extract_images_flag == 'true':
                logger.info("Starting image extraction...")
                # Iterate through all objects in the PDF to find images - EXACTLY like original
                for page_num in range(len(doc)):
                    image_list = doc.get_page_images(page_num, full=True)
                    for img_index, img in enumerate(image_list):
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        image_ext = base_image["ext"]

                        # Encode the image bytes to a Base64 string with a data URI prefix - EXACTLY like original
                        encoded_string = base64.b64encode(image_bytes).decode("utf-8")
                        data_uri = f"data:image/{image_ext};base64,{encoded_string}"
                        base64_images.append(data_uri)
                logger.info(f"Extracted {len(base64_images)} images.")
            else:
                logger.info("No image extraction requested (X-Extract-Images != 'true')")

            doc.close()  # Close the document

        except Exception as e:
            logger.error(f"Failed to process PDF '{filename}': {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An error occurred while processing the PDF: {e}",
            )
            
    # Non-PDF processing - use Azure Document Intelligence
    else:
        logger.info(f"Taking Azure Document Intelligence path for file extension: {file_ext}")
        
        # Azure loader requires a file path, so we save the content to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            temp_file.write(file_bytes)
            temp_file_path = temp_file.name
        
        try:
            api_endpoint = os.getenv("DOCUMENT_INTELLIGENCE_ENDPOINT")
            api_key = os.getenv("DOCUMENT_INTELLIGENCE_KEY")

            if not api_endpoint:
                raise ValueError("DOCUMENT_INTELLIGENCE_ENDPOINT environment variable is not set.")

            if api_key:
                loader = AzureAIDocumentIntelligenceLoader(
                    file_path=temp_file_path,
                    api_endpoint=api_endpoint,
                    api_key=api_key,
                )
            else:
                 # Authenticate using DefaultAzureCredential if no key is provided
                loader = AzureAIDocumentIntelligenceLoader(
                    file_path=temp_file_path,
                    api_endpoint=api_endpoint,
                    azure_credential=DefaultAzureCredential(),
                )
            
            documents = loader.load()
            
            if documents:
                full_text = "\n\n".join([doc.page_content for doc in documents])
                # page_count can be approximated by the number of documents, though it may not be accurate
                page_count = len(documents)
                logger.info(f"Successfully processed document with Azure Document Intelligence. Pages: {page_count}")
            else:
                logger.warning("No content extracted from document with Azure Document Intelligence")
                full_text = ""
                page_count = 0
            
        except Exception as e:
            logger.error(f"Error processing with Azure Document Intelligence: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to process document with Azure: {e}")
        finally:
            try:
                os.remove(temp_file_path) # Clean up the temporary file
            except Exception as cleanup_error:
                logger.warning(f"Failed to clean up temporary file: {cleanup_error}")

    # Prepare the final JSON response payload - EXACTLY like original
    response_payload = {
        "page_content": full_text.strip(),
        "metadata": {
            "source": filename,
            "page_count": page_count,
        },
        "images": base64_images,
    }

    logger.info(f"Returning response with {len(full_text)} chars of text and {len(base64_images)} images")
    logger.info(f"Images array content preview: {[img[:50] + '...' for img in base64_images[:2]]}")
    return JSONResponse(content=response_payload)

@app.get("/")
def read_root():
    """A simple root endpoint to confirm the server is running."""
    azure_configured = bool(os.getenv("DOCUMENT_INTELLIGENCE_ENDPOINT"))
    return {
        "status": "ok", 
        "message": "Content Processing Engine is running.",
        "azure_configured": azure_configured,
        "pdf_processing": "PyMuPDF",
        "other_documents": "Azure Document Intelligence" if azure_configured else "Not configured"
    }

@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "azure_endpoint_configured": bool(os.getenv("DOCUMENT_INTELLIGENCE_ENDPOINT")),
        "azure_key_configured": bool(os.getenv("DOCUMENT_INTELLIGENCE_KEY"))
    }

@app.get("/test-image-extraction")
def test_image_extraction():
    """Test endpoint to verify image extraction capability."""
    return {
        "status": "ready",
        "message": "Send a PDF with 'X-Extract-Images: true' header to /process to test image extraction",
        "pdf_processing": "PyMuPDF",
        "expected_headers": {
            "X-Filename": "your-file.pdf",
            "X-Extract-Images": "true"
        }
    }