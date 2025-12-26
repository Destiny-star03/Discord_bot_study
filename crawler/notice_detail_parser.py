# parsers/notice_detail_parser.py
from __future__ import annotations

import re
import base64
from urllib.parse import urljoin, urlsplit
from bs4 import BeautifulSoup

DOWN_RE = re.compile(
    r"fn_egov_downFile\(\s*'([^']+)'\s*,\s*'([^']+)'\s*\)", re.IGNORECASE
)

DATA_URL_RE = re.compile(r"^data:(image/[a-zA-Z0-9.+-]+);base64,(.+)$", re.DOTALL)


def _clean_text(text: str) -> str:
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    return "\n".join(lines)

def _is_noisy_text(text: str) -> bool:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if len(lines) >= 40:
        short = sum(1 for ln in lines if len(ln) <= 2)
        if short / len(lines) >= 0.35:
            return True
    if text.count("\n") >= 120:
        return True
    return False


def _normalize_broken_text(text: str) -> str:
    # 0) 공백을 한 줄로 정리
    t = re.sub(r"\s+", " ", text).strip()

    # 1) 날짜 붙이기
    # 1-1) 4자리 연도: 2025. 11. 26. -> 2025.11.26.
    t = re.sub(r"(\d{4})\s*\.\s*(\d{1,2})\s*\.\s*(\d{1,2})\s*\.", r"\1.\2.\3.", t)
    # 1-2) 2자리 연도: 25. 11. 26. -> 25.11.26.
    t = re.sub(
        r"(?<!\d)(\d{2})\s*\.\s*(\d{1,2})\s*\.\s*(\d{1,2})\s*\.", r"\1.\2.\3.", t
    )

    # 2) 시간 단위 붙이기: 15 시 -> 15시, 14 시 30 분 -> 14시 30분
    t = re.sub(r"(\d)\s+(시|분|초|호|일|월|년)", r"\1\2", t)

    # 3) 전화번호 붙이기: (055 751 2088) -> (055-751-2088)
    t = re.sub(r"\((\d{2,4})\s+(\d{3,4})\s+(\d{4})\)", r"(\1-\2-\3)", t)

    # 4) 기호 주변 공백 정리
    t = re.sub(r"\s*~\s*", "~", t)
    t = re.sub(r"\s+([:;,.!?])", r"\1", t)
    t = re.sub(r"\(\s+", "(", t)
    t = re.sub(r"\s+\)", ")", t)

    # 5) 섹션/구분자 줄바꿈
    t = re.sub(r"\s*■\s*", "\n■ ", t)

    # 6) ★★★ 헤더 가독성 강화(줄 띄우고 굵게)
    t = re.sub(r"\s*(★{3}\s*[^★]+?\s*★{3})\s*", r"\n\n**\1**\n", t)

    # 7) 동그라미 번호 줄바꿈
    t = re.sub(r"\s*([①②③④⑤⑥⑦⑧⑨⑩])\s*", r"\n\1 ", t)

    # 8) '1. 2. 3.' 목록 줄바꿈
    #    ✅ (?!\d{1,2}\.) 추가: "25.11." 같은 날짜는 목록으로 보지 않음
    t = re.sub(
        r"(?<!\d\.)(?<![0-9A-Za-z가-힣])([1-9]|[1-9]\d)\.\s*(?!\d{1,2}\.)", r"\n\1. ", t
    )

    # 9) 하이픈 항목/주의문 줄바꿈
    t = re.sub(r"\s+-\s+", "\n- ", t)
    t = re.sub(r"\s*※\s*", "\n※ ", t)

    # 10) “문의처:”는 별도 줄로
    t = re.sub(r"\s*(문의처\s*:)", r"\n\1", t)

    # 11) 줄바꿈 정리
    t = re.sub(r"\n{3,}", "\n\n", t).strip()

    return t

def extract_body_text(wrap) -> str:
    raw_nl = wrap.get_text("\n", strip=True)
    if not _is_noisy_text(raw_nl):
        return _clean_text(raw_nl)

    raw_sp = wrap.get_text(" ", strip=True)
    return _normalize_broken_text(raw_sp)


def decode_data_image(data_url: str) -> tuple[str, str, bytes]:
    m = DATA_URL_RE.match(data_url.strip())
    if not m:
        raise ValueError("Invalid data:image base64 URL")

    mime = m.group(1)
    b64 = re.sub(r"\s+", "", m.group(2))
    raw = base64.b64decode(b64)

    ext = mime.split("/")[-1].lower()
    if ext == "jpeg":
        ext = "jpg"

    return mime, ext, raw


def _build_download_url(detail_url: str, atch_file_id: str, file_sn: str) -> str:
    parts = urlsplit(detail_url)
    base = f"{parts.scheme}://{parts.netloc}"
    return f"{base}/cmm/fms/FileDown.do?atchFileId={atch_file_id}&fileSn={file_sn}"


def extract_images(wrap, detail_url: str) -> tuple[list[str], list[dict]]:
    images: list[str] = []
    image_blobs: list[dict] = []

    for img in wrap.select("img[src]"):
        src = (img.get("src") or "").strip()
        if not src:
            continue
        if src.startswith("file://"):
            continue

        if src.startswith("data:image/"):
            try:
                mime, ext, raw = decode_data_image(src)
                image_blobs.append({"mime": mime, "ext": ext, "bytes": raw})
            except Exception:
                continue
            continue

        images.append(urljoin(detail_url, src))

    images = list(dict.fromkeys(images))
    return images, image_blobs


def extract_files(soup, detail_url: str) -> list[str]:
    files: list[str] = []
    file_box = soup.select_one(".board_file")
    if not file_box:
        return []

    for a in file_box.select("a[href]"):
        href = (a.get("href") or "").strip()
        if not href:
            continue
        if href.lower().startswith("javascript:"):
            m = DOWN_RE.search(href)
            if m:
                files.append(_build_download_url(detail_url, m.group(1), m.group(2)))
        else:
            files.append(urljoin(detail_url, href))

    for a in file_box.select("a[onclick]"):
        onclick = a.get("onclick") or ""
        m = DOWN_RE.search(onclick)
        if m:
            files.append(_build_download_url(detail_url, m.group(1), m.group(2)))

    return list(dict.fromkeys(files))


def parse_notice_detail_html(html: str, detail_url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    wrap = soup.select_one(".view_wrap") or soup.body
    if wrap is None:
        return {"text": "", "images": [], "image_blobs": [], "files": []}

    # 불필요 요소 제거
    for bad in wrap.select(".view_subject, .meta"):
        bad.decompose()
    for tag in wrap.select("script, style, noscript"):
        tag.decompose()

    # 본문
    body_text = extract_body_text(wrap)

    # 이미지(본문 안)
    images, image_blobs = extract_images(wrap, detail_url)

    # 첨부파일(보통 wrap 밖에 있을 수도 있어서 soup 기준)
    files = extract_files(soup, detail_url)

    return {
        "text": body_text,
        "images": images,
        "image_blobs": image_blobs,
        "files": files,
    }
