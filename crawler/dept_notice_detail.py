# crawlers/school_notice_detail.py
from urllib.parse import urljoin, urlsplit
import re
import requests
import base64
from bs4 import BeautifulSoup

# javascript:fn_egov_downFile('ATCH_FILE_ID','1');
DOWN_RE = re.compile(
    r"fn_egov_downFile\(\s*'([^']+)'\s*,\s*'([^']+)'\s*\)", re.IGNORECASE
)

# data:image/png;base64,....
DATA_URL_RE = re.compile(r"^data:(image/[a-zA-Z0-9.+-]+);base64,(.+)$", re.DOTALL)


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


def _clean_text(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def _extract_body_text(wrap) -> str:
    raw_nl = wrap.get_text("\n", strip=True)
    if not _is_noisy_text(raw_nl):
        return _clean_text(raw_nl)

    raw_sp = wrap.get_text(" ", strip=True)
    return _normalize_broken_text(raw_sp)


def _build_download_url(detail_url: str, atch_file_id: str, file_sn: str) -> str:
    parts = urlsplit(detail_url)
    base = f"{parts.scheme}://{parts.netloc}"
    return f"{base}/cmm/fms/FileDown.do?atchFileId={atch_file_id}&fileSn={file_sn}"


def decode_data_image(data_url: str):
    """
    return: (mime, ext, bytes)
    """
    m = DATA_URL_RE.match(data_url.strip())
    if not m:
        raise ValueError("Invalid data:image base64 URL")

    mime = m.group(1)  # e.g. image/png
    b64 = m.group(2)

    # base64 문자열 내 공백/개행 제거
    b64 = re.sub(r"\s+", "", b64)

    raw = base64.b64decode(b64)

    ext = mime.split("/")[-1].lower()
    if ext == "jpeg":
        ext = "jpg"

    return mime, ext, raw


def _cell_text(cell) -> str:
    t = cell.get_text(" ", strip=True)
    # 예: "16:10~16~:25" 같은 오타/깨짐 정리(필요시 확장)
    t = re.sub(r"(\d{1,2}):(\d{2})\s*~\s*(\d{1,2})\s*~\s*:(\d{2})", r"\1:\2~\3:\4", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _table_to_grid(table) -> list[list[str]]:
    grid = []
    span_map = {}  # col_idx -> [text, remaining_rows]

    for tr in table.find_all("tr"):
        row = []
        col = 0

        def fill_spans_until():
            nonlocal col, row
            while col in span_map:
                txt, remain = span_map[col]
                row.append(txt)
                remain -= 1
                if remain <= 0:
                    del span_map[col]
                else:
                    span_map[col] = [txt, remain]
                col += 1

        fill_spans_until()

        cells = tr.find_all(["th", "td"])
        for cell in cells:
            fill_spans_until()

            txt = _cell_text(cell)
            rs = int(cell.get("rowspan", 1) or 1)
            cs = int(cell.get("colspan", 1) or 1)

            for i in range(cs):
                row.append(txt if i == 0 else "")
                if rs > 1:
                    span_map[col + i] = [txt, rs - 1]
            col += cs

        # 행 끝에서도 남은 span이 있으면 채워서 열 수 맞추기
        fill_spans_until()

        grid.append(row)

    # 행별 열 개수 맞추기
    max_cols = max((len(r) for r in grid), default=0)
    for r in grid:
        if len(r) < max_cols:
            r.extend([""] * (max_cols - len(r)))
    return grid


def _grid_to_codeblock(grid: list[list[str]], max_width: int = 80) -> str:
    if not grid:
        return ""

    # 너무 긴 셀은 자르기
    def clip(s: str, n: int = 24) -> str:
        s = s or ""
        return s if len(s) <= n else (s[: n - 1] + "…")

    clipped = [[clip(c) for c in row] for row in grid]

    cols = len(clipped[0])
    widths = [0] * cols
    for row in clipped:
        for i, c in enumerate(row):
            widths[i] = max(widths[i], len(c))

    # 전체 폭 너무 넓으면 폭 제한
    total = sum(widths) + (3 * (cols - 1))
    if total > max_width:
        # 폭이 큰 컬럼부터 조금씩 줄이기
        order = sorted(range(cols), key=lambda i: widths[i], reverse=True)
        while total > max_width and order:
            i = order[0]
            if widths[i] <= 6:
                order.pop(0)
                continue
            widths[i] -= 1
            total = sum(widths) + (3 * (cols - 1))

    def fmt_row(row):
        out = []
        for i, c in enumerate(row):
            c = clip(c, widths[i])  # 최종 폭에 맞춰 클립
            out.append(c.ljust(widths[i]))
        return " | ".join(out)

    lines = []
    lines.append(fmt_row(clipped[0]))
    lines.append("-" * min(max_width, len(lines[0])))
    for r in clipped[1:]:
        lines.append(fmt_row(r))

    return "```text\n" + "\n".join(lines) + "\n```"


def fetch_notice_detail(detail_url: str) -> dict:
    res = requests.get(detail_url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
    res.raise_for_status()
    if not res.encoding:
        res.encoding = res.apparent_encoding

    soup = BeautifulSoup(res.text, "html.parser")

    wrap = soup.select_one(".view_wrap") or soup.body
    if wrap is None:
        return {"text": "", "images": [], "image_blobs": [], "files": []}

    for bad in wrap.select(".view_subject, .meta"):
        bad.decompose()

    for tag in wrap.select("script, style, noscript"):
        tag.decompose()

        # ✅ table 먼저 따로 추출 (표 있는 공지만 처리)
    table_blocks = []
    for table in wrap.find_all("table"):
        try:
            grid = _table_to_grid(table)
            block = _grid_to_codeblock(grid, max_width=90)
            if block:
                table_blocks.append(block)
        except Exception:
            pass
        table.decompose()  # 본문 텍스트에서 표 제거 (중복/깨짐 방지)

    body_text = _extract_body_text(wrap)

    if table_blocks:
        body_text = (body_text + "\n\n📋 일정표\n" + "\n".join(table_blocks)).strip()

    # ✅ 이미지 처리: URL 이미지 + data:image(base64) 분리
    images: list[str] = []
    image_blobs: list[dict] = []

    for img in wrap.select("img[src]"):
        src = (img.get("src") or "").strip()
        if not src:
            continue

        # 1) 로컬 file:// 은 서버/봇에서 가져오기 불가 → 제외
        if src.startswith("file://"):
            continue

        # 2) data:image/...;base64,... → 디코딩해서 bytes로 보관
        if src.startswith("data:image/"):
            try:
                mime, ext, raw = decode_data_image(src)
                image_blobs.append({"mime": mime, "ext": ext, "bytes": raw})
            except Exception:
                # 디코딩 실패 시 스킵(필요하면 로그)
                continue
            continue

        # 3) 나머지 → 절대 URL로 통일
        images.append(urljoin(detail_url, src))

    # 중복 제거(순서 유지)
    images = list(dict.fromkeys(images))

    # ✅ 첨부파일 처리
    files: list[str] = []
    file_box = soup.select_one(".board_file")
    if file_box:
        for a in file_box.select("a[href]"):
            href = (a.get("href") or "").strip()
            if not href:
                continue

            if href.lower().startswith("javascript:"):
                m = DOWN_RE.search(href)
                if m:
                    atch_id, sn = m.group(1), m.group(2)
                    files.append(_build_download_url(detail_url, atch_id, sn))
            else:
                files.append(urljoin(detail_url, href))

        for a in file_box.select("a[onclick]"):
            onclick = a.get("onclick", "")
            m = DOWN_RE.search(onclick)
            if m:
                atch_id, sn = m.group(1), m.group(2)
                files.append(_build_download_url(detail_url, atch_id, sn))

    files = list(dict.fromkeys(files))

    # ✅ watcher에서 쓰는 키 포함해서 반환
    return {
        "text": body_text,
        "images": images,  # URL 이미지
        "image_blobs": image_blobs,  # data:image 디코딩 이미지
        "files": files,
    }
