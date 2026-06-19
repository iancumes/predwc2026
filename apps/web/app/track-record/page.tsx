"use client";
import { useEffect, useState } from "react";
import { api, pct } from "../lib/api";
import { Loading, ErrorState } from "../components/ui";

export default function TrackRecordPage() {
  const [m, setM] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.metrics().then(setM).catch((e) => setErr(String(e)));
  }, []);

  if (err) return <ErrorState error={err} />;
  if (!m) return <Loading />;
  const tr = m.track_record || { n: 0 };

  return (
    <div>
      <h1 className="mb-1 text-2xl font-bold">Track record</h1>
      <p className="mb-5 text-sm text-slate-500">
        Predictions frozen <b>before kickoff</b> using only prior data, scored
        against actual results. This is a small, early sample — the backtest over
        thousands of historical matches (see Methodology) is the reliable guide.
      </p>

      {tr.n === 0 ? (
        <div className="card p-5 text-sm text-slate-500">No frozen predictions scored yet. Run <code>make freeze</code>.</div>
      ) : (
        <>
          <div className="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Metric label="Matches" value={String(tr.n)} />
            <Metric label="Accuracy" value={pct(tr.accuracy)} />
            <Metric label="Log loss" value={tr.log_loss?.toFixed(3)} />
            <Metric label="Brier" value={tr.brier?.toFixed(3)} />
          </div>
          <div className="card overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-[11px] uppercase text-slate-400">
                <tr>
                  <th className="px-3 py-2 text-left font-medium">Date</th>
                  <th className="px-3 py-2 text-left font-medium">Match</th>
                  <th className="px-2 py-2 text-center font-medium">Result</th>
                  <th className="px-2 py-2 text-center font-medium">Pred</th>
                  <th className="px-2 py-2 text-center font-medium">Actual</th>
                  <th className="px-2 py-2 text-center font-medium">Hit</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {tr.matches?.map((x: any, i: number) => (
                  <tr key={i} className="hover:bg-slate-50">
                    <td className="px-3 py-1.5 text-xs text-slate-400">{x.date}</td>
                    <td className="px-3 py-1.5">{x.home} vs {x.away}</td>
                    <td className="px-2 text-center font-mono">{x.score}</td>
                    <td className="px-2 text-center">{x.predicted}</td>
                    <td className="px-2 text-center">{x.actual}</td>
                    <td className="px-2 text-center">{x.predicted === x.actual ? "✅" : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="card p-4 text-center">
      <div className="text-[11px] uppercase tracking-wide text-slate-400">{label}</div>
      <div className="mt-1 text-xl font-bold tabular-nums">{value}</div>
    </div>
  );
}
