"use client";
import { useEffect, useMemo, useState } from "react";
import { api, TeamProb, pct } from "../lib/api";
import { Loading, ErrorState, ConfChip, TeamLink, Bar } from "../components/ui";

export default function TeamsPage() {
  const [teams, setTeams] = useState<TeamProb[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [conf, setConf] = useState("");

  useEffect(() => {
    api.teams().then((d) => setTeams(d.teams)).catch((e) => setErr(String(e)));
  }, []);

  const confs = useMemo(
    () => Array.from(new Set((teams || []).map((t) => t.confederation))).sort(),
    [teams]
  );
  const filtered = (teams || []).filter((t) => !conf || t.confederation === conf);

  if (err) return <ErrorState error={err} />;
  if (!teams) return <Loading />;

  return (
    <div>
      <h1 className="mb-4 text-2xl font-bold">Teams</h1>
      <div className="mb-4 flex gap-2">
        <select value={conf} onChange={(e) => setConf(e.target.value)} className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm">
          <option value="">All confederations</option>
          {confs.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <span className="self-center text-sm text-slate-400">{filtered.length} teams</span>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {filtered.map((t) => (
          <div key={t.code} className="card p-4">
            <div className="mb-2 flex items-center justify-between">
              <TeamLink code={t.code} name={t.team} />
              <ConfChip conf={t.confederation} />
            </div>
            <div className="mb-1 flex justify-between text-xs text-slate-400">
              <span>Group {t.group}</span>
              <span>Champion {pct(t.p_champion)}</span>
            </div>
            <Bar value={t.p_champion} />
            <div className="mt-2 flex justify-between text-xs text-slate-500">
              <span>Win group {pct(t.p_win_group, 0)}</span>
              <span>Reach final {pct(t.p_reach_final, 0)}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
