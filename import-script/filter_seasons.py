#!/usr/bin/env python3
"""
JSON Season Filter
Filtert BIW JSON und behält nur bestimmte Saisons
"""

import json
import sys
from pathlib import Path


def filter_seasons(input_file: str, output_file: str, start_season: int = 12, end_season: int = 50):
    """Filter JSON to only include seasons between start_season and end_season"""
    
    print(f"📖 Reading {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    original_count = len(data['seasons'])
    original_matches = data['metadata']['total_matches']
    
    print(f"   Original: {original_count} seasons, {original_matches} matches")
    
    # Filter seasons
    filtered_seasons = [
        season for season in data['seasons']
        if start_season <= season['season'] <= end_season
    ]
    
    # Update data
    data['seasons'] = filtered_seasons
    
    # Recalculate total matches
    total_matches = sum(
        len(match)
        for season in filtered_seasons
        for group in season['groups']
        for match in group['matches']
    )
    
    data['metadata']['total_matches'] = total_matches
    data['metadata']['filtered'] = f"Seasons {start_season}-{end_season}"
    
    print(f"   Filtered: {len(filtered_seasons)} seasons, {total_matches} matches")
    print(f"   Removed: {original_count - len(filtered_seasons)} seasons, {original_matches - total_matches} matches")
    
    # Save filtered data
    print(f"💾 Saving to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Done! Saved {len(filtered_seasons)} seasons ({total_matches} matches)")
    
    return len(filtered_seasons), total_matches


def main():
    if len(sys.argv) < 2:
        print("Usage: python filter_seasons.py <input.json> [start_season] [end_season]")
        print("Example: python filter_seasons.py output/biw_data_xml_10-50.json 12 50")
        sys.exit(1)
    
    input_file = sys.argv[1]
    start_season = int(sys.argv[2]) if len(sys.argv) > 2 else 12
    end_season = int(sys.argv[3]) if len(sys.argv) > 3 else 50
    
    # Generate output filename
    input_path = Path(input_file)
    output_file = input_path.parent / f"{input_path.stem.replace('10-50', f'{start_season}-{end_season}')}{input_path.suffix}"
    
    print("=" * 60)
    print(f"FILTERING SEASONS {start_season}-{end_season}")
    print("=" * 60)
    print(f"Input:  {input_file}")
    print(f"Output: {output_file}")
    print()
    
    filter_seasons(input_file, str(output_file), start_season, end_season)
    
    print("=" * 60)


if __name__ == "__main__":
    main()
