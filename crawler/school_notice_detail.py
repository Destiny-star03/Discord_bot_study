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

    text = _clean_text(wrap.get_text("\n", strip=True))

    images = [urljoin(detail_url, img["src"]) for img in wrap.select("img[src]")]
    files = [urljoin(detail_url, a["href"]) for a in wrap.select("a[href]")]

    return {"text": text, "images": images, "files": files}
