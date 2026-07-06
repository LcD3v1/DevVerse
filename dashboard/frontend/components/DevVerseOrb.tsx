const nodes = [
  { label: "Bot", className: "node bot" },
  { label: "API", className: "node api" },
  { label: "SQLite", className: "node db" },
  { label: "Dashboard", className: "node dash" }
];

export function DevVerseOrb() {
  return (
    <section className="orb-panel" aria-label="Arquitetura 3D do DevVerse">
      <div className="scene">
        <div className="grid-floor" />
        <div className="system-core">
          <div className="core-ring ring-one" />
          <div className="core-ring ring-two" />
          <div className="core-ring ring-three" />
          <div className="core-chip">
            <span>DV</span>
          </div>
          {nodes.map((node) => (
            <div className={node.className} key={node.label}>
              {node.label}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
