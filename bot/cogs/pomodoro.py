from __future__ import annotations

import asyncio

import discord
from discord import app_commands
from discord.ext import commands

from bot.utils import make_embed


class PomodoroCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="pomodoro", description="Inicia Pomodoro.")
    async def pomodoro(self, interaction: discord.Interaction, foco_minutos: app_commands.Range[int, 1, 180] = 25, pausa_minutos: app_commands.Range[int, 1, 60] = 5) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Use dentro de um servidor.", ephemeral=True)
            return
        await interaction.response.send_message(embed=make_embed("Pomodoro iniciado", f"Foco por {foco_minutos} min. Depois, pausa de {pausa_minutos} min."))
        await self.bot.db.execute("INSERT INTO pomodoro_sessions (guild_id, user_id, focus_minutes, break_minutes) VALUES (?, ?, ?, ?)", (interaction.guild.id, interaction.user.id, foco_minutos, pausa_minutos))
        await asyncio.sleep(foco_minutos * 60)
        await interaction.followup.send(embed=make_embed("Fim do foco", f"{interaction.user.mention}, pausa de {pausa_minutos} min começou."))
        await asyncio.sleep(pausa_minutos * 60)
        await self.bot.db.add_xp(interaction.guild.id, interaction.user.id, 30)
        await self.bot.db.execute("UPDATE users SET study_minutes = study_minutes + ? WHERE guild_id = ? AND user_id = ?", (foco_minutos, interaction.guild.id, interaction.user.id))
        await interaction.followup.send(embed=make_embed("Pomodoro concluído", f"{interaction.user.mention}, bom trabalho. XP: +30."))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PomodoroCog(bot))
