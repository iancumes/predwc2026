import type { Metadata } from "next";
import "./globals.css";
import NavBar from "./components/NavBar";
import { TeamPeekProvider } from "./components/TeamModal";

export const metadata: Metadata = {
  title: "World Cup 2026 Predictor",
  description:
    "Analytical match & tournament predictions for the FIFA World Cup 2026. " +
    "Probabilities are estimates, not guarantees.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        {/* Distinctive type pairing loaded at runtime (no build-time fetch). */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          href="https://fonts.googleapis.com/css2?family=Sora:wght@500;600;700;800&family=Inter:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
        {/* eslint-disable-next-line react/no-unknown-property */}
        <style>{`:root{--font-display:'Sora';--font-sans:'Inter';}`}</style>
      </head>
      <body>
        <TeamPeekProvider>
          <NavBar />
          <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
          <footer className="mt-16 border-t border-white/10 bg-base-900/60">
            <div className="mx-auto max-w-6xl px-4 py-8 text-xs text-slate-400">
              <div className="flex items-center gap-2 text-sm font-semibold text-slate-200">
                <span className="grid h-6 w-6 place-items-center rounded-md bg-brand-gradient text-xs">
                  ⚽
                </span>
                WC26 Predictor
              </div>
              <p className="mt-2 max-w-3xl">
                This platform is analytical and informational only. Predicted
                probabilities are model estimates with uncertainty — not
                guarantees, betting advice, or a promise of any outcome.
              </p>
              <p className="mt-2 text-slate-500">
                Data: martj42/international_results (CC0). Built with Elo,
                Poisson, Dixon–Coles, gradient boosting and a calibrated
                ensemble. Flags by flagcdn.com. Auto-refreshed twice daily
                (08:00 &amp; 23:59 Guatemala time).
              </p>
            </div>
          </footer>
        </TeamPeekProvider>
      </body>
    </html>
  );
}
