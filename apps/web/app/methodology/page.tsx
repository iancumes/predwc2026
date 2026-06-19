"use client";
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { Loading, ErrorState } from "../components/ui";

export default function MethodologyPage() {
  const [m, setM] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.metrics().then(setM).catch((e) => setErr(String(e)));
  }, []);

  return (
    <div className="prose-sm max-w-none">
      <h1 className="text-2xl font-bold">Methodology</h1>

      <h2 className="mt-6 text-lg font-semibold">Data</h2>
      <p className="text-sm text-slate-600">
        Primary source: <code>martj42/international_results</code> (CC0) — every
        international men&apos;s match since 1872, including the live 2026 World
        Cup fixtures and results. Team names are normalised across spellings and
        codes; the official 2026 group draw and bracket are verified from FIFA /
        Wikipedia. Every feature uses only information available <b>before</b>{" "}
        kickoff (strict <code>as_of</code> semantics, enforced by tests).
      </p>

      <h2 className="mt-6 text-lg font-semibold">Models</h2>
      <ul className="list-disc pl-5 text-sm text-slate-600">
        <li><b>Elo</b> — World-Football style with margin-of-victory and tournament weighting.</li>
        <li><b>Poisson</b> — team attack/defence GLM with home advantage and time decay.</li>
        <li><b>Dixon–Coles</b> — bivariate Poisson with low-score correction and exponential time decay (MLE).</li>
        <li><b>Gradient boosting</b> — histogram GBM on ~29 engineered features: Elo &amp; Elo
          momentum, weighted form &amp; win rate, goals-for/against and goal-difference form,
          rest days, caps/experience, recent head-to-head, confederation and tournament weight.</li>
        <li><b>Ensemble</b> — convex blend of the above, weights learned on validation, then probability-calibrated.</li>
      </ul>

      <h2 className="mt-6 text-lg font-semibold">What we predict</h2>
      <ul className="list-disc pl-5 text-sm text-slate-600">
        <li><b>Match result</b> — 1X2 (home / draw / away).</li>
        <li><b>Goals</b> — expected goals per side and total, full total-goals distribution,
          over/under 0.5–3.5, both-teams-to-score, and clean-sheet / win-to-nil probabilities.</li>
        <li><b>Exact score</b> — the most likely scorelines, derived from the goal model.</li>
        <li><b>Anytime goalscorer</b> — per-player probabilities from time-decayed recent
          scoring rates combined with each team&apos;s expected goals.</li>
        <li><b>Tournament</b> — group-stage, knockout-round and title probabilities by Monte Carlo.</li>
      </ul>
      <p className="mt-1 text-xs text-slate-500">
        Corners and cards are <i>not</i> modelled: the free CC0 results feed does not include
        them. They could be added later from a (paid) match-events provider.
      </p>

      <h2 className="mt-6 text-lg font-semibold">Validation &amp; calibration</h2>
      <p className="text-sm text-slate-600">
        Models are compared with strict <b>walk-forward backtesting</b> (train on
        the past, predict the next period, never shuffle across time). The model
        is chosen primarily on out-of-sample <b>log loss</b> and{" "}
        <b>calibration</b> (not raw accuracy). Probabilities are calibrated
        (temperature / isotonic, whichever is more robust on validation).
      </p>

      {err ? (
        <ErrorState error={err} />
      ) : !m ? (
        <Loading />
      ) : (
        <div className="card mt-3 overflow-x-auto p-4">
          <div className="mb-2 text-xs text-slate-500">
            Backtest test set: {m.n_test?.toLocaleString()} matches · calibration: {m.calibration} ·
            ensemble weights: {JSON.stringify(
              Object.fromEntries(Object.entries(m.ensemble_weights || {}).map(([k, v]: any) => [k, Number(v).toFixed(2)]))
            )}
          </div>
          <table className="w-full text-sm">
            <thead className="text-[11px] uppercase text-slate-400">
              <tr>
                <th className="px-2 py-1 text-left font-medium">Model</th>
                <th className="px-2 py-1 text-right font-medium">Log loss</th>
                <th className="px-2 py-1 text-right font-medium">Brier</th>
                <th className="px-2 py-1 text-right font-medium">RPS</th>
                <th className="px-2 py-1 text-right font-medium">ECE</th>
                <th className="px-2 py-1 text-right font-medium">Acc</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {Object.entries(m.overall || {})
                .sort((a: any, b: any) => a[1].log_loss - b[1].log_loss)
                .map(([name, met]: any) => (
                  <tr key={name} className={name.startsWith("ensemble") ? "font-semibold" : ""}>
                    <td className="px-2 py-1">{name}</td>
                    <td className="px-2 py-1 text-right tabular-nums">{met.log_loss.toFixed(4)}</td>
                    <td className="px-2 py-1 text-right tabular-nums">{met.brier.toFixed(4)}</td>
                    <td className="px-2 py-1 text-right tabular-nums">{met.rps.toFixed(4)}</td>
                    <td className="px-2 py-1 text-right tabular-nums">{met.ece.toFixed(4)}</td>
                    <td className="px-2 py-1 text-right tabular-nums">{met.accuracy.toFixed(3)}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      )}

      <h2 className="mt-6 text-lg font-semibold">Limitations</h2>
      <p className="text-sm text-slate-600">
        A probability is not a certainty — a 70% favourite still loses ~3 times in
        10. International data is noisy (friendlies, missing line-ups), squad/injury
        information is not yet modelled, and the early-tournament track record is a
        tiny sample. This platform is analytical and informational only; it is not
        betting advice and makes no promise of any outcome.
      </p>
    </div>
  );
}
