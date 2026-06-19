"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api, Health, MatchRow, TeamProb, pct } from "./lib/api";
import { Loading, ErrorState, Section, ConfChip, ProbSplit, TeamLink, Bar } from "./components/ui";

export default function Home() {
  const [health, setHealth] = useState<Health | null>(null);
  const [teams, setTeams] = useState<TeamProb[]>([]);
  const [matches, setMatches] = useState<MatchRow[]>([]);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.health(), api.probabilities(), api.matches("?status=scheduled")])
      .then(([h, p, m]) => {
        setHealth(h);
        setTeams(p.teams);
        setMatches(m.matches.slice(0, 8));
      })
      .catch((e) => setErr(String(e)));
  }, []);

  if (err) return <ErrorState error={err} />;
  if (!health) return <Loading label="Loading the latest model run…" />;

  return (
    <div>
      <div className="card mb-6 overflow-hidden">
        <div className="bg-pitch p-6 text-white">
          <h1 className="text-2xl font-bold">FIFA World Cup 2026 — Live Predictor</h1>
          <p className="mt-1 max-w-2xl text-sm text-white/80">
            Probabilities for every remaining match and the full tournament,
            re-simulated from the real group standings. Finished results are
            locked; only pending matches are forecast.
          </p>
          <p className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-white/15 px-2.5 py-0.5 text-xs text-white/90">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-accent-soft" />
            Auto-updates daily as new results come in
          </p>
        </div>
        <div className="grid grid-cols-2 gap-px bg-slate-200 text-center sm:grid-cols-4">
          <Stat label="Model" value={health.model?.replace("_", " ") || "—"} />
          <Stat label="Data cutoff" value={health.data_cutoff || "—"} />
          <Stat label="Simulations" value={health.n_sims ? health.n_sims.toLocaleString() : "—"} />
          <Stat
            label="Group matches"
            value={`${health.played_group_matches} played / ${health.pending_group_matches} left`}
          />
        </div>
      </div>

      <Section
        title="Title favourites"
        cta={<Link href="/bracket" className="text-sm text-accent hover:underline">Full bracket →</Link>}
      >
        <div className="card divide-y divide-slate-100">
          {teams.slice(0, 10).map((t, i) => (
            <div key={t.code} className="flex items-center gap-3 px-4 py-2.5">
              <span className="w-5 text-sm text-slate-400">{i + 1}</span>
              <span className="w-7 text-center text-xs font-semibold text-slate-500">{t.group}</span>
              <div className="w-40 shrink-0">
                <TeamLink code={t.code} name={t.team} />
              </div>
              <ConfChip conf={t.confederation} />
              <div className="flex-1">
                <Bar value={t.p_champion} />
              </div>
              <span className="w-14 text-right text-sm font-semibold tabular-nums">
                {pct(t.p_champion)}
              </span>
            </div>
          ))}
        </div>
      </Section>

      <Section
        title="Upcoming matches"
        cta={<Link href="/matches" className="text-sm text-accent hover:underline">All matches →</Link>}
      >
        {matches.length === 0 ? (
          <div className="card p-5 text-sm text-slate-500">No pending matches.</div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2">
            {matches.map((m) => (
              <Link key={m.match_id} href={`/matches/${m.match_id}`} className="card p-4 hover:border-accent">
                <div className="mb-1 flex justify-between text-xs text-slate-400">
                  <span>Group {m.group} · {m.date}</span>
                  <span>{m.neutral ? "neutral" : m.country}</span>
                </div>
                <div className="mb-2 flex items-center justify-between font-medium">
                  <span>{m.home}</span>
                  <span className="text-slate-300">vs</span>
                  <span>{m.away}</span>
                </div>
                <ProbSplit h={m.p_home} d={m.p_draw} a={m.p_away} />
              </Link>
            ))}
          </div>
        )}
      </Section>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white p-3">
      <div className="text-[11px] uppercase tracking-wide text-slate-400">{label}</div>
      <div className="mt-0.5 text-sm font-semibold capitalize">{value}</div>
    </div>
  );
}
