// Country-flag helpers.
//
// We map each team's slug (and a few common name variants) to an ISO-3166
// region code understood by flagcdn.com, which serves crisp SVG/PNG flags for
// every nation here — including the UK home nations (gb-eng, gb-sct).  Using a
// real flag CDN renders identically on every OS (emoji flags don't on Windows).

export const TEAM_ISO: Record<string, string> = {
  argentina: "ar",
  spain: "es",
  france: "fr",
  england: "gb-eng",
  brazil: "br",
  portugal: "pt",
  colombia: "co",
  netherlands: "nl",
  belgium: "be",
  germany: "de",
  morocco: "ma",
  japan: "jp",
  switzerland: "ch",
  ecuador: "ec",
  mexico: "mx",
  norway: "no",
  senegal: "sn",
  croatia: "hr",
  canada: "ca",
  australia: "au",
  "ivory-coast": "ci",
  austria: "at",
  algeria: "dz",
  "united-states": "us",
  paraguay: "py",
  egypt: "eg",
  sweden: "se",
  "south-africa": "za",
  "south-korea": "kr",
  "czech-republic": "cz",
  "bosnia-and-herzegovina": "ba",
  qatar: "qa",
  haiti: "ht",
  scotland: "gb-sct",
  turkey: "tr",
  curacao: "cw",
  tunisia: "tn",
  iran: "ir",
  "new-zealand": "nz",
  "cape-verde": "cv",
  "saudi-arabia": "sa",
  uruguay: "uy",
  iraq: "iq",
  jordan: "jo",
  "dr-congo": "cd",
  uzbekistan: "uz",
  ghana: "gh",
  panama: "pa",
};

/** Normalise an arbitrary team name into the slug used across the data layer. */
export function teamSlug(name: string): string {
  return name
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

/** Resolve a flag image URL from either a slug or a display name. */
export function flagUrl(codeOrName: string, w = 40): string | null {
  if (!codeOrName) return null;
  const slug = TEAM_ISO[codeOrName] ? codeOrName : teamSlug(codeOrName);
  const iso = TEAM_ISO[slug];
  if (!iso) return null;
  return `https://flagcdn.com/w${w}/${iso}.png`;
}
