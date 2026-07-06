from __future__ import annotations

import discord

SERVER_CATEGORIES: dict[str, list[tuple[str, str]]] = {
    "📚 Informações": [("📜・regras", "text"), ("📢・avisos", "text"), ("🗺️・roadmap", "text"), ("🎯・metas-semana", "text"), ("🤖・ai-assistant", "text")],
    "💬 Geral": [("💬・chat-geral", "text"), ("🤝・apresentações", "text"), ("😂・memes", "text"), ("☕・off-topic", "text")],
    "💻 Estudos": [("📚・recursos", "text"), ("❓・dúvidas", "text"), ("💡・explicações", "text"), ("📝・anotações", "text"), ("📖・desafios-diários", "text"), ("🏆・conquistas", "text")],
    "👨‍💻 Código": [("🐍・python", "text"), ("🌐・javascript", "text"), ("⚛️・react", "text"), ("⚙️・backend", "text"), ("🗄️・database", "text"), ("🤖・ai-machine-learning", "text"), ("🔒・cybersecurity", "text"), ("☁️・cloud", "text"), ("🐧・linux", "text"), ("📦・git-github", "text")],
    "🚀 Projetos": [("📁・portfolio", "text"), ("📁・ai-assistant", "text"), ("📁・discord-bot", "text"), ("📁・website", "text")],
    "🤝 Pair Programming": [("👥・code-review", "text"), ("🔍・feedback", "text"), ("🧠・brainstorm", "text")],
    "📈 Progresso": [("✅・check-in-diário", "text"), ("📅・planejamento", "text"), ("📊・progresso", "text"), ("🏅・leaderboard", "text")],
    "📂 Arquivos": [("📄・pdfs", "text"), ("📷・prints", "text"), ("🎥・vídeos", "text"), ("💾・downloads", "text")],
    "💼 Carreira": [("💼・currículos", "text"), ("🎤・mock-interviews", "text"), ("❓・leetcode", "text"), ("🧩・system-design", "text"), ("🚀・hackathons", "text"), ("💼・vagas", "text")],
    "🔊 Voz": [("🎧 Study Room 1", "voice"), ("🎧 Study Room 2", "voice"), ("💻 Pair Programming", "voice"), ("☕ Chill", "voice")],
}

ROLE_GROUPS: dict[str, list[str]] = {
    "Administração": ["👑 Owner", "🛡️ Co-Owner", "⚙️ Admin", "🧑‍🏫 Mentor"],
    "Níveis": ["🎓 Estudante", "🌱 Iniciante", "📘 Básico", "📗 Intermediário", "📙 Avançado", "🏆 Expert"],
    "Especialidades": ["🌐 Front-end", "⚙️ Back-end", "👨‍💻 Full Stack", "📱 Mobile", "🎨 UI/UX", "🤖 Inteligência Artificial", "📊 Ciência de Dados", "🛢️ Engenharia de Dados", "☁️ Cloud", "🔒 Cybersecurity", "🧪 DevOps", "🐧 Linux", "📦 Git/GitHub", "🗄️ Banco de Dados", "⚡ Automação", "⛓️ Blockchain"],
    "Linguagens": ["🐍 Python", "☕ Java", "⚙️ C", "⚙️ C++", "🦀 Rust", "💙 C#", "🟨 JavaScript", "🔷 TypeScript", "🐘 PHP", "💎 Ruby", "🐹 Go", "🍎 Swift"],
    "Frameworks": ["⚛️ React", "🟩 Node.js", "🟢 Express", "🚀 Next.js", "🔥 Django", "🌶️ Flask", "🧱 Spring Boot", "🐘 Laravel", "💚 Vue", "🔺 Angular", "📱 Flutter"],
    "Sistemas Operacionais": ["🪟 Windows", "🐧 Linux", "🍎 macOS"],
    "Objetivos": ["💼 Conseguir emprego", "📚 Faculdade", "🏆 Competições", "🚀 Freelancer", "💰 Empreender", "🤖 Criar IA", "🔒 Pentest", "🌐 Full Stack", "📱 Mobile"],
    "Status": ["🟢 Disponível", "📚 Estudando", "💻 Codando", "☕ Pausa", "🌙 Ausente"],
    "Conquistas": ["🥇 10 horas estudadas", "🥈 50 horas estudadas", "🥉 100 horas estudadas", "🔥 7 dias de streak", "🚀 Primeiro projeto", "💻 Primeiro Pull Request", "⭐ Mentor da Semana"],
}

ROLE_COLORS = {
    "Administração": discord.Color.red(),
    "Níveis": discord.Color.blue(),
    "Especialidades": discord.Color.teal(),
    "Linguagens": discord.Color.green(),
    "Frameworks": discord.Color.purple(),
    "Sistemas Operacionais": discord.Color.light_grey(),
    "Objetivos": discord.Color.gold(),
    "Status": discord.Color.orange(),
    "Conquistas": discord.Color.dark_gold(),
}

ROLE_PANEL_GROUPS = ["Especialidades", "Linguagens", "Frameworks", "Sistemas Operacionais", "Objetivos", "Status"]

INITIAL_MESSAGES = {
    "📜・regras": ("Regras do Servidor", "1. Respeite todos os membros.\n2. Nada de spam.\n3. Use os canais corretos.\n4. Ajude antes de julgar.\n5. Compartilhe conhecimento.\n6. Não envie conteúdo ilegal ou ofensivo.\n7. Mantenha o foco nos estudos."),
    "🗺️・roadmap": ("Roadmap de Estudos", "Etapa 1: Lógica de programação\nEtapa 2: Git e GitHub\nEtapa 3: HTML e CSS\nEtapa 4: JavaScript\nEtapa 5: Python\nEtapa 6: Banco de dados\nEtapa 7: APIs\nEtapa 8: React\nEtapa 9: Node.js\nEtapa 10: Docker\nEtapa 11: Linux\nEtapa 12: Cloud\nEtapa 13: Cybersecurity\nEtapa 14: AI e Machine Learning\nEtapa 15: Projeto final em grupo"),
    "📚・recursos": ("Recursos Gratuitos", "- CS50\n- freeCodeCamp\n- The Odin Project\n- Roadmap.sh\n- MDN Web Docs\n- W3Schools\n- Full Stack Open\n- Exercism\n- LeetCode\n- GitHub Docs"),
    "✅・check-in-diário": ("Modelo de Check-in Diário", "Hoje vou estudar:\n- [ ] Tópico 1\n- [ ] Tópico 2\n- [ ] Tópico 3\n\nTempo planejado:\nDificuldade de hoje:\nO que aprendi:"),
    "🎯・metas-semana": ("Metas da Semana", "Cada membro deve postar:\n1. O que vai estudar.\n2. Quantas horas pretende estudar.\n3. Qual projeto vai desenvolver.\n4. Qual dificuldade quer superar."),
    "🤝・apresentações": ("Apresente-se", "Nome:\nÁrea de interesse:\nNível atual:\nObjetivo:\nTecnologias que quer aprender:\nDisponibilidade para estudar:"),
    "🤖・ai-assistant": ("DevVerse AI", "Faça perguntas sobre programação, peça ajuda com código, debugging, explicações, roadmaps, quizzes e desafios.\n\nExemplos:\n/ask O que é uma API?\n/debug_code Python [cole seu código]\n/roadmap Full Stack iniciante"),
}

RESOURCES = {
    "python": ["Python.org Tutorial", "CS50P", "Automate the Boring Stuff", "Exercism Python"],
    "javascript": ["MDN JavaScript", "freeCodeCamp JavaScript", "The Odin Project", "JavaScript.info"],
    "html/css": ["MDN HTML", "MDN CSS", "web.dev", "Frontend Mentor"],
    "react": ["React Docs", "Full Stack Open", "Scrimba React", "Roadmap.sh React"],
    "node.js": ["Node.js Docs", "Express Docs", "Full Stack Open", "The Odin Project"],
    "git": ["Git Book", "GitHub Docs", "Atlassian Git Tutorials", "Learn Git Branching"],
    "linux": ["Linux Journey", "OverTheWire Bandit", "Ubuntu Tutorials", "The Linux Command Line"],
    "sql": ["SQLBolt", "Mode SQL Tutorial", "PostgreSQL Docs", "SQLite Docs"],
    "cybersecurity": ["TryHackMe Pre Security", "OWASP WebGoat", "PortSwigger Academy", "CyberDefenders"],
    "ai": ["Google ML Crash Course", "Hugging Face Course", "Fast.ai", "Ollama Docs"],
    "data science": ["Kaggle Learn", "Pandas Docs", "StatQuest", "DataCamp Free Tracks"],
    "cloud": ["AWS Skill Builder", "Microsoft Learn", "Google Cloud Skills Boost", "Cloud Resume Challenge"],
    "devops": ["Docker Docs", "Kubernetes Basics", "GitHub Actions Docs", "Roadmap.sh DevOps"],
}

SYSTEM_PROMPT = (
    "Você é o DevVerse AI, um tutor de programação dentro de um servidor Discord. "
    "Responda em português por padrão. Seja claro, direto e didático. Ajude com programação, lógica, "
    "desenvolvimento web, backend, frontend, banco de dados, Linux, Git, cloud, IA e cybersecurity defensiva. "
    "Quando o usuário pedir ajuda com código, explique o problema, mostre uma correção e ensine o conceito. "
    "Para cybersecurity, responda apenas de forma ética, educativa e defensiva. Não ajude com invasão real, "
    "roubo de credenciais, malware, phishing, exploração de sistemas reais ou bypass de segurança."
)
