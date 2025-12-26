# utils/http_client.py
import threading
import requests
import truststore

_lock = threading.Lock()
_session: requests.Session | None = None
_inited = False


def init_http() -> None:
    """
    앱 시작 시 1회만 호출 권장.
    - truststore SSL 주입 1회
    - requests.Session 1회 생성
    """
    global _inited, _session
    if _inited:
        return

    truststore.inject_into_ssl()
    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0"})  # 기본 UA 통일
    _session = s
    _inited = True


def get(url: str, *, timeout: int = 15, referer: str | None = None, headers: dict | None = None) -> requests.Response:
    """
    Session 재사용 + 멀티스레드 안전하게 Lock으로 감싸서 요청.
    """
    if not _inited or _session is None:
        init_http()

    h = {}
    if headers:
        h.update(headers)
    if referer:
        h["Referer"] = referer

    # requests.Session은 thread-safe 보장이 약하므로 Lock으로 보호
    with _lock:
        return _session.get(url, timeout=timeout, headers=h or None)
