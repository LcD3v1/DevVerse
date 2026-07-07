from __future__ import annotations

import asyncio
import logging

import discord
from discord import app_commands
from discord.ext import commands

from bot.permissions import admin_check
from bot.templates import ROLE_PANEL_GROUPS
from bot.utils import make_embed
from bot.views.onboarding import EXTRA_ONBOARDING_GROUPS, ONBOARDING_GROUPS, PRIMARY_ONBOARDING_GROUPS, OnboardingPanelView, OnboardingView, load_role_ids, resolve_role
from bot.views.role_menu import RolePanelView


logger = logging.getLogger("devverse.roles")


class RolesCog(commands.Cog):
    permissions_group = app_commands.Group(name="permissions", description="Diagnostico de permissoes do servidor.")

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._auto_sync_done = False
        self.bot.add_view(OnboardingView(PRIMARY_ONBOARDING_GROUPS))
        self.bot.add_view(OnboardingView(EXTRA_ONBOARDING_GROUPS))
        self.bot.add_view(OnboardingPanelView())

    @app_commands.command(name="rolepanel", description="Cria o painel de autoatribuição de cargos.")
    @admin_check()
    async def rolepanel(self, interaction: discord.Interaction) -> None:
        embed = make_embed("Painel de Cargos", "Escolha suas especialidades, linguagens, frameworks, sistemas, objetivos e status.")
        await interaction.response.send_message(embed=embed, view=RolePanelView(ROLE_PANEL_GROUPS))

    @permissions_group.command(name="check", description="Mostra quais canais um usuario consegue ou nao consegue ver.")
    @admin_check()
    async def permissions_check(self, interaction: discord.Interaction, usuario: discord.Member | None = None) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Use este comando dentro de um servidor.", ephemeral=True)
            return
        member = usuario or interaction.user
        if not isinstance(member, discord.Member):
            await interaction.response.send_message("Usuario invalido.", ephemeral=True)
            return
        visible = []
        hidden = []
        for channel in interaction.guild.channels:
            permissions = channel.permissions_for(member)
            target = visible if permissions.view_channel else hidden
            target.append(f"#{channel.name}")
        roles = ", ".join(role.name for role in member.roles if role != interaction.guild.default_role) or "Nenhum"
        description = "\n".join(
            [
                f"Usuario: {member.mention}",
                f"Cargos atuais: {roles}",
                "",
                "Pode ver:",
                "\n".join(visible[:25]) or "Nenhum canal",
                "",
                "Nao pode ver:",
                "\n".join(hidden[:25]) or "Nenhum canal",
            ]
        )
        await interaction.response.send_message(embed=make_embed("Permissions check", description), ephemeral=True)

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        if self._auto_sync_done:
            return
        self._auto_sync_done = True
        for guild in self.bot.guilds:
            await self._sync_unprofiled_visitors(guild)

    @app_commands.command(name="sync_visitors", description="Aplica o cargo Visitante em membros sem perfil concluido.")
    @admin_check()
    async def sync_visitors(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Use este comando dentro de um servidor.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        row = await self.bot.db.fetchone(
            "SELECT visitor_role_id FROM guild_settings WHERE guild_id = ?",
            (interaction.guild.id,),
        )
        visitor_role = self._visitor_role(interaction.guild, row)
        if not visitor_role:
            await interaction.followup.send("Cargo Visitante nao configurado/encontrado. Rode `/setup_roles cargo_visitante:@Visitante`.", ephemeral=True)
            return
        members = interaction.guild.members
        if not members:
            members = [member async for member in interaction.guild.fetch_members(limit=None)]
        applied, skipped = await self._sync_members_with_visitor(members, visitor_role)
        await interaction.followup.send(f"Visitante aplicado em {applied} membro(s). Ignorados: {skipped}.", ephemeral=True)

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
            await self._ensure_mod_logs(interaction.guild)
            await self._save_onboarding_settings(interaction.guild.id, visitor_role, welcome_channel, profile_channel)
            await self._cleanup_old_onboarding_messages(profile_channel)
            await profile_channel.send(embed=self._onboarding_embed(), view=OnboardingPanelView())
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
            hierarchy_warning = self._hierarchy_warning(interaction.guild, visitor_role)
            try:
                await self._apply_visitor_permissions(interaction.guild, visitor_role, welcome_channel, profile_channel)
                permission_status = f"Cargo visitante configurado: {visitor_role.mention}"
                if hierarchy_warning:
                    permission_status += f"\n{hierarchy_warning}"
                await self._log_mod(
                    interaction.guild,
                    "Permissoes de Visitante atualizadas",
                    f"Cargo: {visitor_role.mention}\nEntrada: {welcome_channel.mention}\nPerfil: {profile_channel.mention}",
                )
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
        if visitor_role:
            applied = await self._assign_visitor(member, visitor_role)
            await self._log_mod(
                member.guild,
                "Novo membro entrou",
                f"Usuario: {member.mention}\nCargo aplicado: {visitor_role.mention if applied else 'Falhou'}",
            )
        else:
            logger.warning("Cargo Visitante nao encontrado no servidor %s", member.guild.id)
            await self._log_mod(member.guild, "Falha no Visitante", f"Usuario: {member.mention}\nErro: Cargo Visitante nao encontrado")
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

    async def _ensure_mod_logs(self, guild: discord.Guild) -> discord.TextChannel | None:
        channel = discord.utils.get(guild.text_channels, name="mod-logs")
        if channel:
            return channel
        try:
            return await guild.create_text_channel("mod-logs", reason="DevVerse moderation logs")
        except discord.HTTPException:
            return None

    async def _log_mod(self, guild: discord.Guild, title: str, description: str) -> None:
        channel = discord.utils.get(guild.text_channels, name="mod-logs")
        if not channel:
            return
        try:
            await channel.send(embed=make_embed(title, description))
        except discord.HTTPException:
            logger.exception("Falha ao enviar log de moderacao no servidor %s", guild.id)

    async def _cleanup_old_onboarding_messages(self, channel: discord.TextChannel) -> None:
        titles = {"\U0001f680 Bem-vindo ao DevVerse!", "Preferencias DevVerse", "Configurar perfil DevVerse"}
        try:
            async for message in channel.history(limit=50):
                if message.author != channel.guild.me:
                    continue
                if message.embeds and message.embeds[0].title in titles:
                    await message.delete()
        except discord.HTTPException:
            return

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
        for role in guild.roles:
            if "visitante" in role.name.casefold():
                return role
        return None

    def _hierarchy_warning(self, guild: discord.Guild, visitor_role: discord.Role) -> str:
        bot_member = guild.me
        if not bot_member:
            return "⚠️ Nao consegui verificar a hierarquia do bot."
        if bot_member.top_role <= visitor_role:
            return "⚠️ O cargo do bot precisa estar acima do cargo Visitante para conseguir aplicar cargos."
        if not bot_member.guild_permissions.manage_roles:
            return "⚠️ O bot precisa da permissao Manage Roles para aplicar cargos."
        return ""

    async def _sync_unprofiled_visitors(self, guild: discord.Guild) -> tuple[int, int]:
        row = await self.bot.db.fetchone(
            "SELECT visitor_role_id FROM guild_settings WHERE guild_id = ?",
            (guild.id,),
        )
        visitor_role = self._visitor_role(guild, row)
        if not visitor_role:
            logger.warning("Auto-sync Visitante ignorado: cargo Visitante nao encontrado no servidor %s", guild.id)
            return 0, 0
        members = guild.members
        if not members:
            try:
                members = [member async for member in guild.fetch_members(limit=None)]
            except discord.HTTPException:
                logger.exception("Nao consegui buscar membros para sync de Visitante no servidor %s", guild.id)
                return 0, 0
        return await self._sync_members_with_visitor(members, visitor_role)

    async def _sync_members_with_visitor(self, members: list[discord.Member], visitor_role: discord.Role) -> tuple[int, int]:
        applied = 0
        skipped = 0
        for member in members:
            if member.bot:
                continue
            has_profile = await self.bot.db.fetchone("SELECT 1 FROM user_profiles WHERE user_id = ? LIMIT 1", (member.id,))
            if has_profile or visitor_role in member.roles:
                skipped += 1
                continue
            if await self._assign_visitor(member, visitor_role):
                applied += 1
            else:
                skipped += 1
        return applied, skipped

    async def _assign_visitor(self, member: discord.Member, visitor_role: discord.Role) -> bool:
        if visitor_role in member.roles:
            return True
        hierarchy_warning = self._hierarchy_warning(member.guild, visitor_role)
        if hierarchy_warning:
            logger.error(hierarchy_warning)
            await self._log_mod(member.guild, "Falha ao aplicar Visitante", f"Usuario: {member.mention}\n{hierarchy_warning}")
            return False
        try:
            await member.add_roles(visitor_role, reason="DevVerse new visitor")
            logger.info("Cargo Visitante aplicado em %s (%s)", member, member.id)
            await self._log_mod(member.guild, "Cargo Visitante aplicado", f"Usuario: {member.mention}\nCargo: {visitor_role.mention}")
            return True
        except discord.Forbidden:
            logger.error(
                "Sem permissao/hierarquia para aplicar Visitante. Coloque o cargo do bot acima de %s no servidor %s.",
                visitor_role.name,
                member.guild.id,
            )
        except discord.HTTPException:
            logger.exception("Falha HTTP ao aplicar Visitante em %s (%s)", member, member.id)
            await self._log_mod(member.guild, "Falha ao aplicar Visitante", f"Usuario: {member.mention}\nErro HTTP ao aplicar cargo.")
        return False

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
        for channel in guild.channels:
            if channel.id in allowed or "regras" in channel.name or "escolha-perfil" in channel.name or "inicio" in channel.name.casefold() or "início" in channel.name.casefold():
                await channel.set_permissions(guild.default_role, view_channel=True, read_message_history=True)
                await channel.set_permissions(
                    visitor_role,
                    view_channel=True,
                    read_message_history=True,
                    send_messages=True,
                    connect=True,
                )
            else:
                await channel.set_permissions(guild.default_role, view_channel=False, connect=False)
                await channel.set_permissions(visitor_role, view_channel=False, connect=False)
            await self._apply_area_role_permissions(channel)

    async def _apply_area_role_permissions(self, channel: discord.abc.GuildChannel) -> None:
        assert channel.guild
        channel_name = channel.name.casefold()
        area_map = {
            "backend": ("backend", "back-end"),
            "frontend": ("frontend", "front-end"),
            "ai": ("ai", "ia", "machine-learning", "papers-ai"),
            "cybersecurity": ("cyber", "security", "ctf"),
            "cloud": ("cloud",),
            "devops": ("devops",),
            "data_science": ("data", "dados"),
            "mobile": ("mobile",),
            "blockchain": ("blockchain",),
        }
        for role_key, keywords in area_map.items():
            if not any(keyword in channel_name for keyword in keywords):
                continue
            role = resolve_role(channel.guild, role_key)
            if role:
                await channel.set_permissions(role, view_channel=True, read_message_history=True, send_messages=True, connect=True)

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
                    "Configure seu perfil para liberar o acesso a comunidade.",
                    "",
                    "Use os botoes abaixo:",
                    "\U0001f9ed Perfil: estudante, mentor ou profissional e nivel",
                    "\U0001f4bb Tecnologias: areas e linguagens",
                    "\U0001f6e0\ufe0f Extras: frameworks, sistemas e objetivos",
                    "",
                    "Finalize em Confirmar perfil.",
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
