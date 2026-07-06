from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.utils import make_embed


class TasksCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="task_create", description="Cria tarefa.")
    async def task_create(self, interaction: discord.Interaction, titulo: str, responsavel: discord.Member | None = None, prazo: str = "", status: str = "aberta", prioridade: str = "media", descricao: str = "") -> None:
        if not interaction.guild:
            await interaction.response.send_message("Use dentro de um servidor.", ephemeral=True)
            return
        await self.bot.db.execute(
            "INSERT INTO tasks (guild_id, title, description, assigned_to, created_by, due_date, status, priority) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (interaction.guild.id, titulo, descricao, responsavel.id if responsavel else None, interaction.user.id, prazo, status, prioridade),
        )
        await interaction.response.send_message(embed=make_embed("Tarefa criada", f"{titulo}\nResponsável: {responsavel.mention if responsavel else 'Não definido'}\nPrioridade: {prioridade}"))

    @app_commands.command(name="task_list", description="Lista tarefas.")
    async def task_list(self, interaction: discord.Interaction, status: str = "aberta") -> None:
        if not interaction.guild:
            await interaction.response.send_message("Use dentro de um servidor.", ephemeral=True)
            return
        rows = await self.bot.db.fetchall("SELECT * FROM tasks WHERE guild_id = ? AND status = ? ORDER BY id DESC LIMIT 15", (interaction.guild.id, status))
        lines = [f"#{r['id']} {r['title']} — {r['priority']} — prazo: {r['due_date'] or 'sem prazo'}" for r in rows]
        await interaction.response.send_message(embed=make_embed(f"Tarefas: {status}", "\n".join(lines) or "Nenhuma tarefa encontrada."))

    @app_commands.command(name="task_done", description="Marca tarefa como concluída.")
    async def task_done(self, interaction: discord.Interaction, task_id: int) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Use dentro de um servidor.", ephemeral=True)
            return
        await self.bot.db.execute("UPDATE tasks SET status = 'concluida' WHERE id = ? AND guild_id = ?", (task_id, interaction.guild.id))
        await self.bot.db.add_xp(interaction.guild.id, interaction.user.id, 40)
        await interaction.response.send_message(embed=make_embed("Tarefa concluída", f"Tarefa #{task_id} marcada como concluída. XP: +40."))

    @app_commands.command(name="task_delete", description="Apaga uma tarefa.")
    async def task_delete(self, interaction: discord.Interaction, task_id: int) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Use dentro de um servidor.", ephemeral=True)
            return
        await self.bot.db.execute("DELETE FROM tasks WHERE id = ? AND guild_id = ?", (task_id, interaction.guild.id))
        await interaction.response.send_message(embed=make_embed("Tarefa apagada", f"Tarefa #{task_id} removida."))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TasksCog(bot))
