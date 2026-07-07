from __future__ import annotations

import asyncio

import discord
from discord import app_commands
from discord.ext import commands

from bot.permissions import admin_check
from bot.templates import ROLE_PANEL_GROUPS
from bot.utils import make_embed
from bot.views.onboarding import EXTRA_ONBOARDING_GROUPS, ONBOARDING_GROUPS, PRIMARY_ONBOARDING_GROUPS, OnboardingView, resolve_role
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
    async def setup_roles(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Use este comando dentro de um servidor.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        try:
            missing = self._missing_configured_roles(interaction.guild)
            channel = await self._ensure_welcome_channel(interaction.guild)
            await channel.send(embed=self._onboarding_embed(), view=OnboardingView(PRIMARY_ONBOARDING_GROUPS, interaction.guild))
            await channel.send(embed=self._onboarding_extra_embed(), view=OnboardingView(EXTRA_ONBOARDING_GROUPS, interaction.guild))
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

        description = f"Painel enviado em {channel.mention}.\n{channel_status}"
        if missing:
            description += f"\n\nAlguns cargos ainda nao estao configurados e ficaram ocultos no painel.\nPendentes: {len(missing)}"
        await interaction.followup.send(embed=make_embed("Sistema de cargos pronto", description), ephemeral=True)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        channel = self._find_welcome_channel(member.guild)
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
