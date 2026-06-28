"use client";
import { useEffect, useState } from "react";
import { api, Standing, pct } from "../lib/api";
import { Loading, ErrorState, TeamButton, Bar } from "../components/ui";
import { teamSlug } from "../lib/flags";

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
      <div className="mb-5 animate-fade-up">
        <div className="eyebrow mb-1">Group stage</div>
        <h1 className="text-3xl font-extrabold">Groups</h1>
        <p className="mt-2 max-w-2xl text-sm text-slate-400">
          Real standings from finished matches. <b className="text-slate-200">Advance %</b> is the
          simulated probability of reaching the Round of 32 (top two, or one of
          the eight best third-placed teams). Tap a team to peek at its form.
        </p>
      </div>

      <div className="stagger grid gap-5 md:grid-cols-2">
        {Object.entries(groups).map(([g, rows], gi) => (
          <div key={g} className="card overflow-hidden" style={{ ["--i" as any]: gi }}>
            <div className="flex items-center justify-between border-b border-white/10 bg-white/[0.03] px-4 py-2.5">
              <span className="font-bold">Group {g}</span>
              <span className="text-xs text-slate-500">{rows[0]?.played ?? 0} played</span>
            </div>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-[11px] uppercase text-slate-500">
                  <th className="px-3 py-1.5 text-left font-medium">Team</th>
                  <th className="px-1 py-1.5 text-center font-medium">P</th>
                  <th className="px-1 py-1.5 text-center font-medium">GD</th>
                  <th className="px-1 py-1.5 text-center font-medium">Pts</th>
                  <th className="px-3 py-1.5 text-right font-medium">Advance</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {rows.map((r) => (
                  <tr
                    key={r.team}
                    className={`transition-colors hover:bg-white/5 ${
                      r.position <= 2 ? "bg-brand/[0.06]" : ""
                    }`}
                  >
                    <td className="px-3 py-1.5">
                      <div className="flex items-center gap-2">
                        <span
                          className={`grid h-5 w-5 shrink-0 place-items-center rounded text-[11px] font-bold ${
                            r.position === 1
                              ? "bg-gold/20 text-gold"
                              : r.position === 2
                              ? "bg-white/15 text-slate-200"
                              : "text-slate-500"
                          }`}
                        >
                          {r.position}
                        </span>
                        <TeamButton code={teamSlug(r.team)} name={r.team} bold={false} />
                      </div>
                    </td>
                    <td className="px-1 text-center tnum">{r.played}</td>
                    <td className="px-1 text-center tnum">{r.gd > 0 ? `+${r.gd}` : r.gd}</td>
                    <td className="px-1 text-center font-bold tnum">{r.points}</td>
                    <td className="px-3 py-1.5">
                      <div className="flex items-center justify-end gap-2">
                        <div className="hidden w-16 sm:block">
                          <Bar value={r.p_advance ?? 0} />
                        </div>
                        <span className="w-10 text-right text-xs tnum">{pct(r.p_advance, 0)}</span>
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
