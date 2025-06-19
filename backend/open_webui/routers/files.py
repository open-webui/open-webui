import logging
import os
import uuid
import json
from fnmatch import fnmatch
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
    Query,
)
from fastapi.responses import FileResponse, StreamingResponse
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS

from open_webui.models.users import Users
from open_webui.models.files import (
    FileForm,
    FileModel,
    FileModelResponse,
    Files,
)
from open_webui.models.knowledge import Knowledges

# RAG Imports
from open_webui.models.rag_files import ProcessedFile as RAGProcessedFile, FileChunk as RAGFileChunk # Renamed to avoid conflict
from open_webui.services.rag.document_extractor import extract_text_from_pdf, extract_text_from_markdown, extract_text_from_image
from open_webui.services.rag.content_chunker import chunk_text
from open_webui.services.rag.embedding_service import get_embeddings
from open_webui.database.vector.chroma_adapter import initialize_chroma_client, get_or_create_collection, add_documents_to_collection
from open_webui.config import Config # To access RAG specific configs like embedding model
from open_webui.database.db_utils import get_db

from open_webui.routers.knowledge import get_knowledge, get_knowledge_list
from open_webui.routers.retrieval import ProcessFileForm, process_file
from open_webui.routers.audio import transcribe
from open_webui.storage.provider import Storage
from open_webui.utils.auth import get_admin_user, get_verified_user
from pydantic import BaseModel, Field, UUID4
from typing import Optional, Dict, Any
import datetime

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


router = APIRouter()


############################
# Check if the current user has access to a file through any knowledge bases the user may be in.
############################


def has_access_to_file(
    file_id: Optional[str], access_type: str, user=Depends(get_verified_user)
) -> bool:
    file = Files.get_file_by_id(file_id)
    log.debug(f"Checking if user has {access_type} access to file")

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# Pydantic Models for RAG Context
############################


class RAGFileContextResponse(BaseModel):
    id: UUID4
    filename: str
    file_type: str
    file_size: int
    processing_status: str
    metadata_: Optional[Dict[str, Any]] = None
    created_at: int  # Assuming BigInteger stores a Unix timestamp (integer)
    user_id: UUID4

    class Config:
        orm_mode = True


############################
# RAG Search Query Model
############################


class RAGSearchQuery(BaseModel):
    query: str = Field(..., min_length=1, description="The search query for RAG.")


############################
# RAG Endpoints
############################


@router.get("/search_rag", summary="Search RAG enabled files", response_model=list[dict])
async def search_rag_files(
    request: Request, query: RAGSearchQuery = Depends(), user=Depends(get_verified_user)
):
    try:
        # Configuration for RAG
        chroma_path = getattr(request.app.state.config, 'CHROMA_PATH', "./data/chroma_db")
        embedding_model_name = getattr(request.app.state.config, 'RAG_EMBEDDING_MODEL', "sentence-transformers/all-MiniLM-L6-v2")
        # User-specific collection name, or a general one based on config
        collection_name = getattr(request.app.state.config, 'CHROMA_COLLECTION', f"user_{user.id}_rag_documents")
        top_n_results = getattr(request.app.state.config, 'RAG_TOP_N_RESULTS', 5)

        # Initialize ChromaDB client
        chroma_client = initialize_chroma_client(path=chroma_path)

        try:
            collection = chroma_client.get_collection(name=collection_name)
        except Exception as e: # Replace with specific ChromaDB exception if available
            log.warning(f"ChromaDB collection {collection_name} not found for user {user.id}: {e}")
            # It's also possible the collection doesn't exist yet, which is not an error for a search, just means no results.
            # Depending on Chroma's behavior, get_collection might raise error if not found.
            # If it raises an error (e.g. ValueError, etc.), we catch it.
            # If it returns None or some other indicator, adapt accordingly.
            # For now, assume it might raise an exception that indicates it's not there.
            return [] # Return empty list if collection doesn't exist for the user.


        # Generate embedding for the query
        try:
            query_embedding = get_embeddings([query.query], model_name=embedding_model_name)[0]
            if query_embedding is None:
                raise ValueError("Failed to generate query embedding.")
        except Exception as e:
            log.error(f"Failed to generate query embedding for query '{query.query}': {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process search query.",
            )

        # Query ChromaDB
        results = collection.query(
            query_embeddings=[query_embedding.tolist()], # Ensure it's a list of lists if Chroma client expects that
            n_results=top_n_results,
            include=["metadatas", "documents", "distances"]
        )

        # Format results
        formatted_results = []
        if results and results.get("ids")[0]: # results['ids'] is a list of lists of ids
            for i in range(len(results["ids"][0])):
                # Ensure all expected keys exist before trying to access them
                doc_text = results["documents"][0][i] if results["documents"] and results["documents"][0] else None
                metadata = results["metadatas"][0][i] if results["metadatas"] and results["metadatas"][0] else {}
                distance = results["distances"][0][i] if results["distances"] and results["distances"][0] else None

                formatted_results.append({
                    "chunk_text": doc_text,
                    "metadata": metadata, # Contains original_filename, processed_file_id, chunk_id etc.
                    "score": (1 - distance) if distance is not None else None,  # Convert distance to similarity score if applicable
                })

        return formatted_results

    except HTTPException:
        # Re-raise HTTPExceptions to let FastAPI handle them
        raise
    except Exception as e:
        log.error(f"Error during RAG search for query '{query.query}' by user {user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during search.",
        )


@router.get("/context/{file_id}", summary="Get RAG context for a specific file")
async def get_rag_context(file_id: str, user=Depends(get_verified_user)):
    try:
        # Attempt to parse file_id as UUID to ensure validity early
        try:
            parsed_file_id = uuid.UUID(file_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file_id format. Must be a valid UUID.",
            )

        with get_db() as db:
            # Query for the RAGProcessedFile by its ID
            rag_file_entry = (
                db.query(RAGProcessedFile)
                .filter(RAGProcessedFile.id == parsed_file_id)
                .first()
            )

            if not rag_file_entry:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"RAG processed file with id {file_id} not found.",
                )

            # Check ownership/admin access
            if not (str(rag_file_entry.user_id) == user.id or user.role == "admin"):
                # Note: user.id from token might be string, rag_file_entry.user_id is UUID.
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have permission to access this file context.",
                )

            # If using a Pydantic response model that expects `created_at` as a specific type,
            # ensure conversion if necessary. Here, assuming it's already an int (timestamp).
            # The RAGFileContextResponse model will handle validation.
            return RAGFileContextResponse.from_orm(rag_file_entry)

    except HTTPException:
        # Re-raise HTTPExceptions to let FastAPI handle them
        raise
    except Exception as e:
        log.error(f"Error retrieving RAG context for file_id {file_id} by user {user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving file context.",
        )

    has_access = False
    knowledge_base_id = file.meta.get("collection_name") if file.meta else None

    if knowledge_base_id:
        knowledge_bases = Knowledges.get_knowledge_bases_by_user_id(
            user.id, access_type
        )
        for knowledge_base in knowledge_bases:
            if knowledge_base.id == knowledge_base_id:
                has_access = True
                break

    return has_access


############################
# Upload File
############################


@router.post("/", response_model=FileModelResponse)
def upload_file(
    request: Request,
    file: UploadFile = File(...),
    metadata: Optional[dict | str] = Form(None),
    process: bool = Query(True),
    internal: bool = False,
    user=Depends(get_verified_user),
):
    log.info(f"file.content_type: {file.content_type}")

    # Ensure log is available (it's typically set up at the top of the file)
    # import logging # Already imported at the top
    # if not hasattr(logging, 'getLogger'): # Simple check if basicConfig might be needed
    #     logging.basicConfig(level=logging.INFO)
    # log = logging.getLogger(__name__) # Already initialized at the top

    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("Invalid metadata format"),
            )
    file_metadata = metadata if metadata else {}

    try:
        unsanitized_filename = file.filename
        filename = os.path.basename(unsanitized_filename)

        file_extension = os.path.splitext(filename)[1]
        # Remove the leading dot from the file extension
        file_extension = file_extension[1:] if file_extension else ""

        if (not internal) and request.app.state.config.ALLOWED_FILE_EXTENSIONS:
            request.app.state.config.ALLOWED_FILE_EXTENSIONS = [
                ext for ext in request.app.state.config.ALLOWED_FILE_EXTENSIONS if ext
            ]

            if file_extension not in request.app.state.config.ALLOWED_FILE_EXTENSIONS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.DEFAULT(
                        f"File type {file_extension} is not allowed"
                    ),
                )

        # replace filename with uuid
        id = str(uuid.uuid4())
        name = filename
        filename = f"{id}_{filename}"
        tags = {
            "OpenWebUI-User-Email": user.email,
            "OpenWebUI-User-Id": user.id,
            "OpenWebUI-User-Name": user.name,
            "OpenWebUI-File-Id": id,
        }
        contents, file_path = Storage.upload_file(file.file, filename, tags)

        file_item = Files.insert_new_file(
            user.id,
            FileForm(
                **{
                    "id": id,
                    "filename": name,
                    "path": file_path,
                    "meta": {
                        "name": name,
                        "content_type": file.content_type,
                        "size": len(contents),
                        "data": file_metadata,
                    },
                }
            ),
        )

        # NEW RAG Processing Logic
        rag_processed_file_id = uuid.uuid4()
        # Determine file extension for RAG processing
        file_extension = os.path.splitext(filename)[1].lower()
        # Define RAG-supported extensions (MVP: PDF, MD, common image types, TXT)
        rag_supported_extensions = ['.pdf', '.md', '.png', '.jpg', '.jpeg', '.txt']

        # Use the path from Storage.upload_file, which is file_path
        full_file_path = Storage.get_path(file_path)

        if file_extension in rag_supported_extensions:
            rag_processed_file_db_entry = None
            try:
                with get_db() as db:
                    # Create RAGProcessedFile entry
                    rag_processed_file_db_entry = RAGProcessedFile(
                        id=rag_processed_file_id,
                        user_id=uuid.UUID(user.id), # Convert user.id string to UUID
                        filename=name,
                        file_type=file.content_type,
                        file_size=file_item.meta.get('size', 0),
                        processing_status="processing",
                        metadata_={'original_file_id': file_item.id}
                    )
                    db.add(rag_processed_file_db_entry)
                    db.commit()
                    db.refresh(rag_processed_file_db_entry)
                    log.info(f"Created RAGProcessedFile entry for {name} with id {rag_processed_file_id}")

                extracted_text = ""
                if file_extension == '.pdf':
                    extracted_text = extract_text_from_pdf(full_file_path)
                elif file_extension == '.md':
                    extracted_text = extract_text_from_markdown(full_file_path)
                elif file_extension in ['.png', '.jpg', '.jpeg']:
                    # For MVP, image extraction might just be metadata or filename
                    extracted_text = extract_text_from_image(full_file_path)
                    if not extracted_text: # Fallback if no text extracted (e.g. pure image)
                         extracted_text = f"Image file: {name}" # Placeholder text
                elif file_extension == '.txt':
                    with open(full_file_path, 'r', encoding='utf-8') as f_txt:
                        extracted_text = f_txt.read()

                if extracted_text:
                    log.info(f"Extracted text from {name}. Length: {len(extracted_text)}")

                    chunk_s = getattr(request.app.state.config, 'RAG_CHUNK_SIZE', 512)
                    chunk_o = getattr(request.app.state.config, 'RAG_CHUNK_OVERLAP', 50)
                    text_chunks = chunk_text(extracted_text, chunk_size=chunk_s, chunk_overlap=chunk_o)
                    log.info(f"Created {len(text_chunks)} chunks for {name}.")

                    if text_chunks:
                        embedding_model_name = getattr(request.app.state.config, 'RAG_EMBEDDING_MODEL', "sentence-transformers/all-MiniLM-L6-v2")
                        chunk_embeddings = get_embeddings(text_chunks, model_name=embedding_model_name)
                        log.info(f"Generated {len(chunk_embeddings)} embeddings for {name}.")

                        db_chunks_to_add = []
                        chroma_ids = []
                        chroma_documents = []
                        chroma_embeddings_to_store = []
                        chroma_metadatas = []

                        for i, chunk_content in enumerate(text_chunks):
                            if i < len(chunk_embeddings) and chunk_embeddings[i] is not None:
                                chunk_id = uuid.uuid4()

                                db_chunk_data = {
                                    "id": chunk_id,
                                    "file_id": rag_processed_file_id,
                                    "chunk_text": chunk_content,
                                    "embedding": list(chunk_embeddings[i]), # Store as list for JSONB
                                    "chunk_metadata": {'chunk_order': i, 'original_filename': name, 'processed_file_id': str(rag_processed_file_id)}
                                }
                                db_chunks_to_add.append(RAGFileChunk(**db_chunk_data))

                                chroma_ids.append(str(chunk_id))
                                chroma_documents.append(chunk_content)
                                chroma_embeddings_to_store.append(list(chunk_embeddings[i]))
                                chroma_metadatas.append({
                                    'processed_file_id': str(rag_processed_file_id),
                                    'chunk_id': str(chunk_id),
                                    'original_filename': name,
                                    'original_file_id': str(file_item.id),
                                    'user_id': str(user.id)
                                })

                        if db_chunks_to_add:
                            with get_db() as db:
                                db.add_all(db_chunks_to_add)
                                db.commit()
                                log.info(f"Stored {len(db_chunks_to_add)} chunk records in database for {name}.")

                        if chroma_ids:
                            chroma_path = getattr(request.app.state.config, 'CHROMA_PATH', "./data/chroma_db") # Ensure CHROMA_PATH is defined in config
                            chroma_client = initialize_chroma_client(path=chroma_path)
                            # Using a general collection name or user-specific, consult overall design
                            collection_name = getattr(request.app.state.config, 'CHROMA_COLLECTION', f"user_{user.id}_rag_documents")
                            collection = get_or_create_collection(chroma_client, collection_name)
                            add_documents_to_collection(collection, ids=chroma_ids, documents=chroma_documents, embeddings=chroma_embeddings_to_store, metadatas=chroma_metadatas)
                            log.info(f"Added {len(chroma_ids)} chunks to ChromaDB collection '{collection_name}' for {name}.")

                        with get_db() as db:
                            rag_processed_file_db_entry = db.query(RAGProcessedFile).filter(RAGProcessedFile.id == rag_processed_file_id).first()
                            if rag_processed_file_db_entry:
                                rag_processed_file_db_entry.processing_status = "completed"
                                db.commit()
                                log.info(f"RAG processing completed for {name}.")
                    else:
                        log.warning(f"No text chunks generated for {name}.")
                        if rag_processed_file_db_entry:
                            with get_db() as db:
                                rag_processed_file_db_entry = db.query(RAGProcessedFile).filter(RAGProcessedFile.id == rag_processed_file_id).first()
                                if rag_processed_file_db_entry:
                                    rag_processed_file_db_entry.processing_status = "failed"
                                    rag_processed_file_db_entry.metadata_ = {**rag_processed_file_db_entry.metadata_, 'error': "No text chunks generated"}
                                    db.commit()
                else:
                    log.warning(f"No text extracted from {name}.")
                    if rag_processed_file_db_entry:
                        with get_db() as db:
                            rag_processed_file_db_entry = db.query(RAGProcessedFile).filter(RAGProcessedFile.id == rag_processed_file_id).first()
                            if rag_processed_file_db_entry:
                                rag_processed_file_db_entry.processing_status = "failed"
                                rag_processed_file_db_entry.metadata_ = {**rag_processed_file_db_entry.metadata_, 'error': "No text extracted"}
                                db.commit()

            except Exception as e:
                log.error(f"Error during RAG processing for file {name}: {e}", exc_info=True)
                if rag_processed_file_id: # Check if ID was generated
                    try:
                        with get_db() as db:
                            entry_to_update = db.query(RAGProcessedFile).filter(RAGProcessedFile.id == rag_processed_file_id).first()
                            if entry_to_update:
                                entry_to_update.processing_status = "failed"
                                entry_to_update.metadata_ = {**(entry_to_update.metadata_ or {}), 'error': str(e)}
                                db.commit()
                            else:
                                log.error(f"Failed to find RAGProcessedFile with id {rag_processed_file_id} to update error status.")
                    except Exception as db_exc:
                        log.error(f"Database error while updating RAG status for {name}: {db_exc}", exc_info=True)

        # Original processing logic (e.g., for transcriptions)
        if process and not (file_extension in rag_supported_extensions and extracted_text): # Avoid double processing if RAG handled it
            try:
                if file.content_type:
                    stt_supported_content_types = (
                        request.app.state.config.STT_SUPPORTED_CONTENT_TYPES
                        or [
                            "audio/*",
                            "video/webm",
                        ]
                    )

                    if any(
                        fnmatch(file.content_type, content_type)
                        for content_type in stt_supported_content_types
                    ):
                        file_path = Storage.get_file(file_path)
                        result = transcribe(request, file_path, file_metadata)

                        process_file(
                            request,
                            ProcessFileForm(file_id=id, content=result.get("text", "")),
                            user=user,
                        )
                    elif (not file.content_type.startswith(("image/", "video/"))) or (
                        request.app.state.config.CONTENT_EXTRACTION_ENGINE == "external"
                    ):
                        process_file(request, ProcessFileForm(file_id=id), user=user)
                else:
                    log.info(
                        f"File type {file.content_type} is not provided, but trying to process anyway"
                    )
                    process_file(request, ProcessFileForm(file_id=id), user=user)

                file_item = Files.get_file_by_id(id=id)
            except Exception as e:
                log.exception(e)
                log.error(f"Error processing file: {file_item.id}")
                file_item = FileModelResponse(
                    **{
                        **file_item.model_dump(),
                        "error": str(e.detail) if hasattr(e, "detail") else str(e),
                    }
                )

        if file_item:
            return file_item
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("Error uploading file"),
            )

    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT("Error uploading file"),
        )


############################
# List Files
############################


@router.get("/", response_model=list[FileModelResponse])
async def list_files(user=Depends(get_verified_user), content: bool = Query(True)):
    if user.role == "admin":
        files = Files.get_files()
    else:
        files = Files.get_files_by_user_id(user.id)

    if not content:
        for file in files:
            if "content" in file.data:
                del file.data["content"]

    return files


############################
# Search Files
############################


@router.get("/search", response_model=list[FileModelResponse])
async def search_files(
    filename: str = Query(
        ...,
        description="Filename pattern to search for. Supports wildcards such as '*.txt'",
    ),
    content: bool = Query(True),
    user=Depends(get_verified_user),
):
    """
    Search for files by filename with support for wildcard patterns.
    """
    # Get files according to user role
    if user.role == "admin":
        files = Files.get_files()
    else:
        files = Files.get_files_by_user_id(user.id)

    # Get matching files
    matching_files = [
        file for file in files if fnmatch(file.filename.lower(), filename.lower())
    ]

    if not matching_files:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No files found matching the pattern.",
        )

    if not content:
        for file in matching_files:
            if "content" in file.data:
                del file.data["content"]

    return matching_files


############################
# Delete All Files
############################


@router.delete("/all")
async def delete_all_files(user=Depends(get_admin_user)):
    result = Files.delete_all_files()
    if result:
        try:
            Storage.delete_all_files()
        except Exception as e:
            log.exception(e)
            log.error("Error deleting files")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("Error deleting files"),
            )
        return {"message": "All files deleted successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT("Error deleting files"),
        )


############################
# Get File By Id
############################


@router.get("/{id}", response_model=Optional[FileModel])
async def get_file_by_id(id: str, user=Depends(get_verified_user)):
    file = Files.get_file_by_id(id)

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        file.user_id == user.id
        or user.role == "admin"
        or has_access_to_file(id, "read", user)
    ):
        return file
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# Get File Data Content By Id
############################


@router.get("/{id}/data/content")
async def get_file_data_content_by_id(id: str, user=Depends(get_verified_user)):
    file = Files.get_file_by_id(id)

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        file.user_id == user.id
        or user.role == "admin"
        or has_access_to_file(id, "read", user)
    ):
        return {"content": file.data.get("content", "")}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# Update File Data Content By Id
############################


class ContentForm(BaseModel):
    content: str


@router.post("/{id}/data/content/update")
async def update_file_data_content_by_id(
    request: Request, id: str, form_data: ContentForm, user=Depends(get_verified_user)
):
    file = Files.get_file_by_id(id)

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        file.user_id == user.id
        or user.role == "admin"
        or has_access_to_file(id, "write", user)
    ):
        try:
            process_file(
                request,
                ProcessFileForm(file_id=id, content=form_data.content),
                user=user,
            )
            file = Files.get_file_by_id(id=id)
        except Exception as e:
            log.exception(e)
            log.error(f"Error processing file: {file.id}")

        return {"content": file.data.get("content", "")}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# Get File Content By Id
############################


@router.get("/{id}/content")
async def get_file_content_by_id(
    id: str, user=Depends(get_verified_user), attachment: bool = Query(False)
):
    file = Files.get_file_by_id(id)

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        file.user_id == user.id
        or user.role == "admin"
        or has_access_to_file(id, "read", user)
    ):
        try:
            file_path = Storage.get_file(file.path)
            file_path = Path(file_path)

            # Check if the file already exists in the cache
            if file_path.is_file():
                # Handle Unicode filenames
                filename = file.meta.get("name", file.filename)
                encoded_filename = quote(filename)  # RFC5987 encoding

                content_type = file.meta.get("content_type")
                filename = file.meta.get("name", file.filename)
                encoded_filename = quote(filename)
                headers = {}

                if attachment:
                    headers["Content-Disposition"] = (
                        f"attachment; filename*=UTF-8''{encoded_filename}"
                    )
                else:
                    if content_type == "application/pdf" or filename.lower().endswith(
                        ".pdf"
                    ):
                        headers["Content-Disposition"] = (
                            f"inline; filename*=UTF-8''{encoded_filename}"
                        )
                        content_type = "application/pdf"
                    elif content_type != "text/plain":
                        headers["Content-Disposition"] = (
                            f"attachment; filename*=UTF-8''{encoded_filename}"
                        )

                return FileResponse(file_path, headers=headers, media_type=content_type)

            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ERROR_MESSAGES.NOT_FOUND,
                )
        except Exception as e:
            log.exception(e)
            log.error("Error getting file content")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("Error getting file content"),
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


@router.get("/{id}/content/html")
async def get_html_file_content_by_id(id: str, user=Depends(get_verified_user)):
    file = Files.get_file_by_id(id)

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    file_user = Users.get_user_by_id(file.user_id)
    if not file_user.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        file.user_id == user.id
        or user.role == "admin"
        or has_access_to_file(id, "read", user)
    ):
        try:
            file_path = Storage.get_file(file.path)
            file_path = Path(file_path)

            # Check if the file already exists in the cache
            if file_path.is_file():
                log.info(f"file_path: {file_path}")
                return FileResponse(file_path)
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ERROR_MESSAGES.NOT_FOUND,
                )
        except Exception as e:
            log.exception(e)
            log.error("Error getting file content")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("Error getting file content"),
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


@router.get("/{id}/content/{file_name}")
async def get_file_content_by_id(id: str, user=Depends(get_verified_user)):
    file = Files.get_file_by_id(id)

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        file.user_id == user.id
        or user.role == "admin"
        or has_access_to_file(id, "read", user)
    ):
        file_path = file.path

        # Handle Unicode filenames
        filename = file.meta.get("name", file.filename)
        encoded_filename = quote(filename)  # RFC5987 encoding
        headers = {
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
        }

        if file_path:
            file_path = Storage.get_file(file_path)
            file_path = Path(file_path)

            # Check if the file already exists in the cache
            if file_path.is_file():
                return FileResponse(file_path, headers=headers)
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ERROR_MESSAGES.NOT_FOUND,
                )
        else:
            # File path doesn’t exist, return the content as .txt if possible
            file_content = file.content.get("content", "")
            file_name = file.filename

            # Create a generator that encodes the file content
            def generator():
                yield file_content.encode("utf-8")

            return StreamingResponse(
                generator(),
                media_type="text/plain",
                headers=headers,
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# Delete File By Id
############################


@router.delete("/{id}")
async def delete_file_by_id(id: str, user=Depends(get_verified_user)):
    file = Files.get_file_by_id(id)

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        file.user_id == user.id
        or user.role == "admin"
        or has_access_to_file(id, "write", user)
    ):
        # We should add Chroma cleanup here

        result = Files.delete_file_by_id(id)
        if result:
            try:
                Storage.delete_file(file.path)
            except Exception as e:
                log.exception(e)
                log.error("Error deleting files")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.DEFAULT("Error deleting files"),
                )
            return {"message": "File deleted successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("Error deleting file"),
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
