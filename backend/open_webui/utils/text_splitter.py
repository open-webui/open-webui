import logging
import tiktoken
from langchain.text_splitter import RecursiveCharacterTextSplitter, TokenTextSplitter
from open_webui.constants import ERROR_MESSAGES

log = logging.getLogger(__name__)

def get_text_splitter(request):
    """Get the appropriate text splitter based on configuration."""
    if request.app.state.config.TEXT_SPLITTER in ["", "character"]:
        return RecursiveCharacterTextSplitter(
            chunk_size=request.app.state.config.CHUNK_SIZE,
            chunk_overlap=request.app.state.config.CHUNK_OVERLAP,
            add_start_index=True,
        )
    elif request.app.state.config.TEXT_SPLITTER == "token":
        log.info(
            f"Using token text splitter: {request.app.state.config.TIKTOKEN_ENCODING_NAME}"
        )

        tiktoken.get_encoding(str(request.app.state.config.TIKTOKEN_ENCODING_NAME))
        return TokenTextSplitter(
            encoding_name=str(request.app.state.config.TIKTOKEN_ENCODING_NAME),
            chunk_size=request.app.state.config.CHUNK_SIZE,
            chunk_overlap=request.app.state.config.CHUNK_OVERLAP,
            add_start_index=True,
        )
    else:
        raise ValueError(ERROR_MESSAGES.DEFAULT("Invalid text splitter")) 