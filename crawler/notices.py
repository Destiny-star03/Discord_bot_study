# crawlers/notices.py
import re
from urllib.parse import urlsplit

from bs4 import BeautifulSoup
from models.notice import Notice
from utils.http_client import get as http_get


ONCLICK_RE = re.compile(
    r"(?:javascript:\s*)?"
    r"fn_egov_inqire_notice(?:_mbldn)?"
    r"\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]([^'\"]+)['\"]\s*(?:,\s*this\s*)?\)\s*;?",
    re.IGNORECASE,
)


def _to_int_or_none(text: str) -> int | None:
    try:
        return int(text.strip().replace(",", ""))
    except Exception:
        return None


def _build_detail_url(list_url: str, bbs_id: str, ntt_id: str) -> str:
    """
    list_url(학교/학과) 기준으로 같은 경로의 selectBoardArticle.do로 조합
    예) .../web/cop/bbs/selectBoardList.do -> .../web/cop/bbs/selectBoardArticle.do
    """
    parts = urlsplit(list_url)
    base = f"{parts.scheme}://{parts.netloc}"

    path = parts.path
    if path.endswith("selectBoardList.do"):
        path = path.replace("selectBoardList.do", "selectBoardArticle.do")
    else:
        path = path.rsplit("/", 1)[0] + "/selectBoardArticle.do"

    return f"{base}{path}?bbsId={bbs_id}&nttId={ntt_id}"


def _extract_onclick(subject_td) -> str:
    """
    onclick이 td에 없고 내부 요소(a/span 등)에 걸려있는 경우도 대응
    """
    onclick = (subject_td.get("onclick") or "").strip()
    if onclick:
        return onclick

    inner = subject_td.select_one("[onclick]")
    return (inner.get("onclick") or "").strip() if inner else ""


def fetch_notices(list_url: str, limit: int = 10) -> list[Notice]:
    res = http_get(list_url, timeout=15)
    res.raise_for_status()
    if not res.encoding:
        res.encoding = res.apparent_encoding

    soup = BeautifulSoup(res.text, "html.parser")

    notices: list[Notice] = []
    seen_ids: set[str] = set()

    for tr in soup.select("table tbody tr"):
        td_num2 = tr.select_one("td.td_num2")
        if not td_num2:
            continue

        num_text = td_num2.get_text(strip=True)
        if not num_text.isdigit():
            continue

        subject_td = tr.select_one("td.td_subject")
        if not subject_td:
            continue

        onclick = _extract_onclick(subject_td)
        m = ONCLICK_RE.search(onclick)
        if not m:
            continue

        bbs_id, ntt_id = m.group(1), m.group(2)
        notice_id = ntt_id
        if notice_id in seen_ids:
            continue
        seen_ids.add(notice_id)

        for tag in subject_td.select("a.new_icon"):
            tag.decompose()

        title = subject_td.get_text(" ", strip=True)
        if not title:
            continue

        dept_el = tr.select_one("td.td_name")
        views_el = tr.select_one("td.td_num")
        date_el = tr.select_one("td.td_datetime")

        dept = dept_el.get_text(strip=True) if dept_el else None
        views = _to_int_or_none(views_el.get_text()) if views_el else None
        date = date_el.get_text(strip=True) if date_el else None

        full_url = _build_detail_url(list_url, bbs_id, ntt_id)

        notices.append(
            Notice(
                notice_id=notice_id,
                title=title,
                url=full_url,
                dept=dept,
                views=views,
                date=date,
            )
        )

        if len(notices) >= limit:
            break

    return notices


# ── 기존 인터페이스 유지용 wrapper ──
def fetch_school_notices(list_url: str, limit: int = 10) -> list[Notice]:
    return fetch_notices(list_url, limit)


def fetch_dept_notices(list_url: str, limit: int = 10) -> list[Notice]:
    return fetch_notices(list_url, limit)
