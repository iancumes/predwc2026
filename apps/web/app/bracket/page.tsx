"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, pct } from "../lib/api";
import { Loading, ErrorState, Flag, TeamButton } from "../components/ui";
import { useTeamPeek } from "../components/TeamModal";

// Order + display labels for the knockout rounds (R32 → Final).
const ROUND_META: { key: string; label: string; short: string }[] = [
  { key: "R32", label: "Round of 32", short: "R32" },
  { key: "R16", label: "Round of 16", short: "R16" },
  { key: "QF", label: "Quarter-finals", short: "QF" },
  { key: "SF", label: "Semi-finals", short: "SF" },
  { key: "FINAL", label: "Final", short: "Final" },
];

// One resolved knockout match, as produced by the engine's bracket resolver.
type MatchEntry = {
  match: number;
  round: string;
  team1: { name: string; code: string } | null;
  team2: { name: string; code: string } | null;
  label1: string;
  sub1: string | null;
  label2: string;
  sub2: string | null;
  score1: number | null;
  score2: number | null;
  winner_code: string | null;
  status: "played" | "scheduled" | "pending";
  date: string | null;
  match_id: string | null;
};

export default function BracketPage() {
  const [data, setData] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);
  const [view, setView] = useState<"tree" | "odds">("tree");

  useEffect(() => {
    api.bracket().then(setData).catch((e) => setErr(String(e)));
  }, []);

  if (err) return <ErrorState error={err} />;
  if (!data) return <Loading label="Building the bracket…" />;

  const resolved: Record<string, MatchEntry> = data.resolved || {};
  const get = (n: number): MatchEntry =>
    resolved[String(n)] || ({ match: n, status: "pending" } as MatchEntry);

  const champion = resolved["104"]?.winner_code
    ? resolved["104"].winner_code === resolved["104"].team1?.code
      ? resolved["104"].team1
      : resolved["104"].team2
    : null;

  const playedCount = Object.values(resolved).filter((m) => m.status === "played").length;

  return (
    <div>
      {/* Header + view toggle */}
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div className="animate-fade-up">
          <div className="eyebrow mb-1">Knockout stage</div>
          <h1 className="text-3xl font-extrabold">Road to the final</h1>
          <p className="mt-2 max-w-2xl text-sm text-slate-400">
            The official 2026 bracket from the Round of 32 onward. Real qualified
            nations and scores fill in automatically as matches are played; every
            winner advances to the next tie. Tap any team for its full story.
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

      {/* Champion banner once the final is decided */}
      {champion && (
        <div className="mb-6 flex items-center gap-4 rounded-2xl border border-gold/30 bg-gold/10 p-4 animate-scale-in">
          <span className="text-3xl">🏆</span>
          <Flag code={champion.code} name={champion.name} className="h-10 w-14" w={160} />
          <div>
            <div className="eyebrow text-gold">World champion</div>
            <div className="text-2xl font-extrabold">{champion.name}</div>
          </div>
        </div>
      )}

      {view === "tree" ? (
        <BracketTree get={get} thirdPlace={get(103)} playedCount={playedCount} />
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
  get,
  thirdPlace,
  playedCount,
}: {
  get: (n: number) => MatchEntry;
  thirdPlace: MatchEntry;
  playedCount: number;
}) {
  // The fixed match numbers that make up each round, in vertical order.
  const ROUND_MATCHES: Record<string, number[]> = {
    R32: [73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88],
    R16: [89, 90, 91, 92, 93, 94, 95, 96],
    QF: [97, 98, 99, 100],
    SF: [101, 102],
    FINAL: [104],
  };

  return (
    <div>
      <div className="mb-4 flex items-center gap-2 text-xs text-slate-400">
        <span className="inline-block h-2 w-2 rounded-full bg-brand" />
        {playedCount} of 32 knockout matches played
      </div>

      <div className="hide-scrollbar -mx-4 overflow-x-auto px-4 pb-4">
        <div className="flex min-w-max gap-5">
          {ROUND_META.map((r, ci) => (
            <div key={r.key} className="flex w-[250px] flex-col">
              <div className="mb-3 flex items-center gap-2">
                <span className="rounded-full bg-brand-gradient px-2.5 py-0.5 text-xs font-bold text-base-900">
                  {r.short}
                </span>
                <span className="text-sm font-semibold text-slate-200">{r.label}</span>
              </div>
              <div
                className="flex flex-1 flex-col justify-around gap-3"
                style={{ paddingTop: ci * 10, paddingBottom: ci * 10 }}
              >
                {ROUND_MATCHES[r.key].map((n, mi) => (
                  <MatchCard
                    key={n}
                    m={get(n)}
                    delay={ci * 70 + mi * 35}
                    champion={r.key === "FINAL"}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Third-place play-off */}
      <div className="mt-6 max-w-[250px]">
        <div className="mb-3 flex items-center gap-2">
          <span className="rounded-full bg-white/10 px-2.5 py-0.5 text-xs font-bold text-slate-200">
            3rd
          </span>
          <span className="text-sm font-semibold text-slate-200">Third-place play-off</span>
        </div>
        <MatchCard m={thirdPlace} delay={0} />
      </div>

      <p className="mt-6 text-xs text-slate-500">
        Bracket structure verified against FIFA&apos;s official 2026 format,
        including the best-eight third-placed rule. Slots resolve to real nations
        from live results; nothing is shown until it&apos;s mathematically decided.
      </p>
    </div>
  );
}

function MatchCard({
  m,
  delay,
  champion,
}: {
  m: MatchEntry;
  delay: number;
  champion?: boolean;
}) {
  const router = useRouter();
  const played = m.status === "played";
  const hasPred = !!m.match_id; // a real fixture exists -> full prediction page
  return (
    <div
      style={{ animationDelay: `${delay}ms` }}
      onClick={hasPred ? () => router.push(`/matches/${m.match_id}`) : undefined}
      className={`group/card animate-scale-in overflow-hidden rounded-xl border shadow-card transition-colors ${
        hasPred ? "cursor-pointer" : ""
      } ${
        played ? "border-brand/30 bg-white/[0.05]" : "border-white/10 bg-white/[0.03] hover:border-brand/30"
      }`}
    >
      <div className="flex items-center justify-between border-b border-white/5 px-2.5 py-1 text-[10px] uppercase tracking-wide text-slate-500">
        <span>Match {m.match}</span>
        <span className="flex items-center gap-1.5">
          {champion ? (
            <span className="text-gold">🏆 Final</span>
          ) : m.date ? (
            <span>{played ? "FT" : m.date.slice(5)}</span>
          ) : null}
          {hasPred && (
            <span className="text-brand-300 opacity-0 transition-opacity group-hover/card:opacity-100">
              stats →
            </span>
          )}
        </span>
      </div>
      <SlotRow
        team={m.team1}
        label={m.label1}
        sub={m.sub1}
        score={m.score1}
        played={played}
        isWinner={!!m.winner_code && m.team1?.code === m.winner_code}
        isLoser={!!m.winner_code && m.team1 != null && m.team1.code !== m.winner_code}
      />
      <div className="h-px bg-white/5" />
      <SlotRow
        team={m.team2}
        label={m.label2}
        sub={m.sub2}
        score={m.score2}
        played={played}
        isWinner={!!m.winner_code && m.team2?.code === m.winner_code}
        isLoser={!!m.winner_code && m.team2 != null && m.team2.code !== m.winner_code}
      />
    </div>
  );
}

function SlotRow({
  team,
  label,
  sub,
  score,
  played,
  isWinner,
  isLoser,
}: {
  team: { name: string; code: string } | null;
  label?: string;
  sub?: string | null;
  score: number | null;
  played: boolean;
  isWinner: boolean;
  isLoser: boolean;
}) {
  const { open } = useTeamPeek();

  if (team) {
    return (
      <button
        onClick={(e) => {
          e.stopPropagation();
          open(team.code);
        }}
        className={`flex w-full items-center gap-2 px-3 py-2 text-left text-sm transition-colors hover:bg-white/5 ${
          isWinner ? "bg-brand/10" : ""
        } ${isLoser ? "opacity-55" : ""}`}
      >
        {isWinner && <span className="-ml-1 mr-0.5 h-4 w-1 rounded-full bg-brand" />}
        <Flag code={team.code} name={team.name} className="h-4 w-6 shrink-0" />
        <span className={`truncate ${isWinner ? "font-bold text-white" : "font-semibold"}`}>
          {team.name}
        </span>
        {score !== null && (
          <span
            className={`ml-auto tnum text-sm font-bold ${
              isWinner ? "text-brand" : "text-slate-400"
            }`}
          >
            {score}
          </span>
        )}
      </button>
    );
  }

  return (
    <div className="flex items-center gap-2 px-3 py-2 text-sm text-slate-400">
      <span className="grid h-4 w-6 shrink-0 place-items-center rounded-sm bg-white/5 text-[9px]">
        ?
      </span>
      <span className="truncate">
        {label}
        {sub && <span className="ml-1 text-xs text-slate-500">{sub}</span>}
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
