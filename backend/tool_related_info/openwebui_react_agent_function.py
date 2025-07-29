"""
title: Llama Index Workflow-based ReAct Agent for Open-WebUI
author: open-webui
date: 2024-07-04
version: 1.0
license: MIT
description: An Open-WebUI pipe function for retrieving relevant information from a knowledge base using the Llama Index library with a Workflow-based ReAct Agent.
# requirements: llama-index==0.12.48, llama-index-llms-openai==0.4.7, langfuse==2.60.2, llama-index-embeddings-azure-openai==0.3.9, llama-index-llms-azure-openai==0.3.4, python-dotenv==1.1.0
"""

from typing import List, Union, AsyncIterator, Optional, Any
from pydantic import BaseModel, Field
from llama_index.core import Response
from tenacity import retry, stop_after_attempt, wait_exponential
from llama_index.core.storage import StorageContext
from llama_index.llms.azure_openai import AzureOpenAI
from llama_index.embeddings.azure_openai import AzureOpenAIEmbedding
from llama_index.core.tools import FunctionTool, ToolSelection, ToolOutput, BaseTool
from llama_index.core.llms import ChatMessage, MessageRole, LLM
from llama_index.tools.openapi import OpenAPIToolSpec
from llama_index.tools.requests import RequestsToolSpec
from pydantic import create_model
import json
from urllib.parse import urlparse
import httpx
import requests

# Azure Search imports
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient

# Langfuse integration
from langfuse.llama_index import LlamaIndexInstrumentor

# Import dotenv for loading environment variables from .env file
from dotenv import load_dotenv

import os
import logging
import sys
import asyncio
import time
import threading
import contextlib

# LlamaIndex Workflow imports
from llama_index.core.agent import ReActChatFormatter, ReActOutputParser
from llama_index.core.agent.react.types import (
    ActionReasoningStep,
    ObservationReasoningStep,
    ResponseReasoningStep,
    BaseReasoningStep,
)
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.workflow import (
    Context,
    Workflow,
    StartEvent,
    StopEvent,
    Event,
    step,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("pipeline.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv(override=True)
logger.info("Loaded environment variables from .env file.")


# Workflow Event Classes
class PrepEvent(Event):
    pass


class InputEvent(Event):
    input: List[ChatMessage]


class StreamEvent(Event):
    delta: str


class ToolCallEvent(Event):
    tool_calls: List[ToolSelection]


class FunctionOutputEvent(Event):
    output: ToolOutput


# Workflow-based ReAct Agent Class
class ReActAgentWorkflow(Workflow):
    def __init__(
        self,
        *args: Any,
        llm: LLM | None = None,
        tools: list[BaseTool] | None = None,
        extra_context: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.tools = tools or []
        self.llm = llm or AzureOpenAI()  # Defaulting to AzureOpenAI if not provided
        self.formatter = ReActChatFormatter(system_header=extra_context or "")
        self.output_parser = ReActOutputParser()
        self.logger = logging.getLogger(__name__)  # Add logger

    @step
    async def new_user_msg(self, ctx: Context, ev: StartEvent) -> PrepEvent:
        self.logger.info("Workflow step: new_user_msg")
        await ctx.store.set("sources", [])  # clear sources

        memory = await ctx.store.get("memory", default=None)
        if not memory:
            self.logger.info(
                "No existing memory in context, creating new ChatMemoryBuffer."
            )
            memory = ChatMemoryBuffer.from_defaults(llm=self.llm)
        else:
            self.logger.info("Using existing memory from context.")

        user_input = ev.input
        user_msg = ChatMessage(role=MessageRole.USER, content=user_input)
        memory.put(user_msg)
        self.logger.debug(f"Added user message to memory: {user_input}")

        await ctx.store.set("current_reasoning", [])
        await ctx.store.set("memory", memory)

        return PrepEvent()

    @step
    async def prepare_chat_history(self, ctx: Context, ev: PrepEvent) -> InputEvent:
        self.logger.info("Workflow step: prepare_chat_history")
        memory = await ctx.store.get("memory")
        chat_history = memory.get()
        current_reasoning = await ctx.store.get("current_reasoning", default=[])

        self.logger.debug(
            f"Preparing chat history. History length: {len(chat_history)}, Reasoning steps: {len(current_reasoning)}"
        )

        llm_input = self.formatter.format(
            self.tools, chat_history, current_reasoning=current_reasoning
        )
        return InputEvent(input=llm_input)

    @step
    async def handle_llm_input(
        self, ctx: Context, ev: InputEvent
    ) -> Union[ToolCallEvent, StopEvent, PrepEvent]:
        self.logger.info("Workflow step: handle_llm_input")
        chat_history_for_llm = ev.input
        current_reasoning = await ctx.store.get("current_reasoning", default=[])
        memory = await ctx.store.get("memory")

        self.logger.debug("Getting LLM response...")
        llm_response_message = await self.llm.achat(chat_history_for_llm)

        if llm_response_message is None or llm_response_message.message.content is None:
            self.logger.warning(
                "LLM response message or its content is None. Looping for retry."
            )
            current_reasoning.append(
                ObservationReasoningStep(
                    observation="LLM did not provide a valid response."
                )
            )
            await ctx.store.set("current_reasoning", current_reasoning)
            return PrepEvent()

        try:
            reasoning_step: BaseReasoningStep = self.output_parser.parse(
                llm_response_message.message.content
            )
            current_reasoning.append(reasoning_step)
            self.logger.info(f"Parsed reasoning step: {type(reasoning_step)}")

            if isinstance(reasoning_step, ResponseReasoningStep):
                self.logger.info(
                    "Reasoning step is a final response. Preparing StopEvent."
                )
                memory.put(
                    ChatMessage(
                        role=MessageRole.ASSISTANT, content=reasoning_step.response
                    )
                )
                await ctx.store.set("memory", memory)
                await ctx.store.set("current_reasoning", current_reasoning)

                sources = await ctx.store.get("sources", default=[])
                return StopEvent(
                    result={
                        "response": reasoning_step.response,
                        "sources": sources,
                        "reasoning": current_reasoning,
                    }
                )
            elif isinstance(reasoning_step, ActionReasoningStep):
                self.logger.info(
                    f"ActionReasoningStep: {reasoning_step.action}, Args: {reasoning_step.action_input}"
                )
                return ToolCallEvent(
                    tool_calls=[
                        ToolSelection(
                            tool_id="fake_id",
                            tool_name=reasoning_step.action,
                            tool_kwargs=reasoning_step.action_input or {},
                        )
                    ]
                )
        except Exception as e:
            self.logger.error(
                f"Error parsing LLM output or processing reasoning step: {e}",
                exc_info=True,
            )
            current_reasoning.append(
                ObservationReasoningStep(
                    observation=f"There was an error in parsing my reasoning: {e}"
                )
            )
            await ctx.store.set("current_reasoning", current_reasoning)

        self.logger.info(
            "No tool call or final response, preparing for another iteration."
        )
        return PrepEvent()

    @step
    async def handle_tool_calls(self, ctx: Context, ev: ToolCallEvent) -> PrepEvent:
        self.logger.info("Workflow step: handle_tool_calls")
        tool_calls = ev.tool_calls
        tools_by_name = {tool.metadata.get_name(): tool for tool in self.tools}
        current_reasoning = await ctx.store.get("current_reasoning", default=[])
        sources = await ctx.store.get("sources", default=[])

        for tool_call in tool_calls:
            self.logger.info(
                f"Handling tool call: {tool_call.tool_name} with args {tool_call.tool_kwargs}"
            )
            tool = tools_by_name.get(tool_call.tool_name)
            if not tool:
                self.logger.warning(f"Tool {tool_call.tool_name} not found.")
                current_reasoning.append(
                    ObservationReasoningStep(
                        observation=f"Tool {tool_call.tool_name} does not exist."
                    )
                )
                continue

            try:
                tool_output_obj: ToolOutput = tool(**tool_call.tool_kwargs)

                observation_content = ""
                # Prioritize the raw_output if it's a LlamaIndex Response object
                if isinstance(tool_output_obj.raw_output, Response):
                    sources.append(tool_output_obj.raw_output)
                    observation_content = str(tool_output_obj.raw_output.response)
                # If raw_output is not None but not a Response, stringify it.
                # This handles lists, strings, etc., ensuring the LLM gets the data.
                elif tool_output_obj.raw_output is not None:
                    observation_content = str(tool_output_obj.raw_output)
                    sources.append(Response(response=observation_content))
                # Fallback to the content string if raw_output is None
                elif tool_output_obj.content:
                    observation_content = str(tool_output_obj.content)
                    sources.append(Response(response=observation_content))
                else:
                    # If there's no output at all
                    observation_content = "Tool executed but returned no output."
                    self.logger.warning(observation_content)

                current_reasoning.append(
                    ObservationReasoningStep(observation=observation_content)
                )
                self.logger.info(f"Tool {tool_call.tool_name} executed successfully.")

            except Exception as e:
                self.logger.error(
                    f"Error calling tool {tool.metadata.get_name()}: {e}", exc_info=True
                )
                current_reasoning.append(
                    ObservationReasoningStep(
                        observation=f"Error calling tool {tool.metadata.get_name()}: {e}"
                    )
                )

        await ctx.store.set("sources", sources)
        await ctx.store.set("current_reasoning", current_reasoning)
        return PrepEvent()


class SearchPayload(BaseModel):
    """Schema for Azure AI Search API."""

    index_name: str = Field(
        ..., description="The name of the Azure Search index to query."
    )
    search_text: str = Field(..., description="The main search query text.")
    select: str = Field(
        ...,
        description="Comma-separated list of fields to retrieve. Do NOT include field extracted_vector. Always include fields which indicate the source of the document.",
    )
    filter: Optional[str] = Field(
        default=None, description="OData filter expressions to narrow results."
    )
    top: Optional[int] = Field(default=5, description="Number of results to return.")
    query_type: Optional[str] = Field(
        default=None, description="Type of search query (e.g., 'semantic')."
    )
    semantic_configuration_name: Optional[str] = Field(
        default=None, description="Name of the semantic configuration to use."
    )
    order_by: Optional[str] = Field(
        default=None,
        description="Comma-separated list of fields to sort the results by.",
    )
    vector_filter_mode: Optional[str] = Field(
        default=None, description="Filter mode for vector queries."
    )
    vector_field: Optional[str] = Field(
        ..., description="The name of the vector field in the index."
    )
    k: Optional[int] = Field(
        default=None,
        description="Number of nearest neighbors to return for vector queries.",
    )


class Pipe:
    class Valves(BaseModel):
        AZURE_API_KEY: str = Field(
            default=os.getenv("AZURE_API_KEY", ""),
            description="API key for Azure OpenAI services.",
        )
        AZURE_ENDPOINT: str = Field(
            default=os.getenv("AZURE_ENDPOINT", ""),
            description="Endpoint URL for Azure OpenAI services.",
        )
        AZURE_API_VERSION: str = Field(
            default=os.getenv("AZURE_API_VERSION", ""),
            description="API version for Azure OpenAI services.",
        )
        AZURE_SUBSCRIPTION_KEY: str = Field(
            default=os.getenv("AZURE_SUBSCRIPTION_KEY", ""),
            description="Subscription key for Azure services.",
        )
        LLAMAINDEX_MODEL_NAME: str = Field(
            default=os.getenv("LLAMAINDEX_MODEL_NAME", ""),
            description="Deployment name of the LLM model to use.",
        )
        LLAMAINDEX_EMBEDDING_MODEL_NAME: str = Field(
            default=os.getenv("LLAMAINDEX_EMBEDDING_MODEL_NAME", ""),
            description="Name of the embedding model to use.",
        )
        AZURE_SEARCH_API_KEY: str = Field(
            default=os.getenv("AZURE_SEARCH_API_KEY", ""),
            description="API key for Azure AI Search.",
        )
        AZURE_SEARCH_ENDPOINT: str = Field(
            default=os.getenv("AZURE_SEARCH_ENDPOINT", ""),
            description="Endpoint URL for Azure AI Search.",
        )
        AZURE_SEARCH_ADMIN_KEY: str = Field(
            default=os.getenv("AZURE_SEARCH_ADMIN_KEY", ""),
            description="Admin key for Azure AI Search.",
        )
        LANGFUSE_PUBLIC_KEY: Optional[str] = Field(
            default=os.getenv("LANGFUSE_PUBLIC_KEY"),
            description="Public key for Langfuse observability.",
        )
        LANGFUSE_SECRET_KEY: Optional[str] = Field(
            default=os.getenv("LANGFUSE_SECRET_KEY"),
            description="Secret key for Langfuse observability.",
        )
        LANGFUSE_HOST: Optional[str] = Field(
            default=os.getenv("LANGFUSE_HOST"),
            description="Host URL for Langfuse.",
        )

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.valves = self.Valves()
        self.llm = None
        self.index_client = None
        self.instrumentor = None
        self._initialized = False
        self._init_lock = threading.Lock()

    def _initialize(self):
        with self._init_lock:
            if self._initialized:
                return

            self.logger.info("Initializing pipe dependencies...")
            self.logger.info(f"Using Azure endpoint: {self.valves.AZURE_ENDPOINT}")
            self.logger.warning(f"Using model: {self.valves.LLAMAINDEX_MODEL_NAME}")

            azure_headers = {
                "Ocp-Apim-Subscription-Key": self.valves.AZURE_SUBSCRIPTION_KEY
            }

            if self.valves.LANGFUSE_PUBLIC_KEY and self.valves.LANGFUSE_SECRET_KEY:
                self.instrumentor = LlamaIndexInstrumentor(
                    public_key=self.valves.LANGFUSE_PUBLIC_KEY,
                    secret_key=self.valves.LANGFUSE_SECRET_KEY,
                    host=self.valves.LANGFUSE_HOST,
                )
                self.instrumentor.start()
                self.logger.info("Langfuse instrumentation initialized and started")

            @retry(
                wait=wait_exponential(multiplier=1, min=4, max=60),
                stop=stop_after_attempt(5),
            )
            def create_llm():
                return AzureOpenAI(
                    model=self.valves.LLAMAINDEX_MODEL_NAME,
                    deployment_name=self.valves.LLAMAINDEX_MODEL_NAME,
                    api_key=self.valves.AZURE_API_KEY,
                    azure_endpoint=self.valves.AZURE_ENDPOINT,
                    api_version=self.valves.AZURE_API_VERSION,
                    default_headers=azure_headers,
                    max_retries=3,
                    timeout=60,
                    temperature=0,
                )

            self.llm = create_llm()

            def create_AzureSearchClient():
                return SearchIndexClient(
                    endpoint=self.valves.AZURE_SEARCH_ENDPOINT,
                    credential=AzureKeyCredential(self.valves.AZURE_SEARCH_ADMIN_KEY),
                )

            self.index_client = create_AzureSearchClient()
            self._initialized = True
            self.logger.info("Pipe initialization complete.")

    def get_azure_search_index_list(self) -> str:
        """Retrieves the list of Azure Search indexes."""
        if not self.index_client:
            return "Error: Azure Search client not initialized."
        try:
            index_list = self.index_client.list_indexes()
            index_names = [index.name for index in index_list]
            logger.info(f"Successfully retrieved {len(index_names)} indexes.")
            return json.dumps(index_names, indent=2)
        except Exception as e:
            logger.error(f"Azure Search API call failed: {e}", exc_info=True)
            return f"Error during Azure Search get index list: {str(e)}"

    def get_azure_search_index_schema(self, input: str) -> str:
        """Retrieves the schema of a specific Azure Search index."""
        if not self.index_client:
            return "Error: Azure Search client not initialized."
        try:
            index_definition = self.index_client.get_index(name=input)
            logger.info(
                f"Successfully retrieved schema for index '{index_definition.name}'"
            )
            return json.dumps(index_definition.serialize(), indent=2)
        except Exception as e:
            logger.error(f"Azure Search API call failed: {e}", exc_info=True)
            return f"Error during Azure Search get index schema: {str(e)}"

    def run_azure_search(self, **kwargs) -> Response:
        """Runs a query against an Azure AI Search index."""
        search_payload = SearchPayload(**kwargs)

        search_client = SearchClient(
            endpoint=self.valves.AZURE_SEARCH_ENDPOINT,
            index_name=search_payload.index_name,
            credential=AzureKeyCredential(self.valves.AZURE_SEARCH_API_KEY),
            api_version="2024-11-01-preview",
        )
        try:
            search_args = {
                "search_text": search_payload.search_text,
                "select": search_payload.select,
                "filter": search_payload.filter,
                "top": search_payload.top,
                "query_type": search_payload.query_type,
                "semantic_configuration_name": search_payload.semantic_configuration_name,
                "include_total_count": True,
            }
            if search_payload.vector_field:
                search_args["vector_filter_mode"] = search_payload.vector_filter_mode
                search_args["vector_queries"] = [
                    {
                        "kind": "text",
                        "text": search_payload.search_text,
                        "fields": search_payload.vector_field,
                        "k": search_payload.k,
                    }
                ]

            results = search_client.search(**search_args)
            documents = list(results)
            self.logger.info(f"Azure Search returned {len(documents)} documents.")
            result_str = json.dumps(documents, default=str, indent=2)

            from llama_index.core.schema import TextNode, NodeWithScore

            source_node = NodeWithScore(node=TextNode(text=result_str), score=1.0)

            response = Response(response=result_str)
            response.source_nodes = [source_node]
            response.metadata = {"search_results_count": len(documents)}
            return response

        except Exception as e:
            self.logger.error(f"Azure Search API call failed: {e}", exc_info=True)
            return Response(
                response=f"Error during Azure Search: {str(e)}", source_nodes=[]
            )

    async def pipe(
        self, body: dict, __user__: dict, __tools__: Optional[dict] = None
    ) -> AsyncIterator[str]:
        """
        This is the main execution method for the Open-WebUI pipe.
        It receives the request body and user information, processes it through the
        ReAct agent workflow, and streams back the response.
        """
        if not self._initialized:
            self._initialize()

        try:
            if __tools__:
                self.logger.info(
                    f"Tools received: {json.dumps(__tools__, default=str)}"
                )
            else:
                self.logger.info("No tools received in __tools__.")

            messages = body.get("messages", [])
            if not messages:
                yield "Error: No messages found in the request body."
                return

            user_message = messages[-1]["content"]
            model_id = body.get("model", self.valves.LLAMAINDEX_MODEL_NAME)

            self.logger.info(
                f"Processing query with model {model_id} using Workflow ReAct Agent"
            )
            self.logger.debug(f"User message: {user_message}")

            user_id_to_use = __user__.get("email") or __user__.get("id", "anonymous")

            metadata = {
                "model_id": model_id,
                "query_length": len(user_message),
                "history_length": len(messages),
                "query_type": "workflow_react_agent",
                "user_id": user_id_to_use,
            }

            trace_context = (
                self.instrumentor.observe()
                if self.instrumentor
                else contextlib.nullcontext()
            )

            with trace_context as trace:
                try:
                    if trace:
                        trace.update(metadata=metadata, user_id=user_id_to_use)

                    tools_list: List[BaseTool] = [
                        FunctionTool.from_defaults(
                            fn=self.get_azure_search_index_list,
                            name="get_AzureCognitiveSearch_index_list",
                            description="Get the list of Azure Search indexes.",
                        ),
                        FunctionTool.from_defaults(
                            fn=self.get_azure_search_index_schema,
                            name="get_AzureCognitiveSearch_index_schema",
                            description="Get the schema of the Azure Search index.",
                        ),
                        FunctionTool.from_defaults(
                            fn=self.run_azure_search,
                            name="search_AzureCognitiveSearch_index",
                            description="Search the Azure Search index with the given parameters.",
                            fn_schema=SearchPayload,
                        ),
                    ]

                    if __tools__:
                        endpoints = {}
                        for tool_name, tool_data in __tools__.items():
                            endpoint = tool_data.get("endpoint")
                            api_key = tool_data.get("api_key")
                            if endpoint and endpoint not in endpoints:
                                endpoints[endpoint] = api_key

                        for endpoint, api_key in endpoints.items():
                            try:
                                spec_url = f"{endpoint}/openapi.json"
                                self.logger.info(
                                    f"Loading OpenAPI spec from: {spec_url}"
                                )

                                # Fetch the OpenAPI spec manually to inspect and modify it
                                loop = asyncio.get_running_loop()
                                response = await loop.run_in_executor(
                                    None, lambda: requests.get(spec_url, timeout=30)
                                )
                                response.raise_for_status()
                                spec_dict = response.json()

                                # If 'servers' key is missing, add it based on the endpoint
                                if (
                                    "servers" not in spec_dict
                                    or not spec_dict["servers"]
                                ):
                                    self.logger.warning(
                                        f"OpenAPI spec from {spec_url} is missing 'servers' key. "
                                        f"Injecting default server URL: {endpoint}"
                                    )
                                    spec_dict["servers"] = [{"url": endpoint}]

                                openapi_spec = OpenAPIToolSpec(spec=spec_dict)

                                headers = {}
                                if api_key:
                                    # Assuming Bearer token authentication as a common standard
                                    headers["Authorization"] = f"Bearer {api_key}"

                                domain = urlparse(endpoint).netloc
                                requests_spec = RequestsToolSpec(
                                    domain_headers={domain: headers} if headers else {}
                                )

                                openapi_tools = openapi_spec.to_tool_list()
                                requests_tools = requests_spec.to_tool_list()

                                tools_list.extend(openapi_tools)
                                tools_list.extend(requests_tools)
                                self.logger.info(
                                    f"Successfully loaded {len(openapi_tools)} tools from {endpoint}"
                                )
                            except Exception as e:
                                self.logger.error(
                                    f"Failed to load tools from endpoint {endpoint}: {e}",
                                    exc_info=True,
                                )

                    system_prompt = """You are an AI assistant designed to help with search tasks.
When responding, you MUST use the following format:

Thought: The thought process behind the action.
Action: The specific tool to use from the available tools.
Action Input: The parameters for the action, in JSON format.

If you have enough information to answer the user's query, use the following format:

Thought: I have enough information to answer the user's query.
Answer: The final answer to the user's query.

When executing search tasks, follow these SEARCH STRATEGIES in strict order:
1.  **Index Discovery:** Use `get_AzureCognitiveSearch_index_list` to find relevant indexes.
2.  **Schema Inspection:** Use `get_AzureCognitiveSearch_index_schema` to understand fields. If vectorSearch and semantic configuration are available, use them.
3.  **Query Planning & Execution:** Construct effective queries based on the schema. Break down complex requests into sub-queries and execute each with `search_AzureCognitiveSearch_index`.
4.  **Results Synthesis & Response:** Collate findings, structure the answer in clear Markdown, and always include a Source section listing the documents used.
5.  **Handling Uncertainty:** If results are incomplete, refine your query strategy and re-run searches rather than giving a partial answer.

Important: You may never skip a phase—or return final output—until all sub-queries are executed and synthesized.
                    """

                    workflow_agent = ReActAgentWorkflow(
                        llm=self.llm,
                        tools=tools_list,
                        extra_context=system_prompt,
                        verbose=True,
                        timeout=300,
                    )

                    workflow_ctx = Context(workflow_agent)
                    chat_memory = ChatMemoryBuffer.from_defaults(llm=self.llm)
                    for msg_data in messages:
                        role = (
                            MessageRole.USER
                            if msg_data["role"] == "user"
                            else MessageRole.ASSISTANT
                        )
                        chat_memory.put(
                            ChatMessage(role=role, content=msg_data["content"])
                        )
                    await workflow_ctx.store.set("memory", chat_memory)
                    self.logger.info(
                        f"Initialized workflow context with {len(messages)} historical messages."
                    )

                    start_time = time.time()
                    handler = workflow_agent.run(input=user_message, ctx=workflow_ctx)

                    yield '<details type="reasoning">\n<summary>Thought</summary>\n'

                    final_result_obj = await handler
                    reasoning_steps = (
                        final_result_obj.get("reasoning", [])
                        if final_result_obj
                        else []
                    )
                    for step_item in reasoning_steps:
                        if hasattr(step_item, "thought") and step_item.thought:
                            yield f">Thought: {step_item.thought}\n"
                        elif hasattr(step_item, "action") and step_item.action:
                            action_str = f">Action: {step_item.action}"
                            if (
                                hasattr(step_item, "action_input")
                                and step_item.action_input
                            ):
                                action_str += (
                                    f"\n>Action Input: {step_item.action_input}"
                                )
                            yield f"{action_str}\n"

                    yield "</details>\n"
                    execution_time = time.time() - start_time
                    self.logger.info(
                        f"Workflow execution completed in {execution_time:.2f} seconds."
                    )

                    if final_result_obj:
                        final_answer_content = final_result_obj.get("response", "")
                        if final_answer_content:
                            yield "Answer:\n"
                            yield final_answer_content
                        self.logger.info(
                            f"Final response from workflow: {final_answer_content}"
                        )
                        if trace:
                            trace.score(name="success", value=1.0)
                            trace.update(
                                metadata={
                                    "execution_time_seconds": execution_time,
                                    "response_length": len(
                                        str(final_answer_content)
                                    ),
                                    "reasoning_steps_count": len(reasoning_steps),
                                }
                            )
                    else:
                        self.logger.error(
                            "Workflow returned no final result object."
                        )
                        if trace:
                            trace.score(name="failure_no_result", value=0.0)
                        yield "No response generated from workflow."

                except Exception as e:
                    self.logger.error(f"Error in pipe: {str(e)}", exc_info=True)
                    if trace:
                        trace.update(metadata={"error": str(e)})
                        trace.score(name="error", value=0.0)
                    yield f"Pipeline execution failed: {str(e)}"
        finally:
            if self.instrumentor:
                self.logger.debug("Flushing Langfuse events")
                self.instrumentor.flush()


if __name__ == "__main__":

    async def run_test():
        """
        A simple async function to test the Pipe class functionality.
        This simulates a call from Open-WebUI.
        """
        pipe_instance = Pipe()

        # Example request body from Open-WebUI
        body = {
            "model": "gpt-4.1",
            "messages": [
                {
                    "role": "user",
                    # "content": "How many OPNs will we offer for Granite Ridge and Strix Halo? Help me to create a table to list all the OPN, spec./frequency/clock ...etc. for comparison.",
                    "content": "Perform 10 test tool calls for tool “tool_hello_post”, with different name on each test.",
                }
            ],
        }

        print("--- Starting Pipe Test ---")
        # Sample params
        params = {
            "body": {
                "model": "react_agent",
                "messages": [
                    {
                        "role": "system",
                        "content": 'Available Tools: [{"type": "function", "name": "tool_hello_post", "description": "Hello", "parameters": {"type": "object", "properties": {"name": {"type": "string", "title": "Name", "description": ""}}, "required": ["name"]}}, {"type": "function", "name": "tool_get_project_sheet_list_post", "description": "Tool Name: get_project_sheet_list\\n\\nPurpose:\\nRetrieves a list of sheets for a specific project (non-CRM workspaces) from the backend API.\\nThis is determined by the provided workspace, user email, and a RFQ_ID.\\nThe tool outputs a Markdown formatted table detailing information for each sheet.\\n\\nParameters:\\n    Workspace (str):\\n        Required. Specifies the current workspace context. Must NOT be \'CRM\'.\\n        Common values include: \'E2E\', \'Thermal\', \'PPA\'.\\n        Example: \'E2E\'\\n\\n    Email (str):\\n        Required. The email address of the user making the request for permission checks.\\n        Example: \'user@example.com\'\\n\\n    RFQ_ID (int):\\n        Required. The unique identifier for the project.\\n        Example: 123", "parameters": {"type": "object", "properties": {"Workspace": {"type": "string"}, "Email": {"type": "string"}, "RFQ_ID": {"type": "integer"}}, "required": ["Workspace", "Email", "RFQ_ID"]}}, {"type": "function", "name": "tool_get_program_sheet_list_post", "description": "Tool Name: get_program_sheet_list\\n\\nPurpose:\\nRetrieves a list of sheets for a specific program from the backend API.\\nThis is determined by the user email, a programID, and the workspace.\\nThe tool outputs a Markdown formatted table detailing information for each sheet.\\n\\nParameters:\\n    Email (str):\\n        Required. The email address of the user making the request for permission checks.\\n        Example: \'user@example.com\'\\n\\n    ProgramID (int):\\n        Required. The unique identifier for the program.\\n        Example: 456\\n        \\n    Workspace (str, optional):\\n        The workspace for the program. Defaults to \'CRM\'.\\n        For future use, this parameter can specify other workspaces.\\n        Example: \'CRM\'", "parameters": {"type": "object", "properties": {"Email": {"type": "string"}, "ProgramID": {"type": "integer"}, "Workspace": {"type": "string"}}, "required": ["Email", "ProgramID"]}}, {"type": "function", "name": "tool_get_project_sheet_tool_post", "description": "Tool Name: get_project_sheet_tool\\n\\nPurpose:\\nRetrieves detailed cell data for a specific sheet template within a non-CRM project.\\nThe data is contextualized by workspace, section, user email, and RFQ_ID.\\nThe output is a Markdown table representing the sheet\'s content.\\n\\nParameters:\\n    Workspace (str):\\n        Required. Specifies the current workspace context. Must NOT be \'CRM\'.\\n        Example: \'E2E\'\\n\\n    Section (str):\\n        Required. The name of the section where the sheet template resides.\\n        Example: \'General Info\'\\n\\n    Email (str):\\n        Required. The email address of the user making the request for permission checks.\\n        Example: \'user@example.com\'\\n\\n    SheetTemplateID (int):\\n        Required. The unique identifier of the sheet template to retrieve.\\n        Example: 789\\n\\n    RFQ_ID (int):\\n        Required. The unique identifier for the project.\\n        Example: 123", "parameters": {"type": "object", "properties": {"Workspace": {"type": "string"}, "Section": {"type": "string"}, "Email": {"type": "string"}, "SheetTemplateID": {"type": "integer"}, "RFQ_ID": {"type": "integer"}}, "required": ["Workspace", "Section", "Email", "SheetTemplateID", "RFQ_ID"]}}, {"type": "function", "name": "tool_get_program_sheet_tool_post", "description": "Tool Name: get_program_sheet_tool\\n\\nPurpose:\\nRetrieves detailed cell data for a specific sheet template within a program-based workspace (typically CRM).\\nThe data is contextualized by section, user email, programID, and workspace.\\nThe output is a Markdown table representing the sheet\'s content.\\n\\nParameters:\\n    Section (str):\\n        Required. The name of the section where the sheet template resides.\\n        Example: \'General Info\'\\n\\n    Email (str):\\n        Required. The email address of the user making the request for permission checks.\\n        Example: \'user@example.com\'\\n\\n    SheetTemplateID (int):\\n        Required. The unique identifier of the sheet template to retrieve.\\n        Example: 789\\n\\n    ProgramID (int):\\n        Required. The unique identifier for the program.\\n        Example: 456\\n        \\n    Workspace (str, optional):\\n        The workspace for the program. Defaults to \'CRM\'.\\n        For future use, this parameter can specify other program-based workspaces.\\n        Example: \'CRM\'", "parameters": {"type": "object", "properties": {"Section": {"type": "string"}, "Email": {"type": "string"}, "SheetTemplateID": {"type": "integer"}, "ProgramID": {"type": "integer"}, "Workspace": {"type": "string"}}, "required": ["Section", "Email", "SheetTemplateID", "ProgramID"]}}, {"type": "function", "name": "tool_get_project_list_post", "description": "Tool Name: get_project_list\\n\\nPurpose:\\nRetrieves a list of Projects from the backend API based on the user\'s email, with a required dynamic filter.\\n\\nParameters:\\n    Email (str):\\n        Required. The email address of the user making the request.\\n    Filters (dict):\\n        Required. A dictionary of filters to apply.\\n        Example: {\\"ODM\\": \\"LCFC\\", \\"Key_Program\\": \\"Hawk Point\\"}\\n        Available columns for filtering include:\\n        - RFQ_ID\\n        - APM_ID\\n        - OEM\\n        - ODM\\n        - OEMCodename\\n        - Key_Program\\n\\nReturns:\\n    str: A Markdown table containing the list of Projects.", "parameters": {"type": "object", "properties": {"Email": {"type": "string"}, "Filters": {"type": "object", "properties": {}, "required": []}}, "required": ["Email", "Filters"]}}, {"type": "function", "name": "tool_get_program_list_post", "description": "Tool Name: get_program_list\\n\\nPurpose:\\nRetrieves a list of programs from the backend API based on the user\'s email.\\nProgram list includes IP Year, Main Representing Key Program and it\'s Corresponding Key Program.\\n\\nParameters:\\n    Email (str):\\n        Required. The email address of the user making the request.\\n\\nReturns:\\n    str: A Markdown table containing the list of programs.", "parameters": {"type": "object", "properties": {"Email": {"type": "string"}}, "required": ["Email"]}}, {"type": "function", "name": "tool_get_component_list_post", "description": "Tool Name: get_component_list\\n\\nPurpose:\\nRetrieves a list of components from the backend API based on the CpmID and user\'s email.\\nThe component list contains all the parts and detailed specifications of the project, such as part number, vendor name, etc.\\n\\nParameters:\\n    CpmID (int):\\n        Required. The unique identifier for the CPM.\\n    Email (str):\\n        Required. The email address of the user making the request for permission checks.\\n\\nReturns:\\n    str: A Markdown table containing the list of components.", "parameters": {"type": "object", "properties": {"RFQ_ID": {"type": "integer"}, "Email": {"type": "string"}}, "required": ["RFQ_ID", "Email"]}}]\n\nYour task is to choose and return the correct tool(s) from the list of available tools based on the query. Follow these guidelines:\n\n- Return only the JSON object, without any additional text or explanation.\n\n- If no tools match the query, return an empty array: \n   {\n     "tool_calls": []\n   }\n\n- If one or more tools match the query, construct a JSON response containing a "tool_calls" array with objects that include:\n   - "name": The tool\'s name.\n   - "parameters": A dictionary of required parameters and their corresponding values.\n\nThe format for the JSON response is strictly:\n{\n  "tool_calls": [\n    {"name": "toolName1", "parameters": {"key1": "value1"}},\n    {"name": "toolName2", "parameters": {"key2": "value2"}}\n  ]\n}',
                    },
                    {
                        "role": "user",
                        "content": 'Query: History:\nUSER: """Perform 10 test tool calls for tool “tool_hello_post”, with different name on each test."""\nQuery: Perform 10 test tool calls for tool “tool_hello_post”, with different name on each test.',
                    },
                ],
                "stream": False,
            },
            "__user__": {
                "id": "cbfbe0b7-309c-4456-82f7-00f6daf16ed7",
                "email": "kai@datar.ai",
                "name": "Admin",
                "role": "admin",
            },
            "__tools__": {
                "tool_hello_post": {
                    "tool_id": "server:0",
                    "spec": {
                        "type": "function",
                        "name": "tool_hello_post",
                        "description": "Hello",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "title": "Name",
                                    "description": "",
                                }
                            },
                            "required": ["name"],
                        },
                    },
                    "endpoint": "http://localhost:8000",
                    "api_key": "top-secret",
                },
            },
        }

        try:
            # The pipe method is an async generator, so we iterate over it with 'async for'
            async for chunk in pipe_instance.pipe(
                body=body, __user__=params["__user__"], __tools__=params["__tools__"]
            ):
                print(chunk, end="", flush=True)
        except Exception as e:
            logger.error(f"Error during pipe test: {e}", exc_info=True)
        finally:
            print("\n--- Pipe Test Finished ---")

    # Run the async test function
    asyncio.run(run_test())
