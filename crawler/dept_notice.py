# crawlers/dept_notice.py
import re
import requests
from bs4 import BeautifulSoup
import truststore
from models.notice import Notice

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


def fetch_dept_notices(list_url: str, limit: int = 10) -> list[Notice]:
    truststore.inject_into_ssl()
    res = requests.get(list_url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
    res.raise_for_status()
    if not res.encoding:
        res.encoding = res.apparent_encoding

    # res.text 에 결과 전체가 담김 -> 결과 에서 내가 개수를 정해서 분리해야함
    soup = BeautifulSoup(res.text, "html.parser")

    notices: list[Notice] = []
    seen_ids: set[str] = set()

    for tr in soup.select("table tbody tr"):
        # print(f"tr확인하기{tr}")
        td_num2 = tr.select_one("td.td_num2")
        if not td_num2:
            continue
        # 상단 공지글 분별하는 로직
        num_text = td_num2.get_text(strip=True)
        if not num_text.isdigit():
            continue
        # print(f"이미지 확인하기{num_text}")

        # td 안 subject요소 가져오기
        subject_td = tr.select_one("td.td_subject")
        # print(f"-----------{subject_td}")

        if not subject_td:
            continue
        onclick = subject_td.get("onclick", "")
        m = ONCLICK_RE.search(onclick)

        if not m:
            continue

        bbs_id, ntt_id = m.group(1), m.group(2)
        notice_id = ntt_id

        full_url = f"https://www.yc.ac.kr/smartsw/web/cop/bbs/selectBoardArticle.do?bbsId={bbs_id}&nttId={ntt_id}"

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
