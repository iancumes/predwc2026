"use client";
import { useEffect, useState } from "react";
import { api, pct } from "../lib/api";
import { Loading, ErrorState, TeamLink } from "../components/ui";

const COLS: [string, string][] = [
  ["p_reach_r32", "R32"],
  ["p_reach_r16", "R16"],
  ["p_reach_qf", "QF"],
  ["p_reach_sf", "SF"],
  ["p_reach_final", "Final"],
  ["p_champion", "Win"],
];

export default function BracketPage() {
  const [data, setData] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.bracket().then(setData).catch((e) => setErr(String(e)));
  }, []);

  if (err) return <ErrorState error={err} />;
  if (!data) return <Loading />;

  const rows = [...data.round_reach]
    .filter((r: any) => r.p_champion !== null && r.p_champion !== undefined)
    .sort((a: any, b: any) => b.p_champion - a.p_champion);

  return (
    <div>
      <h1 className="mb-1 text-2xl font-bold">Road to the final</h1>
      <p className="mb-5 text-sm text-slate-500">
        Probability of each team reaching each knockout round (Monte Carlo over
        the official 2026 bracket, including the best-eight third-placed rule).
      </p>

      <div className="card overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-[11px] uppercase text-slate-400">
            <tr>
              <th className="px-3 py-2 text-left font-medium">Team</th>
              <th className="px-2 py-2 text-center font-medium">Grp</th>
              {COLS.map(([, l]) => (
                <th key={l} className="px-2 py-2 text-center font-medium">{l}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {rows.map((r: any) => (
              <tr key={r.code} className="hover:bg-slate-50">
                <td className="px-3 py-1.5"><TeamLink code={r.code} name={r.team} /></td>
                <td className="px-2 text-center text-xs text-slate-500">{r.group}</td>
                {COLS.map(([k, l]) => (
                  <td key={l} className="px-2 py-1.5 text-center tabular-nums">
                    <span
                      className="inline-block rounded px-1.5 py-0.5 text-xs"
                      style={{ backgroundColor: heat(r[k]) }}
                    >
                      {pct(r[k], 0)}
                    </span>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <details className="card mt-6 p-4">
        <summary className="cursor-pointer font-semibold">Official bracket structure (slots)</summary>
        <div className="mt-3 grid gap-4 text-sm md:grid-cols-2">
          {Object.entries(data.rounds).map(([round, matches]: any) => (
            <div key={round}>
              <div className="mb-1 font-medium text-slate-600">{round}</div>
              <ul className="space-y-0.5 text-xs text-slate-500">
                {matches.map((m: any) => (
                  <li key={m.match} className="font-mono">
                    #{m.match}: {m.slot1} vs {m.slot2}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </details>
    </div>
  );
}

function heat(v: number): string {
  if (v === null || v === undefined) return "transparent";
  const a = Math.min(v * 0.9 + 0.05, 0.95);
  return `rgba(22,163,74,${a})`;
}
