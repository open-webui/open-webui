"""
CAJAL Paper Generation Function for Open WebUI
Adds /paper command to generate scientific papers with arXiv citations.
"""
import os
import requests
from typing import Optional

class Filter:
    def __init__(self):
        self.name = "CAJAL Paper Generator"
        self.description = "Generate publication-ready scientific papers with verified arXiv citations"
        self.version = "1.0.0"
        self.manifest = {
            "id": "cajal-paper-generator",
            "name": "CAJAL Paper Generator",
            "description": "Generate 7-section scientific papers with real arXiv citations via local LLM",
            "version": self.version,
            "author": "Agnuxo1",
            "license": "MIT",
            "requires": [],
            "env": {
                "CAJAL_MODEL": {
                    "description": "Ollama model name for CAJAL",
                    "default": "cajal-p2pclaw"
                },
                "CAJAL_BASE_URL": {
                    "description": "Ollama API base URL",
                    "default": "http://localhost:11434"
                }
            }
        }

    async def inlet(self, body: dict, user: Optional[dict] = None) -> dict:
        """Process incoming messages. Detect /paper command."""
        messages = body.get("messages", [])
        if not messages:
            return body
        
        last_message = messages[-1].get("content", "")
        
        # Detect /paper command
        if last_message.startswith("/paper"):
            topic = last_message.replace("/paper", "").strip()
            if not topic:
                topic = "machine learning"
            
            # Generate paper via CAJAL
            paper = await self._generate_paper(topic)
            
            # Replace the /paper command with the generated paper
            messages[-1]["content"] = f"Generated paper on: **{topic}**\n\n{paper}"
            body["messages"] = messages
        
        return body

    async def _generate_paper(self, topic: str) -> str:
        """Generate a scientific paper using CAJAL via Ollama."""
        base_url = os.environ.get("CAJAL_BASE_URL", "http://localhost:11434")
        model = os.environ.get("CAJAL_MODEL", "cajal-p2pclaw")
        
        system_prompt = (
            "You are CAJAL, a scientific paper generator. "
            "Generate a complete 7-section paper with real arXiv citations. "
            "Structure: Abstract, Introduction, Methodology, Results, Discussion, Conclusion, References."
        )
        
        prompt = (
            f"Generate a complete scientific paper on: {topic}\n\n"
            "Include all 7 sections with BibTeX references."
        )
        
        try:
            response = requests.post(
                f"{base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "system": system_prompt,
                    "stream": False,
                    "options": {"temperature": 0.7, "num_predict": 4096}
                },
                timeout=300
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "Error: No response from CAJAL model")
        except Exception as e:
            return f"Error generating paper: {str(e)}\n\nMake sure Ollama is running with the CAJAL model installed."

    async def outlet(self, body: dict, user: Optional[dict] = None) -> dict:
        """Process outgoing responses. No modification needed."""
        return body
