"""Tests für die reinen Helfer des /gruppen Cogs."""

from cogs import gruppen


# --- resolve_season ---

def test_resolve_season_prefers_active_over_planned():
    seasons = [
        {"id": 1, "name": "Alt", "status": "planned"},
        {"id": 2, "name": "Aktuell", "status": "active"},
    ]
    assert gruppen.resolve_season(seasons)["id"] == 2


def test_resolve_season_falls_back_to_planned():
    seasons = [
        {"id": 1, "name": "Archiv", "status": "archived"},
        {"id": 3, "name": "Geplant", "status": "planned"},
    ]
    assert gruppen.resolve_season(seasons)["id"] == 3


def test_resolve_season_returns_none_when_only_archived():
    seasons = [{"id": 1, "name": "Archiv", "status": "archived"}]
    assert gruppen.resolve_season(seasons) is None


# --- build_gruppen_embed ---

def _season():
    return {"id": 2, "name": "BIW Pokal 2026"}


class _User:
    display_name = "Tester"


def test_gruppen_embed_has_one_field_per_group_with_team_names():
    groups_data = [
        {
            "group": {"id": 1, "name": "A"},
            "teams": [{"id": 10, "name": "Alpha"}, {"id": 11, "name": "Beta"}],
            "matches": [],
        },
        {
            "group": {"id": 2, "name": "B"},
            "teams": [{"id": 12, "name": "Gamma"}],
            "matches": [],
        },
    ]
    embed = gruppen.build_gruppen_embed(_season(), groups_data, _User())

    assert len(embed.fields) == 2
    assert "Gruppe A" in embed.fields[0].name
    assert "Alpha" in embed.fields[0].value
    assert "Beta" in embed.fields[0].value
    assert "Gamma" in embed.fields[1].value


def test_gruppen_embed_hints_when_no_teams_drawn_yet():
    groups_data = [
        {"group": {"id": 1, "name": "A"}, "teams": [], "matches": []},
        {"group": {"id": 2, "name": "B"}, "teams": [], "matches": []},
    ]
    embed = gruppen.build_gruppen_embed(_season(), groups_data, _User())

    assert "Auslosung noch nicht erfolgt" in (embed.description or "")
