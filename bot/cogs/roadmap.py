from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.utils import make_embed


ROADMAPS = {
    "frontend": ["HTML semântico", "CSS responsivo", "JavaScript moderno", "React", "APIs", "Testes", "Projeto: dashboard pessoal"],
    "backend": ["HTTP e APIs", "Python ou Node.js", "Banco de dados SQL", "Autenticação", "Filas e cache", "Docker", "Projeto: API de tarefas"],
    "full stack": ["Git", "HTML/CSS", "JavaScript", "React", "Backend com APIs", "SQL", "Deploy", "Projeto: SaaS pequeno"],
    "data science": ["Python", "Pandas", "Estatística", "Visualização", "Machine Learning", "Projeto: análise pública"],
    "cybersecurity": ["Redes", "Linux", "OWASP", "Hardening", "Logs", "Laboratórios defensivos", "Projeto: checklist de segurança"],
    "devops": ["Linux", "Git", "Docker", "CI/CD", "Cloud", "Observabilidade", "Projeto: pipeline de deploy"],
}


class RoadmapCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="roadmap", description="Gera roadmap por área e nível.")
    async def roadmap(self, interaction: discord.Interaction, area: str, nivel: str) -> None:
        key = area.lower().strip()
        steps = ROADMAPS.get(key, ROADMAPS["full stack"])
        description = "\n".join(f"{i}. {step}" for i, step in enumerate(steps, start=1))
        description += f"\n\nNível: {nivel}\nRitmo sugerido: 5 a 7 horas por semana, com um projeto prático a cada etapa."
        await interaction.response.send_message(embed=make_embed(f"Roadmap: {area}", description))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RoadmapCog(bot))
