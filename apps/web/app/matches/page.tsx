"use client";
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { api, MatchRow } from "../lib/api";
import { Loading, ErrorState, ProbSplit, Flag } from "../components/ui";

const GROUPS = "ABCDEFGHIJKL".split("");
const SELECT =
  "rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-sm text-slate-200 outline-none focus:border-brand/50";

export default function MatchesPage() {
  const [matches, setMatches] = useState<MatchRow[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [group, setGroup] = useState("");
  const [status, setStatus] = useState("");

  useEffect(() => {
    api.matches().then((d) => setMatches(d.matches)).catch((e) => setErr(String(e)));
  }, []);

  const filtered = useMemo(() => {
    if (!matches) return [];
    return matches.filter(
      (m) => (!group || m.group === group) && (!status || m.status === status)
    );
  }, [matches, group, status]);

  if (err) return <ErrorState error={err} />;
  if (!matches) return <Loading />;

  return (
    <div>
      <div className="mb-5 animate-fade-up">
        <div className="eyebrow mb-1">Every fixture</div>
        <h1 className="text-3xl font-extrabold">Matches</h1>
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <select value={group} onChange={(e) => setGroup(e.target.value)} className={SELECT}>
          <option value="">All groups</option>
          {GROUPS.map((g) => (
            <option key={g} value={g}>
              Group {g}
            </option>
          ))}
        </select>
        <select value={status} onChange={(e) => setStatus(e.target.value)} className={SELECT}>
          <option value="">All statuses</option>
          <option value="played">Played</option>
          <option value="scheduled">Upcoming</option>
        </select>
        <span className="self-center text-sm text-slate-500">{filtered.length} matches</span>
      </div>

      <div className="card divide-y divide-white/5 overflow-hidden">
        {filtered.map((m, i) => (
          <Link
            key={m.match_id}
            href={`/matches/${m.match_id}`}
            style={{ ["--i" as any]: Math.min(i, 12) }}
            className="flex flex-wrap items-center gap-3 px-4 py-3 transition-colors hover:bg-white/5"
          >
            <span className="w-20 text-xs text-slate-500">{m.date}</span>
            <span className="grid h-6 w-6 place-items-center rounded-md bg-white/5 text-xs font-semibold text-slate-400">
              {m.group}
            </span>
            <div className="flex w-64 items-center gap-2 font-medium">
              <div className="flex min-w-0 flex-1 items-center justify-end gap-2">
                <span className="truncate text-right">{m.home}</span>
                <Flag code={m.home_code} name={m.home} className="h-4 w-6 shrink-0" />
              </div>
              {m.status === "played" ? (
                <span className="shrink-0 rounded-md bg-white/10 px-2 py-0.5 text-xs font-bold tnum">
                  {m.home_score}–{m.away_score}
                </span>
              ) : (
                <span className="shrink-0 text-[11px] font-bold text-slate-600">VS</span>
              )}
              <div className="flex min-w-0 flex-1 items-center gap-2">
                <Flag code={m.away_code} name={m.away} className="h-4 w-6 shrink-0" />
                <span className="truncate">{m.away}</span>
              </div>
            </div>
            <div className="min-w-[140px] flex-1">
              <ProbSplit h={m.p_home} d={m.p_draw} a={m.p_away} />
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
