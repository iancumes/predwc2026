"use client";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import Link from "next/link";
import { api, pct } from "../lib/api";
import { flagUrl } from "../lib/flags";

// ---------------------------------------------------------------------------
// Global "team peek" modal.
//
// Any element on any page can call `useTeamPeek().open(code)` to slide up an
// animated panel with that nation's flag, tournament odds, group fixtures and
// recent form — without leaving the current view.  This is what makes browsing
// matches/brackets feel fluid: tap a team, read its story, tap away.
// ---------------------------------------------------------------------------

type Ctx = { open: (code: string) => void; close: () => void };
const TeamPeekCtx = createContext<Ctx | null>(null);

export function useTeamPeek(): Ctx {
  const ctx = useContext(TeamPeekCtx);
  // Render-safe fallback so components work even outside the provider (e.g. tests).
  return ctx ?? { open: () => {}, close: () => {} };
}

const CONF_TINT: Record<string, string> = {
  UEFA: "from-sky-500/30",
  CONMEBOL: "from-amber-400/30",
  CONCACAF: "from-rose-500/30",
  CAF: "from-emerald-500/30",
  AFC: "from-violet-500/30",
  OFC: "from-cyan-500/30",
};

const ODDS: [string, string][] = [
  ["p_win_group", "Win group"],
  ["p_reach_r16", "Round of 16"],
  ["p_reach_qf", "Quarter-final"],
  ["p_reach_sf", "Semi-final"],
  ["p_reach_final", "Final"],
  ["p_champion", "Champion"],
];

export function TeamPeekProvider({ children }: { children: React.ReactNode }) {
  const [code, setCode] = useState<string | null>(null);
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [closing, setClosing] = useState(false);

  const close = useCallback(() => {
    setClosing(true);
    setTimeout(() => {
      setCode(null);
      setData(null);
      setClosing(false);
    }, 200);
  }, []);

  const open = useCallback((c: string) => {
    setCode(c);
    setData(null);
    setClosing(false);
    setLoading(true);
    api
      .team(c)
      .then((d) => setData(d))
      .catch(() => setData({ error: true }))
      .finally(() => setLoading(false));
  }, []);

  // Lock scroll + close on Escape while the panel is open.
  useEffect(() => {
    if (!code) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && close();
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [code, close]);

  const s = data?.simulation || {};
  const tint = CONF_TINT[data?.confederation] || "from-brand/30";
  const flag = data ? flagUrl(data.code, 160) : null;

  return (
    <TeamPeekCtx.Provider value={{ open, close }}>
      {children}
      {code && (
        <div
          className={`fixed inset-0 z-50 flex items-end justify-center sm:items-center ${
            closing ? "animate-fade-in [animation-direction:reverse]" : "animate-fade-in"
          }`}
        >
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/70 backdrop-blur-sm"
            onClick={close}
            aria-hidden
          />

          {/* Panel */}
          <div
            role="dialog"
            aria-modal="true"
            className={`relative z-10 max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-t-3xl border border-white/10 bg-base-800/95 shadow-lift backdrop-blur-2xl sm:rounded-3xl ${
              closing ? "translate-y-4 opacity-0 transition-all duration-200" : "animate-scale-in"
            }`}
          >
            {/* Header with confederation-tinted glow + big flag */}
            <div className={`relative overflow-hidden rounded-t-3xl bg-gradient-to-br ${tint} to-transparent p-5`}>
              <button
                onClick={close}
                aria-label="Close"
                className="absolute right-4 top-4 grid h-8 w-8 place-items-center rounded-full bg-white/10 text-slate-200 transition hover:bg-white/20"
              >
                ✕
              </button>

              {loading || !data ? (
                <div className="flex items-center gap-4">
                  <div className="skeleton h-12 w-16 rounded-md" />
                  <div className="space-y-2">
                    <div className="skeleton h-5 w-40" />
                    <div className="skeleton h-3 w-24" />
                  </div>
                </div>
              ) : data.error ? (
                <p className="text-sm text-amber-300">Couldn’t load this team right now.</p>
              ) : (
                <div className="flex items-center gap-4">
                  {flag ? (
                    /* eslint-disable-next-line @next/next/no-img-element */
                    <img
                      src={flag}
                      alt=""
                      onError={(e) => {
                        (e.currentTarget as HTMLImageElement).style.display = "none";
                      }}
                      className="h-12 w-16 rounded-md object-cover shadow-lg ring-1 ring-white/20"
                    />
                  ) : (
                    <span className="grid h-12 w-16 place-items-center rounded-md bg-white/10 text-sm font-bold ring-1 ring-white/20">
                      {data.name.slice(0, 2).toUpperCase()}
                    </span>
                  )}
                  <div>
                    <h2 className="text-2xl font-bold leading-tight">{data.name}</h2>
                    <div className="mt-1 flex items-center gap-2 text-xs text-slate-300">
                      <span className="rounded-full bg-white/10 px-2 py-0.5">{data.confederation}</span>
                      <span>Group {data.group}</span>
                      {data.is_host && (
                        <span className="rounded-full bg-gold/20 px-2 py-0.5 text-gold">Host</span>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>

            {data && !data.error && (
              <div className="space-y-5 p-5">
                {/* Headline: title odds */}
                <div className="flex items-end justify-between rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3">
                  <div>
                    <div className="eyebrow">Title chance</div>
                    <div className="text-3xl font-bold gradient-text tnum">{pct(s.p_champion)}</div>
                  </div>
                  <div className="text-right text-xs text-slate-400">
                    <div>Reach final {pct(s.p_reach_final, 0)}</div>
                    <div>Reach SF {pct(s.p_reach_sf, 0)}</div>
                  </div>
                </div>

                {/* Tournament progression bars */}
                <div className="space-y-2.5">
                  {ODDS.map(([k, label], i) => (
                    <div key={k} style={{ ["--i" as any]: i }} className="animate-fade-up">
                      <div className="mb-1 flex justify-between text-[13px]">
                        <span className="text-slate-300">{label}</span>
                        <span className="font-semibold tnum">{pct(s[k])}</span>
                      </div>
                      <div className="h-2 overflow-hidden rounded-full bg-white/10">
                        <div
                          className="h-full origin-left rounded-full bg-brand-gradient animate-bar-grow"
                          style={{ width: `${Math.min((s[k] || 0) * 100, 100)}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>

                {/* Recent form dots */}
                {data.recent_matches?.length > 0 && (
                  <div>
                    <div className="eyebrow mb-2">Recent form</div>
                    <FormStrip matches={data.recent_matches} team={data.name} />
                  </div>
                )}

                {/* Group fixtures */}
                {data.group_fixtures?.length > 0 && (
                  <div>
                    <div className="eyebrow mb-2">Group {data.group} fixtures</div>
                    <ul className="space-y-1 text-sm">
                      {data.group_fixtures.map((m: any) => (
                        <li
                          key={m.match_id}
                          className="flex items-center justify-between rounded-lg px-2 py-1 hover:bg-white/5"
                        >
                          <span className="truncate text-slate-300">
                            {m.home} <span className="text-slate-500">v</span> {m.away}
                          </span>
                          <span className="ml-2 shrink-0 tnum text-xs">
                            {m.status === "played" ? (
                              <span className="rounded bg-white/10 px-1.5 py-0.5 font-semibold">
                                {m.home_score}–{m.away_score}
                              </span>
                            ) : (
                              <span className="text-slate-400">{m.date.slice(5)}</span>
                            )}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                <Link
                  href={`/teams/${data.code}`}
                  onClick={close}
                  className="block rounded-xl bg-brand-gradient py-2.5 text-center text-sm font-semibold text-base-900 transition hover:brightness-110"
                >
                  Full team profile →
                </Link>
              </div>
            )}
          </div>
        </div>
      )}
    </TeamPeekCtx.Provider>
  );
}

// Win/Draw/Loss dots from the team's POV.
function FormStrip({ matches, team }: { matches: any[]; team: string }) {
  const last = matches.slice(-6);
  return (
    <div className="flex gap-1.5">
      {last.map((m, i) => {
        const [hs, as] = (m.score || "").split("-").map((x: string) => parseInt(x, 10));
        let res: "W" | "D" | "L" | "?" = "?";
        if (!isNaN(hs) && !isNaN(as)) {
          const isHome = m.home === team;
          const gf = isHome ? hs : as;
          const ga = isHome ? as : hs;
          res = gf > ga ? "W" : gf < ga ? "L" : "D";
        }
        const cls =
          res === "W"
            ? "bg-brand text-base-900"
            : res === "L"
            ? "bg-magenta/80 text-white"
            : res === "D"
            ? "bg-white/20 text-white"
            : "bg-white/10 text-slate-400";
        return (
          <div
            key={i}
            title={`${m.home} ${m.score} ${m.away}`}
            style={{ ["--i" as any]: i }}
            className={`grid h-7 w-7 animate-scale-in place-items-center rounded-md text-xs font-bold ${cls}`}
          >
            {res}
          </div>
        );
      })}
    </div>
  );
}
