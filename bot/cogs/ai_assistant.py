from __future__ import annotations

import time

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from bot.config import settings
from bot.templates import SYSTEM_PROMPT
from bot.utils import make_embed, send_long, split_message


class AIAssistantCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.cooldowns: dict[int, float] = {}

    def _cooldown_left(self, user_id: int, seconds: int = 12) -> int:
        now = time.monotonic()
        last = self.cooldowns.get(user_id, 0)
        if now - last < seconds:
            return int(seconds - (now - last))
        self.cooldowns[user_id] = now
        return 0

    async def ask_ollama(self, prompt: str) -> str:
        payload = {
            "model": settings.ollama_model,
            "stream": False,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt[:8000]},
            ],
        }
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=90)) as session:
                async with session.post(f"{settings.ollama_host}/api/chat", json=payload) as response:
                    if response.status >= 400:
                        return f"Ollama respondeu com erro HTTP {response.status}. Verifique se o modelo `{settings.ollama_model}` está instalado."
                    data = await response.json()
        except (aiohttp.ClientError, TimeoutError):
            return "Não consegui falar com o Ollama. Confirme se ele está aberto com `ollama serve` e se o host no `.env` está correto."
        content = data.get("message", {}).get("content", "").strip()
        return content[:5500] or "A IA não retornou conteúdo."

    async def _run_ai(self, interaction: discord.Interaction, command: str, prompt: str) -> None:
        if left := self._cooldown_left(interaction.user.id):
            await interaction.response.send_message(f"Aguarde {left}s antes de usar a IA novamente.", ephemeral=True)
            return
        await interaction.response.defer()
        if interaction.guild:
            await self.bot.db.execute(
                "INSERT INTO ai_logs (guild_id, user_id, command, prompt) VALUES (?, ?, ?, ?)",
                (interaction.guild.id, interaction.user.id, command, prompt[:1000]),
            )
        answer = await self.ask_ollama(prompt)
        await send_long(interaction, answer, "DevVerse AI")

    @app_commands.command(name="ask", description="Pergunta geral para a IA.")
    async def ask(self, interaction: discord.Interaction, pergunta: str) -> None:
        await self._run_ai(interaction, "ask", pergunta)

    @app_commands.command(name="explain_code", description="Explica um código.")
    async def explain_code(self, interaction: discord.Interaction, linguagem: str, codigo: str) -> None:
        await self._run_ai(interaction, "explain_code", f"Explique este código em {linguagem}:\n```{linguagem}\n{codigo}\n```")

    @app_commands.command(name="debug_code", description="Ajuda a encontrar um erro no código.")
    async def debug_code(self, interaction: discord.Interaction, linguagem: str, codigo: str, erro: str = "") -> None:
        await self._run_ai(interaction, "debug_code", f"Ajude a depurar este código em {linguagem}. Erro: {erro}\n```{linguagem}\n{codigo}\n```")

    @app_commands.command(name="review_code", description="Faz code review.")
    async def review_code(self, interaction: discord.Interaction, linguagem: str, codigo: str) -> None:
        await self._run_ai(interaction, "review_code", f"Faça code review didático deste código em {linguagem}:\n```{linguagem}\n{codigo}\n```")

    @app_commands.command(name="optimize_code", description="Sugere melhorias de código.")
    async def optimize_code(self, interaction: discord.Interaction, linguagem: str, codigo: str) -> None:
        await self._run_ai(interaction, "optimize_code", f"Otimize este código em {linguagem} e explique as melhorias:\n```{linguagem}\n{codigo}\n```")

    @app_commands.command(name="generate_code", description="Gera código a partir de uma descrição.")
    async def generate_code(self, interaction: discord.Interaction, linguagem: str, descricao: str) -> None:
        await self._run_ai(interaction, "generate_code", f"Gere código em {linguagem} para: {descricao}")

    @app_commands.command(name="quiz", description="Gera um quiz de programação.")
    async def quiz(self, interaction: discord.Interaction, tema: str, dificuldade: str) -> None:
        await self._run_ai(interaction, "quiz", f"Crie um quiz de 5 perguntas sobre {tema}, nível {dificuldade}, com gabarito no final.")

    @app_commands.command(name="challenge", description="Gera desafio de programação.")
    async def challenge(self, interaction: discord.Interaction, linguagem: str, dificuldade: str) -> None:
        await self._run_ai(interaction, "challenge", f"Crie um desafio prático de programação em {linguagem}, nível {dificuldade}, com critérios de aceite.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or not message.guild:
            return
        if message.channel.name != settings.ai_channel_name:
            await self._maybe_add_message_xp(message)
            return
        if left := self._cooldown_left(message.author.id):
            await message.reply(f"Aguarde {left}s antes de perguntar de novo.", mention_author=False)
            return
        async with message.channel.typing():
            await self.bot.db.execute(
                "INSERT INTO ai_logs (guild_id, user_id, command, prompt) VALUES (?, ?, ?, ?)",
                (message.guild.id, message.author.id, "ai_channel", message.content[:1000]),
            )
            answer = await self.ask_ollama(message.content)
        for chunk in split_message(answer):
            await message.channel.send(embed=make_embed("DevVerse AI", chunk))

    async def _maybe_add_message_xp(self, message: discord.Message) -> None:
        row = await self.bot.db.fetchone("SELECT last_message_xp FROM users WHERE guild_id = ? AND user_id = ?", (message.guild.id, message.author.id))
        now = int(time.time())
        last = int(row["last_message_xp"]) if row and row["last_message_xp"] else 0
        if now - last < 60:
            return
        await self.bot.db.execute(
            """
            INSERT INTO users (guild_id, user_id, xp, last_message_xp) VALUES (?, ?, 5, ?)
            ON CONFLICT(guild_id, user_id) DO UPDATE SET xp = xp + 5, last_message_xp = excluded.last_message_xp
            """,
            (message.guild.id, message.author.id, str(now)),
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AIAssistantCog(bot))
