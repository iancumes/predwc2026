"use client";
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { api, MatchRow, pct } from "../lib/api";
import { Loading, ErrorState, ProbSplit } from "../components/ui";

const GROUPS = "ABCDEFGHIJKL".split("");

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
      <h1 className="mb-4 text-2xl font-bold">Matches</h1>
      <div className="mb-4 flex flex-wrap gap-2">
        <select value={group} onChange={(e) => setGroup(e.target.value)} className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm">
          <option value="">All groups</option>
          {GROUPS.map((g) => <option key={g} value={g}>Group {g}</option>)}
        </select>
        <select value={status} onChange={(e) => setStatus(e.target.value)} className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm">
          <option value="">All statuses</option>
          <option value="played">Played</option>
          <option value="scheduled">Upcoming</option>
        </select>
        <span className="self-center text-sm text-slate-400">{filtered.length} matches</span>
      </div>

      <div className="card divide-y divide-slate-100">
        {filtered.map((m) => (
          <Link key={m.match_id} href={`/matches/${m.match_id}`} className="flex flex-wrap items-center gap-3 px-4 py-3 hover:bg-slate-50">
            <span className="w-20 text-xs text-slate-400">{m.date}</span>
            <span className="w-8 text-center text-xs font-semibold text-slate-500">{m.group}</span>
            <div className="flex w-56 items-center justify-between font-medium">
              <span className="truncate">{m.home}</span>
              {m.status === "played" ? (
                <span className="mx-2 rounded bg-slate-800 px-2 py-0.5 text-xs text-white tabular-nums">
                  {m.home_score}–{m.away_score}
                </span>
              ) : (
                <span className="mx-2 text-xs text-slate-300">vs</span>
              )}
              <span className="truncate text-right">{m.away}</span>
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
