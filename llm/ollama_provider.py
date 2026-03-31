"""Ollama LLM provider implementation."""
import ollama
from llm.base import LLMProvider


class OllamaProvider(LLMProvider):
    """Ollama client provider using the ollama library."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.2"):
        self.base_url = base_url
        self.model = model

    def generate(self, resume_latex: str, jd_text: str) -> str:
        """Call Ollama API to tailor the resume."""
        from prompt import build_prompt

        system_prompt, user_prompt = build_prompt(resume_latex, jd_text)

        response = ollama.generate(
            model=self.model,
            prompt=user_prompt,
            system=system_prompt,
            options={
                "temperature": 0.2,
                "num_predict": 4096,
            },
        )

        return response["response"]
