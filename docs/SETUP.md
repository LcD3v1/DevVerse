# Setup do DevVerse Assistant

## 1. Criar o bot no Discord

1. Acesse o Discord Developer Portal.
2. Crie uma aplicação.
3. Abra a área Bot e clique em Add Bot.
4. Copie o token e coloque em `.env` como `DISCORD_TOKEN`.
5. Ative as intents:
   - Server Members Intent
   - Message Content Intent
   - Presence Intent, se quiser expandir recursos depois

## 2. Convidar o bot

Na aba OAuth2 > URL Generator:

- Scopes: `bot` e `applications.commands`
- Permissões recomendadas:
  - Administrator, para o setup inicial
  - Ou permissões específicas: gerenciar cargos, canais, mensagens, membros, banir, expulsar, timeout, enviar mensagens, embeds e usar comandos

Abra a URL gerada e adicione o bot ao servidor.

## 3. Instalar dependências

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 4. Configurar `.env`

Copie `.env.example` para `.env` e preencha:

```env
DISCORD_TOKEN=seu_token
GUILD_ID=id_do_servidor
AI_PROVIDER=ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder
```

## 5. Instalar Ollama

Instale o Ollama pelo site oficial, abra o serviço e baixe o modelo:

```bash
ollama pull qwen2.5-coder
```

Se quiser outro modelo, baixe com `ollama pull nome-do-modelo` e altere `OLLAMA_MODEL`.

## 6. Rodar

```bash
python run.py
```

Depois use `/setup_devserver` no Discord.
