'''
title: DeepSeek R1 with Bocha search
author: liuboyangaa
description: In OpenWebUI, displays the thought chain of the DeepSeek R1 model and searchs (version 0.5.6 or higher)
version: 0.1.0  
licence: MIT  
references:
  - author: zgccrui
    title: DeepSeek R1
    description: In OpenWebUI, displays the thought chain of the DeepSeek R1 model (version 0.5.6 or higher)
  - author: atgehrhardt
    title: Live Search
    description: Implements live search functionality in OpenWebUI
'''
import json
import httpx
import re
from typing import AsyncGenerator, Callable, Awaitable
from pydantic import BaseModel, Field
import asyncio
from typing import List, Union, Generator, Iterator
import requests
from bs4 import BeautifulSoup
import urllib.parse

def _parse_response(response):
    
    if "data" in response:
        data = response["data"]
        if "webPages" in data:
            webPages = data["webPages"]
            if "value" in webPages:
                result = [
                    {
                        "id": item.get("id", ""),
                        "name": item.get("name", ""),
                        "url": item.get("url", ""),
                        "snippet": item.get("snippet", ""),
                        "summary": item.get("summary", ""),
                        "siteName": item.get("siteName", ""),
                        "siteIcon": item.get("siteIcon", ""),
                        "datePublished": item.get("datePublished", "") or item.get("dateLastCrawled", ""),
                    }
                    for item in webPages["value"]
                ]
    return result

class Pipe:
    class Valves(BaseModel):
        DEEPSEEK_API_BASE_URL: str = Field(
            default="https://api.deepseek.com/v1",
            description="DeepSeek API的基础请求地址",
        )
        DEEPSEEK_API_KEY: str = Field(
            default="",
            description="用于身份验证的DeepSeek API密钥，可从控制台获取"
        )
        DEEPSEEK_API_MODEL: str = Field(
            default="deepseek-reasoner",
            description="API请求的模型名称，默认为 deepseek-reasoner ",
        )
        Bocha_API_KEY: str = Field(
            default="",
            description="用于身份验证的Bocha API密钥，可从控制台获取"
        )
        enable_bocha: bool = Field(default=True)
        bocha_results: int = Field(default=30)

    def __init__(self):
        self.valves = self.Valves()
        self.data_prefix = "data:"
        self.emitter = None
        self.type = "manifold"
        self.id = "engine_search"
        self.name = "engines/"
        self.search_result = ""

    def pipes(self):
        return [
            {
                "id": self.valves.DEEPSEEK_API_MODEL,
                "name": self.valves.DEEPSEEK_API_MODEL,
            }
        ]

    async def pipe(self, body: dict, __event_emitter__: Callable[[dict], Awaitable[None]] = None, results=None) -> AsyncGenerator[str, None]:
        """主处理管道（已移除缓冲）"""
        user_input = self._extract_user_input(body)

        if not user_input:
            yield json.dumps({"error": "No search query provided"}, ensure_ascii=False)
            return

        model = body.get("model", "")
        print(f"Received model: {model}")  # Debug print

        if isinstance(results, str):
            try:
                results = int(results)
            except ValueError:
                yield json.dumps(
                    {"error": "Invalid number of results '{results}'"},
                    ensure_ascii=False,
                )
                return

        if self.valves.enable_bocha:
            print("Calling Bocha search")
            self.search_result = self._search_bocha(user_input, results)
        else:
            yield json.dumps(
                {"error": "Unsupported or disabled search engine for model: {model}"},
                ensure_ascii=False,
            )
            return

        yield f"""
        <details>
            <summary>点击展开搜索结果</summary>
            {self.search_result} 
        </details>
        """

        thinking_state = {"thinking": -1}  # 使用字典来存储thinking状态
        self.emitter = __event_emitter__

        # 验证配置
        if not self.valves.DEEPSEEK_API_KEY:
            yield json.dumps({"error": "未配置API密钥"}, ensure_ascii=False)
            return

        # 获取用户输入
        messages = body["messages"]
        user_input = messages[-1]["content"]

        # 合并搜索结果和用户输入
        combined_input = (
            f"Search Results: {self.search_result}\n\nUser Input: {user_input}"
        )
        # 准备请求参数
        headers = {
            "Authorization": f"Bearer {self.valves.DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        }

        try:
            # 模型ID提取
            model_id = body["model"].split(".", 1)[-1]
            payload = {**body, "model": model_id}

            # 将合并后的输入替换掉原来的用户输入部分
            payload["messages"] = [{"role": "user", "content": combined_input}]
            # 处理消息以防止连续的相同角色
            messages = payload["messages"]
            i = 0
            while i < len(messages) - 1:
                if messages[i]["role"] == messages[i + 1]["role"]:
                    # 插入具有替代角色的占位符消息
                    alternate_role = (
                        "assistant" if messages[i]["role"] == "user" else "user"
                    )
                    messages.insert(
                        i + 1,
                        {"role": alternate_role, "content": "[Unfinished thinking]"},
                    )
                i += 1

            # yield json.dumps(payload, ensure_ascii=False)

            # 发起API请求
            async with httpx.AsyncClient(http2=True) as client:
                async with client.stream(
                    "POST",
                    f"{self.valves.DEEPSEEK_API_BASE_URL}/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=300,
                ) as response:
                    # 错误处理
                    if response.status_code != 200:
                        error = await response.aread()
                        yield self._format_error(response.status_code, error)
                        return

                    # 流式处理响应
                    async for line in response.aiter_lines():
                        if not line.startswith(self.data_prefix):
                            continue

                        # 截取 JSON 字符串
                        json_str = line[len(self.data_prefix) :]

                        # 去除首尾空格后检查是否为结束标记
                        if json_str.strip() == "[DONE]":
                            return

                        try:
                            data = json.loads(json_str)
                        except json.JSONDecodeError as e:
                            # 格式化错误信息，这里传入错误类型和详细原因（包括出错内容和异常信息）
                            error_detail = f"解析失败 - 内容：{json_str}，原因：{e}"
                            yield self._format_error("JSONDecodeError", error_detail)
                            return

                        choice = data.get("choices", [{}])[0]

                        # 结束条件判断
                        if choice.get("finish_reason"):
                            return

                        # 状态机处理
                        state_output = await self._update_thinking_state(
                            choice.get("delta", {}), thinking_state
                        )
                        if state_output:
                            yield state_output  # 直接发送状态标记
                            if state_output == "<think>":
                                yield "\n"

                        # 内容处理并立即发送
                        content = self._process_content(choice["delta"])
                        if content:
                            if content.startswith("<think>"):
                                match = re.match(r"^<think>", content)
                                if match:
                                    content = re.sub(r"^<think>", "", content)
                                    yield "<think>"
                                    await asyncio.sleep(0.1)
                                    yield "\n"

                            elif content.startswith("</think>"):
                                match = re.match(r"^</think>", content)
                                if match:
                                    content = re.sub(r"^</think>", "", content)
                                    yield "</think>"
                                    await asyncio.sleep(0.1)
                                    yield "\n"
                            yield content


        except Exception as e:
            yield self._format_exception(e)

    def _extract_user_input(self, body: dict) -> str:
        messages = body.get("messages", [])
        if messages:
            last_message = messages[-1]
            if isinstance(last_message.get("content"), list):
                for item in last_message["content"]:
                    if item["type"] == "text":
                        return item["text"]
            else:
                return last_message.get("content", "")
        return ""

    def _search_bocha(self, query: str, results=None) -> str:
        if not self.valves.enable_bocha:
            return "Bocha search is disabled"
        print("Searching with bocha")
        try:
            url = "https://api.bochaai.com/v1/web-search?utm_source=ollama"
            headers = {
                "Authorization": f"Bearer {self.valves.Bocha_API_KEY}",
                "Content-Type": "application/json"
            }
            
            count = 5
            payload = json.dumps({
                "query": query,
                "summary": True,
                "freshness": "noLimit",
                "count": count
            })

            response = requests.post(url, headers=headers, data=payload, timeout=5)
            response.raise_for_status()
            results_list = _parse_response(response.json())

            
            if not results_list:
                return f"No results found for: {query}"

            # return results_list
            formatted_results = "Bocha Search Results:\n\n"
            for i, result in enumerate(results_list[:count]):
                link=result["url"], 
                title=result["name"], 
                snippet=result["summary"]
                formatted_results += f"{i}: {title}\n   {snippet}\n   URL: {link}\n\n"

            return formatted_results

        except Exception as e:
            return f"An error occurred while searching Bocha: {str(e)}"

    async def _update_thinking_state(self, delta: dict, thinking_state: dict) -> str:
        """更新思考状态机（简化版）"""
        state_output = ""

        # 状态转换：未开始 -> 思考中
        if thinking_state["thinking"] == -1 and delta.get("reasoning_content"):
            thinking_state["thinking"] = 0
            state_output = "<think>"

        # 状态转换：思考中 -> 已回答
        elif (
            thinking_state["thinking"] == 0
            and not delta.get("reasoning_content")
            and delta.get("content")
        ):
            thinking_state["thinking"] = 1
            state_output = "\n</think>\n\n"

        return state_output

    def _process_content(self, delta: dict) -> str:
        """直接返回处理后的内容"""
        return delta.get("reasoning_content", "") or delta.get("content", "")

    def _format_error(self, status_code: int, error: bytes) -> str:
        # 如果 error 已经是字符串，则无需 decode
        if isinstance(error, str):
            error_str = error
        else:
            error_str = error.decode(errors="ignore")

        try:
            err_msg = json.loads(error_str).get("message", error_str)[:200]
        except Exception as e:
            err_msg = error_str[:200]
        return json.dumps(
            {"error": f"HTTP {status_code}: {err_msg}"}, ensure_ascii=False
        )

    def _format_exception(self, e: Exception) -> str:
        """异常格式化保持不变"""
        err_type = type(e).__name__
        return json.dumps({"error": f"{err_type}: {str(e)}"}, ensure_ascii=False)
