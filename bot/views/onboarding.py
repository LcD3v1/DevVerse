from __future__ import annotations

import json
import logging
from pathlib import Path

import discord

from bot.config import BASE_DIR


ROLES_CONFIG_PATH = BASE_DIR / "data" / "roles.json"
logger = logging.getLogger("devverse.roles.onboarding")

ONBOARDING_GROUPS = {
    "profile": {
        "label": "Perfil",
        "single": True,
        "options": [
            ("student", "\U0001f393", "Estudante"),
            ("mentor", "\U0001f9d1\u200d\U0001f3eb", "Mentor"),
            ("professional", "\U0001f4bc", "Profissional"),
        ],
    },
    "level": {
        "label": "Nivel de estudo",
        "single": True,
        "options": [
            ("beginner", "\U0001f331", "Iniciante"),
            ("basic", "\U0001f4d8", "Basico"),
            ("intermediate", "\U0001f4d7", "Intermediario"),
            ("advanced", "\U0001f4d9", "Avancado"),
            ("expert", "\U0001f3c6", "Expert"),
        ],
    },
    "specialties": {
        "label": "Especialidades",
        "single": False,
        "options": [
            ("frontend", "\U0001f310", "Front-end"),
            ("backend", "\u2699\ufe0f", "Back-end"),
            ("fullstack", "\U0001f468\u200d\U0001f4bb", "Full Stack"),
            ("mobile", "\U0001f4f1", "Mobile"),
            ("uiux", "\U0001f3a8", "UI/UX"),
            ("ai", "\U0001f916", "Inteligencia Artificial"),
            ("data_science", "\U0001f4ca", "Ciencia de Dados"),
            ("data_engineering", "\U0001f6e2\ufe0f", "Engenharia de Dados"),
            ("cloud", "\u2601\ufe0f", "Cloud"),
            ("cybersecurity", "\U0001f512", "Cybersecurity"),
            ("devops", "\U0001f9ea", "DevOps"),
            ("linux", "\U0001f427", "Linux"),
            ("git", "\U0001f4e6", "Git/GitHub"),
            ("database", "\U0001f5c4\ufe0f", "Banco de Dados"),
            ("webdev", "\U0001f30d", "Web Development"),
            ("automation", "\u26a1", "Automacao"),
            ("blockchain", "\u26d3\ufe0f", "Blockchain"),
        ],
    },
    "languages": {
        "label": "Linguagens",
        "single": False,
        "options": [
            ("python", "\U0001f40d", "Python"),
            ("java", "\u2615", "Java"),
            ("c", "\u2699\ufe0f", "C"),
            ("cpp", "\u2699\ufe0f", "C++"),
            ("rust", "\U0001f980", "Rust"),
            ("csharp", "\U0001f499", "C#"),
            ("javascript", "\U0001f7e8", "JavaScript"),
            ("typescript", "\U0001f539", "TypeScript"),
            ("php", "\U0001f418", "PHP"),
            ("ruby", "\U0001f48e", "Ruby"),
            ("go", "\U0001f439", "Go"),
            ("kotlin", "\U0001f42a", "Kotlin"),
            ("swift", "\U0001f34e", "Swift"),
        ],
    },
    "frameworks": {
        "label": "Frameworks",
        "single": False,
        "options": [
            ("react", "\u269b\ufe0f", "React"),
            ("nodejs", "\U0001f7e9", "Node.js"),
            ("express", "\U0001f7e2", "Express"),
            ("nextjs", "\U0001f680", "Next.js"),
            ("django", "\U0001f525", "Django"),
            ("flask", "\U0001f336\ufe0f", "Flask"),
            ("spring", "\U0001f9f1", "Spring Boot"),
            ("laravel", "\U0001f418", "Laravel"),
            ("vue", "\U0001f49a", "Vue"),
            ("angular", "\U0001f53a", "Angular"),
            ("flutter", "\U0001f4f1", "Flutter"),
        ],
    },
    "systems": {
        "label": "Sistemas",
        "single": False,
        "options": [
            ("windows", "\U0001fa9f", "Windows"),
            ("linux_os", "\U0001f427", "Linux"),
            ("macos", "\U0001f34e", "macOS"),
        ],
    },
    "goals": {
        "label": "Objetivos",
        "single": False,
        "options": [
            ("job", "\U0001f4bc", "Conseguir emprego"),
            ("college", "\U0001f4da", "Faculdade"),
            ("competitions", "\U0001f3c6", "Competicoes"),
            ("freelancer", "\U0001f680", "Freelancer"),
            ("business", "\U0001f4b0", "Empreender"),
            ("build_ai", "\U0001f916", "Criar IA"),
            ("pentest", "\U0001f512", "Pentest"),
            ("goal_fullstack", "\U0001f310", "Full Stack"),
            ("goal_mobile", "\U0001f4f1", "Mobile"),
        ],
    },
}

PRIMARY_ONBOARDING_GROUPS = ["profile", "level", "specialties", "languages"]
EXTRA_ONBOARDING_GROUPS = ["frameworks", "systems", "goals"]
ONBOARDING_STATES: dict[int, dict[int, "OnboardingState"]] = {}


def load_role_ids() -> dict[str, int]:
    if not ROLES_CONFIG_PATH.exists():
        return {}
    try:
        data = json.loads(ROLES_CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    role_ids: dict[str, int] = {}
    for key, value in data.items():
        try:
            role_ids[key] = int(value)
        except (TypeError, ValueError):
            continue
    return role_ids


def configured_options(guild: discord.Guild | None, group_key: str) -> list[tuple[str, str, str]]:
    return ONBOARDING_GROUPS[group_key]["options"]


def resolve_role(guild: discord.Guild, key: str) -> discord.Role | None:
    role_ids = load_role_ids()
    role_id = role_ids.get(key)
    if role_id:
        role = guild.get_role(role_id)
        if role:
            return role
    option = _option_by_key(key)
    if not option:
        return None
    _, emoji, label = option
    candidates = {
        label,
        f"{emoji} {label}",
        f"{emoji}\ufe0f {label}",
        label.replace("Back-end", "Backend").replace("Front-end", "Frontend"),
    }
    lowered = {candidate.casefold() for candidate in candidates}
    for role in guild.roles:
        if role.name.casefold() in lowered:
            return role
    for role in guild.roles:
        if label.casefold() in role.name.casefold():
            return role
    return None


def _option_by_key(key: str) -> tuple[str, str, str] | None:
    for group in ONBOARDING_GROUPS.values():
        for option in group["options"]:
            if option[0] == key:
                return option
    return None


class OnboardingState:
    def __init__(self) -> None:
        self.selected: dict[str, list[str]] = {}


class OnboardingSelect(discord.ui.Select):
    def __init__(self, group_key: str, states: dict[int, dict[int, OnboardingState]], guild: discord.Guild | None = None) -> None:
        group = ONBOARDING_GROUPS[group_key]
        group_options = configured_options(guild, group_key)
        options = [
            discord.SelectOption(label=label, value=key, emoji=emoji)
            for key, emoji, label in group_options
        ]
        super().__init__(
            placeholder=group["label"],
            min_values=1 if group["single"] else 0,
            max_values=1 if group["single"] else min(25, len(options)),
            options=options,
            custom_id=f"devverse_profile_select:{group_key}",
        )
        self.group_key = group_key
        self.states = states

    async def callback(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("Use este menu dentro do servidor.", ephemeral=True)
            return
        state = self.states.setdefault(interaction.guild.id, {}).setdefault(interaction.user.id, OnboardingState())
        state.selected[self.group_key] = list(self.values)
        current = self._current_role_labels(interaction.user, self.group_key)
        selected = self._selected_labels(self.group_key, self.values)
        description = "\n".join(
            [
                f"Categoria: {ONBOARDING_GROUPS[self.group_key]['label']}",
                f"Cargos atuais desta categoria: {', '.join(current) if current else 'Nenhum'}",
                f"Nova selecao pendente: {', '.join(selected) if selected else 'Nenhum'}",
                "",
                "Clique em Confirmar perfil para aplicar. Voce pode voltar aqui e editar quando quiser.",
            ]
        )
        await interaction.response.send_message(description, ephemeral=True, delete_after=20)

    def _current_role_labels(self, member: discord.Member, group_key: str) -> list[str]:
        labels = []
        for key, _, label in ONBOARDING_GROUPS[group_key]["options"]:
            role = resolve_role(member.guild, key)
            if role and role in member.roles:
                labels.append(label)
        return labels

    def _selected_labels(self, group_key: str, values: list[str]) -> list[str]:
        labels = []
        options = {key: label for key, _, label in ONBOARDING_GROUPS[group_key]["options"]}
        for key in values:
            labels.append(options.get(key, key))
        return labels


class ConfirmProfileButton(discord.ui.Button):
    def __init__(self, states: dict[int, dict[int, OnboardingState]]) -> None:
        super().__init__(label="Confirmar perfil", emoji="\u2705", style=discord.ButtonStyle.success, custom_id="devverse_profile_confirm")
        self.states = states

    async def callback(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("Use dentro do servidor.", ephemeral=True)
            return
        await self._safe_defer(interaction)
        state = self.states.get(interaction.guild.id, {}).get(interaction.user.id)
        if not state or not state.selected:
            await interaction.followup.send("Nenhuma alteracao pendente. Use os menus para editar seu perfil.", ephemeral=True)
            return
        try:
            result = await self._apply_profile_update(interaction, state)
        except discord.Forbidden:
            logger.exception("Forbidden ao atualizar perfil guild_id=%s user_id=%s selected=%s", interaction.guild.id, interaction.user.id, state.selected)
            await interaction.followup.send(
                "Nao foi possivel aplicar alguns cargos. Verifique se o cargo do bot esta acima dos cargos selecionados.",
                ephemeral=True,
            )
            return
        except discord.NotFound:
            logger.exception("Membro/cargo nao encontrado ao atualizar perfil guild_id=%s user_id=%s selected=%s", interaction.guild.id, interaction.user.id, state.selected)
            await interaction.followup.send("Nao consegui atualizar seu perfil agora. Tente novamente em alguns segundos.", ephemeral=True)
            return
        except discord.HTTPException:
            logger.exception("Erro HTTP ao atualizar perfil guild_id=%s user_id=%s selected=%s", interaction.guild.id, interaction.user.id, state.selected)
            await interaction.followup.send("O Discord recusou a atualizacao agora. Tente novamente em instantes.", ephemeral=True)
            return
        except Exception:
            logger.exception("Erro inesperado ao atualizar perfil guild_id=%s user_id=%s selected=%s", interaction.guild.id, interaction.user.id, state.selected)
            await interaction.followup.send("Nao foi possivel salvar seu perfil agora. A equipe ja pode verificar os logs.", ephemeral=True)
            return
        self.states.get(interaction.guild.id, {}).pop(interaction.user.id, None)
        await self._log_profile_completed(interaction, result["added_roles"], result["removed_roles"], result["visitor_removed"])
        await interaction.followup.send(self._summary_message(result), ephemeral=True)

    async def _safe_defer(self, interaction: discord.Interaction) -> None:
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)

    async def _apply_profile_update(self, interaction: discord.Interaction, state: OnboardingState) -> dict[str, object]:
        guild = interaction.guild
        member = interaction.user
        assert guild and isinstance(member, discord.Member)
        added_roles: list[discord.Role] = []
        removed_roles: list[discord.Role] = []
        skipped: list[str] = []
        selected_roles_by_category: dict[str, list[discord.Role]] = {}
        future_role_ids = {role.id for role in member.roles}
        for category, selected_keys in state.selected.items():
            valid_selected, invalid = self._resolve_safe_roles(guild, category, selected_keys)
            skipped.extend(invalid)
            selected_roles_by_category[category] = valid_selected
            category_roles = [
                role
                for role in (resolve_role(guild, key) for key, _, _ in ONBOARDING_GROUPS[category]["options"])
                if role and self._role_can_be_managed(guild, role, strict=False)[0]
            ]
            selected_ids = {role.id for role in valid_selected}
            to_add = [role for role in valid_selected if role not in member.roles]
            to_remove = [role for role in category_roles if role in member.roles and role.id not in selected_ids]
            if to_remove:
                await member.remove_roles(*to_remove, reason="Atualizacao do perfil DevVerse")
                removed_roles.extend(to_remove)
                future_role_ids.difference_update(role.id for role in to_remove)
            if to_add:
                await member.add_roles(*to_add, reason="Atualizacao do perfil DevVerse")
                added_roles.extend(to_add)
                future_role_ids.update(role.id for role in to_add)
            await self._save_category_profile(interaction, category, valid_selected)
            logger.info(
                "Perfil atualizado guild_id=%s user_id=%s categoria=%s solicitados=%s adicionados=%s removidos=%s",
                guild.id,
                member.id,
                category,
                selected_keys,
                [role.id for role in to_add],
                [role.id for role in to_remove],
            )
        minimum_ok, missing_minimum = self._minimum_profile_status_by_ids(guild, future_role_ids)
        visitor_removed = await self._maybe_remove_visitor(interaction, minimum_ok)
        return {
            "added_roles": added_roles,
            "removed_roles": removed_roles,
            "selected_roles_by_category": selected_roles_by_category,
            "visitor_removed": visitor_removed,
            "minimum_ok": minimum_ok,
            "missing_minimum": missing_minimum,
            "skipped": skipped,
        }

    def _resolve_safe_roles(self, guild: discord.Guild, category: str, selected_keys: list[str]) -> tuple[list[discord.Role], list[str]]:
        roles: list[discord.Role] = []
        skipped: list[str] = []
        seen: set[int] = set()
        for key in selected_keys:
            role = resolve_role(guild, key)
            if not role:
                skipped.append(f"{key}: cargo nao configurado")
                continue
            ok, reason = self._role_can_be_managed(guild, role)
            if not ok:
                skipped.append(f"{role.name}: {reason}")
                continue
            if role.id not in seen:
                roles.append(role)
                seen.add(role.id)
        return roles, skipped

    def _role_can_be_managed(self, guild: discord.Guild, role: discord.Role, strict: bool = True) -> tuple[bool, str]:
        if role == guild.default_role:
            return False, "cargo @everyone ignorado"
        if role.managed:
            return False, "cargo gerenciado por integracao"
        bot_member = guild.me
        if not bot_member:
            return False, "bot nao encontrado no servidor"
        if not bot_member.guild_permissions.manage_roles:
            return False, "bot sem permissao Manage Roles"
        if bot_member.top_role <= role:
            return False, "cargo acima do cargo do bot"
        return True, ""

    async def _maybe_remove_visitor(self, interaction: discord.Interaction, minimum_ok: bool) -> discord.Role | None:
        assert isinstance(interaction.user, discord.Member)
        visitor_role = await self._visitor_role(interaction)
        if not visitor_role or visitor_role not in interaction.user.roles:
            return None
        if not minimum_ok:
            return None
        ok, reason = self._role_can_be_managed(interaction.guild, visitor_role) if interaction.guild else (False, "sem guild")
        if not ok:
            logger.warning("Visitante nao removido guild_id=%s user_id=%s motivo=%s", interaction.guild.id if interaction.guild else None, interaction.user.id, reason)
            return None
        await interaction.user.remove_roles(visitor_role, reason="DevVerse onboarding completed")
        return visitor_role

    def _minimum_profile_status_by_ids(self, guild: discord.Guild, role_ids: set[int]) -> tuple[bool, list[str]]:
        profile_roles = self._role_ids_for_group(guild, "profile") & role_ids
        level_roles = self._role_ids_for_group(guild, "level") & role_ids
        specialty_roles = self._role_ids_for_group(guild, "specialties") & role_ids
        language_roles = self._role_ids_for_group(guild, "languages") & role_ids
        missing = []
        if not profile_roles:
            missing.append("perfil principal")
        if len(level_roles) != 1:
            missing.append("um nivel de estudo")
        if not specialty_roles and not language_roles:
            missing.append("uma especialidade ou linguagem")
        return not missing, missing

    def _role_ids_for_group(self, guild: discord.Guild, group_key: str) -> set[int]:
        role_ids = set()
        for key, _, _ in ONBOARDING_GROUPS[group_key]["options"]:
            role = resolve_role(guild, key)
            if role:
                role_ids.add(role.id)
        return role_ids

    async def _visitor_role(self, interaction: discord.Interaction) -> discord.Role | None:
        if not interaction.guild:
            return None
        row = await interaction.client.db.fetchone(
            "SELECT visitor_role_id FROM guild_settings WHERE guild_id = ?",
            (interaction.guild.id,),
        )
        role_id = row["visitor_role_id"] if row and row["visitor_role_id"] else load_role_ids().get("visitor")
        role = interaction.guild.get_role(role_id) if role_id else None
        if role:
            return role
        for candidate in ("👤 Visitante", "Visitante"):
            role = discord.utils.get(interaction.guild.roles, name=candidate)
            if role:
                return role
        for role in interaction.guild.roles:
            if "visitante" in role.name.casefold():
                return role
        return None

    async def _save_category_profile(self, interaction: discord.Interaction, category: str, roles: list[discord.Role]) -> None:
        if not interaction.guild:
            return
        db = interaction.client.db
        if not db.conn:
            raise RuntimeError("Banco de dados indisponivel")
        await db.conn.execute(
            "DELETE FROM user_profiles WHERE guild_id = ? AND user_id = ? AND category = ?",
            (interaction.guild.id, interaction.user.id, category),
        )
        for role in roles:
            await db.conn.execute(
                """
                INSERT OR IGNORE INTO user_profiles (guild_id, user_id, category, role_id)
                VALUES (?, ?, ?, ?)
                """,
                (interaction.guild.id, interaction.user.id, category, role.id),
            )
        await db.conn.commit()

    def _summary_message(self, result: dict[str, object]) -> str:
        added = result["added_roles"]
        removed = result["removed_roles"]
        skipped = result["skipped"]
        visitor_removed = result["visitor_removed"]
        missing_minimum = result["missing_minimum"]
        parts = ["✅ Perfil atualizado", ""]
        parts.append("Adicionados:\n" + self._role_lines(added if isinstance(added, list) else []))
        parts.append("Removidos:\n" + self._role_lines(removed if isinstance(removed, list) else []))
        if visitor_removed:
            parts.append(f"Visitante removido:\n• {visitor_removed.name}")
        if missing_minimum:
            parts.append("Perfil minimo ainda incompleto:\n" + "\n".join(f"• {item}" for item in missing_minimum))
        if skipped:
            parts.append("Alguns cargos nao foram aplicados:\n" + "\n".join(f"• {item}" for item in skipped[:8]))
        parts.append("Voce pode voltar a este painel e alterar seus cargos quando quiser.")
        return "\n\n".join(parts)

    def _role_lines(self, roles: list[discord.Role]) -> str:
        return "\n".join(f"• {role.name}" for role in roles) if roles else "• Nenhum"

    async def _log_profile_completed(
        self,
        interaction: discord.Interaction,
        added_roles: list[discord.Role],
        removed_roles: list[discord.Role],
        removed_visitor: discord.Role | None,
    ) -> None:
        if not interaction.guild:
            return
        channel = discord.utils.get(interaction.guild.text_channels, name="mod-logs")
        if not channel:
            return
        added = ", ".join(role.mention for role in added_roles) or "Nenhum"
        removed_roles_text = ", ".join(role.mention for role in removed_roles) or "Nenhum"
        removed = removed_visitor.mention if removed_visitor else "Nao estava com Visitante"
        embed = discord.Embed(
            title="Perfil atualizado",
            description=f"Usuario: {interaction.user.mention}\nAdicionados: {added}\nRemovidos: {removed_roles_text}\nVisitante: {removed}",
            color=discord.Color.green(),
        )
        try:
            await channel.send(embed=embed)
        except discord.HTTPException:
            return


class OnboardingView(discord.ui.View):
    def __init__(self, groups: list[str] | None = None, guild: discord.Guild | None = None) -> None:
        super().__init__(timeout=None)
        groups = groups or PRIMARY_ONBOARDING_GROUPS
        for group_key in groups:
            if configured_options(guild, group_key):
                self.add_item(OnboardingSelect(group_key, ONBOARDING_STATES, guild))
        self.add_item(ConfirmProfileButton(ONBOARDING_STATES))


class OnboardingPanelButton(discord.ui.Button):
    def __init__(self, label: str, emoji: str, groups: list[str]) -> None:
        super().__init__(label=label, emoji=emoji, style=discord.ButtonStyle.primary, custom_id=f"devverse_onboarding_panel:{label}")
        self.groups = groups

    async def callback(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Use dentro do servidor.", ephemeral=True)
            return
        await interaction.response.send_message(
            embed=discord.Embed(
                title="Configurar perfil DevVerse",
                description="Escolha as opcoes abaixo e clique em Confirmar perfil.",
                color=discord.Color.blurple(),
            ),
            view=OnboardingView(self.groups, interaction.guild),
            ephemeral=True,
        )


class OnboardingPanelView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)
        self.add_item(OnboardingPanelButton("Perfil", "\U0001f9ed", ["profile", "level"]))
        self.add_item(OnboardingPanelButton("Tecnologias", "\U0001f4bb", ["specialties", "languages"]))
        self.add_item(OnboardingPanelButton("Extras", "\U0001f6e0\ufe0f", ["frameworks", "systems", "goals"]))
        self.add_item(ConfirmProfileButton(ONBOARDING_STATES))
