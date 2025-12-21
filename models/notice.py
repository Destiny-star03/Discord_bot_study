# models/notice.py
from dataclasses import dataclass

@dataclass
class Notice:
    title: str
    url: str
    date: str | None = None