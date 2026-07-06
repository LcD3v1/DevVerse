from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.permissions import admin_check
from bot.templates import ROLE_PANEL_GROUPS
from bot.utils import make_embed
from bot.views.onboarding import ALL_ONBOARDING_ROLES, OnboardingView
from bot.views.role_menu import RolePanelView


class RolesCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.bot.add_view(OnboardingView())

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
        await self._ensure_onboarding_roles(interaction.guild)
        channel = await self._ensure_welcome_channel(interaction.guild)
        await channel.send(embed=self._onboarding_embed(), view=OnboardingView())
        await interaction.followup.send(embed=make_embed("Sistema de cargos pronto", f"Painel enviado em {channel.mention}."), ephemeral=True)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        channel = self._find_welcome_channel(member.guild)
        if not channel:
            return
        try:
            await channel.send(content=member.mention, embed=self._onboarding_embed(), view=OnboardingView(), delete_after=3600)
        except discord.HTTPException:
            return

    async def _ensure_onboarding_roles(self, guild: discord.Guild) -> None:
        existing = {role.name for role in guild.roles}
        for role_name in ALL_ONBOARDING_ROLES:
            if role_name not in existing:
                await guild.create_role(name=role_name, reason="DevVerse setup_roles")

    async def _ensure_welcome_channel(self, guild: discord.Guild) -> discord.TextChannel:
        channel = self._find_welcome_channel(guild)
        if channel:
            return channel
        return await guild.create_text_channel("\U0001f44b\u30fbbem-vindo", reason="DevVerse setup_roles")

    def _find_welcome_channel(self, guild: discord.Guild) -> discord.TextChannel | None:
        for channel in guild.text_channels:
            if "bem-vindo" in channel.name:
                return channel
        return None

    def _onboarding_embed(self) -> discord.Embed:
        return make_embed(
            "Bem-vindo ao DevVerse!",
            "\n".join(
                [
                    "Escolha seu perfil abaixo:",
                    "\U0001f393 Estudante",
                    "\U0001f9d1\u200d\U0001f3eb Mentor",
                    "\U0001f4bc Profissional",
                    "",
                    "Escolha sua area:",
                    "\U0001f4bb Frontend",
                    "\u2699\ufe0f Backend",
                    "\U0001f310 Full Stack",
                    "\U0001f4f1 Mobile",
                    "\U0001f916 Inteligencia Artificial",
                    "\U0001f4ca Data Science",
                    "\U0001f510 Cybersecurity",
                    "\u2601\ufe0f Cloud",
                    "\U0001f3ae Game Development",
                    "",
                    "Escolha seu nivel:",
                    "\U0001f331 Iniciante",
                    "\U0001f4da Estudando",
                    "\U0001f9d1\u200d\U0001f4bb Junior",
                    "\U0001f680 Pleno",
                    "\u2b50 Senior",
                ]
            ),
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RolesCog(bot))
