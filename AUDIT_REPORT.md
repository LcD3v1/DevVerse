# DevVerse Assistant - Audit Report

Branch: `audit-devverse-stabilization`

Backup criado: `backup/pre-audit-devverse-20260711`

## 1. Inventario real

### Cogs

| Funcionalidade | Arquivo | Status | Dependencias | Riscos |
| --- | --- | --- | --- | --- |
| Setup do servidor | `bot/cogs/setup.py` | Parcial | Discord guild, Manage Channels | Precisa de teste em servidor real para idempotencia/permissoes. |
| Cargos, onboarding e permissoes | `bot/cogs/roles.py` | Parcial | Server Members Intent, Manage Roles, IDs em `data/roles.json` | Depende da hierarquia do cargo do bot no Discord. |
| IA | `bot/cogs/ai_assistant.py` | Parcial | Gateway/Ollama | Ollama em localhost nao funciona na ShardCloud sem tunel/gateway. |
| Pomodoro | `bot/cogs/pomodoro.py` | Funcionando localmente | SQLite | Nao testado em Discord real. |
| Tarefas | `bot/cogs/tasks.py` | Funcionando localmente | SQLite | Nao testado em Discord real. |
| Estudos/ranking | `bot/cogs/study.py` | Funcionando localmente | SQLite | Nao testado em Discord real. |
| Canais de estudo | `bot/cogs/study_channels.py` | Parcial | Manage Channels, cargos existentes | Permissoes precisam de validacao real. |
| Perfil | `bot/cogs/profile.py` | Funcionando localmente | SQLite | Nome do comando real e `/profile`, nao `/perfil`. |
| Moderacao | `bot/cogs/moderation.py` | Parcial | Manage Messages | Purge exige teste real com permissoes/canais. |
| Recursos | `bot/cogs/resources.py` | Funcionando localmente | Nenhuma externa critica | Nao testado em Discord real. |
| Roadmap | `bot/cogs/roadmap.py` | Funcionando localmente | Nenhuma externa critica | Nao testado em Discord real. |
| GitHub | `bot/cogs/github.py` | Nao testavel sem config | `ENABLE_GITHUB`, secret | Desativado quando `ENABLE_GITHUB=false`. |
| Monitores | `bot/cogs/monitor.py` | Parcial | HTTP externo, SQLite, canais configurados | Fontes sem API real podem falhar ou retornar vazio. |
| Central de comandos | `bot/cogs/help.py` | Funcionando localmente | discord.py app commands | Navegacao UI exige teste real. |
| Diagnostico | `bot/cogs/diagnostics.py` | Funcionando localmente | Admin, SQLite | Novo comando precisa sync no Discord apos deploy. |

### Slash commands/grupos detectados

`/ping`, `/setup_devserver`, `/limpar_devserver`, `/setup_roles`, `/editar_perfil`, `/sync_visitors`, `/permissions check`, `/rolepanel`, `/ask`, `/explain_code`, `/debug_code`, `/review_code`, `/optimize_code`, `/generate_code`, `/quiz`, `/challenge`, `/pomodoro`, `/task_create`, `/task_list`, `/task_done`, `/task_delete`, `/checkin`, `/ranking`, `/setup_study_channels`, `/profile`, `/clear quantidade`, `/clear tempo`, `/clear usuario`, `/warn`, `/warnings`, `/timeout`, `/kick`, `/ban`, `/resource`, `/roadmap`, `/github_link`, `/jobs setup`, `/jobs interval`, `/hackathon setup`, `/freelance setup`, `/freelance interval`, `/monitor status`, `/monitor remove`, `/monitor run jobs`, `/monitor run hackathons`, `/monitor run instagram`, `/monitor run freelance`, `/monitor instagram adicionar`, `/monitor youtube adicionar`, `/comandos`, `/diagnostico`.

### Events, tasks e views

| Item | Arquivo | Status | Observacao |
| --- | --- | --- | --- |
| `on_ready` | `bot/main.py`, `bot/cogs/roles.py` | Funcionando localmente | Logs adicionados; sync de visitantes roda uma vez. |
| `on_member_join` | `bot/cogs/roles.py` | Parcial | Aplica Visitante se ID/hierarquia/permissao estiverem corretos. |
| `monitor_task` | `bot/cogs/monitor.py` | Parcial | Log de inicio/cancelamento adicionado. |
| Persistent views | `bot/views/onboarding.py`, `bot/views/role_menu.py` | Funcionando localmente | Registradas no init de `RolesCog`; log adicionado. |

### Banco SQLite

Tabelas validadas pelo diagnostico: 27 tabelas, incluindo `guild_settings`, `users`, `user_profiles`, `monitors`, `monitor_logs`, `monitor_item_logs`, `notifications`, `sent_notifications`, `moderation_logs`, `jobs`, `hackathons`, `social_posts`, `freelance_opportunities`, `tasks`, `pomodoro_sessions`, `ai_logs`.

### Monitores e providers

| Monitor | Arquivos | Status | Observacao |
| --- | --- | --- | --- |
| Jobs | `jobs_monitor.py`, `providers/linkedin_provider.py`, `providers/indeed_provider.py`, `providers/public_jobs_provider.py` | Parcial | Providers existem; integracoes dependem de fontes externas e podem retornar erro/vazio. |
| Hackathons | `hackathon_monitor.py` | Parcial | Normalizacao existente; envio real depende de canal e HTTP externo. |
| Freelance | `freelance_monitor.py`, `providers/freelance/*` | Parcial | Providers importam; fontes reais dependem de endpoints/config. |
| Instagram/YouTube | `social_monitor.py` | Parcial | Diagnostico avisa quando provider do Instagram nao esta configurado. |

### Backend e dashboard

| Item | Arquivo | Status | Observacao |
| --- | --- | --- | --- |
| FastAPI app | `dashboard/backend/main.py` | Funcionando localmente | Import validado: `DevVerse Dashboard API`. |
| Rotas | `routes/platform.py`, `stats.py`, `tasks.py`, `users.py` | Parcial | Import geral OK; testes HTTP completos nao executados. |
| Frontend pages | `/`, `/commands`, `/dashboard` | Funcionando localmente | `npm run build` passou. |
| Lint frontend | `dashboard/frontend/package.json` | Quebrado | `next lint` invalido no Next 16: script tenta tratar `lint` como diretorio. |

## 2. Bugs corrigidos

- Adicionados logs claros de startup: banco pronto, cog carregado, cog ignorado, cog que falhou, comandos sincronizados.
- Adicionado log de registro das views persistentes de onboarding/cargos.
- Adicionado log de inicio/cancelamento da background task de monitores.
- Criado `python -m bot.diagnostics`, sem imprimir secrets.
- Criado comando admin `/diagnostico`, resposta privada.
- Criada suite local de testes com 30 verificacoes usando `unittest`.

## 3. Problemas encontrados

- O Python global do Windows nao possui dependencias do projeto (`discord`, `dotenv`, `aiosqlite`, `httpx`). Usar `.venv`.
- `ruff` nao esta instalado no `.venv`.
- `pytest` nao esta instalado no `.venv`; a suite local roda por `unittest`.
- `npm run lint` falha porque `next lint` nao e valido nessa instalacao do Next 16.
- Permissoes reais de Discord, purge, onboarding e slash command sync exigem servidor real.
- `AI_PROVIDER=ollama` com `OLLAMA_HOST=localhost` e ShardCloud tende a ficar offline fora do PC do desenvolvedor.
- Existem alteracoes nao relacionadas em `README.md` e `dashboard/*` antes desta auditoria. Elas nao foram revertidas nem incluidas neste commit.

## 4. Funcionalidades que exigem credenciais/Discord real

- Aplicacao automatica do cargo Visitante em membro novo.
- Visibilidade real de canais por `@everyone`, Visitante e cargos especificos.
- Envio real de embeds em canais configurados.
- `clear` com purge e mensagens antigas/fixadas.
- Sincronizacao de slash commands no Discord.
- Providers externos de LinkedIn/Indeed/Instagram/YouTube quando exigirem API/token.
- GitHub webhook/comandos com `ENABLE_GITHUB=true`.

## 5. Testes executados

- `.venv\Scripts\python.exe -m compileall -q bot tests` - passou.
- `.venv\Scripts\python.exe -m unittest discover -s tests` - 30 testes passaram.
- `.venv\Scripts\python.exe -m bot.diagnostics` - passou com avisos nao criticos.
- `.venv\Scripts\python.exe -c "from dashboard.backend.main import app; print(app.title)"` - passou.
- `npm run build` em `dashboard/frontend` - passou.
- `.venv\Scripts\python.exe -m ruff check bot tests` - nao executavel, ruff ausente.
- `.venv\Scripts\python.exe -m pytest -q` - nao executavel, pytest ausente.
- `npm.cmd run lint` - falhou por script `next lint` invalido.

## 6. Como testar localmente

1. Ative o ambiente: `.venv\Scripts\Activate.ps1`.
2. Rode: `python -m bot.diagnostics`.
3. Rode: `python -m unittest discover -s tests`.
4. Rode: `python -m compileall -q bot tests`.
5. Para dashboard: entre em `dashboard/frontend` e rode `npm run build`.

## 7. Como publicar na ShardCloud

1. Configure `.env`/variaveis da ShardCloud sem expor tokens.
2. Confirme `DISCORD_TOKEN`, `GUILD_ID`, `DATABASE_PATH`, `MONITOR_ENABLED`.
3. Ative Server Members Intent no Discord Developer Portal.
4. Garanta que o cargo do bot esteja acima de Visitante e cargos que ele aplica.
5. Se usar IA, prefira gateway publico/privado configurado em `AI_GATEWAY_URL`; nao dependa de `localhost` da maquina pessoal.
6. Fazer deploy da branch/commit auditado.

## 8. Checklist pos-deploy

- Rodar `/diagnostico`.
- Rodar `/setup_roles` informando cargo Visitante e canais.
- Testar entrada de usuario novo e verificar cargo Visitante.
- Rodar `/permissions check` para Visitante.
- Rodar `/monitor status`.
- Rodar `/monitor run jobs` e confirmar envio no canal configurado.
- Verificar logs do host para `Cog carregado`, `Banco pronto`, `Task iniciada`.
