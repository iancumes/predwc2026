"use client";
import { useEffect, useState } from "react";
import { api, pct } from "../../lib/api";
import { Loading, ErrorState, ConfChip } from "../../components/ui";

const ROUNDS: [string, string][] = [
  ["p_win_group", "Win group"],
  ["p_runner_up", "Runner-up"],
  ["p_qualify_third", "Qualify (3rd)"],
  ["p_reach_r16", "Reach R16"],
  ["p_reach_qf", "Reach QF"],
  ["p_reach_sf", "Reach SF"],
  ["p_reach_final", "Reach final"],
  ["p_champion", "Champion"],
];

export default function TeamClient({ code }: { code: string }) {
  const [data, setData] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.team(code).then(setData).catch((e) => setErr(String(e)));
  }, [code]);

  if (err) return <ErrorState error={err} />;
  if (!data) return <Loading />;
  const s = data.simulation || {};

  return (
    <div>
      <div className="mb-4 flex items-center gap-3">
        <h1 className="text-2xl font-bold">{data.name}</h1>
        <ConfChip conf={data.confederation} />
        <span className="text-sm text-slate-400">Group {data.group}</span>
        {data.is_host && <span className="chip bg-accent-soft text-pitch">Host</span>}
      </div>

      <div className="grid gap-5 md:grid-cols-2">
        <div className="card p-5">
          <h3 className="mb-3 font-semibold">Tournament probabilities</h3>
          <div className="space-y-2">
            {ROUNDS.map(([k, l]) => (
              <div key={k}>
                <div className="flex justify-between text-sm">
                  <span>{l}</span>
                  <span className="font-semibold tabular-nums">{pct(s[k])}</span>
                </div>
                <div className="h-2 rounded-full bg-slate-100">
                  <div className="h-2 rounded-full bg-accent" style={{ width: `${(s[k] || 0) * 100}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-5">
          <div className="card p-5">
            <h3 className="mb-3 font-semibold">Group fixtures</h3>
            <ul className="space-y-1.5 text-sm">
              {data.group_fixtures?.map((m: any) => (
                <li key={m.match_id} className="flex justify-between">
                  <span className={m.home === data.name || m.away === data.name ? "font-medium" : ""}>
                    {m.home} vs {m.away}
                  </span>
                  <span className="text-slate-400">
                    {m.status === "played" ? `${m.home_score}–${m.away_score}` : m.date.slice(5)}
                  </span>
                </li>
              ))}
            </ul>
          </div>

          <div className="card p-5">
            <h3 className="mb-3 font-semibold">Recent results</h3>
            <ul className="space-y-1 text-sm">
              {data.recent_matches?.map((m: any, i: number) => (
                <li key={i} className="flex justify-between">
                  <span className="truncate">{m.home} {m.score} {m.away}</span>
                  <span className="ml-2 shrink-0 text-xs text-slate-400">{m.date}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
