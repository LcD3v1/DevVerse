# DevVerse Monitor

O DevVerse Monitor adiciona tarefas automaticas para procurar oportunidades e conteudo externo e avisar nos canais certos do Discord.

## O que foi adicionado

- `bot/services/monitor/jobs_monitor.py`: busca e filtra vagas de tecnologia.
- `bot/services/monitor/providers/`: providers de vagas para LinkedIn, Indeed e fontes existentes.
- `bot/services/monitor/hackathon_monitor.py`: busca eventos e hackathons.
- `bot/services/monitor/social_monitor.py`: monitora YouTube por RSS e Instagram por template RSS configuravel.
- `bot/services/monitor/notification_service.py`: cria embeds, envia mensagens e registra duplicidade.
- `bot/services/monitor/monitor_manager.py`: executa monitores com retry, logs e controle de frequencia.
- `bot/cogs/monitor.py`: comandos slash e task de background.

## Variaveis de ambiente

```env
MONITOR_ENABLED=true
MONITOR_INTERVAL_MINUTES=5
JOBS_SOURCE_URLS=https://remoteok.com/api
JOBS_DEFAULT_LOCATION=Worldwide
HACKATHON_SOURCE_URLS=https://devpost.com/api/hackathons
INSTAGRAM_RSS_TEMPLATE=
```

`MONITOR_INTERVAL_MINUTES` controla a task base. Cada monitor tambem tem sua propria frequencia configurada pelo comando.

`JOBS_SOURCE_URLS` alimenta o provider `existing` e aceita multiplas URLs separadas por virgula. Os parsers aceitam formatos JSON comuns com listas na raiz ou em `data`.

`JOBS_DEFAULT_LOCATION` e usado nas buscas de LinkedIn e Indeed.

`INSTAGRAM_RSS_TEMPLATE` deve conter `{username}`. Sem essa variavel, perfis do Instagram podem ser cadastrados, mas a checagem nao envia novos posts.

## Comandos

### Vagas

```text
/jobs setup canal:#vagas fontes:linkedin,indeed,existing areas:backend,ai engineer,cybersecurity niveis:junior,mid modelos:remote,hybrid frequencia_minutos:60
```

Fontes suportadas:

- linkedin
- indeed
- existing

Areas suportadas:

- frontend
- backend
- full stack
- mobile
- data science
- machine learning
- ai engineer
- cybersecurity
- devops
- cloud

Aliases aceitos incluem `ai`, `ia`, `ml`, `fullstack`, `front-end`, `back-end` e `security`.

Niveis suportados:

- internship
- entry level
- junior
- mid
- senior

Aliases aceitos incluem `estagio`, `estagiario`, `jr`, `pleno`, `sr` e `trainee`.

Modelos suportados:

- remote
- hybrid
- on-site

Aliases aceitos incluem `remoto`, `hibrido`, `presencial`, `onsite` e `on site`.

### Hackathons

```text
/hackathon setup canal:#hackathons categorias:ai,web3 frequencia_minutos:720
```

### Conteudo social

```text
/monitor youtube adicionar canal_youtube:@canal canal:#conteudo frequencia_minutos:120
/monitor instagram adicionar perfil:@perfil canal:#conteudo frequencia_minutos:120
```

YouTube aceita:

- `@handle`
- URL do canal
- ID de canal iniciado por `UC`
- URL direta do RSS

### Administracao

```text
/monitor status
/monitor remove monitor_id:1
```

## Banco de dados

O setup do bot cria automaticamente:

- `monitors`
- `notifications`
- `jobs`
- `hackathons`
- `social_posts`

`jobs` e `notifications` guardam `source`, `external_id` e `unique_hash`. Para vagas, a deduplicacao prioriza o hash de `source + external_id`, evitando reenviar a mesma vaga mesmo quando o link tiver parametros diferentes.

## Como testar

1. Configure o `.env`.
2. Rode `python run.py`.
3. No Discord, execute `/jobs setup` em um canal de teste.
4. Execute `/monitor status` para conferir se a fonte foi cadastrada.
5. Aguarde o proximo ciclo ou reduza temporariamente a frequencia para 5 minutos.

Para validar YouTube rapidamente, use uma URL direta de feed RSS ou um ID de canal `UC...`.

## Preparacao para IA

Os itens trafegam como `MonitorItem`, com `summary` e `metadata`. Antes do envio, o `NotificationService` pode receber uma etapa futura de IA para enriquecer resumo, relevancia e recomendacoes sem mudar os comandos ou a task principal.
