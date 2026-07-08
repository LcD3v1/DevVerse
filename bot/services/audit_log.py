from __future__ import annotations

from dataclasses import dataclass, field

import discord

from bot.utils import utcnow


AUDIT_CHANNEL_NAME = "bot-auditoria"


@dataclass(slots=True)
class AuditReport:
    title: str
    actor: str
    added: list[str] = field(default_factory=list)
    changed: list[str] = field(default_factory=list)
    reused: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    summary: str = ""


async def ensure_audit_channel(guild: discord.Guild) -> discord.TextChannel | None:
    channel = discord.utils.get(guild.text_channels, name=AUDIT_CHANNEL_NAME)
    overwrites = _admin_only_overwrites(guild)
    if channel:
        try:
            await channel.edit(overwrites=overwrites, reason="DevVerse audit channel permissions")
        except discord.HTTPException:
            return channel
        return channel
    try:
        return await guild.create_text_channel(AUDIT_CHANNEL_NAME, overwrites=overwrites, reason="DevVerse audit channel")
    except discord.HTTPException:
        return None


async def send_audit_report(guild: discord.Guild, report: AuditReport) -> None:
    channel = await ensure_audit_channel(guild)
    if not channel:
        return
    embed = discord.Embed(title=report.title, description=report.summary or None, color=discord.Color.dark_teal(), timestamp=utcnow())
    embed.add_field(name="Executado por", value=report.actor, inline=False)
    _add_section(embed, "Adicionados", report.added)
    _add_section(embed, "Alterados", report.changed)
    _add_section(embed, "Reutilizados", report.reused)
    _add_section(embed, "Removidos", report.removed)
    _add_section(embed, "Erros", report.errors)
    embed.set_footer(text="DevVerse Audit Log")
    await channel.send(embed=embed)


def _admin_only_overwrites(guild: discord.Guild) -> dict[discord.abc.Snowflake, discord.PermissionOverwrite]:
    overwrites: dict[discord.abc.Snowflake, discord.PermissionOverwrite] = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
    }
    if guild.me:
        overwrites[guild.me] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
    for role in guild.roles:
        if role.is_default():
            continue
        if role.permissions.administrator or role.permissions.manage_guild:
            overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        if len(overwrites) >= 20:
            break
    return overwrites


def _add_section(embed: discord.Embed, title: str, values: list[str]) -> None:
    text = "\n".join(f"- {value}" for value in values[:20]) if values else "Nenhum"
    if len(values) > 20:
        text += f"\n... mais {len(values) - 20}"
    embed.add_field(name=title, value=text[:1024], inline=False)

