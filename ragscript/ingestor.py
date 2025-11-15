"""Document ingestion utilities for the RAG chatbot."""

from __future__ import annotations

import logging
from typing import List

import requests
from bs4 import BeautifulSoup

from utils import clean_text

logger = logging.getLogger(__name__)


def fetch_url(url: str, user_agent: str) -> str:
    """Retrieve raw HTML content from a URL."""

    headers = {"User-Agent": user_agent}
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.text


def extract_text_from_html(html: str) -> str:
    """Parse raw HTML and extract readable text."""

    soup = BeautifulSoup(html, "html.parser")

    # Remove script and style elements
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text(separator=" ")
    return clean_text(text)


def ingest_urls(urls: List[str], user_agent: str) -> List[str]:
    """Fetch and clean text content from a list of URLs."""

    texts: List[str] = []
    for url in urls:
        try:
            logger.info("Đang tải nội dung %s", url)
            html = fetch_url(url, user_agent)
            text = extract_text_from_html(html)
            if text:
                texts.append(text)
        except Exception as exc:
            logger.warning("Không thể tải %s: %s", url, exc)
    return texts