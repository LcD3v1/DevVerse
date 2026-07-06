# DevVerse Assistant

Bot all-in-one para Discord feito em Python 3.11+, `discord.py` 2.x, slash commands, SQLite e IA local gratuita com Ollama.

Ele foi pensado para um grupo pequeno estudar programação, organizar projetos, registrar progresso, usar Pomodoro, criar tarefas, revisar código com IA e preparar o servidor Discord inteiro com um comando.

## Recursos

- `/setup_devserver` cria cargos, categorias, canais, permissões e mensagens iniciais.
- `/limpar_devserver` remove somente itens registrados como criados pelo bot.
- `/rolepanel` cria menus de autoatribuição de cargos.
- IA local com Ollama: `/ask`, `/explain_code`, `/debug_code`, `/review_code`, `/optimize_code`, `/generate_code`, `/quiz`, `/challenge`.
- Canal `🤖・ai-assistant` responde automaticamente mensagens com IA.
- `/checkin`, `/profile`, `/ranking`, `/pomodoro`.
- `/task_create`, `/task_list`, `/task_done`, `/task_delete`.
- `/resource` e `/roadmap`.
- Moderação: `/warn`, `/warnings`, `/clear`, `/timeout`, `/kick`, `/ban`.
- Módulo opcional GitHub com `/github_link`.
- DevVerse Monitor: alertas automaticos de vagas, hackathons, YouTube e Instagram via feed configuravel.

## Requisitos

- Python 3.11+
- Discord bot criado no Discord Developer Portal
- Ollama instalado localmente
- Modelo local, por exemplo `qwen2.5-coder`

## Instalação

```bash
cd devverse-assistant
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Edite o `.env`:

```env
DISCORD_TOKEN=seu_token
GUILD_ID=id_do_servidor
COMMAND_PREFIX=!
AI_PROVIDER=gateway
AI_GATEWAY_URL=
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder
AI_CHANNEL_NAME=🤖・ai-assistant
DATABASE_PATH=data/database.sqlite3
OWNER_IDS=
ENABLE_GITHUB=false
GITHUB_WEBHOOK_SECRET=
MONITOR_ENABLED=true
MONITOR_INTERVAL_MINUTES=5
JOBS_DEFAULT_SOURCES=linkedin,indeed,existing
JOBS_SOURCE_URLS=https://remoteok.com/api
JOBS_DEFAULT_LOCATION=Worldwide
HACKATHON_SOURCE_URLS=https://devpost.com/api/hackathons
INSTAGRAM_RSS_TEMPLATE=https://rsshub.app/instagram/user/{username}
```

## Criar o bot no Discord

1. Acesse o Discord Developer Portal.
2. Crie uma aplicação.
3. Abra Bot > Add Bot.
4. Copie o token para `DISCORD_TOKEN`.
5. Ative `Server Members Intent` e `Message Content Intent`.
6. Em OAuth2 > URL Generator, marque `bot` e `applications.commands`.
7. Convide com permissão `Administrator` para o setup inicial.

## Instalar Ollama

Instale o Ollama e baixe o modelo:

```bash
ollama pull qwen2.5-coder
```

Se o serviço não estiver rodando:

```bash
ollama serve
```

Para trocar o modelo:

```bash
ollama pull llama3.1
```

Depois altere no `.env`:

```env
OLLAMA_MODEL=llama3.1
```

## IA com bot hospedado

Se o bot estiver em host/cloud, ele nao consegue acessar `http://localhost:11434` do seu PC. Nesse caso, `localhost` aponta para o proprio servidor do bot, nao para a sua maquina.

Use uma destas opcoes:

```env
AI_PROVIDER=gateway
AI_GATEWAY_URL=https://sua-url-publica/api/generate
OLLAMA_MODEL=qwen2.5-coder
```

Enquanto `AI_GATEWAY_URL` estiver vazio, o bot nao quebra: ele responde com a mensagem amigavel `IA local offline (Ollama rodando apenas no PC do dev)`.

Para desenvolvimento local, quando bot e Ollama rodam na mesma maquina:

```env
AI_PROVIDER=ollama_local
OLLAMA_HOST=http://localhost:11434
```

Gateway opcional para rodar na maquina/VPS que tem Ollama:

```bash
ai_gateway\start-gateway.cmd
```

Esse gateway expõe `POST /api/generate` e repassa para o Ollama local da maquina onde ele estiver rodando.

## Rodar

```bash
python run.py
```

No Discord, use:

```text
/setup_devserver
```

Esse comando cria a estrutura do servidor e registra os itens criados na tabela `created_items`.

## Hospedar na ShardCloud

Configure o start como:

```text
python run.py
```

O repositório também inclui `Procfile` com `worker: python run.py` e `main.py` na raiz para hosts que detectam automaticamente o arquivo principal.

No painel da hospedagem, configure pelo menos:

```env
DISCORD_TOKEN=seu_token
GUILD_ID=id_do_servidor
AI_PROVIDER=gateway
DATABASE_PATH=data/database.sqlite3
MONITOR_ENABLED=true
MONITOR_INTERVAL_MINUTES=5
```

No Discord Developer Portal, deixe ativados:

```text
Server Members Intent
Message Content Intent
```

Se o log mostrar `Defina DISCORD_TOKEN`, a variável não foi configurada na hospedagem. Se o processo iniciar e cair durante o carregamento, veja o log do deploy para identificar o cog que falhou.

## DevVerse Monitor

O DevVerse Monitor roda em segundo plano e envia notificacoes automaticas nos canais configurados. Ele evita duplicidade pelo link do conteudo e salva historico no SQLite nas tabelas `monitors`, `notifications`, `jobs`, `hackathons` e `social_posts`.

Configurar vagas:

```text
/jobs setup canal:#vagas fontes:linkedin,indeed,existing frequencia_minutos:5
/jobs interval minutos:15
```

As fontes suportadas sao `linkedin`, `indeed` e `existing`. O monitor de vagas nao limita por usuario: ele busca continuamente vagas de tecnologia em frontend, backend, full stack, mobile, data science, machine learning, artificial intelligence, cybersecurity, devops, cloud, blockchain e game development.

Configurar hackathons:

```text
/hackathon setup canal:#hackathons categorias:ai,web3 frequencia_minutos:720
```

Monitorar YouTube:

```text
/monitor youtube adicionar canal_youtube:@canal canal:#conteudo frequencia_minutos:120
```

Tambem funciona com URL do canal, ID iniciado por `UC...` ou URL direta do feed RSS.

Monitorar Instagram:

```text
/monitor instagram adicionar perfil:@perfil canal:#conteudo frequencia_minutos:120
```

O Instagram nao fornece feed publico oficial sem credenciais. Por padrao, o bot usa RSSHub:

```env
INSTAGRAM_RSS_TEMPLATE=https://rsshub.app/instagram/user/{username}
```

Se a instancia publica do RSSHub limitar ou bloquear requisicoes, use uma instancia propria e troque apenas essa variavel.

Administracao:

```text
/monitor status
/monitor run jobs
/monitor run hackathons
/monitor run instagram
/monitor remove monitor_id:1
```

## Onboarding e cargos

Configure os IDs dos cargos ja existentes em `data/roles.json`. O bot nao cria cargos novos para o painel de entrada; ele apenas aplica/remover cargos pelos IDs configurados.

Use `/setup_roles` para publicar o painel em `#👋・bem-vindo`, criar a estrutura de canais por area e ativar a selecao por menus. Quando alguem entrar no servidor, o bot envia o painel de boas-vindas no mesmo canal.

Permissoes necessarias:

```text
Manage Roles
Manage Channels
Send Messages
Use Application Commands
```

Limpeza de mensagens:

```text
/clear quantidade quantidade:100
/clear tempo tempo:24h
/clear usuario usuario:@membro
```

Exige `Administrator` ou `Manage Messages` e registra logs em `#mod-logs` quando o canal existir.

As fontes podem ser trocadas por `.env`:

```env
JOBS_SOURCE_URLS=https://remoteok.com/api
JOBS_DEFAULT_LOCATION=Worldwide
HACKATHON_SOURCE_URLS=https://devpost.com/api/hackathons
MONITOR_INTERVAL_MINUTES=5
```

Mais detalhes em `docs/MONITOR.md`.

## Rodar dashboard e backend

Em um terminal, suba a API FastAPI:

```bash
dashboard\backend\start-backend.cmd
```

Em outro terminal, suba o dashboard web:

```bash
cd dashboard\frontend
npm.cmd install
npm.cmd run dev -- --hostname 127.0.0.1 --port 3000
```

URLs locais:

```text
Dashboard: http://localhost:3000
Backend:   http://127.0.0.1:8000
Health:    http://127.0.0.1:8000/health
```

O dashboard le `/stats/server` do backend. Se a API estiver ligada, o botao no topo mostra `API online`; se nao estiver, a tela continua em modo demo.

## Limpar estrutura

```text
/limpar_devserver
```

O bot pede confirmação e remove somente canais, categorias e cargos que ele mesmo registrou. Canais antigos ou criados manualmente não são removidos.

## Comandos de IA

```text
/ask pergunta
/explain_code linguagem codigo
/debug_code linguagem codigo erro
/review_code linguagem codigo
/optimize_code linguagem codigo
/generate_code linguagem descricao
/quiz tema dificuldade
/challenge linguagem dificuldade
/roadmap area nivel
```

Também é possível escrever direto no canal `🤖・ai-assistant`.

## Testar se está funcionando

1. Rode `ollama serve`.
2. Rode `python run.py`.
3. Use `/ping`.
4. Use `/setup_devserver`.
5. Escreva uma pergunta no canal `🤖・ai-assistant`.
6. Use `/checkin`, `/profile` e `/task_create`.

## Estrutura

```text
bot/
  cogs/
  services/
    monitor/
  views/
  config.py
  database.py
  templates.py
  permissions.py
  utils.py
data/
docs/
run.py
requirements.txt
```
