"""Tests für die reinen Helfer des /spielplan Cogs."""

from cogs import spielplan


def _season():
    return {"id": 2, "name": "BIW Pokal 2026"}


class _User:
    display_name = "Tester"


def _groups():
    return [
        {
            "group": {"id": 1, "name": "A"},
            "teams": [{"id": 10, "name": "Alpha"}, {"id": 11, "name": "Beta"}],
            "matches": [
                {"home_team_name": "Alpha", "away_team_name": "Beta",
                 "home_goals": 2, "away_goals": 1, "status": "played", "matchday": 1},
                {"home_team_name": "Alpha", "away_team_name": "Beta",
                 "home_goals": None, "away_goals": None, "status": "scheduled", "matchday": 2},
            ],
        },
        {
            "group": {"id": 2, "name": "B"},
            "teams": [{"id": 12, "name": "Gamma"}],
            "matches": [
                {"home_team_name": "Gamma", "away_team_name": "Delta",
                 "home_goals": 0, "away_goals": 3, "status": "played", "matchday": 1},
            ],
        },
    ]


# --- format_score ---

def test_format_score_played():
    assert spielplan.format_score(2, 1, "played").strip() == "2 : 1"


def test_format_score_unplayed_has_no_digits():
    result = spielplan.format_score(None, None, "scheduled")
    assert ":" in result
    assert not any(c.isdigit() for c in result)


# --- build_group_options ---

def test_group_options_start_with_alle_gruppen():
    options = spielplan.build_group_options(_groups())
    assert options[0].value == "__all__"
    assert "Alle Gruppen" in options[0].label


def test_group_options_one_per_group_with_group_name_value():
    options = spielplan.build_group_options(_groups())
    # "Alle Gruppen" + eine Option pro Gruppe
    assert len(options) == 3
    values = [o.value for o in options]
    assert "A" in values
    assert "B" in values


# --- build_spielplan_embeds ---

def _all_fields(embeds):
    return [f for e in embeds for f in e.fields]


def test_spielplan_single_group_returns_single_embed_grouped_by_matchday():
    embeds = spielplan.build_spielplan_embeds(_season(), _groups(), "A", _User())
    assert len(embeds) == 1
    field_names = [f.name for f in embeds[0].fields]

    # Spieltag 1 und Spieltag 2 der Gruppe A
    assert any("Spieltag 1" in n for n in field_names)
    assert any("Spieltag 2" in n for n in field_names)
    # Nur Gruppe A -> Gruppe B Team taucht nicht auf
    joined = " ".join(f.value for f in embeds[0].fields)
    assert "Alpha" in joined
    assert "Gamma" not in joined


def test_spielplan_single_group_marks_unplayed_match():
    embeds = spielplan.build_spielplan_embeds(_season(), _groups(), "A", _User())
    joined = " ".join(f.value for f in _all_fields(embeds))
    assert "⏳" in joined


def test_spielplan_all_groups_includes_every_group():
    embeds = spielplan.build_spielplan_embeds(_season(), _groups(), "__all__", _User())
    joined_names = " ".join(f.name for f in _all_fields(embeds))
    assert "Gruppe A" in joined_names
    assert "Gruppe B" in joined_names
    joined_values = " ".join(f.value for f in _all_fields(embeds))
    assert "Alpha" in joined_values
    assert "Gamma" in joined_values


def test_spielplan_all_groups_paginates_when_over_25_fields():
    # 9 Gruppen x 3 Spieltage = 27 Felder -> muss ueber mehrere Embeds verteilt werden
    groups = []
    for i in range(9):
        name = chr(ord("A") + i)
        matches = [
            {"home_team_name": f"H{name}{md}", "away_team_name": f"G{name}{md}",
             "home_goals": 1, "away_goals": 0, "status": "played", "matchday": md}
            for md in (1, 2, 3)
        ]
        groups.append({"group": {"id": i, "name": name},
                       "teams": [], "matches": matches})

    embeds = spielplan.build_spielplan_embeds(_season(), groups, "__all__", _User())

    assert len(embeds) >= 2
    # Discord-Hardlimit: kein Embed darf mehr als 25 Felder haben
    for e in embeds:
        assert len(e.fields) <= 25
        # und der 6000-Zeichen-Gesamtrahmen darf nicht gesprengt werden
        total = len(e.title or "") + sum(len(f.name) + len(f.value) for f in e.fields)
        assert total <= 6000
    # alle 27 Felder sind erhalten geblieben
    assert len(_all_fields(embeds)) == 27
