# config.py
import os
from dotenv import load_dotenv

load_dotenv() #프로젝트 루트의 .env 로드
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

ROLE_ID_TEST = "1366421630510698509"
ROLE_ID_1 = "1354021351249154118"
ROLE_ID_2 = "1354021325122830407"
ROLE_ID_3 = "1370075952255602809"
ROLE_ID_4 = "1370075971901980703"

#학교 공지
SCHOOL_NOTICE_URL = "https://www.yc.ac.kr/yonam/web/cop/bbs/selectBoardList.do?bbsId=BBSMSTR_000000000590"
SCHOOL_NOTICE_CHANNEL_ID = 1325088325492805684
CHECK_INTERVAL_SECONDS = 3600
STATE_FILE = "state.json"
#학과 공지
DEPT_NOTICE_URL = "https://www.yc.ac.kr/smartsw/web/cop/bbs/selectBoardList.do?bbsId=BBSMSTR_000000000565"