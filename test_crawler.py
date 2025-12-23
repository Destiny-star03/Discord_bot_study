from crawler.school_notice import fetch_school_notices
from crawler.school_notice_detail import fetch_notice_detail
import truststore
url = "https://www.yc.ac.kr/yonam/web/cop/bbs/selectBoardList.do?bbsId=BBSMSTR_000000000590"

print(fetch_school_notices)
# print(f"============={fetch_notice_detail}")
truststore.inject_into_ssl()

for n in fetch_school_notices(url):
    print(n.notice_id, n.title, n.dept, n.views, n.date, n.url)



   
