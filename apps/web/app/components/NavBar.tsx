"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

const NAV = [
  { href: "/", label: "Home" },
  { href: "/matches", label: "Matches" },
  { href: "/groups", label: "Groups" },
  { href: "/bracket", label: "Bracket" },
  { href: "/teams", label: "Teams" },
  { href: "/track-record", label: "Track record" },
  { href: "/methodology", label: "Methodology" },
];

export default function NavBar() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  return (
    <header className="sticky top-0 z-40 border-b border-white/10 bg-base-900/70 backdrop-blur-xl">
      <nav className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-3">
        <Link href="/" className="group flex items-center gap-2.5">
          <span className="grid h-9 w-9 place-items-center rounded-xl bg-brand-gradient text-lg shadow-glow transition-transform group-hover:scale-105">
            ⚽
          </span>
          <span className="text-lg font-bold tracking-tight">
            WC<span className="gradient-text">26</span>
            <span className="ml-1.5 hidden text-sm font-medium text-slate-400 sm:inline">
              Predictor
            </span>
          </span>
        </Link>

        {/* Desktop links */}
        <div className="ml-auto hidden items-center gap-1 md:flex">
          {NAV.slice(1).map((n) => (
            <Link
              key={n.href}
              href={n.href}
              className={`nav-link ${isActive(n.href) ? "nav-link-active" : ""}`}
            >
              {n.label}
            </Link>
          ))}
        </div>

        {/* Mobile toggle */}
        <button
          onClick={() => setOpen((o) => !o)}
          aria-label="Menu"
          className="ml-auto grid h-9 w-9 place-items-center rounded-lg bg-white/10 md:hidden"
        >
          <div className="space-y-1">
            <span className={`block h-0.5 w-4 bg-white transition ${open ? "translate-y-1.5 rotate-45" : ""}`} />
            <span className={`block h-0.5 w-4 bg-white transition ${open ? "opacity-0" : ""}`} />
            <span className={`block h-0.5 w-4 bg-white transition ${open ? "-translate-y-1.5 -rotate-45" : ""}`} />
          </div>
        </button>
      </nav>

      {/* Mobile menu */}
      {open && (
        <div className="animate-fade-up border-t border-white/10 px-4 pb-4 pt-2 md:hidden">
          <div className="grid grid-cols-2 gap-1.5">
            {NAV.slice(1).map((n) => (
              <Link
                key={n.href}
                href={n.href}
                onClick={() => setOpen(false)}
                className={`rounded-lg px-3 py-2 text-sm ${
                  isActive(n.href) ? "bg-white/10 text-white" : "text-slate-300"
                }`}
              >
                {n.label}
              </Link>
            ))}
          </div>
        </div>
      )}
    </header>
  );
}
