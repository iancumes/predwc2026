import fs from "node:fs";
import path from "node:path";
import TeamClient from "./TeamClient";

// Enumerate every team code at build time for the static export.
export function generateStaticParams() {
  try {
    const file = path.join(process.cwd(), "public", "data", "teams.json");
    const { teams } = JSON.parse(fs.readFileSync(file, "utf-8"));
    return teams.map((t: { code: string }) => ({ code: t.code }));
  } catch {
    return [];
  }
}

export default async function TeamPage({ params }: { params: Promise<{ code: string }> }) {
  const { code } = await params;
  return <TeamClient code={code} />;
}
