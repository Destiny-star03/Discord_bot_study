# crawlers/school_notice_detail.py
from urllib.parse import urljoin
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
    files: list[str] = []
    file_area = soup.select_one(".board_file") or wrap.find_next_sibling(
        "div", class_="board_file"
    )
    if file_area:
        for a in file_area.select("a.link_down"):
            href = (a.get("href") or "").strip()
            if not href:
                continue

            # javascript:fn_egov_downFile('ATCH_FILE_ID','1');
            m = DOWN_RE.search(href)
            if m:
                atch_id, file_sn = m.group(1), m.group(2)

                # ✅ 다운로드 URL (필요하면 경로만 조정)
                files.append(
                    f"https://www.yc.ac.kr/cmm/fms/FileDown.do?atchFileId={atch_id}&fileSn={file_sn}"
                )
            else:
                # 혹시 실제 URL이면 그대로
                files.append(urljoin(detail_url, href))

    # 중복 제거
    files = list(dict.fromkeys(files))
    # ✅ 여기까지

    return {"text": text, "images": images, "files": files}
