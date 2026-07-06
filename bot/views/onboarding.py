from __future__ import annotations

import discord


PROFILE_OPTIONS = {
    "student": ("\U0001f393", "Estudante", "Estudante"),
    "mentor": ("\U0001f9d1\u200d\U0001f3eb", "Mentor", "Mentor"),
    "professional": ("\U0001f4bc", "Profissional", "Profissional"),
}

AREA_OPTIONS = {
    "frontend": ("\U0001f4bb", "Frontend", "Frontend Developer"),
    "backend": ("\u2699\ufe0f", "Backend", "Backend Developer"),
    "fullstack": ("\U0001f310", "Full Stack", "Full Stack Developer"),
    "mobile": ("\U0001f4f1", "Mobile", "Mobile Developer"),
    "ai": ("\U0001f916", "Inteligencia Artificial", "AI Developer"),
    "data": ("\U0001f4ca", "Data Science", "Data Science Developer"),
    "cybersecurity": ("\U0001f510", "Cybersecurity", "Cybersecurity Developer"),
    "cloud": ("\u2601\ufe0f", "Cloud", "Cloud Developer"),
    "gamedev": ("\U0001f3ae", "Game Development", "Game Developer"),
}

LEVEL_OPTIONS = {
    "beginner": ("\U0001f331", "Iniciante", "Beginner Developer"),
    "studying": ("\U0001f4da", "Estudando", "Learning Developer"),
    "junior": ("\U0001f9d1\u200d\U0001f4bb", "Junior", "Junior Developer"),
    "mid": ("\U0001f680", "Pleno", "Mid Developer"),
    "senior": ("\u2b50", "Senior", "Senior Developer"),
}


class OnboardingButton(discord.ui.Button):
    def __init__(self, group: str, key: str, emoji: str, label: str) -> None:
        super().__init__(
            label=label,
            emoji=emoji,
            style=discord.ButtonStyle.secondary,
            custom_id=f"devverse_onboarding:{group}:{key}",
        )
        self.group = group
        self.key = key

    async def callback(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("Use dentro do servidor.", ephemeral=True)
            return
        option_map = {"profile": PROFILE_OPTIONS, "area": AREA_OPTIONS, "level": LEVEL_OPTIONS}[self.group]
        _, label, role_name = option_map[self.key]
        assigned = await self._sync_role(interaction.user, interaction.guild, role_name, [value[2] for value in option_map.values()])
        await self._save_profile(interaction, label if assigned else "")
        message = f"Perfil atualizado: {label}" if assigned else f"Perfil removido: {label}"
        await interaction.response.send_message(message, ephemeral=True, delete_after=8)

    async def _sync_role(self, member: discord.Member, guild: discord.Guild, role_name: str, group_roles: list[str]) -> bool:
        role = discord.utils.get(guild.roles, name=role_name)
        if not role:
            role = await guild.create_role(name=role_name, reason="DevVerse onboarding")
        if role in member.roles:
            await member.remove_roles(role, reason="DevVerse onboarding role remove")
            return False
        to_remove = [existing for existing in member.roles if existing.name in group_roles and existing.name != role_name]
        if to_remove:
            await member.remove_roles(*to_remove, reason="DevVerse onboarding role swap")
        await member.add_roles(role, reason="DevVerse onboarding role")
        return True

    async def _save_profile(self, interaction: discord.Interaction, label: str) -> None:
        field = {"profile": "role_type", "area": "area", "level": "level"}[self.group]
        await interaction.client.db.execute(
            f"""
            INSERT INTO user_profiles (user_id, {field}) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET {field} = excluded.{field}
            """,
            (interaction.user.id, label),
        )


class OnboardingView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)
        for key, (emoji, label, _) in PROFILE_OPTIONS.items():
            self.add_item(OnboardingButton("profile", key, emoji, label))
        for key, (emoji, label, _) in AREA_OPTIONS.items():
            self.add_item(OnboardingButton("area", key, emoji, label))
        for key, (emoji, label, _) in LEVEL_OPTIONS.items():
            self.add_item(OnboardingButton("level", key, emoji, label))


ALL_ONBOARDING_ROLES = [
    *(value[2] for value in PROFILE_OPTIONS.values()),
    *(value[2] for value in AREA_OPTIONS.values()),
    *(value[2] for value in LEVEL_OPTIONS.values()),
]
