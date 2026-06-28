"use client";
import { useEffect, useMemo, useState } from "react";
import { api, pct, Standing } from "../lib/api";
import { Loading, ErrorState, Flag, TeamButton } from "../components/ui";
import { teamSlug } from "../lib/flags";
import { useTeamPeek } from "../components/TeamModal";

// Order + display labels for the knockout rounds (R32 → Final).
const ROUND_META: { key: string; label: string; short: string }[] = [
  { key: "R32", label: "Round of 32", short: "R32" },
  { key: "R16", label: "Round of 16", short: "R16" },
  { key: "QF", label: "Quarter-finals", short: "QF" },
  { key: "SF", label: "Semi-finals", short: "SF" },
  { key: "FINAL", label: "Final", short: "Final" },
];

type Resolved =
  | { kind: "team"; code: string; name: string }
  | { kind: "slot"; label: string; sub?: string };

export default function BracketPage() {
  const [data, setData] = useState<any>(null);
  const [groups, setGroups] = useState<Record<string, Standing[]> | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [view, setView] = useState<"tree" | "odds">("tree");

  useEffect(() => {
    Promise.all([api.bracket(), api.groups()])
      .then(([b, g]) => {
        setData(b);
        setGroups(g.groups);
      })
      .catch((e) => setErr(String(e)));
  }, []);

  // Resolve "1A"/"2B" slots to real teams once a group is mathematically locked.
  const locked = useMemo(() => {
    const winner: Record<string, Standing> = {};
    const runner: Record<string, Standing> = {};
    if (!groups) return { winner, runner };
    for (const [g, rows] of Object.entries(groups)) {
      const w = rows.find((r) => r.p_win_group === 1);
      const r = rows.find((r) => r.p_runner_up === 1);
      if (w) winner[g] = w;
      if (r) runner[g] = r;
    }
    return { winner, runner };
  }, [groups]);

  const resolve = (slot: string): Resolved => {
    // Group winner / runner-up, e.g. "1A", "2C".
    const gm = /^([12])([A-L])$/.exec(slot);
    if (gm) {
      const [, pos, g] = gm;
      const row = pos === "1" ? locked.winner[g] : locked.runner[g];
      if (row) return { kind: "team", code: teamSlug(row.team), name: row.team };
      return { kind: "slot", label: pos === "1" ? `Winner Group ${g}` : `Runner-up ${g}` };
    }
    // Best-third-placed qualifier, e.g. "3:A/B/C/D/F".
    if (slot.startsWith("3:"))
      return { kind: "slot", label: "3rd place", sub: slot.slice(2).replace(/\//g, " / ") };
    // Winner / loser of an earlier knockout match.
    const wm = /^W(\d+)$/.exec(slot);
    if (wm) return { kind: "slot", label: `Winner`, sub: `Match ${wm[1]}` };
    const lm = /^L(\d+)$/.exec(slot);
    if (lm) return { kind: "slot", label: `Loser`, sub: `Match ${lm[1]}` };
    return { kind: "slot", label: slot };
  };

  if (err) return <ErrorState error={err} />;
  if (!data) return <Loading label="Building the bracket…" />;

  const thirdPlace = data.rounds.THIRD_PLACE?.[0];

  return (
    <div>
      {/* Header + view toggle */}
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div className="animate-fade-up">
          <div className="eyebrow mb-1">Knockout stage</div>
          <h1 className="text-3xl font-extrabold">Road to the final</h1>
          <p className="mt-2 max-w-2xl text-sm text-slate-400">
            The official 2026 bracket from the Round of 32 onward. Decided group
            slots show the real qualified nation; the rest fill in as results
            land. Tap any team for its full story.
          </p>
        </div>
        <div className="inline-flex rounded-xl border border-white/10 bg-white/5 p-1 text-sm">
          {(["tree", "odds"] as const).map((v) => (
            <button
              key={v}
              onClick={() => setView(v)}
              className={`rounded-lg px-4 py-1.5 font-medium transition ${
                view === v ? "bg-brand-gradient text-base-900" : "text-slate-300 hover:text-white"
              }`}
            >
              {v === "tree" ? "Bracket" : "Reach odds"}
            </button>
          ))}
        </div>
      </div>

      {view === "tree" ? (
        <BracketTree rounds={data.rounds} resolve={resolve} thirdPlace={thirdPlace} />
      ) : (
        <ReachTable rows={data.round_reach} />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Bracket tree
// ---------------------------------------------------------------------------
function BracketTree({
  rounds,
  resolve,
  thirdPlace,
}: {
  rounds: any;
  resolve: (s: string) => Resolved;
  thirdPlace: any;
}) {
  return (
    <div>
      <div className="hide-scrollbar -mx-4 overflow-x-auto px-4 pb-4">
        <div className="flex min-w-max gap-5">
          {ROUND_META.map((r, ci) => {
            const matches = rounds[r.key] || [];
            return (
              <div key={r.key} className="flex w-[230px] flex-col" style={{ ["--i" as any]: ci }}>
                <div className="mb-3 flex items-center gap-2">
                  <span className="rounded-full bg-brand-gradient px-2.5 py-0.5 text-xs font-bold text-base-900">
                    {r.short}
                  </span>
                  <span className="text-sm font-semibold text-slate-200">{r.label}</span>
                  <span className="ml-auto text-xs text-slate-500">{matches.length}</span>
                </div>
                {/* Spread matches vertically so each round centres against its feeders. */}
                <div
                  className="flex flex-1 flex-col justify-around gap-3"
                  style={{ paddingTop: ci * 8, paddingBottom: ci * 8 }}
                >
                  {matches.map((m: any, mi: number) => (
                    <MatchCard
                      key={m.match}
                      match={m}
                      resolve={resolve}
                      delay={ci * 80 + mi * 40}
                      champion={r.key === "FINAL"}
                    />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Third-place play-off, shown apart from the main tree. */}
      {thirdPlace && (
        <div className="mt-6 max-w-[230px]">
          <div className="mb-3 flex items-center gap-2">
            <span className="rounded-full bg-white/10 px-2.5 py-0.5 text-xs font-bold text-slate-200">
              3rd
            </span>
            <span className="text-sm font-semibold text-slate-200">Third-place play-off</span>
          </div>
          <MatchCard match={thirdPlace} resolve={resolve} delay={0} />
        </div>
      )}

      <p className="mt-6 text-xs text-slate-500">
        Bracket structure verified against FIFA&apos;s official 2026 format,
        including the best-eight third-placed rule. Placeholders resolve to real
        nations automatically as each round is decided.
      </p>
    </div>
  );
}

function MatchCard({
  match,
  resolve,
  delay,
  champion,
}: {
  match: any;
  resolve: (s: string) => Resolved;
  delay: number;
  champion?: boolean;
}) {
  const a = resolve(match.slot1);
  const b = resolve(match.slot2);
  return (
    <div
      style={{ animationDelay: `${delay}ms` }}
      className="animate-scale-in overflow-hidden rounded-xl border border-white/10 bg-white/[0.04] shadow-card transition-colors hover:border-brand/40"
    >
      <div className="flex items-center justify-between border-b border-white/5 px-2.5 py-1 text-[10px] uppercase tracking-wide text-slate-500">
        <span>Match {match.match}</span>
        {champion && <span className="text-gold">🏆 Final</span>}
      </div>
      <SlotRow r={a} />
      <div className="h-px bg-white/5" />
      <SlotRow r={b} />
    </div>
  );
}

function SlotRow({ r }: { r: Resolved }) {
  const { open } = useTeamPeek();
  if (r.kind === "team") {
    return (
      <button
        onClick={() => open(r.code)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm transition-colors hover:bg-white/5"
      >
        <Flag code={r.code} name={r.name} className="h-4 w-6 shrink-0" />
        <span className="truncate font-semibold">{r.name}</span>
      </button>
    );
  }
  return (
    <div className="flex items-center gap-2 px-3 py-2 text-sm text-slate-400">
      <span className="grid h-4 w-6 shrink-0 place-items-center rounded-sm bg-white/5 text-[9px]">
        ?
      </span>
      <span className="truncate">
        {r.label}
        {r.sub && <span className="ml-1 text-xs text-slate-500">{r.sub}</span>}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Reach-probability heatmap (predictive view)
// ---------------------------------------------------------------------------
const COLS: [string, string][] = [
  ["p_reach_r32", "R32"],
  ["p_reach_r16", "R16"],
  ["p_reach_qf", "QF"],
  ["p_reach_sf", "SF"],
  ["p_reach_final", "Final"],
  ["p_champion", "Win"],
];

function ReachTable({ rows }: { rows: any[] }) {
  const sorted = [...rows]
    .filter((r) => r.p_champion !== null && r.p_champion !== undefined)
    .sort((a, b) => b.p_champion - a.p_champion);

  return (
    <div className="card overflow-x-auto animate-fade-up">
      <table className="w-full text-sm">
        <thead className="text-[11px] uppercase text-slate-400">
          <tr className="border-b border-white/10">
            <th className="px-3 py-2.5 text-left font-medium">Team</th>
            <th className="px-2 py-2.5 text-center font-medium">Grp</th>
            {COLS.map(([, l]) => (
              <th key={l} className="px-2 py-2.5 text-center font-medium">
                {l}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-white/5">
          {sorted.map((r) => (
            <tr key={r.code} className="transition-colors hover:bg-white/5">
              <td className="px-3 py-1.5">
                <TeamButton code={r.code} name={r.team} flagClass="h-4 w-6" />
              </td>
              <td className="px-2 text-center text-xs text-slate-500">{r.group}</td>
              {COLS.map(([k, l]) => (
                <td key={l} className="px-2 py-1.5 text-center tnum">
                  <span
                    className="inline-block min-w-[42px] rounded-md px-1.5 py-0.5 text-xs font-medium"
                    style={{ backgroundColor: heat(r[k]), color: r[k] > 0.5 ? "#04110c" : "#cbd5e1" }}
                  >
                    {pct(r[k], 0)}
                  </span>
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function heat(v: number): string {
  if (v === null || v === undefined || v === 0) return "rgba(255,255,255,0.04)";
  const a = Math.min(v * 0.85 + 0.12, 0.95);
  return `rgba(34,211,166,${a})`;
}
