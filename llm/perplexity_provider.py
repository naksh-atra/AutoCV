"""Perplexity Sonar LLM provider implementation."""
import json
import urllib.request
from llm.base import LLMProvider


class PerplexityProvider(LLMProvider):
    """Perplexity Sonar API provider (OpenAI-compatible)."""

    def __init__(self, api_key: str, model: str = "sonar"):
        self.api_key = api_key
        self.model = model
        self.api_url = "https://api.perplexity.ai/chat/completions"

    def generate(self, resume_latex: str, jd_text: str) -> str:
        """Call Perplexity API to tailor the resume."""
        from prompt import build_prompt
        import time
        import random
        import string

        system_prompt, user_prompt = build_prompt(resume_latex, jd_text)
        
        # Add unique identifier to prevent caching
        unique_id = str(int(time.time() * 1000))
        random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        user_prompt_with_id = f"[Request ID: {unique_id}-{random_str}]\n\n{user_prompt}"
        system_prompt_with_id = f"[System ID: {unique_id}-{random_str}]\n\n{system_prompt}"

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt_with_id},
                {"role": "user", "content": user_prompt_with_id},
            ],
            "temperature": 0.5,
            "max_tokens": 4096,
            "seed": random.randint(0, 2**32-1),  # Random seed for variation
        }

        data = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(
            self.api_url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))

        return result["choices"][0]["message"]["content"]
