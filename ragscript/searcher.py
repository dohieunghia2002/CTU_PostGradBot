"""Simple web search client using Tavily or SerpAPI."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import List, Optional

import requests

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str


class WebSearcher:
    """Abstraction layer for web search providers."""

    def __init__(self) -> None:
        self.provider = os.getenv("SEARCH_PROVIDER", "tavily").lower()
        self.api_key = os.getenv("SEARCH_API_KEY", "").strip()

        if not self.api_key:
            raise ValueError(
                "SEARCH_API_KEY chưa được cấu hình. Đặt biến môi trường hoặc chỉnh lại code."
            )

        logger.info("Sử dụng provider tìm kiếm: %s", self.provider)

    def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        if not query.strip():
            return []

        if self.provider == "tavily":
            return self._search_tavily(query, max_results)
        if self.provider == "serpapi":
            return self._search_serpapi(query, max_results)

        raise ValueError(f"Provider không được hỗ trợ: {self.provider}")

    def _search_tavily(self, query: str, max_results: int) -> List[SearchResult]:
        endpoint = "https://api.tavily.com/search"
        payload = {
            "api_key": self.api_key,
            "query": query,
            "search_depth": "advanced",
            "max_results": max_results,
        }
        response = requests.post(endpoint, json=payload, timeout=30)
        response.raise_for_status()

        data = response.json()
        results = []
        for item in data.get("results", [])[:max_results]:
            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("content", ""),
                )
            )
        return results

    def _search_serpapi(self, query: str, max_results: int) -> List[SearchResult]:
        endpoint = "https://serpapi.com/search"
        params = {
            "q": query,
            "engine": "google",
            "api_key": self.api_key,
            "num": max_results,
            "hl": os.getenv("SEARCH_REGION", "vi"),
        }
        response = requests.get(endpoint, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        results = []
        for item in data.get("organic_results", [])[:max_results]:
            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                )
            )
        return results