from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.permissions import admin_check
from bot.services.audit_log import AuditReport, send_audit_report
from bot.templates import INITIAL_MESSAGES, ROLE_GROUPS, SERVER_CATEGORIES
from bot.utils import make_embed
from bot.views.confirm_view import ConfirmView


class SetupCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _ensure_role(self, guild: discord.Guild, group: str, name: str) -> discord.Role:
        existing = discord.utils.get(guild.roles, name=name)
        if existing:
            return existing
        raise ValueError(f"Cargo existente nao encontrado: {name}")

    async def _base_overwrites(self, guild: discord.Guild) -> dict[discord.Role, discord.PermissionOverwrite]:
        student = discord.utils.get(guild.roles, name="🎓 Estudante") or guild.default_role
        return {
            guild.default_role: discord.PermissionOverwrite(read_messages=True),
            student: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                use_application_commands=True,
                attach_files=True,
                connect=True,
                speak=True,
                stream=True,
            ),
        }

    async def _restricted_overwrites(self, guild: discord.Guild, channel_name: str) -> dict[discord.Role, discord.PermissionOverwrite]:
        overwrites = await self._base_overwrites(guild)
        overwrites[guild.default_role] = discord.PermissionOverwrite(read_messages=True, send_messages=False)
        allowed_names = {"👑 Owner", "🛡️ Co-Owner", "⚙️ Admin", "🧑‍🏫 Mentor"}
        if channel_name == "📜・regras":
            allowed_names.discard("🧑‍🏫 Mentor")
        for name in allowed_names:
            role = discord.utils.get(guild.roles, name=name)
            if role:
                overwrites[role] = discord.PermissionOverwrite(send_messages=True, read_messages=True)
        return overwrites

    async def _ensure_category(self, guild: discord.Guild, name: str) -> discord.CategoryChannel:
        existing = discord.utils.get(guild.categories, name=name)
        if existing:
            return existing
        category = await guild.create_category(name, reason="DevVerse setup")
        await self.bot.db.add_created_item(guild.id, "category", category.id, category.name)
        return category

    async def _ensure_channel(self, guild: discord.Guild, category: discord.CategoryChannel, name: str, kind: str) -> discord.abc.GuildChannel:
        existing = discord.utils.get(category.channels, name=name)
        if existing:
            return existing
        overwrites = await self._restricted_overwrites(guild, name) if name in {"📢・avisos", "📜・regras"} else await self._base_overwrites(guild)
        if kind == "voice":
            channel = await guild.create_voice_channel(name, category=category, overwrites=overwrites, reason="DevVerse setup")
        else:
            channel = await guild.create_text_channel(name, category=category, overwrites=overwrites, reason="DevVerse setup")
        await self.bot.db.add_created_item(guild.id, "channel", channel.id, channel.name)
        return channel

    async def _send_initial_messages(self, guild: discord.Guild) -> int:
        sent = 0
        for channel_name, (title, description) in INITIAL_MESSAGES.items():
            channel = discord.utils.get(guild.text_channels, name=channel_name)
            if not channel:
                continue
            async for message in channel.history(limit=20):
                if message.author == guild.me and message.embeds and message.embeds[0].title == title:
                    break
            else:
                await channel.send(embed=make_embed(title, description))
                sent += 1
        return sent

    def _missing_roles(self, guild: discord.Guild) -> list[str]:
        return [
            role_name
            for roles in ROLE_GROUPS.values()
            for role_name in roles
            if discord.utils.get(guild.roles, name=role_name) is None
        ]

    @app_commands.command(name="setup_devserver", description="Cria a estrutura completa do servidor DevVerse.")
    @admin_check()
    async def setup_devserver(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Use este comando dentro de um servidor.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        missing_roles = self._missing_roles(guild)
        if missing_roles:
            await interaction.followup.send(
                embed=make_embed(
                    "Setup pausado",
                    "O DevVerse nao cria cargos automaticamente. Crie os cargos no servidor e configure os IDs em `data/roles.json`.\n\n"
                    "Cargos ausentes:\n" + ", ".join(missing_roles[:20]),
                ),
                ephemeral=True,
            )
            return
        audit = AuditReport(title="Setup DevVerse", actor=f"{interaction.user} ({interaction.user.id})")
        for group, roles in ROLE_GROUPS.items():
            for role_name in roles:
                await self._ensure_role(guild, group, role_name)
        for category_name, channels in SERVER_CATEGORIES.items():
            category_existed = discord.utils.get(guild.categories, name=category_name) is not None
            category = await self._ensure_category(guild, category_name)
            if category_existed:
                audit.reused.append(f"Categoria {category.name}")
            else:
                audit.added.append(f"Categoria {category.name}")
            for channel_name, kind in channels:
                channel_existed = discord.utils.get(category.channels, name=channel_name) is not None
                await self._ensure_channel(guild, category, channel_name, kind)
                if channel_existed:
                    audit.reused.append(f"Canal {channel_name}")
                else:
                    audit.added.append(f"Canal {channel_name}")
        ai_channel = discord.utils.get(guild.text_channels, name="🤖・ai-assistant")
        if ai_channel:
            await self.bot.db.execute(
                "INSERT INTO guild_settings (guild_id, ai_channel_id) VALUES (?, ?) ON CONFLICT(guild_id) DO UPDATE SET ai_channel_id=excluded.ai_channel_id",
                (guild.id, ai_channel.id),
            )
        sent = await self._send_initial_messages(guild)
        if sent:
            audit.added.append(f"Mensagens iniciais enviadas: {sent}")
        audit.summary = "Estrutura principal criada/validada. Nenhum item removido por este comando."
        await send_audit_report(guild, audit)
        await interaction.followup.send(embed=make_embed("Servidor DevVerse pronto", f"Estrutura criada/validada. Mensagens iniciais enviadas: {sent}."), ephemeral=True)

    @app_commands.command(name="limpar_devserver", description="Remove somente canais e categorias criados pelo bot.")
    @admin_check()
    async def limpar_devserver(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Use este comando dentro de um servidor.", ephemeral=True)
            return
        view = ConfirmView(interaction.user.id)
        await interaction.response.send_message(embed=make_embed("Confirmar limpeza", "Vou remover apenas canais e categorias registrados como criados pelo DevVerse Assistant."), view=view, ephemeral=True)
        await view.wait()
        if not view.confirmed:
            await interaction.followup.send("Limpeza cancelada.", ephemeral=True)
            return
        rows = await self.bot.db.fetchall(
            "SELECT item_type, item_id FROM created_items WHERE guild_id = ? AND item_type IN ('channel', 'category') ORDER BY CASE item_type WHEN 'channel' THEN 1 WHEN 'category' THEN 2 ELSE 3 END",
            (interaction.guild.id,),
        )
        removed = 0
        audit = AuditReport(title="Limpeza DevVerse", actor=f"{interaction.user} ({interaction.user.id})")
        for row in rows:
            target = interaction.guild.get_channel(row["item_id"])
            if target:
                audit.removed.append(f"{row['item_type']}: {target.name}")
                await target.delete(reason="DevVerse cleanup")
                removed += 1
        await self.bot.db.execute("DELETE FROM created_items WHERE guild_id = ? AND item_type IN ('channel', 'category')", (interaction.guild.id,))
        audit.summary = f"Itens removidos: {removed}"
        await send_audit_report(interaction.guild, audit)
        await interaction.followup.send(embed=make_embed("Limpeza concluida", f"Itens removidos: {removed}."), ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SetupCog(bot))
