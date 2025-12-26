# crawlers/school_notice_detail.py
from utils.http_client import get as http_get
from crawler.notice_detail_parser import parse_notice_detail_html


def fetch_notice_detail(detail_url: str) -> dict:
    res = http_get(detail_url, timeout=15)
    res.raise_for_status()
    if not res.encoding:
        res.encoding = res.apparent_encoding

    return parse_notice_detail_html(res.text, detail_url)
