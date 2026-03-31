"""Groq LLM provider implementation."""
import json
import urllib.request
from llm.base import LLMProvider


class GroqProvider(LLMProvider):
    """Groq API provider (OpenAI-compatible)."""

    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile"):
        self.api_key = api_key
        self.model = model
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"

    def generate(self, resume_latex: str, jd_text: str) -> str:
        """Call Groq API to tailor the resume."""
        from prompt import build_prompt

        system_prompt, user_prompt = build_prompt(resume_latex, jd_text)

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "max_completion_tokens": 4096,
        }

        data = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(
            self.api_url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))

        return result["choices"][0]["message"]["content"]
