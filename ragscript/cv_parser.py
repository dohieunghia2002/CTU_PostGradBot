"""CV parsing utilities for extracting and organizing CV data."""

from __future__ import annotations

import logging
from typing import Dict, List, Tuple

from utils import clean_text

logger = logging.getLogger(__name__)


def extract_cv_sections(cv_text: str) -> Dict[str, str]:
    """Extract common CV sections from raw text.
    
    Returns a dictionary with potential sections:
    - name, contact, summary, experience, skills, education, etc.
    """
    
    # Split by common section headers (Vietnamese + English)
    section_keywords = [
        r"(?i)(thông tin cá nhân|personal information|contact)",
        r"(?i)(kỹ năng|skills)",
        r"(?i)(kinh nghiệm|experience|quá trình làm việc)",
        r"(?i)(học vấn|education|bằng cấp)",
        r"(?i)(chứng chỉ|certifications|certificate)",
        r"(?i)(dự án|projects|project)",
        r"(?i)(languages|ngôn ngữ)",
    ]
    
    sections = {}
    lines = cv_text.split('\n')
    
    # Try to extract first line as name/candidate name
    if lines:
        potential_name = clean_text(lines[0])
        if potential_name and len(potential_name) < 100:
            sections["candidate_name"] = potential_name
    
    return sections


def format_cv_for_display(cv_text: str, cv_name: str = "") -> str:
    """Format CV text for nice CLI display."""
    
    display = f"\n{'='*70}\n"
    display += f"📄 CV SOURCE: {cv_name}\n"
    display += f"{'='*70}\n\n"
    display += cv_text
    display += f"\n\n{'='*70}\n"
    
    return display


def parse_cvs_from_documents(
    documents: List[Tuple[str, str]],
) -> Dict[str, str]:
    """Create a mapping from CV text to CV source name.
    
    Args:
        documents: List of (cv_text, cv_filename) tuples
        
    Returns:
        Dictionary mapping CV full text to source filename
    """
    
    cv_map = {}
    for cv_text, source_name in documents:
        # Use full CV text as key, source name as value
        cv_map[cv_text] = source_name
        logger.info("Parsed CV: %s (%d chars)", source_name, len(cv_text))
    
    return cv_map