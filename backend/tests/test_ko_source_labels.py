"""
Tests für die Platzhalter-Beschriftung offener KO-Slots.

Statt "Team null" liefert /ko-brackets für noch nicht feststehende Slots
ein Label wie "Sieger HF1" / "Sieger VF2" (Quelle = vorgelagertes Match,
Runde relativ zur Bracket-Tiefe, Nummer = position).
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app import models
from app.ko_bracket_generator import generate_rounds
from app.routers.ko import get_season_ko_brackets


def _make_db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _seed_8_team_meister(db):
    season = models.Season(name="Test", participant_count=8, status="active")
    db.add(season)
    db.flush()
    for i in range(1, 9):
        db.add(models.Team(id=i, name=f"T{i}"))
    bracket = models.KOBracket(season_id=season.id, bracket_type="meister", status="active")
    db.add(bracket)
    db.flush()
    generate_rounds(
        pairs=[(1, 2), (3, 4), (5, 6), (7, 8)],
        bracket_id=bracket.id,
        season_id=season.id,
        bracket_type="meister",
        db=db,
    )
    db.commit()
    return season.id


def test_final_slots_labelled_from_semifinals():
    db = _make_db()
    season_id = _seed_8_team_meister(db)

    rounds = get_season_ko_brackets(season_id, db=db)["brackets"]["meister"]["rounds"]
    final = [m for m in rounds["runde_3"] if not m["is_third_place"]][0]

    assert final["home_team"] is None and final["away_team"] is None
    assert final["home_source"] == "Sieger HF1"
    assert final["away_source"] == "Sieger HF2"


def test_semifinal_slots_labelled_from_quarterfinals():
    db = _make_db()
    season_id = _seed_8_team_meister(db)

    rounds = get_season_ko_brackets(season_id, db=db)["brackets"]["meister"]["rounds"]
    hf = rounds["runde_2"]

    sources = sorted(
        [m["home_source"] for m in hf] + [m["away_source"] for m in hf]
    )
    assert sources == ["Sieger VF1", "Sieger VF2", "Sieger VF3", "Sieger VF4"]


def test_third_place_slots_labelled_as_semifinal_losers():
    db = _make_db()
    season_id = _seed_8_team_meister(db)

    rounds = get_season_ko_brackets(season_id, db=db)["brackets"]["meister"]["rounds"]
    third = [m for m in rounds["runde_3"] if m["is_third_place"]][0]

    # Spiel um Platz 3 wird von den Halbfinal-VERLIERERN gefüllt.
    assert {third["home_source"], third["away_source"]} == {"Verlierer HF1", "Verlierer HF2"}


def test_seeded_first_round_has_no_source_labels():
    db = _make_db()
    season_id = _seed_8_team_meister(db)

    rounds = get_season_ko_brackets(season_id, db=db)["brackets"]["meister"]["rounds"]
    vf = rounds["runde_1"]

    assert all(m["home_team"] is not None and m["away_team"] is not None for m in vf)
    assert all(m["home_source"] is None and m["away_source"] is None for m in vf)
