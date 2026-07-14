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


# --- build_spielplan_embed ---

def test_spielplan_single_group_groups_matches_by_matchday():
    embed = spielplan.build_spielplan_embed(_season(), _groups(), "A", _User())
    field_names = [f.name for f in embed.fields]

    # Spieltag 1 und Spieltag 2 der Gruppe A
    assert any("Spieltag 1" in n for n in field_names)
    assert any("Spieltag 2" in n for n in field_names)
    # Nur Gruppe A -> Gruppe B Team taucht nicht auf
    joined = " ".join(f.value for f in embed.fields)
    assert "Alpha" in joined
    assert "Gamma" not in joined


def test_spielplan_single_group_marks_unplayed_match():
    embed = spielplan.build_spielplan_embed(_season(), _groups(), "A", _User())
    joined = " ".join(f.value for f in embed.fields)
    assert "⏳" in joined


def test_spielplan_all_groups_includes_every_group():
    embed = spielplan.build_spielplan_embed(_season(), _groups(), "__all__", _User())
    field_names = [f.name for f in embed.fields]
    joined_names = " ".join(field_names)
    assert "Gruppe A" in joined_names
    assert "Gruppe B" in joined_names
    joined_values = " ".join(f.value for f in embed.fields)
    assert "Alpha" in joined_values
    assert "Gamma" in joined_values
