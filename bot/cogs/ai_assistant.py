from __future__ import annotations

import asyncio
import time

import discord
import requests
from discord import app_commands
from discord.ext import commands

from bot.config import settings
from bot.templates import SYSTEM_PROMPT
from bot.utils import split_message


DEVVERSE_AI_COLOR = discord.Color(0x6C5CE7)
DEVVERSE_AI_ICON_URL = "https://i.imgur.com/placeholder.png"


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
        try:
            content = await asyncio.to_thread(self._ask_ollama_sync, prompt)
        except requests.Timeout:
            return "O Ollama demorou para responder. Tente novamente ou use um prompt menor."
        except requests.RequestException:
            return "Não consegui falar com o Ollama. Confirme se ele está aberto com `ollama serve` e se o host no `.env` está correto."
        except (KeyError, ValueError):
            return "O Ollama respondeu em um formato inesperado. Verifique se o endpoint `/api/generate` está ativo."
        return content[:5500] or "A IA não retornou conteúdo."

    def _ask_ollama_sync(self, prompt: str) -> str:
        url = f"{settings.ollama_host}/api/generate"
        payload = {
            "model": settings.ollama_model,
            "prompt": f"{SYSTEM_PROMPT}\n\n{prompt[:8000]}",
            "stream": False,
        }
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()
        return response.json()["response"].strip()

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
        await self._send_ai_response(interaction, answer, prompt)

    def _make_ai_embed(self, answer: str, question: str | None = None, continuation: bool = False) -> discord.Embed:
        embed = discord.Embed(
            title="🤖 DevVerse AI" if not continuation else "🤖 DevVerse AI · continuação",
            description=f"```{answer[:3500]}```",
            color=DEVVERSE_AI_COLOR,
        )
        embed.set_author(
            name="AI Assistant",
            icon_url=DEVVERSE_AI_ICON_URL,
        )
        if question and not continuation:
            embed.add_field(
                name="🧠 Prompt",
                value=question[:1000],
                inline=False,
            )
        embed.set_footer(text="Powered by Ollama • DevVerse System")
        return embed

    async def _send_ai_response(self, interaction: discord.Interaction, answer: str, question: str) -> None:
        chunks = split_message(answer, limit=3400)
        first = self._make_ai_embed(chunks[0], question)
        if interaction.response.is_done():
            await interaction.followup.send(embed=first)
        else:
            await interaction.response.send_message(embed=first)
        for chunk in chunks[1:]:
            await interaction.followup.send(embed=self._make_ai_embed(chunk, continuation=True))

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
        for index, chunk in enumerate(split_message(answer, limit=3400)):
            await message.channel.send(
                embed=self._make_ai_embed(chunk, message.content if index == 0 else None, continuation=index > 0)
            )

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
