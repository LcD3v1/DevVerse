from __future__ import annotations

import time
from collections import defaultdict, deque
from datetime import timedelta

import discord
from discord import app_commands
from discord.ext import commands

from bot.permissions import admin_check
from bot.utils import make_embed


class ModerationCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.messages: dict[tuple[int, int], deque[float]] = defaultdict(lambda: deque(maxlen=8))
        self.warned: set[tuple[int, int]] = set()

    @app_commands.command(name="warn", description="Adiciona aviso a um membro.")
    @admin_check()
    async def warn(self, interaction: discord.Interaction, membro: discord.Member, motivo: str) -> None:
        await self.bot.db.execute("INSERT INTO warnings (guild_id, user_id, moderator_id, reason) VALUES (?, ?, ?, ?)", (interaction.guild.id, membro.id, interaction.user.id, motivo))
        await interaction.response.send_message(embed=make_embed("Aviso registrado", f"{membro.mention}: {motivo}"))

    @app_commands.command(name="warnings", description="Lista avisos de um membro.")
    @admin_check()
    async def warnings(self, interaction: discord.Interaction, membro: discord.Member) -> None:
        rows = await self.bot.db.fetchall("SELECT reason, created_at FROM warnings WHERE guild_id = ? AND user_id = ? ORDER BY id DESC LIMIT 10", (interaction.guild.id, membro.id))
        lines = [f"- {r['created_at']}: {r['reason']}" for r in rows]
        await interaction.response.send_message(embed=make_embed(f"Avisos de {membro.display_name}", "\n".join(lines) or "Sem avisos."))

    @app_commands.command(name="clear", description="Limpa mensagens recentes.")
    @admin_check()
    async def clear(self, interaction: discord.Interaction, quantidade: app_commands.Range[int, 1, 100]) -> None:
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("Use em canal de texto.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=quantidade)
        await interaction.followup.send(f"Mensagens apagadas: {len(deleted)}", ephemeral=True)

    @app_commands.command(name="timeout", description="Aplica timeout em um membro.")
    @admin_check()
    async def timeout(self, interaction: discord.Interaction, membro: discord.Member, minutos: int, motivo: str = "Moderação") -> None:
        await membro.timeout(timedelta(minutes=minutos), reason=motivo)
        await interaction.response.send_message(embed=make_embed("Timeout aplicado", f"{membro.mention} por {minutos} min. Motivo: {motivo}"))

    @app_commands.command(name="kick", description="Expulsa um membro.")
    @admin_check()
    async def kick(self, interaction: discord.Interaction, membro: discord.Member, motivo: str = "Moderação") -> None:
        await membro.kick(reason=motivo)
        await interaction.response.send_message(embed=make_embed("Membro expulso", f"{membro} — {motivo}"))

    @app_commands.command(name="ban", description="Bane um membro.")
    @admin_check()
    async def ban(self, interaction: discord.Interaction, membro: discord.Member, motivo: str = "Moderação") -> None:
        await membro.ban(reason=motivo)
        await interaction.response.send_message(embed=make_embed("Membro banido", f"{membro} — {motivo}"))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or not message.guild or not isinstance(message.author, discord.Member):
            return
        key = (message.guild.id, message.author.id)
        now = time.monotonic()
        bucket = self.messages[key]
        bucket.append(now)
        recent = [stamp for stamp in bucket if now - stamp <= 8]
        if len(recent) < 6:
            return
        if key not in self.warned:
            self.warned.add(key)
            await message.channel.send(f"{message.author.mention}, cuidado com spam.", delete_after=10)
            return
        try:
            await message.author.timeout(timedelta(minutes=2), reason="Anti-spam DevVerse")
            await message.channel.send(f"{message.author.mention} recebeu timeout curto por spam.", delete_after=10)
        except discord.Forbidden:
            pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ModerationCog(bot))
