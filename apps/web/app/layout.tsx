import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "World Cup 2026 Predictor",
  description:
    "Analytical match & tournament predictions for the FIFA World Cup 2026. " +
    "Probabilities are estimates, not guarantees.",
};

const NAV = [
  { href: "/", label: "Home" },
  { href: "/matches", label: "Matches" },
  { href: "/groups", label: "Groups" },
  { href: "/bracket", label: "Bracket" },
  { href: "/teams", label: "Teams" },
  { href: "/track-record", label: "Track record" },
  { href: "/methodology", label: "Methodology" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="bg-pitch text-white">
          <nav className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-5 gap-y-2 px-4 py-3">
            <Link href="/" className="mr-2 text-lg font-bold tracking-tight">
              ⚽ WC2026 <span className="text-accent-soft">Predictor</span>
            </Link>
            <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
              {NAV.slice(1).map((n) => (
                <Link key={n.href} href={n.href} className="opacity-90 hover:opacity-100 hover:underline">
                  {n.label}
                </Link>
              ))}
            </div>
          </nav>
        </header>
        <main className="mx-auto max-w-6xl px-4 py-6">{children}</main>
        <footer className="mt-12 border-t border-slate-200 bg-white">
          <div className="mx-auto max-w-6xl px-4 py-6 text-xs text-slate-500">
            <p className="font-medium text-slate-600">
              This platform is analytical and informational only.
            </p>
            <p>
              Predicted probabilities are model estimates with uncertainty — not
              guarantees, betting advice, or a promise of any outcome. Data:
              martj42/international_results (CC0). Built with Elo, Poisson,
              Dixon–Coles, gradient boosting and a calibrated ensemble.
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
