# ui/grade_role_view.py
import discord
from config import ROLE_ID_1, ROLE_ID_2, ROLE_ID_3, ROLE_ID_4

ROLE_MAP = {
    "grade:1": int(ROLE_ID_1),
    "grade:2": int(ROLE_ID_2),
    "grade:3": int(ROLE_ID_3),
    "grade:4": int(ROLE_ID_4),
}

ALL_ROLE_IDS = set(ROLE_MAP.values())


class GradeRoleView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def _apply_grade_role(self, interaction: discord.Interaction, target_role_id: int):
        guild = interaction.guild
        member = interaction.user

        if guild is None or not isinstance(member, discord.Member):
            await interaction.response.send_message("서버에서만 사용할 수 있어요.", ephemeral=True)
            return

        target_role = guild.get_role(target_role_id)
        if target_role is None:
            await interaction.response.send_message("역할을 찾지 못했어요. 관리자에게 문의하세요.", ephemeral=True)
            return

        # ✅ 기존 학년 역할 제거 후, 새 역할 부여 (학년 1개만 유지)
        remove_roles = [r for r in member.roles if r.id in ALL_ROLE_IDS and r.id != target_role_id]
        try:
            if remove_roles:
                await member.remove_roles(*remove_roles, reason="학년 역할 변경")
            await member.add_roles(target_role, reason="학년 역할 선택")
            await interaction.response.send_message(f"완료! `{target_role.name}` 역할을 부여했어요.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("권한이 부족해서 역할을 부여할 수 없어요.", ephemeral=True)

    @discord.ui.button(label="1학년", style=discord.ButtonStyle.primary, custom_id="grade:1")
    async def grade1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._apply_grade_role(interaction, ROLE_MAP["grade:1"])

    @discord.ui.button(label="2학년", style=discord.ButtonStyle.primary, custom_id="grade:2")
    async def grade2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._apply_grade_role(interaction, ROLE_MAP["grade:2"])

    @discord.ui.button(label="3학년", style=discord.ButtonStyle.primary, custom_id="grade:3")
    async def grade3(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._apply_grade_role(interaction, ROLE_MAP["grade:3"])

    @discord.ui.button(label="4학년", style=discord.ButtonStyle.primary, custom_id="grade:4")
    async def grade4(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._apply_grade_role(interaction, ROLE_MAP["grade:4"])
