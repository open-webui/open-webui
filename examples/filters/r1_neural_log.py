"""
title: DeepSeek R1 Neural-Log Visualizer
author: Open WebUI Community
author_url: https://github.com/open-webui/open-webui
funding_url: https://github.com/open-webui/open-webui
version: 0.1.0
"""

from pydantic import BaseModel, Field
from typing import Optional
import re
import datetime
import random

class Filter:
    class Valves(BaseModel):
        status: bool = Field(default=True, description="Enable or disable the neural log visualization.")
        theme: str = Field(default="Cyberpunk", description="Visual theme: 'Cyberpunk', 'Matrix', or 'Minimalist'.")
        think_tag_start: str = Field(default="<think>", description="Start tag for the thinking process.")
        think_tag_end: str = Field(default="</think>", description="End tag for the thinking process.")
        show_timestamps: bool = Field(default=True, description="Show timestamps in the log.")

    def __init__(self):
        self.valves = self.Valves()

    def outlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        if not self.valves.status:
            return body

        messages = body.get("messages", [])
        if not messages:
            return body

        last_message = messages[-1]
        if last_message.get("role") != "assistant":
            return body

        content = last_message.get("content", "")
        
        # Regex to find think tags (handling potentially unclosed tags)
        start_tag = re.escape(self.valves.think_tag_start)
        end_tag = re.escape(self.valves.think_tag_end)
        
        # Pattern: <think> ... (</think> or end of string)
        # We use non-greedy matching .*? to capture content inside tags
        pattern = f"{start_tag}(.*?)(?:{end_tag}|$)"
        match = re.search(pattern, content, re.DOTALL)
        
        if match:
            think_content = match.group(1)
            # If the content is empty, skip
            if not think_content.strip():
                return body
                
            formatted_think = self.format_think_content(think_content)
            
            # Replace the match with the formatted content
            # match.group(0) includes the tags (or start tag + content if unclosed)
            new_content = content.replace(match.group(0), formatted_think)
            
            # Update the message content
            last_message["content"] = new_content
            
        return body

    def format_think_content(self, content: str) -> str:
        theme = self.valves.theme.lower()
        lines = content.strip().split('\n')
        formatted_lines = []
        
        # Theme Configuration
        if "cyberpunk" in theme:
            header = [
                "> INITIALIZING NEURAL PATHWAYS...",
                "> ACCESSING KNOWLEDGE GRAPH: SECTOR 7",
                "> DECRYPTING LOGIC CHAIN..."
            ]
            block_lang = "log" # 'log' often gives nice terminal-like highlighting
        elif "matrix" in theme:
            header = [
                "> WAKE UP NEO...",
                "> THE MATRIX HAS YOU...",
                "> FOLLOWING THE WHITE RABBIT..."
            ]
            block_lang = "bash"
        else: # Minimalist
            header = ["> Thinking Process:"]
            block_lang = "text"

        # Generate Header
        header_text = "\n".join(header)
        
        # Process Lines
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
                
            prefix = ""
            if self.valves.show_timestamps:
                # Simulate a fast process time sequence
                # We use a fixed start time + increments to look like a coherent log
                delta = datetime.timedelta(seconds=i * 0.05 + random.uniform(0, 0.02))
                time_str = (datetime.datetime.min + delta).time().strftime("%H:%M:%S.%f")[:-3]
                
                if "cyberpunk" in theme:
                    prefix = f"[{time_str}] [NEURAL] "
                elif "matrix" in theme:
                    prefix = f"[{time_str}] [0x{random.randint(1000,9999)}] "
                else:
                    prefix = f"[{time_str}] "
            
            formatted_lines.append(f"{prefix}{line}")
            
        # Construct the Markdown Block
        return f"\n```{block_lang}\n{header_text}\n\n" + "\n".join(formatted_lines) + "\n```\n"
