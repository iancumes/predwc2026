"use client";
import Link from "next/link";
import { pct } from "../lib/api";

export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 py-10 text-slate-500">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-accent" />
      {label}
    </div>
  );
}

export function ErrorState({ error }: { error: string }) {
  return (
    <div className="card border-amber-200 bg-amber-50 p-5 text-sm text-amber-800">
      <p className="font-semibold">Couldn’t load this prediction snapshot.</p>
      <p className="mt-1">
        {error}. The data may still be generating — it refreshes automatically
        after each matchday. Please try again in a moment.
      </p>
    </div>
  );
}

export function Empty({ label }: { label: string }) {
  return <div className="card p-6 text-sm text-slate-500">{label}</div>;
}

export function Section({
  title,
  children,
  cta,
}: {
  title: string;
  children: React.ReactNode;
  cta?: React.ReactNode;
}) {
  return (
    <section className="mb-8">
      <div className="mb-3 flex items-baseline justify-between">
        <h2 className="text-lg font-semibold text-ink">{title}</h2>
        {cta}
      </div>
      {children}
    </section>
  );
}

const CONF_COLORS: Record<string, string> = {
  UEFA: "bg-blue-100 text-blue-700",
  CONMEBOL: "bg-yellow-100 text-yellow-800",
  CONCACAF: "bg-red-100 text-red-700",
  CAF: "bg-green-100 text-green-700",
  AFC: "bg-purple-100 text-purple-700",
  OFC: "bg-cyan-100 text-cyan-700",
  UNK: "bg-slate-100 text-slate-600",
};

export function ConfChip({ conf }: { conf: string }) {
  return <span className={`chip ${CONF_COLORS[conf] || CONF_COLORS.UNK}`}>{conf}</span>;
}

// 1X2 stacked probability bar
export function ProbSplit({
  h,
  d,
  a,
}: {
  h: number | null;
  d: number | null;
  a: number | null;
}) {
  if (h === null || d === null || a === null)
    return <span className="text-xs text-slate-400">no prediction</span>;
  return (
    <div>
      <div className="prob-bar">
        <div style={{ width: `${h * 100}%` }} className="bg-accent" title={`Home ${pct(h)}`} />
        <div style={{ width: `${d * 100}%` }} className="bg-slate-300" title={`Draw ${pct(d)}`} />
        <div style={{ width: `${a * 100}%` }} className="bg-sky-500" title={`Away ${pct(a)}`} />
      </div>
      <div className="mt-1 flex justify-between text-[11px] text-slate-500">
        <span>H {pct(h, 0)}</span>
        <span>D {pct(d, 0)}</span>
        <span>A {pct(a, 0)}</span>
      </div>
    </div>
  );
}

export function TeamLink({ code, name }: { code: string; name: string }) {
  return (
    <Link href={`/teams/${code}`} className="font-medium hover:text-accent hover:underline">
      {name}
    </Link>
  );
}

export function Bar({ value, color = "bg-accent" }: { value: number; color?: string }) {
  return (
    <div className="h-2 w-full rounded-full bg-slate-100">
      <div className={`h-2 rounded-full ${color}`} style={{ width: `${Math.min(value * 100, 100)}%` }} />
    </div>
  );
}
