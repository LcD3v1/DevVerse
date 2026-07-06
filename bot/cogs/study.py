from __future__ import annotations

from datetime import date, datetime

import discord
from discord import app_commands
from discord.ext import commands

from bot.utils import make_embed


class StudyCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="checkin", description="Registra check-in diário.")
    async def checkin(self, interaction: discord.Interaction, estudo: str, tempo_planejado_min: int, dificuldade: str) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Use dentro de um servidor.", ephemeral=True)
            return
        user_id = interaction.user.id
        guild_id = interaction.guild.id
        today = date.today().isoformat()
        row = await self.bot.db.fetchone("SELECT last_checkin, streak FROM users WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
        streak = 1
        if row and row["last_checkin"]:
            last = datetime.fromisoformat(row["last_checkin"]).date()
            if last == date.today():
                await interaction.response.send_message("Você já fez check-in hoje.", ephemeral=True)
                return
            streak = int(row["streak"] or 0) + 1 if (date.today() - last).days == 1 else 1
        await self.bot.db.execute("INSERT INTO checkins (guild_id, user_id, topic, planned_minutes, difficulty) VALUES (?, ?, ?, ?, ?)", (guild_id, user_id, estudo, tempo_planejado_min, dificuldade))
        await self.bot.db.execute(
            """
            INSERT INTO users (guild_id, user_id, xp, streak, last_checkin) VALUES (?, ?, 50, ?, ?)
            ON CONFLICT(guild_id, user_id) DO UPDATE SET xp = xp + 50, streak = excluded.streak, last_checkin = excluded.last_checkin
            """,
            (guild_id, user_id, streak, today),
        )
        await interaction.response.send_message(embed=make_embed("Check-in registrado", f"Estudo: {estudo}\nTempo planejado: {tempo_planejado_min} min\nDificuldade: {dificuldade}\nStreak: {streak} dias\nXP: +50"))

    @app_commands.command(name="ranking", description="Mostra ranking por XP, horas estudadas e streak.")
    async def ranking(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Use dentro de um servidor.", ephemeral=True)
            return
        rows = await self.bot.db.fetchall("SELECT user_id, xp, study_minutes, streak FROM users WHERE guild_id = ? ORDER BY xp DESC, study_minutes DESC, streak DESC LIMIT 10", (interaction.guild.id,))
        lines = []
        for index, row in enumerate(rows, start=1):
            member = interaction.guild.get_member(row["user_id"])
            name = member.display_name if member else str(row["user_id"])
            lines.append(f"{index}. {name} — {row['xp']} XP | {row['study_minutes'] // 60}h | {row['streak']} streak")
        await interaction.response.send_message(embed=make_embed("Ranking DevVerse", "\n".join(lines) or "Sem dados ainda."))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(StudyCog(bot))
