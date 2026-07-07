from __future__ import annotations

import asyncio

import discord
from discord import app_commands
from discord.ext import commands

from bot.permissions import admin_check
from bot.templates import ROLE_PANEL_GROUPS
from bot.utils import make_embed
from bot.views.onboarding import EXTRA_ONBOARDING_GROUPS, ONBOARDING_GROUPS, PRIMARY_ONBOARDING_GROUPS, OnboardingView, load_role_ids, resolve_role
from bot.views.role_menu import RolePanelView


class RolesCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.bot.add_view(OnboardingView(PRIMARY_ONBOARDING_GROUPS))
        self.bot.add_view(OnboardingView(EXTRA_ONBOARDING_GROUPS))

    @app_commands.command(name="rolepanel", description="Cria o painel de autoatribuição de cargos.")
    @admin_check()
    async def rolepanel(self, interaction: discord.Interaction) -> None:
        embed = make_embed("Painel de Cargos", "Escolha suas especialidades, linguagens, frameworks, sistemas, objetivos e status.")
        await interaction.response.send_message(embed=embed, view=RolePanelView(ROLE_PANEL_GROUPS))

    @app_commands.command(name="setup_roles", description="Cria painel de cargos e mensagem de boas-vindas.")
    @admin_check()
    async def setup_roles(
        self,
        interaction: discord.Interaction,
        cargo_visitante: discord.Role | None = None,
        canal_entrada: discord.TextChannel | None = None,
        canal_escolha: discord.TextChannel | None = None,
    ) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Use este comando dentro de um servidor.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        try:
            missing = self._missing_configured_roles(interaction.guild)
            visitor_role = cargo_visitante or self._visitor_role(interaction.guild)
            welcome_channel = canal_entrada or await self._ensure_welcome_channel(interaction.guild)
            profile_channel = canal_escolha or welcome_channel
            await self._save_onboarding_settings(interaction.guild.id, visitor_role, welcome_channel, profile_channel)
            await profile_channel.send(embed=self._onboarding_embed(), view=OnboardingView(PRIMARY_ONBOARDING_GROUPS, interaction.guild))
            await profile_channel.send(embed=self._onboarding_extra_embed(), view=OnboardingView(EXTRA_ONBOARDING_GROUPS, interaction.guild))
        except discord.Forbidden:
            await interaction.followup.send("Nao tenho permissao para criar/enviar o painel. Verifique `Manage Channels` e `Send Messages`.", ephemeral=True)
            return
        except discord.HTTPException as exc:
            await interaction.followup.send(f"Nao consegui publicar o painel agora. Erro do Discord: {exc}", ephemeral=True)
            return

        channel_status = "Canais de area validados."
        try:
            await asyncio.wait_for(self._ensure_area_channels(interaction.guild), timeout=20)
        except asyncio.TimeoutError:
            channel_status = "Painel publicado. A criacao de canais demorou demais e foi interrompida."
        except discord.Forbidden:
            channel_status = "Painel publicado. Nao tenho permissao para criar canais de area."
        except discord.HTTPException as exc:
            channel_status = f"Painel publicado. Nao consegui criar todos os canais de area: {exc}"

        permission_status = "Cargo Visitante nao configurado."
        if visitor_role:
            try:
                await self._apply_visitor_permissions(interaction.guild, visitor_role, welcome_channel, profile_channel)
                permission_status = f"Cargo visitante configurado: {visitor_role.mention}"
            except discord.Forbidden:
                permission_status = "Nao tenho permissao para ajustar canais do Visitante."
            except discord.HTTPException as exc:
                permission_status = f"Nao consegui ajustar todas as permissoes do Visitante: {exc}"

        description = f"Painel enviado em {profile_channel.mention}.\n{channel_status}\n{permission_status}"
        if missing:
            description += f"\n\nAlguns cargos ainda nao estao configurados e ficaram ocultos no painel.\nPendentes: {len(missing)}"
        await interaction.followup.send(embed=make_embed("Sistema de cargos pronto", description), ephemeral=True)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        row = await self.bot.db.fetchone(
            "SELECT visitor_role_id, welcome_channel_id, profile_channel_id FROM guild_settings WHERE guild_id = ?",
            (member.guild.id,),
        )
        channel = self._configured_channel(member.guild, row, "welcome_channel_id") or self._find_welcome_channel(member.guild)
        profile_channel = self._configured_channel(member.guild, row, "profile_channel_id") or channel
        visitor_role = self._visitor_role(member.guild, row)
        try:
            if visitor_role:
                await member.add_roles(visitor_role, reason="DevVerse new visitor")
        except discord.HTTPException:
            pass
        try:
            if profile_channel:
                await member.send(
                    "\n".join(
                        [
                            "Bem-vindo ao DevVerse!",
                            "",
                            "Para acessar a comunidade complete seu perfil no canal:",
                            profile_channel.mention,
                        ]
                    )
                )
        except discord.HTTPException:
            pass
        if not channel:
            return
        try:
            await channel.send(content=member.mention, embed=self._onboarding_embed(), view=OnboardingView(PRIMARY_ONBOARDING_GROUPS, member.guild), delete_after=3600)
            await channel.send(embed=self._onboarding_extra_embed(), view=OnboardingView(EXTRA_ONBOARDING_GROUPS, member.guild), delete_after=3600)
        except discord.HTTPException:
            return

    def _missing_configured_roles(self, guild: discord.Guild) -> list[str]:
        missing = []
        expected = [key for group in ONBOARDING_GROUPS.values() for key, _, _ in group["options"]]
        for key in expected:
            if resolve_role(guild, key) is None:
                missing.append(key)
        return sorted(set(missing))

    async def _ensure_welcome_channel(self, guild: discord.Guild) -> discord.TextChannel:
        channel = self._find_welcome_channel(guild)
        if channel:
            return channel
        return await guild.create_text_channel("\U0001f44b\u30fbbem-vindo", reason="DevVerse setup_roles")

    async def _save_onboarding_settings(
        self,
        guild_id: int,
        visitor_role: discord.Role | None,
        welcome_channel: discord.TextChannel,
        profile_channel: discord.TextChannel,
    ) -> None:
        await self.bot.db.execute(
            """
            INSERT INTO guild_settings (guild_id, visitor_role_id, welcome_channel_id, profile_channel_id)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET
                visitor_role_id = excluded.visitor_role_id,
                welcome_channel_id = excluded.welcome_channel_id,
                profile_channel_id = excluded.profile_channel_id
            """,
            (guild_id, visitor_role.id if visitor_role else None, welcome_channel.id, profile_channel.id),
        )

    def _visitor_role(self, guild: discord.Guild, row=None) -> discord.Role | None:
        role_id = row["visitor_role_id"] if row and row["visitor_role_id"] else load_role_ids().get("visitor")
        role = guild.get_role(role_id) if role_id else None
        if role:
            return role
        for candidate in ("👤 Visitante", "Visitante"):
            role = discord.utils.get(guild.roles, name=candidate)
            if role:
                return role
        return None

    def _configured_channel(self, guild: discord.Guild, row, column: str) -> discord.TextChannel | None:
        if not row or not row[column]:
            return None
        channel = guild.get_channel(row[column])
        return channel if isinstance(channel, discord.TextChannel) else None

    async def _apply_visitor_permissions(
        self,
        guild: discord.Guild,
        visitor_role: discord.Role,
        welcome_channel: discord.TextChannel,
        profile_channel: discord.TextChannel,
    ) -> None:
        allowed = {welcome_channel.id, profile_channel.id}
        for channel in guild.text_channels:
            if channel.id in allowed or "regras" in channel.name:
                await channel.set_permissions(visitor_role, view_channel=True, read_message_history=True, send_messages=True)
            else:
                await channel.set_permissions(visitor_role, view_channel=False)

    async def _ensure_area_channels(self, guild: discord.Guild) -> None:
        role_ids = load_role_ids()
        category = discord.utils.get(guild.categories, name="\U0001f4da Estudos")
        if not category:
            category = await guild.create_category("\U0001f4da Estudos", reason="DevVerse setup_roles")
        area_channels = {
            "backend": ["backend-chat", "backend-news", "backend-recursos", "vagas-backend"],
            "frontend": ["frontend-chat", "frontend-news", "frontend-recursos"],
            "ai": ["ai-chat", "ai-news", "ai-recursos", "machine-learning", "papers-ai"],
            "cybersecurity": ["cyber-chat", "security-news", "ctf"],
        }
        for area_key, channel_names in area_channels.items():
            role = guild.get_role(role_ids.get(area_key, 0))
            overwrites = None
            if role:
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                }
            for channel_name in channel_names:
                if discord.utils.get(guild.text_channels, name=channel_name):
                    continue
                await guild.create_text_channel(channel_name, category=category, overwrites=overwrites, reason="DevVerse setup_roles")

    def _find_welcome_channel(self, guild: discord.Guild) -> discord.TextChannel | None:
        for channel in guild.text_channels:
            if "bem-vindo" in channel.name:
                return channel
        return None

    def _onboarding_embed(self) -> discord.Embed:
        return make_embed(
            "\U0001f680 Bem-vindo ao DevVerse!",
            "\n".join(
                [
                    "Configure seu perfil usando os menus abaixo.",
                    "",
                    "Escolha seu perfil:",
                    "\U0001f393 Estudante",
                    "\U0001f9d1\u200d\U0001f3eb Mentor",
                    "\U0001f4bc Profissional",
                    "",
                    "Escolha seu nivel:",
                    "\U0001f331 Iniciante",
                    "\U0001f4d8 Basico",
                    "\U0001f4d7 Intermediario",
                    "\U0001f4d9 Avancado",
                    "\U0001f3c6 Expert",
                    "",
                    "Escolha suas especialidades.",
                    "Depois clique em Confirmar neste painel.",
                ]
            ),
        )

    def _onboarding_extra_embed(self) -> discord.Embed:
        return make_embed(
            "Preferencias DevVerse",
            "\n".join(
                [
                    "Escolha frameworks, sistemas e objetivos.",
                    "As linguagens tambem ficam disponiveis no painel de cargos completo.",
                    "Depois clique em Confirmar neste painel.",
                    "",
                    "Essas escolhas ajudam o DevVerse a direcionar canais, recursos e futuras recomendacoes por IA.",
                ]
            ),
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RolesCog(bot))
