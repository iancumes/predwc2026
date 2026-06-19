"""Team-name normalisation, stable codes, and confederation mapping.

The canonical names follow the `martj42/international_results` dataset (our
primary source). The alias table maps the many spellings used by other sources
(FIFA, Wikipedia, betting feeds, 3-letter codes) onto those canonical names.
Matching is accent- and case-insensitive; the returned canonical name keeps
its proper diacritics.
"""
from __future__ import annotations

import unicodedata

# ---------------------------------------------------------------------------
# Alias table.  key = any spelling (will be normalised), value = canonical name.
# Only non-trivial aliases need listing; an exact canonical name always maps to
# itself.
# ---------------------------------------------------------------------------
_ALIASES_RAW: dict[str, str] = {
    # United States
    "usa": "United States",
    "united states of america": "United States",
    "us": "United States",
    # Korea
    "korea republic": "South Korea",
    "republic of korea": "South Korea",
    "kor": "South Korea",
    "korea dpr": "North Korea",
    "dpr korea": "North Korea",
    # DR Congo
    "dr congo": "DR Congo",
    "congo dr": "DR Congo",
    "democratic republic of the congo": "DR Congo",
    "congo kinshasa": "DR Congo",
    "congo-kinshasa": "DR Congo",
    "congo brazzaville": "Congo",
    "republic of the congo": "Congo",
    # Cote d'Ivoire
    "cote d'ivoire": "Ivory Coast",
    "cote divoire": "Ivory Coast",
    "ivory coast": "Ivory Coast",
    # Czechia
    "czechia": "Czech Republic",
    "czech republic": "Czech Republic",
    # Curacao
    "curacao": "Curaçao",
    # Cape Verde
    "cabo verde": "Cape Verde",
    # Iran
    "ir iran": "Iran",
    "iran": "Iran",
    # China
    "china": "China PR",
    "china pr": "China PR",
    # Others commonly divergent
    "turkiye": "Turkey",
    "türkiye": "Turkey",
    "bosnia": "Bosnia and Herzegovina",
    "bosnia-herzegovina": "Bosnia and Herzegovina",
    "north macedonia": "North Macedonia",
    "fyr macedonia": "North Macedonia",
    "macedonia": "North Macedonia",
    "republic of ireland": "Republic of Ireland",
    "ireland": "Republic of Ireland",
    "uae": "United Arab Emirates",
    "ksa": "Saudi Arabia",
    "england": "England",
    "the gambia": "Gambia",
    "saint kitts and nevis": "Saint Kitts and Nevis",
    "st kitts and nevis": "Saint Kitts and Nevis",
    "cape verde islands": "Cape Verde",
    "swaziland": "Eswatini",
    "kyrgyz republic": "Kyrgyzstan",
    "chinese taipei": "Taiwan",
}


def _norm_key(name: str) -> str:
    """Accent- and case-insensitive lookup key."""
    s = unicodedata.normalize("NFKD", name)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().strip()
    s = s.replace(".", "").replace("’", "'")
    while "  " in s:
        s = s.replace("  ", " ")
    return s


# Pre-normalise alias keys once.
_ALIASES: dict[str, str] = {_norm_key(k): v for k, v in _ALIASES_RAW.items()}
# Allow every canonical value to resolve to itself too.
for _v in set(_ALIASES_RAW.values()):
    _ALIASES.setdefault(_norm_key(_v), _v)


def canonical_name(name: str) -> str:
    """Return the canonical team name for any known spelling.

    Unknown names are returned trimmed but otherwise untouched (so the data
    layer can flag them rather than silently dropping a team).
    """
    if name is None:
        return ""
    key = _norm_key(str(name))
    return _ALIASES.get(key, str(name).strip())


def team_code(name: str) -> str:
    """Deterministic short code for API routes/URLs (slugified canonical name)."""
    canon = canonical_name(name)
    s = unicodedata.normalize("NFKD", canon)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    out = []
    for ch in s:
        if ch.isalnum():
            out.append(ch)
        elif ch in (" ", "-", "'"):
            out.append("-")
    code = "".join(out)
    while "--" in code:
        code = code.replace("--", "-")
    return code.strip("-")


# ---------------------------------------------------------------------------
# Confederations.  Covers the 48 WC-2026 finalists plus the major nations that
# appear in qualification; everything else resolves to "UNK".
# ---------------------------------------------------------------------------
_CONF: dict[str, list[str]] = {
    "UEFA": [
        "Spain", "France", "England", "Portugal", "Netherlands", "Belgium",
        "Italy", "Germany", "Croatia", "Switzerland", "Denmark", "Austria",
        "Ukraine", "Sweden", "Poland", "Serbia", "Turkey", "Norway", "Scotland",
        "Czech Republic", "Hungary", "Wales", "Greece", "Romania", "Slovakia",
        "Slovenia", "Republic of Ireland", "Iceland", "Bosnia and Herzegovina",
        "North Macedonia", "Albania", "Finland", "Russia", "Montenegro",
        "Georgia", "Kosovo",
    ],
    "CONMEBOL": [
        "Brazil", "Argentina", "Uruguay", "Colombia", "Ecuador", "Paraguay",
        "Chile", "Peru", "Venezuela", "Bolivia",
    ],
    "CONCACAF": [
        "United States", "Mexico", "Canada", "Costa Rica", "Panama", "Jamaica",
        "Honduras", "Haiti", "El Salvador", "Curaçao", "Trinidad and Tobago",
        "Guatemala", "Suriname",
    ],
    "CAF": [
        "Morocco", "Senegal", "Egypt", "Nigeria", "Algeria", "Tunisia", "Ghana",
        "Cameroon", "Ivory Coast", "Mali", "South Africa", "DR Congo", "Cape Verde",
        "Burkina Faso", "Angola", "Zambia", "Gabon", "Guinea", "Benin", "Uganda",
    ],
    "AFC": [
        "Japan", "South Korea", "Iran", "Australia", "Saudi Arabia", "Qatar",
        "Iraq", "United Arab Emirates", "Uzbekistan", "Jordan", "Oman", "Bahrain",
        "China PR", "Vietnam", "Thailand", "Indonesia",
    ],
    "OFC": [
        "New Zealand", "Fiji", "New Caledonia", "Solomon Islands", "Tahiti",
        "Papua New Guinea", "Vanuatu",
    ],
}

CONFEDERATION: dict[str, str] = {}
for _conf, _teams in _CONF.items():
    for _t in _teams:
        CONFEDERATION[_t] = _conf


def confederation(name: str) -> str:
    return CONFEDERATION.get(canonical_name(name), "UNK")


# Hosts of the 2026 tournament (automatic qualifiers, get host advantage).
HOSTS_2026: set[str] = {"United States", "Mexico", "Canada"}
