"use client";
import { useEffect, useState } from "react";
import { api, pct } from "../../lib/api";
import { Loading, ErrorState, ConfChip, Flag, Bar } from "../../components/ui";

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
      {/* Hero header */}
      <div className="mb-6 flex items-center gap-4 animate-fade-up">
        <Flag code={data.code} name={data.name} className="h-14 w-20" w={160} />
        <div>
          <h1 className="text-3xl font-extrabold">{data.name}</h1>
          <div className="mt-1.5 flex items-center gap-2 text-sm text-slate-400">
            <ConfChip conf={data.confederation} />
            <span>Group {data.group}</span>
            {data.is_host && (
              <span className="chip bg-gold/20 text-gold">Host</span>
            )}
            <span className="rounded-full bg-white/5 px-2 py-0.5 text-xs">
              Champion {pct(s.p_champion)}
            </span>
          </div>
        </div>
      </div>

      <div className="grid gap-5 md:grid-cols-2">
        <div className="card p-5 animate-fade-up">
          <h3 className="mb-4 font-semibold">Tournament probabilities</h3>
          <div className="space-y-3">
            {ROUNDS.map(([k, l], i) => (
              <div key={k} style={{ ["--i" as any]: i }} className="animate-fade-up">
                <div className="mb-1 flex justify-between text-sm">
                  <span className="text-slate-300">{l}</span>
                  <span className="font-semibold tnum">{pct(s[k])}</span>
                </div>
                <Bar value={s[k] || 0} />
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-5">
          <div className="card p-5 animate-fade-up">
            <h3 className="mb-3 font-semibold">Group fixtures</h3>
            <ul className="space-y-1.5 text-sm">
              {data.group_fixtures?.map((m: any) => (
                <li
                  key={m.match_id}
                  className="flex items-center justify-between rounded-lg px-2 py-1 hover:bg-white/5"
                >
                  <span className={m.home === data.name || m.away === data.name ? "font-medium" : "text-slate-400"}>
                    {m.home} <span className="text-slate-600">v</span> {m.away}
                  </span>
                  <span className="tnum text-xs text-slate-400">
                    {m.status === "played" ? (
                      <span className="rounded bg-white/10 px-1.5 py-0.5 font-semibold">
                        {m.home_score}–{m.away_score}
                      </span>
                    ) : (
                      m.date.slice(5)
                    )}
                  </span>
                </li>
              ))}
            </ul>
          </div>

          <div className="card p-5 animate-fade-up">
            <h3 className="mb-3 font-semibold">Recent results</h3>
            <ul className="space-y-1 text-sm">
              {data.recent_matches?.map((m: any, i: number) => (
                <li key={i} className="flex justify-between gap-2">
                  <span className="truncate text-slate-300">
                    {m.home} <span className="font-semibold text-white">{m.score}</span> {m.away}
                  </span>
                  <span className="ml-2 shrink-0 text-xs text-slate-500">{m.date}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
