import json
from dataclasses import dataclass
from typing import Callable, Dict, List, Literal, NamedTuple, Optional, Self, TypedDict
from unittest.mock import MagicMock, patch

# Test module name and function names
module_name: str = "apps.rag.batch_utils"
sync_function_name: str = "_request_sync_embedding"
async_function_name: str = "_request_async_embedding"
token_counter_function_name: str = "_get_token_count"
EXPECTED_EMBEDDING_DIMENSION: int = 1536
FAKE_EMBEDDING: Dict[Literal["embedding"], List[float]] = {
    "embedding": [0.0] * EXPECTED_EMBEDDING_DIMENSION
}
NUM_TEXTS: int = 16384
NUM_TOKENS: int = 1_000_000
FAKE_TOKENIZER: Callable[[str], int] = lambda x: len(x) // 4  # noqa: E731
TEXT_LENGTH: int = (NUM_TOKENS * 4) // NUM_TEXTS + 1


class MockEmbeddingRequest(TypedDict):
    model: str
    input: List[str]


class MockBatchRequest(TypedDict):
    custom_id: str
    method: str
    url: str
    body: MockEmbeddingRequest


class MockBatchResponse(TypedDict):
    custom_id: str
    response: Dict[
        Literal["body"],
        Dict[Literal["data"], List[Dict[Literal["embedding"], List[float]]]],
    ]


class MockHTTPResponse(NamedTuple):
    status_code: int
    text: str


@dataclass
class MockBatch:
    id: str

    input_file_id: str
    """The ID of the input file for the batch."""

    status: Literal[
        "validating",
        "failed",
        "in_progress",
        "finalizing",
        "completed",
        "expired",
        "cancelling",
        "cancelled",
    ]
    """The current status of the batch."""

    output_file_id: Optional[str]
    """The ID of the file containing the outputs of successfully executed requests."""


@dataclass
class MockFileObject:
    id: str
    bytes: int
    filename: str
    purpose: Literal[
        "assistants",
        "assistants_output",
        "batch",
        "batch_output",
        "fine-tune",
        "fine-tune-results",
        "vision",
    ]
    status: Literal["uploaded", "processed", "error"]


# Define the MockOpenAIClient class
class MockOpenAIClient:
    def __init__(self) -> None:
        self.mock_batches: Dict[str, MockBatch] = {}
        self.mock_requests: Dict[str, List[MockBatchRequest]] = {}
        self.mock_responses: Dict[str, List[MockBatchResponse]] = {}

    @property
    def files(self) -> Self:
        self.create = MagicMock(side_effect=self.files_create)
        self.content = MagicMock(side_effect=self.files_content)
        return self

    @property
    def batches(self) -> Self:
        self.create = MagicMock(side_effect=self.batches_create)
        self.retrieve = MagicMock(side_effect=self.batches_retrieve)
        return self

    def files_create(
        self, file: tuple[str, bytes], purpose: Literal["batch"]
    ) -> MockFileObject:
        # Simulate creating a file object
        file_name, file_bytes = file
        assert purpose == "batch", f"Expected purpose 'batch', got '{purpose}'"
        mock_file_object = MockFileObject(
            id=f"mock_file_id_{len(self.mock_requests)}",
            bytes=len(file_bytes),
            filename=file_name,
            purpose=purpose,
            status="uploaded",
        )
        request_file: List[MockBatchRequest] = list(
            map(json.loads, file_bytes.split(b"\n"))
        )
        num_texts: int = sum(
            len(file_json["body"]["input"]) for file_json in request_file
        )
        assert num_texts == NUM_TEXTS, f"Expected {NUM_TEXTS} texts, got {num_texts}"
        self.mock_requests[mock_file_object.id] = request_file
        return mock_file_object

    def batches_create(
        self, input_file_id: str, endpoint: str, completion_window: str
    ) -> MockBatch:
        # Simulate creating a batch job
        mock_batch = MockBatch(
            id=f"mock_batch_id_{len(self.mock_batches)}",
            input_file_id=input_file_id,
            status="validating",
            output_file_id=None,
        )
        self.mock_batches[mock_batch.id] = mock_batch
        return mock_batch

    def batches_retrieve(self, batch_id: str) -> MockBatch:
        # Simulate retrieving the status of a batch job
        # For demonstration, it will always return "completed" after the first call
        mock_batch: MockBatch = self.mock_batches[batch_id]
        mock_batch.status = "completed"
        mock_batch.output_file_id = f"mock_output_file_id_{batch_id}"
        request_file = self.mock_requests[mock_batch.input_file_id]
        self.mock_responses[mock_batch.output_file_id] = [
            {
                "custom_id": request["custom_id"],
                "response": {
                    "body": {
                        "data": [
                            FAKE_EMBEDDING for _ in range(len(request["body"]["input"]))
                        ]
                    }
                },
            }
            for request in request_file
        ]
        return mock_batch

    def files_content(self, output_file_id: str) -> MockHTTPResponse:
        # Simulate retrieving the content of a file
        responses: List[MockBatchResponse] = self.mock_responses[output_file_id]
        return MockHTTPResponse(
            status_code=200, text="\n".join(json.dumps(result) for result in responses)
        )


def test_openai_batch_api_embedding() -> None:
    """Test the flow of generate_openai_batch_embeddings function.

    This test verifies that the function calls the correct OpenAI Batch API endpoints
    function based on the size of the input text.
    """
    model: str = "text-embedding-3-small"
    mock_key: str = "mock_api_key"
    mock_url: str = "https://batch.mock.test/v1"
    texts: List[str] = ["A" * TEXT_LENGTH for _ in range(NUM_TEXTS)]

    with patch(
        f"{module_name}.{token_counter_function_name}"
    ) as mock_token_counter, patch(f"{module_name}.OpenAI") as mock_openai_client:
        # Set up mock token counter, roughly 1/4 of the text length
        mock_token_counter.return_value = FAKE_TOKENIZER

        # Set up mock OpenAI client using MockOpenAIClient
        mock_client_instance = MockOpenAIClient()
        mock_openai_client.return_value = mock_client_instance

        # Import function and call
        from apps.rag.batch_utils import generate_openai_batch_embeddings

        result: Optional[List[List[float]]] = generate_openai_batch_embeddings(
            model, texts, mock_key, mock_url
        )
        mock_openai_client.assert_called_once_with(api_key=mock_key, base_url=mock_url)
        mock_token_counter.assert_called_once_with(model)

        # Verify that the result has the correct number of embeddings
        assert result and len(result) == len(
            texts
        ), f"Expected {len(texts)} embeddings, got {len(result or ())}"

        # Check that all embeddings have the expected dimension and values
        for embedding in result:
            assert (
                len(embedding) == EXPECTED_EMBEDDING_DIMENSION
            ), f"Embedding dimension mismatch: {len(embedding)} != {EXPECTED_EMBEDDING_DIMENSION}"
            assert all(value == 0.0 for value in embedding), "Embedding values mismatch"
