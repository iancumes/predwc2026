from wc2026.teams import canonical_name, confederation, team_code


def test_alias_normalisation():
    assert canonical_name("USA") == "United States"
    assert canonical_name("United States") == "United States"
    assert canonical_name("Korea Republic") == "South Korea"
    assert canonical_name("Congo DR") == "DR Congo"
    assert canonical_name("Côte d'Ivoire") == "Ivory Coast"
    assert canonical_name("Cote d'Ivoire") == "Ivory Coast"
    assert canonical_name("Czechia") == "Czech Republic"
    assert canonical_name("Curacao") == "Curaçao"
    assert canonical_name("Türkiye") == "Turkey"


def test_team_code_is_url_safe_and_stable():
    assert team_code("United States") == "united-states"
    assert team_code("Côte d'Ivoire") == team_code("Ivory Coast")
    assert team_code("Curaçao") == "curacao"


def test_confederations():
    assert confederation("Brazil") == "CONMEBOL"
    assert confederation("Spain") == "UEFA"
    assert confederation("USA") == "CONCACAF"
    assert confederation("Morocco") == "CAF"
    assert confederation("Japan") == "AFC"
    assert confederation("New Zealand") == "OFC"
