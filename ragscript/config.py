"""Configuration utilities for the Colab-friendly RAG chatbot."""

from __future__ import annotations

from dataclasses import dataclass
from getpass import getpass
import os


@dataclass
class Settings:
    """Holds runtime settings and secrets for the chatbot."""

    gemini_api_key: str
    gemini_model: str = "gemini-2.0-flash"
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
    search_region: str = "vi-vn"
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    @classmethod
    def from_env(cls) -> "Settings":
        """Build settings from environment variables, prompting if needed."""

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            prompt_message = (
                "Nhập Google Gemini API key (sẽ không được in ra màn hình): "
            )
            api_key = getpass(prompt_message).strip()

        if not api_key:
            raise ValueError(
                "Google Gemini API key là bắt buộc để chatbot hoạt động."
            )

        return cls(
            gemini_api_key=api_key,
            gemini_model=os.getenv("GEMINI_MODEL", cls.gemini_model),
            embedding_model=os.getenv(
                "EMBEDDING_MODEL", cls.embedding_model
            ),
            search_region=os.getenv("SEARCH_REGION", cls.search_region),
            user_agent=os.getenv("HTTP_USER_AGENT", cls.user_agent),
        )

    def as_dict(self) -> dict[str, str]:
        """Expose settings (except secrets) for logging or debugging."""

        return {
            "gemini_model": self.gemini_model,
            "embedding_model": self.embedding_model,
            "search_region": self.search_region,
        }