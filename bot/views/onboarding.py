from __future__ import annotations

import json
from pathlib import Path

import discord

from bot.config import BASE_DIR


ROLES_CONFIG_PATH = BASE_DIR / "data" / "roles.json"

ONBOARDING_GROUPS = {
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

PRIMARY_ONBOARDING_GROUPS = ["level", "specialties", "languages"]
EXTRA_ONBOARDING_GROUPS = ["frameworks", "systems", "goals"]


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
    role_ids = load_role_ids()
    options = ONBOARDING_GROUPS[group_key]["options"]
    if guild is None:
        return options
    return [option for option in options if guild.get_role(role_ids.get(option[0], 0))]


class OnboardingState:
    def __init__(self) -> None:
        self.selected: dict[str, list[str]] = {}


class OnboardingSelect(discord.ui.Select):
    def __init__(self, group_key: str, states: dict[int, OnboardingState], guild: discord.Guild | None = None) -> None:
        group = ONBOARDING_GROUPS[group_key]
        group_options = configured_options(guild, group_key)
        options = [
            discord.SelectOption(label=label, value=key, emoji=emoji)
            for key, emoji, label in group_options
        ]
        super().__init__(
            placeholder=group["label"],
            min_values=1,
            max_values=1 if group["single"] else min(25, len(options)),
            options=options,
            custom_id=f"devverse_profile_select:{group_key}",
        )
        self.group_key = group_key
        self.states = states

    async def callback(self, interaction: discord.Interaction) -> None:
        state = self.states.setdefault(interaction.user.id, OnboardingState())
        state.selected[self.group_key] = list(self.values)
        await interaction.response.send_message("Selecao salva. Clique em Confirmar para aplicar os cargos.", ephemeral=True, delete_after=8)


class ConfirmProfileButton(discord.ui.Button):
    def __init__(self, states: dict[int, OnboardingState]) -> None:
        super().__init__(label="Confirmar", emoji="\u2705", style=discord.ButtonStyle.success, custom_id="devverse_profile_confirm")
        self.states = states

    async def callback(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("Use dentro do servidor.", ephemeral=True)
            return
        state = self.states.get(interaction.user.id)
        if not state or not state.selected:
            await interaction.response.send_message("Escolha pelo menos uma opcao antes de confirmar.", ephemeral=True, delete_after=8)
            return
        role_ids = load_role_ids()
        missing = [key for values in state.selected.values() for key in values if key not in role_ids or interaction.guild.get_role(role_ids.get(key, 0)) is None]
        warning = ""
        if missing:
            warning = "\nAlgumas escolhas ainda nao tem cargo configurado e foram ignoradas: " + ", ".join(sorted(set(missing)))
            for values in state.selected.values():
                values[:] = [key for key in values if key not in missing]
            if not any(state.selected.values()):
                await interaction.response.send_message(warning.strip(), ephemeral=True)
                return
        all_configured_roles = [interaction.guild.get_role(role_id) for role_id in role_ids.values()]
        selected_keys = {key for values in state.selected.values() for key in values}
        selected_roles = [interaction.guild.get_role(role_ids[key]) for key in selected_keys]
        selected_roles = [role for role in selected_roles if role is not None]
        removable = [role for role in all_configured_roles if role and role in interaction.user.roles and role.id not in {r.id for r in selected_roles}]
        if removable:
            await interaction.user.remove_roles(*removable, reason="DevVerse profile update")
        if selected_roles:
            await interaction.user.add_roles(*selected_roles, reason="DevVerse profile update")
        await self._save_profile(interaction, role_ids, state)
        await interaction.response.send_message("Perfil atualizado com sucesso." + warning, ephemeral=True, delete_after=12)

    async def _save_profile(self, interaction: discord.Interaction, role_ids: dict[str, int], state: OnboardingState) -> None:
        await interaction.client.db.execute("DELETE FROM user_profiles WHERE user_id = ?", (interaction.user.id,))
        for category, keys in state.selected.items():
            for key in keys:
                await interaction.client.db.execute(
                    "INSERT INTO user_profiles (user_id, category, role_id) VALUES (?, ?, ?)",
                    (interaction.user.id, category, role_ids[key]),
                )


class OnboardingView(discord.ui.View):
    def __init__(self, groups: list[str] | None = None, guild: discord.Guild | None = None) -> None:
        super().__init__(timeout=None)
        groups = groups or PRIMARY_ONBOARDING_GROUPS
        states: dict[int, OnboardingState] = {}
        for group_key in groups:
            if configured_options(guild, group_key):
                self.add_item(OnboardingSelect(group_key, states, guild))
        self.add_item(ConfirmProfileButton(states))
