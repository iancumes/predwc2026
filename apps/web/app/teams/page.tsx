"use client";
import { useEffect, useMemo, useState } from "react";
import { api, TeamProb, pct } from "../lib/api";
import { Loading, ErrorState, ConfChip, Flag, Bar } from "../components/ui";
import { useTeamPeek } from "../components/TeamModal";

const SELECT =
  "rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-sm text-slate-200 outline-none focus:border-brand/50";

export default function TeamsPage() {
  const [teams, setTeams] = useState<TeamProb[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [conf, setConf] = useState("");
  const [q, setQ] = useState("");
  const { open } = useTeamPeek();

  useEffect(() => {
    api.teams().then((d) => setTeams(d.teams)).catch((e) => setErr(String(e)));
  }, []);

  const confs = useMemo(
    () => Array.from(new Set((teams || []).map((t) => t.confederation))).sort(),
    [teams]
  );
  const filtered = (teams || []).filter(
    (t) =>
      (!conf || t.confederation === conf) &&
      (!q || t.team.toLowerCase().includes(q.toLowerCase()))
  );

  if (err) return <ErrorState error={err} />;
  if (!teams) return <Loading />;

  return (
    <div>
      <div className="mb-5 animate-fade-up">
        <div className="eyebrow mb-1">All 48 nations</div>
        <h1 className="text-3xl font-extrabold">Teams</h1>
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search team…"
          className={`${SELECT} w-44 placeholder:text-slate-500`}
        />
        <select value={conf} onChange={(e) => setConf(e.target.value)} className={SELECT}>
          <option value="">All confederations</option>
          {confs.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
        <span className="self-center text-sm text-slate-500">{filtered.length} teams</span>
      </div>

      <div className="stagger grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {filtered.map((t, i) => (
          <button
            key={t.code}
            onClick={() => open(t.code)}
            style={{ ["--i" as any]: Math.min(i, 16) }}
            className="card card-hover p-4 text-left"
          >
            <div className="mb-3 flex items-center justify-between">
              <div className="flex min-w-0 items-center gap-2.5">
                <Flag code={t.code} name={t.team} className="h-7 w-10" w={80} />
                <span className="truncate font-semibold">{t.team}</span>
              </div>
              <ConfChip conf={t.confederation} />
            </div>
            <div className="mb-1 flex items-end justify-between">
              <span className="text-xs text-slate-400">Group {t.group}</span>
              <span className="text-lg font-bold gradient-text tnum">{pct(t.p_champion)}</span>
            </div>
            <Bar value={t.p_champion} />
            <div className="mt-2 flex justify-between text-xs text-slate-400">
              <span>Win group {pct(t.p_win_group, 0)}</span>
              <span>Reach final {pct(t.p_reach_final, 0)}</span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
