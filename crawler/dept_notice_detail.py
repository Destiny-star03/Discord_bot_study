# crawlers/school_notice_detail.py
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup


def _clean_text(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def fetch_notice_detail(detail_url: str) -> dict:
    res = requests.get(detail_url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
    res.raise_for_status()
    if not res.encoding:
        res.encoding = res.apparent_encoding

    soup = BeautifulSoup(res.text, "html.parser")
    wrap = soup.select_one(".view_wrap") or soup.body
    if wrap is None:
        return {"text": "", "images": [], "files": []}

    for bad in wrap.select(".view_subject, .meta"):
        bad.decompose()

    for tag in wrap.select("script, style, noscript"):
        tag.decompose()

    body_text = _clean_text(wrap.get_text("\n", strip=True))

    images = [urljoin(detail_url, img["src"]) for img in wrap.select("img[src]")]
    FILE_HINTS = (
        "download",
        "atch",
        "attach",
        "fileDown",
        "FileDown",
        ".hwp",
        ".pdf",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
        ".zip",
    )
    links = []

    for a in wrap.select("a[href]"):
        href = a.get("href", "").strip()
        if not href:
            continue

        text = a.get_text(" ", strip=True)

        # href나 링크 텍스트에 첨부파일 느낌이 있으면만 채택
        hay = (href + " " + text).lower()
        if any(h.lower() in hay for h in FILE_HINTS):
            links.append(urljoin(detail_url, href))

    files = list(dict.fromkeys(links))  # 중복 제거
    return {"text": text, "images": images, "files": files}
