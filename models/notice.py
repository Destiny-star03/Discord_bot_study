# models/notice.py
from dataclasses import dataclass

@dataclass
class Notice:
    notice_id: str
    title: str
    url: str
    dept: str | None = None        # td_name
    views: int | None = None       # td_num
    date: str | None = None        # td_datetime

@dataclass(frozen=True)
class notice_id:
    notice_id: str
    title: str
    url: str
    dept: str | None = None
    views: int | None = None
    date: str | None = None