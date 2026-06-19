"use client";
import { useEffect, useState } from "react";
import { api, Standing, pct } from "../lib/api";
import { Loading, ErrorState, TeamLink, Bar } from "../components/ui";

export default function GroupsPage() {
  const [groups, setGroups] = useState<Record<string, Standing[]> | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.groups().then((d) => setGroups(d.groups)).catch((e) => setErr(String(e)));
  }, []);

  if (err) return <ErrorState error={err} />;
  if (!groups) return <Loading />;

  return (
    <div>
      <h1 className="mb-1 text-2xl font-bold">Groups</h1>
      <p className="mb-5 text-sm text-slate-500">
        Real standings from finished matches. <b>Advance %</b> is the simulated
        probability of reaching the round of 32 (top two, or one of the eight
        best third-placed teams).
      </p>
      <div className="grid gap-5 md:grid-cols-2">
        {Object.entries(groups).map(([g, rows]) => (
          <div key={g} className="card overflow-hidden">
            <div className="border-b border-slate-100 bg-slate-50 px-4 py-2 font-semibold">
              Group {g}
            </div>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-[11px] uppercase text-slate-400">
                  <th className="px-3 py-1.5 text-left font-medium">Team</th>
                  <th className="px-1 py-1.5 text-center font-medium">P</th>
                  <th className="px-1 py-1.5 text-center font-medium">GD</th>
                  <th className="px-1 py-1.5 text-center font-medium">Pts</th>
                  <th className="px-3 py-1.5 text-right font-medium">Advance</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {rows.map((r) => (
                  <tr key={r.team} className={r.position <= 2 ? "bg-accent/5" : ""}>
                    <td className="px-3 py-1.5">
                      <span className="mr-2 text-xs text-slate-400">{r.position}</span>
                      <TeamLink code={r.team.toLowerCase().replace(/[^a-z]+/g, "-")} name={r.team} />
                    </td>
                    <td className="px-1 text-center tabular-nums">{r.played}</td>
                    <td className="px-1 text-center tabular-nums">{r.gd > 0 ? `+${r.gd}` : r.gd}</td>
                    <td className="px-1 text-center font-semibold tabular-nums">{r.points}</td>
                    <td className="px-3 py-1.5">
                      <div className="flex items-center justify-end gap-2">
                        <div className="w-16">
                          <Bar value={r.p_advance ?? 0} />
                        </div>
                        <span className="w-10 text-right text-xs tabular-nums">
                          {pct(r.p_advance, 0)}
                        </span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
      </div>
    </div>
  );
}
