from __future__ import annotations

import discord

from bot.templates import ROLE_GROUPS


class RoleSelect(discord.ui.Select):
    def __init__(self, group: str) -> None:
        options = [discord.SelectOption(label=name[:100], value=name) for name in ROLE_GROUPS[group]][:25]
        super().__init__(
            placeholder=group,
            min_values=0,
            max_values=len(options),
            options=options,
            custom_id=f"devverse_roles:{group}",
        )
        self.group = group

    async def callback(self, interaction: discord.Interaction) -> None:
        if not isinstance(interaction.user, discord.Member) or not interaction.guild:
            await interaction.response.send_message("Use este menu dentro do servidor.", ephemeral=True)
            return
        selected = set(self.values)
        available = {role.name: role for role in interaction.guild.roles if role.name in ROLE_GROUPS[self.group]}
        added, removed = [], []
        for role_name, role in available.items():
            if role_name in selected and role not in interaction.user.roles:
                await interaction.user.add_roles(role, reason="DevVerse role panel")
                added.append(role.name)
            elif role_name not in selected and role in interaction.user.roles:
                await interaction.user.remove_roles(role, reason="DevVerse role panel")
                removed.append(role.name)
        parts = []
        if added:
            parts.append("Adicionados: " + ", ".join(added))
        if removed:
            parts.append("Removidos: " + ", ".join(removed))
        await interaction.response.send_message("\n".join(parts) or "Nada mudou.", ephemeral=True)


class RolePanelView(discord.ui.View):
    def __init__(self, groups: list[str]) -> None:
        super().__init__(timeout=None)
        for group in groups:
            self.add_item(RoleSelect(group))
