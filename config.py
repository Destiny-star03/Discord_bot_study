# config.py
import os
from dotenv import load_dotenv

load_dotenv() #프로젝트 루트의 .env 로드
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
COMMAND_PREFIX = "?"

#학교 공지
SCHOOL_NOTICE_URL = "https://www.yc.ac.kr/yonam/web/cop/bbs/selectBoardList.do?bbsId=BBSMSTR_000000000590"

#학과 공지
DEPT_NOTICE_URL = "https://www.yc.ac.kr/smartsw/web/cop/bbs/selectBoardList.do?bbsId=BBSMSTR_000000000565"