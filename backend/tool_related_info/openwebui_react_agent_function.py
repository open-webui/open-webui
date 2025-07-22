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
import json

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
            default=os.getenv("AZURE_API_KEY", "default"),
            description="API key for Azure OpenAI services.",
        )
        AZURE_ENDPOINT: str = Field(
            default=os.getenv("AZURE_ENDPOINT", "https://llm-api.amd.com"),
            description="Endpoint URL for Azure OpenAI services.",
        )
        AZURE_API_VERSION: str = Field(
            default=os.getenv("AZURE_API_VERSION", "default"),
            description="API version for Azure OpenAI services.",
        )
        AZURE_SUBSCRIPTION_KEY: str = Field(
            default=os.getenv("AZURE_SUBSCRIPTION_KEY", "7cce1ac73d98442c844bb040b983114c"),
            description="Subscription key for Azure services.",
        )
        LLAMAINDEX_MODEL_NAME: str = Field(
            default=os.getenv("LLAMAINDEX_MODEL_NAME", "gpt-4.1"),
            description="Deployment name of the LLM model to use.",
        )
        LLAMAINDEX_EMBEDDING_MODEL_NAME: str = Field(
            default="text-embedding-ada-002",
            description="Name of the embedding model to use.",
        )
        AZURE_SEARCH_API_KEY: str = Field(
            default=os.getenv("AZURE_SEARCH_API_KEY", "SbEBqR8O01YJ7WwhFJo32DGEhG4pRqk9YZ7rjGEfrhAzSeAnryoB"),
            description="API key for Azure AI Search.",
        )
        AZURE_SEARCH_ENDPOINT: str = Field(
            default=os.getenv("AZURE_SEARCH_ENDPOINT", "https://pdase-cepm-search.search.windows.net"),
            description="Endpoint URL for Azure AI Search.",
        )
        AZURE_SEARCH_ADMIN_KEY: str = Field(
            default=os.getenv("AZURE_SEARCH_ADMIN_KEY", "cNK2ZylNjszCu7HnNhFYQYPLyHOGkP4nJh6cZxa0rGAzSeDa9nt7"),
            description="Admin key for Azure AI Search.",
        )
        LANGFUSE_PUBLIC_KEY: Optional[str] = Field(
            default=os.getenv("LANGFUSE_PUBLIC_KEY", "pk-lf-dc0f9f5d-7f02-472c-9032-8b5112a92d0c"),
            description="Public key for Langfuse observability.",
        )
        LANGFUSE_SECRET_KEY: Optional[str] = Field(
            default=os.getenv("LANGFUSE_SECRET_KEY", "sk-lf-15e0fb26-b64f-4cc7-bab9-5b073daad037"),
            description="Secret key for Langfuse observability.",
        )
        LANGFUSE_HOST: Optional[str] = Field(
            default=os.getenv("LANGFUSE_HOST", "https://us.cloud.langfuse.com"),
            description="Host URL for Langfuse.",
        )

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.valves = self.Valves()

        self.logger.info("Initializing pipe...")
        self.logger.info(f"Using Azure endpoint: {self.valves.AZURE_ENDPOINT}")
        self.logger.warning(f"Using model: {self.valves.LLAMAINDEX_MODEL_NAME}")

        azure_headers = {
            "Ocp-Apim-Subscription-Key": self.valves.AZURE_SUBSCRIPTION_KEY
        }

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
        self.logger.info("Pipe initialization complete.")

    def get_azure_search_index_list(self) -> str:
        """Retrieves the list of Azure Search indexes."""
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

    async def pipe(self, body: dict, __user__: dict) -> AsyncIterator[str]:
        """
        This is the main execution method for the Open-WebUI pipe.
        It receives the request body and user information, processes it through the
        ReAct agent workflow, and streams back the response.
        """
        try:
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

            with self.instrumentor.observe() as trace:
                try:
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
                        trace.score(name="success", value=1.0)
                        trace.update(
                            metadata={
                                "execution_time_seconds": execution_time,
                                "response_length": len(str(final_answer_content)),
                                "reasoning_steps_count": len(reasoning_steps),
                            }
                        )
                    else:
                        self.logger.error("Workflow returned no final result object.")
                        trace.score(name="failure_no_result", value=0.0)
                        yield "No response generated from workflow."

                except Exception as e:
                    self.logger.error(f"Error in pipe: {str(e)}", exc_info=True)
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
                    "content": "How many OPNs will we offer for Granite Ridge and Strix Halo? Help me to create a table to list all the OPN, spec./frequency/clock ...etc. for comparison.",
                }
            ],
        }

        # Example user object from Open-WebUI
        user = {"id": "test-user-id", "email": "test@example.com"}

        print("--- Starting Pipe Test ---")
        try:
            # The pipe method is an async generator, so we iterate over it with 'async for'
            async for chunk in pipe_instance.pipe(body=body, __user__=user):
                print(chunk, end="", flush=True)
        except Exception as e:
            logger.error(f"Error during pipe test: {e}", exc_info=True)
        finally:
            print("\n--- Pipe Test Finished ---")

    # Run the async test function
    asyncio.run(run_test())
