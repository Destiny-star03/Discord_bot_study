# crawlers/school_notice_detail.py
from urllib.parse import urljoin, urlsplit
import re
import requests
from bs4 import BeautifulSoup

# javascript:fn_egov_downFile('ATCH_FILE_ID','1');
DOWN_RE = re.compile(
    r"fn_egov_downFile\(\s*'([^']+)'\s*,\s*'([^']+)'\s*\)", re.IGNORECASE
)


def _clean_text(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def _build_download_url(detail_url: str, atch_file_id: str, file_sn: str) -> str:
    # eGov 첨부 다운로드 기본 패턴(대부분 이 경로를 씀)
    parts = urlsplit(detail_url)
    base = f"{parts.scheme}://{parts.netloc}"
    return f"{base}/cmm/fms/FileDown.do?atchFileId={atch_file_id}&fileSn={file_sn}"


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
    files: list[str] = []
    file_box = soup.select_one(".board_file")
    if file_box:
        # 1) a.href가 실제 링크면 그대로 사용
        for a in file_box.select("a[href]"):
            href = a.get("href", "").strip()
            if not href:
                continue

            # javascript 다운로드 함수 형태 처리
            if href.lower().startswith("javascript:"):
                m = DOWN_RE.search(href)
                if m:
                    atch_id, sn = m.group(1), m.group(2)
                    files.append(_build_download_url(detail_url, atch_id, sn))
            else:
                files.append(urljoin(detail_url, href))
        # 2) href가 없고 onclick에만 있는 경우도 대응
        for a in file_box.select("a[onclick]"):
            onclick = a.get("onclick", "")
            m = DOWN_RE.search(onclick)
            if m:
                atch_id, sn = m.group(1), m.group(2)
                files.append(_build_download_url(detail_url, atch_id, sn))

    # 중복 제거
    files = list(dict.fromkeys(files))

    return {"text": body_text, "images": images, "files": files}
