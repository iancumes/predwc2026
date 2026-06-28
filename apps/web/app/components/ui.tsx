"use client";
import Link from "next/link";
import { useState } from "react";
import { pct } from "../lib/api";
import { flagUrl } from "../lib/flags";
import { useTeamPeek } from "./TeamModal";

export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="space-y-3 py-6">
      <div className="flex items-center gap-3 text-sm text-slate-400">
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/20 border-t-brand" />
        {label}
      </div>
      <div className="space-y-2">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="skeleton h-12 w-full" style={{ ["--i" as any]: i }} />
        ))}
      </div>
    </div>
  );
}

export function ErrorState({ error }: { error: string }) {
  return (
    <div className="card border-amber-400/30 bg-amber-400/10 p-5 text-sm text-amber-200">
      <p className="font-semibold">Couldn’t load this prediction snapshot.</p>
      <p className="mt-1 text-amber-200/80">
        {error}. The data may still be generating — it refreshes automatically
        after each matchday. Please try again in a moment.
      </p>
    </div>
  );
}

export function Empty({ label }: { label: string }) {
  return <div className="card p-6 text-sm text-slate-400">{label}</div>;
}

export function Section({
  title,
  children,
  cta,
  eyebrow,
}: {
  title: string;
  children: React.ReactNode;
  cta?: React.ReactNode;
  eyebrow?: string;
}) {
  return (
    <section className="mb-10 animate-fade-up">
      <div className="mb-4 flex items-end justify-between gap-3">
        <div>
          {eyebrow && <div className="eyebrow mb-1">{eyebrow}</div>}
          <h2 className="text-xl font-bold text-white">{title}</h2>
        </div>
        {cta}
      </div>
      {children}
    </section>
  );
}

const CONF_COLORS: Record<string, string> = {
  UEFA: "bg-sky-400/15 text-sky-300 ring-1 ring-sky-400/30",
  CONMEBOL: "bg-amber-400/15 text-amber-300 ring-1 ring-amber-400/30",
  CONCACAF: "bg-rose-400/15 text-rose-300 ring-1 ring-rose-400/30",
  CAF: "bg-emerald-400/15 text-emerald-300 ring-1 ring-emerald-400/30",
  AFC: "bg-violet-400/15 text-violet-300 ring-1 ring-violet-400/30",
  OFC: "bg-cyan-400/15 text-cyan-300 ring-1 ring-cyan-400/30",
  UNK: "bg-white/10 text-slate-300 ring-1 ring-white/15",
};

export function ConfChip({ conf }: { conf: string }) {
  return <span className={`chip ${CONF_COLORS[conf] || CONF_COLORS.UNK}`}>{conf}</span>;
}

/**
 * A flag image with graceful fallback: shows the nation's initials inside a
 * tinted box when the country isn't mapped OR the CDN image fails to load.
 */
export function Flag({
  code,
  name,
  className = "h-4 w-6",
  w = 40,
}: {
  code?: string;
  name?: string;
  className?: string;
  w?: number;
}) {
  const [failed, setFailed] = useState(false);
  const url = flagUrl(code || name || "", w);
  const initials = (name || code || "?")
    .replace(/[^a-zA-Z]/g, "")
    .slice(0, 2)
    .toUpperCase();

  if (!url || failed)
    return (
      <span
        className={`grid shrink-0 place-items-center rounded-sm bg-white/10 text-[9px] font-bold text-slate-300 ring-1 ring-white/10 ${className}`}
      >
        {initials}
      </span>
    );
  return (
    /* eslint-disable-next-line @next/next/no-img-element */
    <img
      src={url}
      alt=""
      loading="lazy"
      onError={() => setFailed(true)}
      className={`rounded-sm object-cover shadow ring-1 ring-white/10 ${className}`}
    />
  );
}

/**
 * A clickable team token: flag + name that opens the team-peek modal.
 * Used everywhere a team is mentioned so the whole UI is explorable.
 */
export function TeamButton({
  code,
  name,
  className = "",
  flagClass = "h-4 w-6",
  bold = true,
}: {
  code: string;
  name: string;
  className?: string;
  flagClass?: string;
  bold?: boolean;
}) {
  const { open } = useTeamPeek();
  return (
    <button
      onClick={() => open(code)}
      className={`group inline-flex items-center gap-2 text-left transition-colors hover:text-brand ${
        bold ? "font-semibold" : ""
      } ${className}`}
    >
      <Flag code={code} name={name} className={`${flagClass} shrink-0`} />
      <span className="truncate underline-offset-4 group-hover:underline">{name}</span>
    </button>
  );
}

// 1X2 stacked probability bar.
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
    return <span className="text-xs text-slate-500">no prediction</span>;
  return (
    <div>
      <div className="prob-bar">
        <div style={{ width: `${h * 100}%` }} className="bg-brand transition-all" title={`Home ${pct(h)}`} />
        <div style={{ width: `${d * 100}%` }} className="bg-white/25 transition-all" title={`Draw ${pct(d)}`} />
        <div style={{ width: `${a * 100}%` }} className="bg-electric transition-all" title={`Away ${pct(a)}`} />
      </div>
      <div className="mt-1 flex justify-between text-[11px] text-slate-400">
        <span className="text-brand-300">H {pct(h, 0)}</span>
        <span>D {pct(d, 0)}</span>
        <span className="text-electric">A {pct(a, 0)}</span>
      </div>
    </div>
  );
}

export function TeamLink({ code, name }: { code: string; name: string }) {
  return <TeamButton code={code} name={name} />;
}

export function Bar({ value, gradient = true }: { value: number; gradient?: boolean }) {
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-white/10">
      <div
        className={`h-2 origin-left rounded-full animate-bar-grow ${
          gradient ? "bg-brand-gradient" : "bg-brand"
        }`}
        style={{ width: `${Math.min(value * 100, 100)}%` }}
      />
    </div>
  );
}
