// Typed client for the WC2026 data layer.
//
// The site is deployed 100% static: instead of calling a live FastAPI backend,
// it reads pre-generated JSON snapshots from `/data/**` (produced by
// `wc2026 export`).  The `api.*` surface is unchanged so pages don't care, and
// every call still degrades gracefully — a missing file throws and the page
// renders its error/empty state.

// Optional override (e.g. point at a CDN); defaults to same-origin /data.
const DATA_BASE = (process.env.NEXT_PUBLIC_DATA_URL || "").replace(/\/$/, "");

async function get<T>(file: string): Promise<T> {
  const res = await fetch(`${DATA_BASE}/data/${file}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return (await res.json()) as T;
}

export type Health = {
  status: string;
  demo_mode: boolean;
  data_cutoff: string | null;
  model: string | null;
  model_calibration: string | null;
  n_sims: number | null;
  played_group_matches: number;
  pending_group_matches: number;
};

export type Manifest = {
  generated_at: string | null;
  data_cutoff: string | null;
  model: string | null;
  n_sims: number | null;
  n_matches: number;
  n_teams: number;
  played_group_matches: number;
  pending_group_matches: number;
};

export type TeamProb = {
  team: string;
  code: string;
  group: string;
  confederation: string;
  p_win_group: number;
  p_runner_up: number;
  p_qualify_third: number;
  p_reach_r32: number;
  p_reach_r16: number;
  p_reach_qf: number;
  p_reach_sf: number;
  p_reach_final: number;
  p_champion: number;
  se_champion: number;
};

export type MatchRow = {
  match_id: string;
  date: string;
  group: string | null;
  stage?: string | null;
  home: string;
  away: string;
  home_code: string;
  away_code: string;
  status: string;
  neutral: boolean;
  city: string;
  country: string;
  home_score: number | null;
  away_score: number | null;
  p_home: number | null;
  p_draw: number | null;
  p_away: number | null;
};

export type ScorerProb = { player: string; team: string; prob: number };

export type Prediction = {
  match_id: string;
  model_version_id: string;
  data_cutoff: string;
  created_at: string;
  home_team: string;
  away_team: string;
  home_win_probability: number;
  draw_probability: number;
  away_win_probability: number;
  expected_home_goals: number;
  expected_away_goals: number;
  over_2_5: number;
  btts_yes: number;
  top_scorelines: { score: string; prob: number }[];
  factors: Record<string, number | boolean | string>;
  is_frozen: boolean;
  status: string;
  home_score: number | null;
  away_score: number | null;
  // --- enriched markets (optional; older snapshots may omit them) ---------
  expected_total_goals?: number;
  most_likely_score?: string;
  over_under?: Record<string, number>; // {"0.5": p, "1.5": p, "2.5": p, "3.5": p}
  total_goals_dist?: number[]; // P(total = 0,1,2,...)
  btts_no?: number;
  home_clean_sheet?: number;
  away_clean_sheet?: number;
  home_win_to_nil?: number;
  away_win_to_nil?: number;
  scorers?: ScorerProb[];
};

export type Standing = {
  team: string;
  group: string;
  position: number;
  played: number;
  won: number;
  drawn: number;
  lost: number;
  gf: number;
  ga: number;
  gd: number;
  points: number;
  p_win_group?: number | null;
  p_runner_up?: number | null;
  p_qualify_third?: number | null;
  p_advance?: number | null;
};

// Filter the full match list client-side to mimic the old query API.
function filterMatches(all: MatchRow[], q: string): MatchRow[] {
  if (!q) return all;
  const params = new URLSearchParams(q.startsWith("?") ? q.slice(1) : q);
  const status = params.get("status");
  const group = params.get("group");
  const team = params.get("team");
  return all.filter(
    (m) =>
      (!status || m.status === status) &&
      (!group || m.group === group) &&
      (!team || m.home_code === team || m.away_code === team)
  );
}

export const api = {
  health: () => get<Health>("health.json"),
  manifest: () => get<Manifest>("manifest.json"),
  teams: () => get<{ teams: TeamProb[] }>("teams.json"),
  team: (code: string) => get<any>(`teams/${code}.json`),
  matches: async (q = "") => {
    const d = await get<{ matches: MatchRow[] }>("matches.json");
    return { matches: filterMatches(d.matches, q) };
  },
  match: (id: string) => get<any>(`matches/${id}.json`),
  groups: () => get<{ groups: Record<string, Standing[]> }>("groups.json"),
  probabilities: () =>
    get<{ n_sims: number; model: string; teams: TeamProb[] }>(
      "probabilities.json"
    ),
  bracket: () => get<any>("bracket.json"),
  metrics: () => get<any>("metrics.json"),
  calibration: () => get<any>("calibration.json"),
  scorers: () => get<any>("scorers.json"),
};

export const pct = (x: number | null | undefined, d = 1) =>
  x === null || x === undefined ? "—" : `${(x * 100).toFixed(d)}%`;
