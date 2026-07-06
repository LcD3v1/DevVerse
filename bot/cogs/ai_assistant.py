from __future__ import annotations

import asyncio
import logging
import time

import discord
import requests
from discord import app_commands
from discord.ext import commands

from bot.config import settings
from bot.templates import SYSTEM_PROMPT
from bot.utils import split_message


DEVVERSE_AI_COLOR = discord.Color(0x6C5CE7)
AI_OFFLINE_MESSAGE = (
    "IA local offline (Ollama rodando apenas no PC do dev).\n\n"
    "Configure `AI_GATEWAY_URL` com uma URL publica/VPS para conectar o bot hospedado ao motor de IA."
)
logger = logging.getLogger("devverse.ai")


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

    async def ask_ai(self, prompt: str) -> str:
        try:
            content = await asyncio.to_thread(self._ask_ai_sync, prompt)
        except requests.Timeout:
            logger.warning("AI request timed out. provider=%s gateway=%s", settings.ai_provider, bool(settings.ai_gateway_url))
            return "A IA demorou para responder. Tente novamente em alguns segundos."
        except requests.RequestException as exc:
            logger.warning("AI request failed: %s", exc)
            return AI_OFFLINE_MESSAGE
        except (KeyError, ValueError):
            logger.exception("AI response format was invalid.")
            return "A IA respondeu em um formato inesperado. Verifique o AI Gateway."
        return content[:5500] or "A IA nao retornou conteudo."

    def _ask_ai_sync(self, prompt: str) -> str:
        if settings.ai_gateway_url:
            return self._ask_ai_gateway_sync(prompt)
        if settings.ai_provider == "ollama_local":
            logger.warning("Using local Ollama mode. This only works when the bot runs on the same machine as Ollama.")
            return self._ask_local_ollama_sync(prompt)
        logger.warning("AI Gateway is not configured. Cloud bot cannot reach local Ollama.")
        return AI_OFFLINE_MESSAGE

    def _ask_ai_gateway_sync(self, prompt: str) -> str:
        payload = {
            "model": settings.ollama_model,
            "prompt": f"{SYSTEM_PROMPT}\n\n{prompt[:8000]}",
            "stream": False,
        }
        response = requests.post(settings.ai_gateway_url, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        return (data.get("response") or data.get("answer") or data.get("content") or "").strip()

    def _ask_local_ollama_sync(self, prompt: str) -> str:
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
        logger.info("AI command received. command=%s user_id=%s", command, interaction.user.id)
        answer = await self.ask_ai(prompt)
        await self._send_ai_response(interaction, answer, prompt)

    def create_ai_embed(self, question: str | None, answer: str, continuation: bool = False) -> discord.Embed:
        embed = discord.Embed(
            title="🧠 DevVerse AI Assistant" if not continuation else "🧠 DevVerse AI Assistant · continuação",
            description=f"```{answer[:3500]}```",
            color=DEVVERSE_AI_COLOR,
        )
        if question and not continuation:
            embed.add_field(
                name="Pergunta",
                value=question[:1000],
                inline=False,
            )
        embed.set_footer(text="DevVerse • AI System")
        return embed

    async def _send_ai_response(self, interaction: discord.Interaction, answer: str, question: str) -> None:
        chunks = split_message(answer, limit=3400)
        first = self.create_ai_embed(question, chunks[0])
        if interaction.response.is_done():
            await interaction.followup.send(embed=first)
        else:
            await interaction.response.send_message(embed=first)
        for chunk in chunks[1:]:
            await interaction.followup.send(embed=self.create_ai_embed(None, chunk, continuation=True))

    @app_commands.command(name="ask", description="Pergunta geral para a IA.")
    async def ask(self, interaction: discord.Interaction, pergunta: str) -> None:
        await self._run_ai(interaction, "ask", pergunta)

    @app_commands.command(name="explain_code", description="Explica um codigo.")
    async def explain_code(self, interaction: discord.Interaction, linguagem: str, codigo: str) -> None:
        await self._run_ai(interaction, "explain_code", f"Explique este codigo em {linguagem}:\n```{linguagem}\n{codigo}\n```")

    @app_commands.command(name="debug_code", description="Ajuda a encontrar um erro no codigo.")
    async def debug_code(self, interaction: discord.Interaction, linguagem: str, codigo: str, erro: str = "") -> None:
        await self._run_ai(interaction, "debug_code", f"Ajude a depurar este codigo em {linguagem}. Erro: {erro}\n```{linguagem}\n{codigo}\n```")

    @app_commands.command(name="review_code", description="Faz code review.")
    async def review_code(self, interaction: discord.Interaction, linguagem: str, codigo: str) -> None:
        await self._run_ai(interaction, "review_code", f"Faca code review didatico deste codigo em {linguagem}:\n```{linguagem}\n{codigo}\n```")

    @app_commands.command(name="optimize_code", description="Sugere melhorias de codigo.")
    async def optimize_code(self, interaction: discord.Interaction, linguagem: str, codigo: str) -> None:
        await self._run_ai(interaction, "optimize_code", f"Otimize este codigo em {linguagem} e explique as melhorias:\n```{linguagem}\n{codigo}\n```")

    @app_commands.command(name="generate_code", description="Gera codigo a partir de uma descricao.")
    async def generate_code(self, interaction: discord.Interaction, linguagem: str, descricao: str) -> None:
        await self._run_ai(interaction, "generate_code", f"Gere codigo em {linguagem} para: {descricao}")

    @app_commands.command(name="quiz", description="Gera um quiz de programacao.")
    async def quiz(self, interaction: discord.Interaction, tema: str, dificuldade: str) -> None:
        await self._run_ai(interaction, "quiz", f"Crie um quiz de 5 perguntas sobre {tema}, nivel {dificuldade}, com gabarito no final.")

    @app_commands.command(name="challenge", description="Gera desafio de programacao.")
    async def challenge(self, interaction: discord.Interaction, linguagem: str, dificuldade: str) -> None:
        await self._run_ai(interaction, "challenge", f"Crie um desafio pratico de programacao em {linguagem}, nivel {dificuldade}, com criterios de aceite.")

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
            logger.info("AI channel message received. user_id=%s guild_id=%s", message.author.id, message.guild.id)
            await self.bot.db.execute(
                "INSERT INTO ai_logs (guild_id, user_id, command, prompt) VALUES (?, ?, ?, ?)",
                (message.guild.id, message.author.id, "ai_channel", message.content[:1000]),
            )
            answer = await self.ask_ai(message.content)
        for index, chunk in enumerate(split_message(answer, limit=3400)):
            await message.channel.send(
                embed=self.create_ai_embed(message.content if index == 0 else None, chunk, continuation=index > 0)
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
