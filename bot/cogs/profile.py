from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.utils import level_from_xp, make_embed, progress_bar


class ProfileCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="profile", description="Mostra perfil do usuário.")
    async def profile(self, interaction: discord.Interaction, membro: discord.Member | None = None) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Use dentro de um servidor.", ephemeral=True)
            return
        member = membro or interaction.user
        row = await self.bot.db.fetchone("SELECT * FROM users WHERE guild_id = ? AND user_id = ?", (interaction.guild.id, member.id))
        xp = int(row["xp"]) if row else 0
        level = level_from_xp(xp)
        next_xp = (level + 1) ** 2 * 100
        current_level_xp = level**2 * 100
        embed = make_embed(f"Perfil de {member.display_name}")
        embed.add_field(name="XP", value=str(xp))
        embed.add_field(name="Nível", value=str(level))
        embed.add_field(name="Progresso", value=progress_bar(xp - current_level_xp, next_xp - current_level_xp))
        embed.add_field(name="Horas estudadas", value=f"{(row['study_minutes'] if row else 0) // 60}h")
        embed.add_field(name="Streak", value=f"{row['streak'] if row else 0} dias")
        embed.add_field(name="Linguagens", value=(row["languages"] if row and row["languages"] else "Não informado"), inline=False)
        embed.add_field(name="Área", value=(row["area"] if row and row["area"] else "Não informado"), inline=False)
        embed.add_field(name="Desafios concluídos", value=str(row["challenges_done"] if row else 0))
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ProfileCog(bot))
