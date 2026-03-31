"""LLM provider abstraction."""
from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate(self, resume_latex: str, jd_text: str) -> str:
        """Generate tailored LaTeX resume from original and job description.

        Args:
            resume_latex: The original resume in LaTeX format.
            jd_text: The job description text.

        Returns:
            The tailored resume in LaTeX format.
        """
        pass
