"use client";

import Image from "next/image";
import { useEffect, useMemo, useState } from "react";
import { activity, leaderboard, stats, tasks, user } from "@/lib/mock-data";
import { DevVerseOrb } from "./DevVerseOrb";

type ServerStats = {
  users: number;
  total_xp: number;
  tasks: {
    total: number;
    completed: number;
  };
  ai_logs: number;
  completed_focus_minutes: number;
  checkins: number;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

function ProgressBar({ value }: { value: number }) {
  return (
    <div className="progress-track">
      <div className="progress-fill" style={{ width: `${value}%` }} />
    </div>
  );
}

export function DashboardShell() {
  const [serverStats, setServerStats] = useState<ServerStats | null>(null);
  const [apiOnline, setApiOnline] = useState(false);
  const xpPercent = Math.round((user.xp / user.nextLevelXp) * 100);
  const visibleStats = useMemo(() => {
    if (!serverStats) {
      return stats;
    }

    return [
      { label: "XP total", value: serverStats.total_xp.toLocaleString("pt-BR"), trend: "SQLite" },
      { label: "Tarefas", value: String(serverStats.tasks.total), trend: `${serverStats.tasks.completed} feitas` },
      { label: "Sessões IA", value: String(serverStats.ai_logs), trend: "API" },
      { label: "Check-ins", value: String(serverStats.checkins), trend: "Bot" }
    ];
  }, [serverStats]);

  useEffect(() => {
    let active = true;

    async function loadStats() {
      try {
        const response = await fetch(`${API_BASE_URL}/stats/server`, { cache: "no-store" });
        if (!response.ok) {
          throw new Error("API offline");
        }
        const data = (await response.json()) as ServerStats;
        if (active) {
          setServerStats(data);
          setApiOnline(true);
        }
      } catch {
        if (active) {
          setApiOnline(false);
        }
      }
    }

    loadStats();

    return () => {
      active = false;
    };
  }, []);

  return (
    <main className="dashboard">
      <aside className="sidebar">
        <div className="brand">
          <Image src="/devverse-logo.png" alt="DevVerse" width={48} height={48} priority />
          <div>
            <strong>DevVerse</strong>
            <span>System</span>
          </div>
        </div>

        <nav className="nav-list" aria-label="Principal">
          {["Visão geral", "Perfil", "Leaderboard", "Tarefas", "Estatísticas"].map((item, index) => (
            <a className={index === 0 ? "active" : ""} href={`#${item.toLowerCase().replace("í", "i")}`} key={item}>
              {item}
            </a>
          ))}
        </nav>

        <div className="sidebar-note">
          <span>Banco compartilhado</span>
          <strong>SQLite ativo</strong>
        </div>
      </aside>

      <section className="content">
        <header className="topbar">
          <div>
            <p className="eyebrow">Ecossistema de estudos com IA</p>
            <h1>DevVerse System</h1>
          </div>
          <button className={apiOnline ? "sync-button" : "sync-button offline"} type="button">
            {apiOnline ? "API online" : "Modo demo"}
          </button>
        </header>

        <section className="hero-grid">
          <div className="hero-copy">
            <p className="status-pill">Bot + API + Dashboard</p>
            <h2>Uma central bonita para acompanhar XP, streak, tarefas e aprendizado.</h2>
            <p>
              A UI já nasce preparada para consumir o backend FastAPI e refletir os dados que o bot grava no SQLite.
            </p>
            <div className="hero-actions">
              <a href="#perfil">Abrir perfil</a>
              <a href="#leaderboard">Ver ranking</a>
            </div>
          </div>
          <DevVerseOrb />
        </section>

        <section className="stats-grid" id="estatisticas">
          {visibleStats.map((item) => (
            <article className="metric-card" key={item.label}>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
              <em>{item.trend}</em>
            </article>
          ))}
        </section>

        <section className="main-grid">
          <article className="panel profile-panel" id="perfil">
            <div className="panel-heading">
              <div>
                <span>Perfil</span>
                <h3>{user.name}</h3>
              </div>
              <div className="avatar">{user.avatar}</div>
            </div>
            <div className="profile-meta">
              <span>{user.handle}</span>
              <span>{user.area}</span>
              <span>{user.streak} dias</span>
            </div>
            <div className="xp-row">
              <strong>Level {user.level}</strong>
              <span>{user.xp.toLocaleString("pt-BR")} XP</span>
            </div>
            <ProgressBar value={xpPercent} />
            <div className="language-list">
              {user.languages.map((language) => (
                <span key={language}>{language}</span>
              ))}
            </div>
          </article>

          <article className="panel leaderboard-panel" id="leaderboard">
            <div className="panel-heading">
              <div>
                <span>Leaderboard</span>
                <h3>Top usuários por XP</h3>
              </div>
            </div>
            <div className="table-list">
              {leaderboard.map((member) => (
                <div className="table-row" key={member.rank}>
                  <span>#{member.rank}</span>
                  <strong>{member.name}</strong>
                  <small>{member.area}</small>
                  <em>{member.xp.toLocaleString("pt-BR")} XP</em>
                </div>
              ))}
            </div>
          </article>

          <article className="panel tasks-panel" id="tarefas">
            <div className="panel-heading">
              <div>
                <span>Tarefas</span>
                <h3>Próximas entregas</h3>
              </div>
            </div>
            <div className="task-list">
              {tasks.map((task) => (
                <div className="task-item" key={task.title}>
                  <div>
                    <strong>{task.title}</strong>
                    <span>{task.status} · {task.due}</span>
                  </div>
                  <ProgressBar value={task.progress} />
                </div>
              ))}
            </div>
          </article>

          <article className="panel activity-panel">
            <div className="panel-heading">
              <div>
                <span>Atividade</span>
                <h3>Últimos eventos</h3>
              </div>
            </div>
            <div className="activity-list">
              {activity.map((item) => (
                <div className="activity-item" key={item}>
                  <span />
                  <p>{item}</p>
                </div>
              ))}
            </div>
          </article>
        </section>
      </section>
    </main>
  );
}
