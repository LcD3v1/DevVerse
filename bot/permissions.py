from __future__ import annotations

import discord
from discord import app_commands

ADMIN_ROLE_NAMES = {"👑 Owner", "🛡️ Co-Owner", "⚙️ Admin"}
MENTOR_ROLE_NAMES = {"🧑‍🏫 Mentor"}


def has_named_role(member: discord.Member, names: set[str]) -> bool:
    return any(role.name in names for role in member.roles)


def is_admin_or_owner(member: discord.Member) -> bool:
    return member.guild_permissions.administrator or has_named_role(member, ADMIN_ROLE_NAMES)


def is_mentor_or_above(member: discord.Member) -> bool:
    return is_admin_or_owner(member) or has_named_role(member, MENTOR_ROLE_NAMES)


def admin_check():
    async def predicate(interaction: discord.Interaction) -> bool:
        if isinstance(interaction.user, discord.Member) and is_admin_or_owner(interaction.user):
            return True
        raise app_commands.CheckFailure("Você precisa ser Admin ou superior.")

    return app_commands.check(predicate)
