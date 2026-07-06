# DevVerse Monitor

O DevVerse Monitor adiciona tarefas automaticas para procurar oportunidades e conteudo externo e avisar nos canais certos do Discord.

## O que foi adicionado

- `bot/services/monitor/jobs_monitor.py`: busca e filtra vagas de tecnologia.
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
HACKATHON_SOURCE_URLS=https://devpost.com/api/hackathons
INSTAGRAM_RSS_TEMPLATE=
```

`MONITOR_INTERVAL_MINUTES` controla a task base. Cada monitor tambem tem sua propria frequencia configurada pelo comando.

`JOBS_SOURCE_URLS` e `HACKATHON_SOURCE_URLS` aceitam multiplas URLs separadas por virgula. Os parsers aceitam formatos JSON comuns com listas na raiz ou em `data`.

`INSTAGRAM_RSS_TEMPLATE` deve conter `{username}`. Sem essa variavel, perfis do Instagram podem ser cadastrados, mas a checagem nao envia novos posts.

## Comandos

### Vagas

```text
/jobs setup canal:#vagas areas:backend,python,devops frequencia_minutos:60
```

Areas suportadas:

- frontend
- backend
- full stack
- mobile
- data science
- machine learning
- artificial intelligence
- cybersecurity
- devops
- cloud
- blockchain

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

`notifications` tem indice unico por `type` e `url`, evitando notificacoes duplicadas.

## Como testar

1. Configure o `.env`.
2. Rode `python run.py`.
3. No Discord, execute `/jobs setup` em um canal de teste.
4. Execute `/monitor status` para conferir se a fonte foi cadastrada.
5. Aguarde o proximo ciclo ou reduza temporariamente a frequencia para 5 minutos.

Para validar YouTube rapidamente, use uma URL direta de feed RSS ou um ID de canal `UC...`.

## Preparacao para IA

Os itens trafegam como `MonitorItem`, com `summary` e `metadata`. Antes do envio, o `NotificationService` pode receber uma etapa futura de IA para enriquecer resumo, relevancia e recomendacoes sem mudar os comandos ou a task principal.
