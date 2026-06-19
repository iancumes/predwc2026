import fs from "node:fs";
import path from "node:path";
import MatchClient from "./MatchClient";

// Enumerate every match id at build time so the static export pre-renders one
// page per fixture (required when next.config output === "export").
export function generateStaticParams() {
  try {
    const file = path.join(process.cwd(), "public", "data", "matches.json");
    const { matches } = JSON.parse(fs.readFileSync(file, "utf-8"));
    return matches.map((m: { match_id: string }) => ({ id: m.match_id }));
  } catch {
    return [];
  }
}

export default async function MatchDetail({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <MatchClient id={id} />;
}
