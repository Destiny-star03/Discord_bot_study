# ui/role_embed.py
import discord

def build_role_embed() -> discord.Embed:
    e = discord.Embed(
        title="학년 선택",
        description="아래 버튼을 눌러 본인 학년 역할을 선택하세요.\n(변경도 가능)",
    )
    return e
