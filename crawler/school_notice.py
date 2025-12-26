# # crawlers/school_notice.py
# import re
# from urllib.parse import urlsplit

# import requests
# from bs4 import BeautifulSoup
# import truststore
# from models.notice import Notice

# ONCLICK_RE = re.compile(
#     r"(?:javascript:\s*)?"
#     r"fn_egov_inqire_notice(?:_mbldn)?"
#     r"\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]([^'\"]+)['\"]\s*(?:,\s*this\s*)?\)\s*;?",
#     re.IGNORECASE,
# )


# def _to_int_or_none(text: str) -> int | None:
#     try:
#         return int(text.strip().replace(",", ""))
#     except Exception:
#         return None


# def _build_detail_url(list_url: str, bbs_id: str, ntt_id: str) -> str:
#     """
#     list_url(학교/학과)를 기준으로 같은 경로의 selectBoardArticle.do로 자동 조합
#     예) .../yonam/web/cop/bbs/selectBoardList.do  -> .../yonam/web/cop/bbs/selectBoardArticle.do
#     """
#     parts = urlsplit(list_url)
#     base = f"{parts.scheme}://{parts.netloc}"

#     # list_url 경로에서 List.do만 Article.do로 교체
#     path = parts.path
#     if path.endswith("selectBoardList.do"):
#         path = path.replace("selectBoardList.do", "selectBoardArticle.do")
#     else:
#         # 혹시 경로가 달라도 최소한 bbs 폴더로 붙이기
#         # (필요시 조정)
#         path = path.rsplit("/", 1)[0] + "/selectBoardArticle.do"

#     return f"{base}{path}?bbsId={bbs_id}&nttId={ntt_id}"


# def fetch_school_notices(list_url: str, limit: int = 10) -> list[Notice]:
#     truststore.inject_into_ssl()
#     res = requests.get(list_url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
#     res.raise_for_status()
#     if not res.encoding:
#         res.encoding = res.apparent_encoding

#     # res.text 에 결과 전체가 담김 -> 결과 에서 내가 개수를 정해서 분리해야함
#     soup = BeautifulSoup(res.text, "html.parser")

#     notices: list[Notice] = []
#     seen_ids: set[str] = set()

#     for tr in soup.select("table tbody tr"):
#         td_num2 = tr.select_one("td.td_num2")
#         if not td_num2:
#             continue

#         # 상단 공지(아이콘/빈값) 제외
#         num_text = td_num2.get_text(strip=True)
#         if not num_text.isdigit():
#             continue

#         subject_td = tr.select_one("td.td_subject")
#         if not subject_td:
#             continue

#         # ✅ (수정1) onclick이 td에 없으면 td 내부의 아무 요소나 찾아서 가져오기
#         onclick = subject_td.get("onclick", "")
#         if not onclick:
#             inner = subject_td.select_one("[onclick]")
#             onclick = inner.get("onclick", "") if inner else ""

#         m = ONCLICK_RE.search(onclick)
#         if not m:
#             continue

#         bbs_id, ntt_id = m.group(1), m.group(2)
#         notice_id = ntt_id

#         # ✅ (수정2) list_url 기반으로 상세 URL 자동 생성
#         full_url = _build_detail_url(list_url, bbs_id, ntt_id)

#         if notice_id in seen_ids:
#             continue
#         seen_ids.add(notice_id)

#         for tag in subject_td.select("a.new_icon"):
#             tag.decompose()

#         title = subject_td.get_text(" ", strip=True)
#         if not title:
#             continue

#         dept_el = tr.select_one("td.td_name")
#         views_el = tr.select_one("td.td_num")
#         date_el = tr.select_one("td.td_datetime")

#         dept = dept_el.get_text(strip=True) if dept_el else None
#         views = _to_int_or_none(views_el.get_text()) if views_el else None
#         date = date_el.get_text(strip=True) if date_el else None

#         notices.append(
#             Notice(
#                 notice_id=notice_id,
#                 title=title,
#                 url=full_url,
#                 dept=dept,
#                 views=views,
#                 date=date,
#             )
#         )

#         if len(notices) >= limit:
#             break

#     return notices
