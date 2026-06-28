"use client";
import { useEffect, useState } from "react";
import { api, pct, ScorerProb } from "../../lib/api";
import { Loading, ErrorState, Flag } from "../../components/ui";
import { useTeamPeek } from "../../components/TeamModal";
import { teamSlug } from "../../lib/flags";

export default function MatchClient({ id }: { id: string }) {
  const [data, setData] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);
  const { open } = useTeamPeek();

  useEffect(() => {
    api.match(id).then(setData).catch((e) => setErr(String(e)));
  }, [id]);

  if (err) return <ErrorState error={err} />;
  if (!data) return <Loading />;
  const p = data.prediction;
  const homeCode = data.home_code || teamSlug(data.home);
  const awayCode = data.away_code || teamSlug(data.away);

  return (
    <div>
      {/* Scoreboard header */}
      <div className="relative mb-6 overflow-hidden rounded-3xl border border-white/10 bg-base-800/40 p-6 shadow-card animate-fade-up">
        <div className="pointer-events-none absolute -top-16 left-1/2 h-40 w-40 -translate-x-1/2 rounded-full bg-brand/15 blur-3xl" />
        <div className="relative">
          <div className="mb-4 text-center text-xs text-slate-400">
            Group {data.group} · {data.date} · {data.neutral ? "neutral venue" : data.country}
          </div>
          <div className="flex items-center justify-center gap-4 sm:gap-8">
            <button onClick={() => open(homeCode)} className="flex flex-1 flex-col items-center gap-2 transition hover:text-brand">
              <Flag code={homeCode} name={data.home} className="h-12 w-16" w={160} />
              <span className="text-center text-sm font-semibold sm:text-lg">{data.home}</span>
            </button>
            <div className="shrink-0 text-center">
              {data.status === "played" ? (
                <div className="rounded-xl bg-white/10 px-4 py-2 text-3xl font-extrabold tnum">
                  {data.home_score}<span className="mx-1 text-slate-500">–</span>{data.away_score}
                </div>
              ) : (
                <div className="text-2xl font-bold text-slate-500">VS</div>
              )}
            </div>
            <button onClick={() => open(awayCode)} className="flex flex-1 flex-col items-center gap-2 transition hover:text-brand">
              <Flag code={awayCode} name={data.away} className="h-12 w-16" w={160} />
              <span className="text-center text-sm font-semibold sm:text-lg">{data.away}</span>
            </button>
          </div>
        </div>
      </div>

      {!p ? (
        <div className="card p-5 text-sm text-slate-400">No frozen prediction available for this match.</div>
      ) : (
        <div className="stagger grid gap-5 md:grid-cols-2">
          {/* 1X2 + headline goal numbers */}
          <div className="card p-5">
            <h3 className="mb-3 font-semibold">Match outcome (1X2)</h3>
            <Outcome label={`${data.home} win`} v={p.home_win_probability} color="bg-brand" />
            <Outcome label="Draw" v={p.draw_probability} color="bg-white/30" />
            <Outcome label={`${data.away} win`} v={p.away_win_probability} color="bg-electric" />
            <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
              <Box label="Expected goals" value={`${p.expected_home_goals.toFixed(2)} – ${p.expected_away_goals.toFixed(2)}`} />
              <Box label="Expected total" value={(p.expected_total_goals ?? p.expected_home_goals + p.expected_away_goals).toFixed(2)} />
              <Box label="Most likely score" value={p.most_likely_score ?? p.top_scorelines?.[0]?.score ?? "—"} />
              <Box label="Model" value={String(p.model_version_id).split("-")[0]} />
            </div>
          </div>

          {/* Most likely scorelines */}
          <div className="card p-5">
            <h3 className="mb-3 font-semibold">Most likely scorelines</h3>
            <ul className="space-y-1.5 text-sm">
              {p.top_scorelines.map((s: any) => (
                <li key={s.score} className="flex items-center gap-2">
                  <span className="w-12 font-mono text-slate-300">{s.score}</span>
                  <div className="h-2 flex-1 overflow-hidden rounded-full bg-white/10">
                    <div className="h-2 rounded-full bg-brand-gradient" style={{ width: `${Math.min(s.prob * 100 * 4, 100)}%` }} />
                  </div>
                  <span className="w-12 text-right tnum">{pct(s.prob)}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Goal markets */}
          <div className="card p-5">
            <h3 className="mb-3 font-semibold">Goals</h3>
            <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
              {p.over_under
                ? Object.entries(p.over_under).map(([line, prob]) => (
                    <Line key={line} label={`Over ${line}`} v={prob as number} />
                  ))
                : <Line label="Over 2.5" v={p.over_2_5} />}
            </div>
            <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
              <Box label="Both teams score" value={pct(p.btts_yes)} />
              <Box label="No (BTTS)" value={pct(p.btts_no ?? 1 - p.btts_yes)} />
              {p.home_clean_sheet !== undefined && <Box label={`${data.home} clean sheet`} value={pct(p.home_clean_sheet)} />}
              {p.away_clean_sheet !== undefined && <Box label={`${data.away} clean sheet`} value={pct(p.away_clean_sheet)} />}
            </div>
          </div>

          {/* Total goals distribution */}
          {Array.isArray(p.total_goals_dist) && (
            <div className="card p-5">
              <h3 className="mb-3 font-semibold">Total goals in the match</h3>
              <TotalGoals dist={p.total_goals_dist} />
            </div>
          )}

          {/* Anytime goalscorers */}
          {Array.isArray(p.scorers) && p.scorers.length > 0 && (
            <div className="card p-5 md:col-span-2">
              <h3 className="mb-1 font-semibold">Anytime goalscorer</h3>
              <p className="mb-3 text-xs text-slate-500">
                Probability each player scores at least once — from recent scoring
                rate × the team’s expected goals. Estimates, not guarantees.
              </p>
              <div className="grid gap-x-8 gap-y-1 sm:grid-cols-2">
                <ScorerColumn team={data.home} scorers={p.scorers.filter((s: ScorerProb) => s.team === data.home)} />
                <ScorerColumn team={data.away} scorers={p.scorers.filter((s: ScorerProb) => s.team === data.away)} />
              </div>
            </div>
          )}

          {/* Factors */}
          <div className="card p-5 md:col-span-2">
            <h3 className="mb-1 font-semibold">Why these numbers</h3>
            <p className="mb-3 text-xs text-slate-500">
              Statistical factors from the model — associations, not causal claims.
            </p>
            <div className="flex flex-wrap gap-2 text-sm">
              {Object.entries(p.factors).map(([k, v]) => (
                <span key={k} className="rounded-lg border border-white/10 bg-white/5 px-3 py-1">
                  <span className="text-slate-400">{k.replace(/_/g, " ")}:</span>{" "}
                  <span className="font-medium">{String(v)}</span>
                </span>
              ))}
            </div>
            <p className="mt-4 text-xs text-slate-500">
              Frozen {p.is_frozen ? "✓" : "✗"} · data cutoff {p.data_cutoff} · created {p.created_at?.slice(0, 10)}.
              Probabilities are estimates with uncertainty, not guarantees.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

function Outcome({ label, v, color }: { label: string; v: number; color: string }) {
  return (
    <div className="mb-2.5">
      <div className="mb-1 flex justify-between text-sm">
        <span className="text-slate-300">{label}</span>
        <span className="font-semibold tnum">{pct(v)}</span>
      </div>
      <div className="h-2.5 w-full overflow-hidden rounded-full bg-white/10">
        <div className={`h-2.5 origin-left rounded-full animate-bar-grow ${color}`} style={{ width: `${v * 100}%` }} />
      </div>
    </div>
  );
}

function Line({ label, v }: { label: string; v: number }) {
  return (
    <div className="flex items-center justify-between border-b border-white/5 py-1">
      <span className="text-slate-400">{label}</span>
      <span className="font-semibold tnum">{pct(v)}</span>
    </div>
  );
}

function Box({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.03] p-2.5">
      <div className="text-[11px] uppercase tracking-wide text-slate-400">{label}</div>
      <div className="mt-0.5 font-semibold">{value}</div>
    </div>
  );
}

function TotalGoals({ dist }: { dist: number[] }) {
  const max = Math.max(...dist, 0.01);
  return (
    <div className="flex items-end gap-1.5">
      {dist.map((v, i) => (
        <div key={i} className="flex flex-1 flex-col items-center justify-end">
          <span className="mb-1 text-[10px] tnum text-slate-400">{pct(v, 0)}</span>
          <div className="w-full rounded-t bg-brand-gradient" style={{ height: `${Math.max((v / max) * 96, 2)}px` }} title={`${i} goals: ${pct(v)}`} />
          <span className="mt-1 text-[11px] text-slate-500">{i === dist.length - 1 ? `${i}+` : i}</span>
        </div>
      ))}
    </div>
  );
}

function ScorerColumn({ team, scorers }: { team: string; scorers: ScorerProb[] }) {
  if (!scorers.length)
    return (
      <div>
        <div className="mb-1 text-sm font-semibold">{team}</div>
        <div className="text-xs text-slate-500">No recent scorer data.</div>
      </div>
    );
  return (
    <div>
      <div className="mb-1 text-sm font-semibold">{team}</div>
      <ul className="space-y-1 text-sm">
        {scorers.slice(0, 8).map((s) => (
          <li key={s.player} className="flex items-center gap-2">
            <span className="flex-1 truncate text-slate-300">{s.player}</span>
            <div className="h-1.5 w-20 overflow-hidden rounded-full bg-white/10">
              <div className="h-1.5 rounded-full bg-electric" style={{ width: `${Math.min(s.prob * 100 * 2.2, 100)}%` }} />
            </div>
            <span className="w-10 text-right tnum text-slate-400">{pct(s.prob, 0)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
