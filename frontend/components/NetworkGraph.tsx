"use client";

type Node = { id: string; label: string; group: string };
type Link = { source: string; target: string; weight: number };

export default function NetworkGraph({
  nodes,
  links,
  width = 900,
  height = 560,
}: {
  nodes: Node[];
  links: Link[];
  width?: number;
  height?: number;
}) {
  const plants = nodes.filter((n) => n.group === "planta");
  const poll = nodes.filter((n) => n.group === "polinizador");
  const yFor = (i: number, n: number) => ((i + 0.5) / Math.max(1, n)) * height;
  const pos = new Map<string, { x: number; y: number }>();
  plants.forEach((p, i) => pos.set(p.id, { x: 90, y: yFor(i, plants.length) }));
  poll.forEach((q, i) => pos.set(q.id, { x: width - 90, y: yFor(i, poll.length) }));
  const maxW = Math.max(1, ...links.map((l) => l.weight));

  return (
    <svg viewBox={`0 0 ${width} ${height}`} style={{ width: "100%", height: "auto" }}>
      {links.map((l, i) => {
        const a = pos.get(l.source);
        const b = pos.get(l.target);
        if (!a || !b) return null;
        return (
          <line
            key={i}
            x1={a.x}
            y1={a.y}
            x2={b.x}
            y2={b.y}
            stroke="#38bdf8"
            strokeOpacity={0.12 + 0.4 * (l.weight / maxW)}
            strokeWidth={0.5 + 2.5 * (l.weight / maxW)}
          />
        );
      })}
      {plants.map((p) => {
        const c = pos.get(p.id)!;
        return (
          <g key={p.id}>
            <circle cx={c.x} cy={c.y} r={5} fill="#22c55e" />
            <text x={c.x - 10} y={c.y + 4} textAnchor="end" fontSize={10} fill="#e2e8f0">
              {p.label}
            </text>
          </g>
        );
      })}
      {poll.map((q) => {
        const c = pos.get(q.id)!;
        return (
          <g key={q.id}>
            <circle cx={c.x} cy={c.y} r={4.5} fill="#f59e0b" />
            <text x={c.x + 10} y={c.y + 4} fontSize={10} fill="#e2e8f0">
              {q.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
