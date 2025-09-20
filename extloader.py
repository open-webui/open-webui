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
    logger.info(f"All headers: {dict(request.headers)}")
    
    file_bytes = await request.body()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file content received."
        )

    filename = request.headers.get("x-filename", "unknown_file")
    file_ext = os.path.splitext(filename)[1].lower()
    extract_images_flag = request.headers.get("x-extract-images", "false").lower() == 'true'

    logger.info(f"Processing file: {filename}")
    logger.info(f"Image extraction enabled: {extract_images_flag}")

    base64_images = []
    full_text = ""
    page_count = 0

    if file_ext == ".pdf":
        logger.info("Processing PDF with PyMuPDF.")
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            page_count = doc.page_count
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                full_text += page.get_text() + "\n\n"

            if extract_images_flag:
                logger.info("Starting image extraction for PDF...")
                for page_num in range(len(doc)):
                    image_list = doc.get_page_images(page_num, full=True)
                    for img_index, img in enumerate(image_list):
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        image_ext = base_image["ext"]
                        encoded_string = base64.b64encode(image_bytes).decode("utf-8")
                        data_uri = f"data:image/{image_ext};base64,{encoded_string}"
                        base64_images.append(data_uri)
                logger.info(f"Extracted {len(base64_images)} images from PDF.")
        except Exception as e:
            logger.error(f"Error processing PDF with PyMuPDF: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to process PDF file: {e}")
    else:
        logger.info(f"Processing non-PDF file ({filename}) with Azure Document Intelligence.")
        
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
                    mode="markdown", # Use markdown for better text representation
                )
            else:
                 # Authenticate using DefaultAzureCredential if no key is provided
                loader = AzureAIDocumentIntelligenceLoader(
                    file_path=temp_file_path,
                    api_endpoint=api_endpoint,
                    azure_credential=DefaultAzureCredential(),
                    mode="markdown",
                )
            
            documents = loader.load()
            
            if documents:
                full_text = "\n\n".join([doc.page_content for doc in documents])
                # page_count can be approximated by the number of documents, though it may not be accurate
                page_count = len(documents)
            
        except Exception as e:
            logger.error(f"Error processing with Azure Document Intelligence: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to process document with Azure: {e}")
        finally:
            os.remove(temp_file_path) # Clean up the temporary file

    response_payload = {
        "page_content": full_text.strip(),
        "metadata": {
            "source": filename,
            "page_count": page_count,
        },
        "images": base64_images,
    }

    return JSONResponse(content=response_payload)