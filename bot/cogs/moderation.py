from __future__ import annotations

import asyncio
import re
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands

from bot.permissions import admin_check
from bot.utils import make_embed


class ClearConfirmView(discord.ui.View):
    def __init__(self, author_id: int, timeout: float = 45) -> None:
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.confirmed: bool | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Somente quem iniciou a limpeza pode confirmar.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Confirmar", emoji="\u2705", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.confirmed = True
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="Cancelar", emoji="\u274c", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.confirmed = False
        await interaction.response.defer()
        self.stop()


class ModerationCog(commands.Cog):
    clear_group = app_commands.Group(name="clear", description="Limpa mensagens com confirmacao.")

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

    @clear_group.command(name="quantidade", description="Apaga as ultimas mensagens do canal atual.")
    async def clear_quantidade(self, interaction: discord.Interaction, quantidade: app_commands.Range[int, 1, 500]) -> None:
        channel = await self._validate_clear_request(interaction)
        if not channel:
            return
        await interaction.response.defer(ephemeral=True)
        messages = [message async for message in channel.history(limit=quantidade)]
        await self._confirm_and_delete(interaction, channel, messages, "quantidade", f"{len(messages)} mensagens")

    @clear_group.command(name="tempo", description="Apaga mensagens dentro do periodo informado, como 30m, 1h, 24h ou 7d.")
    async def clear_tempo(self, interaction: discord.Interaction, tempo: str) -> None:
        channel = await self._validate_clear_request(interaction)
        if not channel:
            return
        delta = self._parse_duration(tempo)
        if not delta:
            await interaction.response.send_message("Formato invalido. Use `30m`, `1h`, `24h` ou `7d`.", ephemeral=True, delete_after=8)
            return
        await interaction.response.defer(ephemeral=True)
        since = datetime.now(timezone.utc) - delta
        messages = [message async for message in channel.history(limit=None, after=since)]
        await self._confirm_and_delete(interaction, channel, messages, "tempo", f"{tempo} ({len(messages)} mensagens)")

    @clear_group.command(name="usuario", description="Apaga mensagens de um usuario especifico no canal atual.")
    async def clear_usuario(self, interaction: discord.Interaction, usuario: discord.Member) -> None:
        channel = await self._validate_clear_request(interaction)
        if not channel:
            return
        await interaction.response.defer(ephemeral=True)
        messages = [message async for message in channel.history(limit=None) if message.author.id == usuario.id]
        await self._confirm_and_delete(interaction, channel, messages, "usuario", f"{usuario.mention} ({len(messages)} mensagens)")

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

    async def _validate_clear_request(self, interaction: discord.Interaction) -> discord.TextChannel | None:
        if not interaction.guild or not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("Use este comando em um canal de texto do servidor.", ephemeral=True, delete_after=8)
            return None
        if not isinstance(interaction.user, discord.Member) or not (
            interaction.user.guild_permissions.administrator or interaction.user.guild_permissions.manage_messages
        ):
            await interaction.response.send_message("\u274c Você não tem permissão para usar este comando.", ephemeral=True, delete_after=8)
            return None
        bot_member = interaction.guild.me
        if not bot_member or not interaction.channel.permissions_for(bot_member).manage_messages:
            await interaction.response.send_message("Não consigo limpar mensagens neste canal sem a permissão `Manage Messages`.", ephemeral=True, delete_after=10)
            return None
        return interaction.channel

    async def _confirm_and_delete(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        messages: list[discord.Message],
        action: str,
        quantity_label: str,
    ) -> None:
        if not messages:
            if interaction.response.is_done():
                await self._finish_temporary(interaction, "Nenhuma mensagem encontrada para limpar.")
            else:
                await interaction.response.send_message("Nenhuma mensagem encontrada para limpar.", ephemeral=True, delete_after=8)
            return
        view = ClearConfirmView(interaction.user.id)
        embed = make_embed(
            "\u26a0\ufe0f Confirma limpeza?",
            f"Canal:\n{channel.mention}\n\nQuantidade:\n{quantity_label}\n\nConfirmar:\n\u2705\n\nCancelar:\n\u274c",
            discord.Color.orange(),
        )
        if interaction.response.is_done():
            await interaction.edit_original_response(embed=embed, view=view)
        else:
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        await view.wait()
        if not view.confirmed:
            await self._finish_temporary(interaction, "Limpeza cancelada.")
            return
        try:
            deleted = await self._delete_messages(channel, messages)
        except discord.Forbidden:
            await self._finish_temporary(interaction, "Não tenho permissão para apagar mensagens neste canal.")
            return
        except discord.HTTPException:
            await self._finish_temporary(interaction, "O Discord recusou a limpeza. Tente uma quantidade menor.")
            return
        await self._record_moderation_log(interaction, channel, action, deleted)
        await self._send_mod_log(interaction, channel, action, deleted)
        await self._finish_temporary(interaction, f"Limpeza concluída. Mensagens apagadas: {deleted}.")

    async def _delete_messages(self, channel: discord.TextChannel, messages: list[discord.Message]) -> int:
        deleted = 0
        for message in messages:
            try:
                await message.delete()
                deleted += 1
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                continue
        return deleted

    async def _record_moderation_log(self, interaction: discord.Interaction, channel: discord.TextChannel, action: str, amount: int) -> None:
        await self.bot.db.execute(
            "INSERT INTO moderation_logs (moderator_id, channel_id, action, amount) VALUES (?, ?, ?, ?)",
            (interaction.user.id, channel.id, action, amount),
        )

    async def _send_mod_log(self, interaction: discord.Interaction, channel: discord.TextChannel, action: str, amount: int) -> None:
        if not interaction.guild:
            return
        log_channel = discord.utils.get(interaction.guild.text_channels, name="mod-logs")
        if not log_channel:
            return
        embed = make_embed("\U0001f9f9 Limpeza realizada", color=discord.Color.green())
        embed.add_field(name="Administrador", value=interaction.user.mention, inline=False)
        embed.add_field(name="Canal", value=channel.mention, inline=False)
        embed.add_field(name="Mensagens removidas", value=str(amount), inline=False)
        embed.add_field(name="Motivo", value="Limpeza manual", inline=False)
        embed.add_field(name="Tipo", value=action, inline=True)
        await log_channel.send(embed=embed)

    async def _finish_temporary(self, interaction: discord.Interaction, content: str) -> None:
        await interaction.edit_original_response(content=content, embed=None, view=None)
        asyncio.create_task(self._delete_original_later(interaction, 8))

    async def _delete_original_later(self, interaction: discord.Interaction, delay: int) -> None:
        await asyncio.sleep(delay)
        try:
            await interaction.delete_original_response()
        except (discord.NotFound, discord.HTTPException):
            pass

    def _parse_duration(self, value: str) -> timedelta | None:
        match = re.fullmatch(r"\s*(\d+)\s*([mhd])\s*", value.lower())
        if not match:
            return None
        amount = int(match.group(1))
        unit = match.group(2)
        if amount <= 0:
            return None
        if unit == "m":
            return timedelta(minutes=amount)
        if unit == "h":
            return timedelta(hours=amount)
        if unit == "d":
            return timedelta(days=amount)
        return None


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ModerationCog(bot))
