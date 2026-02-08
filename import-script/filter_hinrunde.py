#!/usr/bin/env python3
"""
Filtert die Import-Daten: Behält nur die Hinrunde (erste Hälfte der Matches)
"""

import json
import sys

def filter_to_hinrunde(input_file, output_file):
    """Filtert JSON-Daten: Nur Hinrunde behalten"""

    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    filtered_seasons = []

    for season in data['seasons']:
        season_copy = season.copy()
        season_copy['groups'] = []

        for group in season['groups']:
            group_copy = group.copy()

            # Anzahl der Matches in der Hinrunde berechnen
            # Bei n Teams: n*(n-1)/2 Spiele
            all_matches = group['matches']

            if len(all_matches) == 0:
                group_copy['matches'] = []
            else:
                # Teams in dieser Gruppe zählen
                teams = set()
                for match in all_matches:
                    teams.add(match['home_team'])
                    teams.add(match['away_team'])

                team_count = len(teams)

                # Hinrunde: n*(n-1)/2 Spiele
                if team_count > 0:
                    hinrunde_count = (team_count * (team_count - 1)) // 2
                else:
                    hinrunde_count = 0

                # Nur die ersten hinrunde_count Matches behalten
                hinrunde_matches = all_matches[:hinrunde_count]

                print(f"  Saison {season['season']}, Gruppe {group['group']}: {len(all_matches)} Matches → {len(hinrunde_matches)} Matches (Hinrunde)")

                group_copy['matches'] = hinrunde_matches

            season_copy['groups'].append(group_copy)

        filtered_seasons.append(season_copy)

    # Neue Datenstruktur erstellen
    filtered_data = {
        'metadata': data['metadata'].copy(),
        'seasons': filtered_seasons
    }

    # Metadata aktualisieren
    filtered_data['metadata']['filtered'] = 'Seasons 12-50, nur Hinrunde'

    # Matches zählen
    total_matches = sum(len(m) for s in filtered_seasons for g in s['groups'] for m in [g['matches']])
    print(f"\n✓ Gesamt: {total_matches} Matches (nur Hinrunde)")

    # Speichern
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(filtered_data, f, indent=2, ensure_ascii=False)

    print(f"✓ Gespeichert: {output_file}")

if __name__ == "__main__":
    input_file = "output/biw_data_xml_12-50.json"
    output_file = "output/biw_data_xml_12-50_hinrunde.json"

    print(f"Filtere Hinrunde: {input_file} → {output_file}")
    print()

    filter_to_hinrunde(input_file, output_file)
