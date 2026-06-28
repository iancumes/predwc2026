"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api, Health, MatchRow, TeamProb, pct } from "./lib/api";
import {
  Loading,
  ErrorState,
  Section,
  ConfChip,
  ProbSplit,
  TeamButton,
  Flag,
  Bar,
} from "./components/ui";

const ROUND_LABEL: Record<string, string> = {
  R32: "Round of 32",
  R16: "Round of 16",
  QF: "Quarter-final",
  SF: "Semi-final",
  FINAL: "Final",
  THIRD_PLACE: "Third place",
};

type KnockoutTie = {
  match: number;
  round: string;
  team1: { name: string; code: string };
  team2: { name: string; code: string };
  date: string | null;
};

export default function Home() {
  const [health, setHealth] = useState<Health | null>(null);
  const [teams, setTeams] = useState<TeamProb[]>([]);
  const [matches, setMatches] = useState<MatchRow[]>([]);
  const [ koTies, setKoTies] = useState<KnockoutTie[]>([]);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      api.health(),
      api.probabilities(),
      api.matches("?status=scheduled"),
      api.bracket().catch(() => null),
    ])
      .then(([h, p, m, b]) => {
        setHealth(h);
        setTeams(p.teams);
        setMatches(m.matches.slice(0, 6));
        // Upcoming knockout ties (both teams known, not yet played) — keeps the
        // home page useful once the group stage is over.
        if (b?.resolved) {
          const ties = (Object.values(b.resolved) as any[])
            .filter((e) => e.status === "scheduled" && e.team1 && e.team2)
            .sort((a, b) => (a.date || "").localeCompare(b.date || "") || a.match - b.match)
            .slice(0, 6);
          setKoTies(ties);
        }
      })
      .catch((e) => setErr(String(e)));
  }, []);

  if (err) return <ErrorState error={err} />;
  if (!health) return <Loading label="Loading the latest model run…" />;

  const podium = teams.slice(0, 3);
  const rest = teams.slice(3, 12);

  return (
    <div>
      {/* ----------------------------------------------------------------- */}
      {/* HERO                                                              */}
      {/* ----------------------------------------------------------------- */}
      <div className="relative mb-12 overflow-hidden rounded-3xl border border-white/10 bg-base-800/40 p-6 shadow-card sm:p-10">
        {/* animated ambient blobs */}
        <div className="pointer-events-none absolute -right-20 -top-24 h-72 w-72 rounded-full bg-brand/20 blur-3xl animate-float" />
        <div className="pointer-events-none absolute -bottom-24 left-1/4 h-72 w-72 rounded-full bg-violet/20 blur-3xl animate-float [animation-delay:2s]" />
        <div className="pointer-events-none absolute inset-0 bg-grid-faint [background-size:38px_38px] opacity-40" />

        <div className="relative animate-fade-up">
          <span className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-3 py-1 text-xs font-medium text-slate-300">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-brand" />
            Live · auto-updates 08:00 &amp; 23:59 (Guatemala)
          </span>
          <h1 className="mt-4 max-w-3xl text-4xl font-extrabold leading-[1.05] sm:text-5xl">
            The FIFA World Cup 2026,
            <br />
            <span className="gradient-text">re-simulated every matchday.</span>
          </h1>
          <p className="mt-4 max-w-2xl text-sm text-slate-300 sm:text-base">
            Probabilities for every remaining match and the full 48-team
            tournament — driven by Elo, Poisson &amp; a calibrated ensemble over{" "}
            {health.n_sims ? health.n_sims.toLocaleString() : "tens of thousands of"}{" "}
            Monte-Carlo runs. Finished results are locked; only what&apos;s left is
            forecast.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link
              href="/bracket"
              className="rounded-xl bg-brand-gradient px-5 py-2.5 text-sm font-semibold text-base-900 shadow-glow transition hover:brightness-110"
            >
              Explore the bracket →
            </Link>
            <Link
              href="/matches"
              className="rounded-xl border border-white/15 bg-white/5 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-white/10"
            >
              Upcoming matches
            </Link>
          </div>

          {/* stat strip */}
          <div className="stagger mt-8 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Stat i={0} label="Model" value={health.model?.replace(/_/g, " ") || "—"} />
            <Stat i={1} label="Data cutoff" value={health.data_cutoff || "—"} />
            <Stat
              i={2}
              label="Simulations"
              value={health.n_sims ? health.n_sims.toLocaleString() : "—"}
            />
            <Stat
              i={3}
              label="Group stage"
              value={`${health.played_group_matches}/${
                health.played_group_matches + health.pending_group_matches
              } played`}
            />
          </div>
        </div>
      </div>

      {/* ----------------------------------------------------------------- */}
      {/* PODIUM                                                            */}
      {/* ----------------------------------------------------------------- */}
      <Section
        eyebrow="Who lifts the trophy?"
        title="Title favourites"
        cta={
          <Link href="/teams" className="text-sm text-brand-300 hover:underline">
            All 48 teams →
          </Link>
        }
      >
        <div className="stagger mb-4 grid gap-4 sm:grid-cols-3">
          {podium.map((t, i) => (
            <PodiumCard key={t.code} t={t} rank={i + 1} i={i} />
          ))}
        </div>

        <div className="card divide-y divide-white/5 overflow-hidden">
          {rest.map((t, i) => (
            <div
              key={t.code}
              className="flex items-center gap-3 px-4 py-2.5 transition-colors hover:bg-white/5"
            >
              <span className="w-5 text-sm tnum text-slate-500">{i + 4}</span>
              <span className="w-7 text-center text-xs font-semibold text-slate-500">
                {t.group}
              </span>
              <div className="w-44 shrink-0">
                <TeamButton code={t.code} name={t.team} />
              </div>
              <ConfChip conf={t.confederation} />
              <div className="hidden flex-1 sm:block">
                <Bar value={t.p_champion} />
              </div>
              <span className="w-14 text-right text-sm font-semibold tnum">
                {pct(t.p_champion)}
              </span>
            </div>
          ))}
        </div>
      </Section>

      {/* ----------------------------------------------------------------- */}
      {/* UPCOMING                                                          */}
      {/* ----------------------------------------------------------------- */}
      <Section
        eyebrow="Next on the pitch"
        title="Upcoming matches"
        cta={
          <Link href={matches.length === 0 && koTies.length ? "/bracket" : "/matches"} className="text-sm text-brand-300 hover:underline">
            {matches.length === 0 && koTies.length ? "Full bracket →" : "All matches →"}
          </Link>
        }
      >
        {matches.length === 0 && koTies.length > 0 ? (
          <div className="stagger grid gap-3 sm:grid-cols-2">
            {koTies.map((m, i) => (
              <Link
                key={m.match}
                href="/bracket"
                style={{ ["--i" as any]: i }}
                className="card card-hover p-4"
              >
                <div className="mb-3 flex justify-between text-xs text-slate-400">
                  <span className="rounded-full bg-brand/15 px-2 py-0.5 font-semibold text-brand-300">
                    {ROUND_LABEL[m.round] || m.round}
                  </span>
                  <span>{m.date || "TBD"}</span>
                </div>
                <div className="flex items-center justify-between gap-2">
                  <div className="flex min-w-0 items-center gap-2 font-semibold">
                    <Flag code={m.team1.code} name={m.team1.name} className="h-5 w-7" />
                    <span className="truncate">{m.team1.name}</span>
                  </div>
                  <span className="text-[11px] font-bold text-slate-500">VS</span>
                  <div className="flex min-w-0 items-center justify-end gap-2 font-semibold">
                    <span className="truncate text-right">{m.team2.name}</span>
                    <Flag code={m.team2.code} name={m.team2.name} className="h-5 w-7" />
                  </div>
                </div>
              </Link>
            ))}
          </div>
        ) : matches.length === 0 ? (
          <div className="card p-5 text-sm text-slate-400">No pending matches.</div>
        ) : (
          <div className="stagger grid gap-3 sm:grid-cols-2">
            {matches.map((m, i) => (
              <Link
                key={m.match_id}
                href={`/matches/${m.match_id}`}
                style={{ ["--i" as any]: i }}
                className="card card-hover p-4"
              >
                <div className="mb-3 flex justify-between text-xs text-slate-400">
                  <span className="rounded-full bg-white/5 px-2 py-0.5">
                    Group {m.group} · {m.date}
                  </span>
                  <span>{m.neutral ? "neutral" : m.country}</span>
                </div>
                <div className="mb-3 flex items-center justify-between gap-2">
                  <div className="flex min-w-0 items-center gap-2 font-semibold">
                    <Flag code={m.home_code} name={m.home} className="h-5 w-7" />
                    <span className="truncate">{m.home}</span>
                  </div>
                  <span className="text-[11px] font-bold text-slate-500">VS</span>
                  <div className="flex min-w-0 items-center justify-end gap-2 font-semibold">
                    <span className="truncate text-right">{m.away}</span>
                    <Flag code={m.away_code} name={m.away} className="h-5 w-7" />
                  </div>
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

function Stat({ label, value, i }: { label: string; value: string; i: number }) {
  return (
    <div
      style={{ ["--i" as any]: i }}
      className="rounded-2xl border border-white/10 bg-white/[0.03] p-3"
    >
      <div className="text-[11px] uppercase tracking-wide text-slate-400">{label}</div>
      <div className="mt-0.5 text-sm font-bold capitalize text-white">{value}</div>
    </div>
  );
}

function PodiumCard({ t, rank, i }: { t: TeamProb; rank: number; i: number }) {
  const medal = ["🥇", "🥈", "🥉"][rank - 1];
  return (
    <div
      style={{ ["--i" as any]: i }}
      className="card card-hover relative overflow-hidden p-5"
    >
      <div className="pointer-events-none absolute -right-8 -top-8 h-24 w-24 rounded-full bg-brand/10 blur-2xl" />
      <div className="flex items-start justify-between">
        <span className="text-2xl">{medal}</span>
        <ConfChip conf={t.confederation} />
      </div>
      <div className="mt-3 flex items-center gap-3">
        <Flag code={t.code} name={t.team} className="h-9 w-12" w={80} />
        <div>
          <TeamButton code={t.code} name={t.team} className="text-lg" />
          <div className="text-xs text-slate-400">Group {t.group}</div>
        </div>
      </div>
      <div className="mt-4">
        <div className="flex items-end justify-between">
          <span className="eyebrow">Champion</span>
          <span className="text-2xl font-extrabold gradient-text tnum">
            {pct(t.p_champion)}
          </span>
        </div>
        <div className="mt-1.5">
          <Bar value={t.p_champion} />
        </div>
        <div className="mt-2 flex justify-between text-xs text-slate-400">
          <span>Win group {pct(t.p_win_group, 0)}</span>
          <span>Reach final {pct(t.p_reach_final, 0)}</span>
        </div>
      </div>
    </div>
  );
}
