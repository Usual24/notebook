from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader
from readability import Document
from youtube_transcript_api import YouTubeTranscriptApi


@dataclass
class ParsedDocument:
    doc_id: str
    source_type: str
    source_ref: str
    title: str
    text: str


def _stable_id(prefix: str, value: str) -> str:
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def _normalize_text(text: str) -> str:
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    if chunk_size <= chunk_overlap:
        raise ValueError("chunk_size must be greater than chunk_overlap")

    text = _normalize_text(text)
    if not text:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(end - chunk_overlap, start + 1)
    return chunks


def parse_uploaded_file(path: Path) -> ParsedDocument:
    suffix = path.suffix.lower()
    raw: str

    if suffix == ".pdf":
        reader = PdfReader(str(path))
        raw = "\n\n".join((page.extract_text() or "") for page in reader.pages)
    else:
        raw = path.read_text(encoding="utf-8", errors="ignore")

    title = path.name
    source_ref = str(path.resolve())
    return ParsedDocument(
        doc_id=_stable_id("file", source_ref),
        source_type="file",
        source_ref=source_ref,
        title=title,
        text=_normalize_text(raw),
    )


def parse_url(url: str, timeout: int = 20) -> ParsedDocument:
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        resp = client.get(url)
        resp.raise_for_status()
        html = resp.text

    readable = Document(html)
    title = readable.short_title() or url
    content_html = readable.summary(html_partial=True)

    soup = BeautifulSoup(content_html, "html.parser")
    text = soup.get_text("\n", strip=True)

    return ParsedDocument(
        doc_id=_stable_id("url", url),
        source_type="url",
        source_ref=url,
        title=title,
        text=_normalize_text(text),
    )




def _fetch_youtube_title(video_id: str) -> str:
    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        if soup.title and soup.title.string:
            title = soup.title.string.replace(" - YouTube", "").strip()
            if title:
                return title
    except Exception:
        pass
    return f"YouTube:{video_id}"

def _extract_video_id(url_or_id: str) -> str:
    if "youtube.com" in url_or_id or "youtu.be" in url_or_id:
        patterns = [r"v=([\w-]{11})", r"youtu\.be/([\w-]{11})", r"shorts/([\w-]{11})"]
        for pattern in patterns:
            m = re.search(pattern, url_or_id)
            if m:
                return m.group(1)
    return url_or_id.strip()


def parse_youtube(url_or_id: str, language_priority: tuple[str, ...] = ("ko", "en")) -> ParsedDocument:
    video_id = _extract_video_id(url_or_id)
    transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=list(language_priority))
    text = "\n".join(part["text"] for part in transcript)
    title = _fetch_youtube_title(video_id)
    source_ref = f"https://www.youtube.com/watch?v={video_id}"

    return ParsedDocument(
        doc_id=_stable_id("yt", video_id),
        source_type="youtube",
        source_ref=source_ref,
        title=title,
        text=_normalize_text(text),
    )
