from crawler.school_notice_detail import fetch_notice_detail
import truststore

truststore.inject_into_ssl()

u = "https://www.yc.ac.kr/yonam/web/cop/bbs/selectBoardArticle.do?bbsId=BBSMSTR_000000000590&nttId=79220"
d = fetch_notice_detail(u)
print("files:", d["files"])
print("text head:", d["text"][:200])
