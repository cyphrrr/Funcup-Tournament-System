#!/usr/bin/env python3
"""
WordPress XML to JSON Converter für BIW Pokal
Konvertiert WordPress/SportsPress XML Export in das gleiche Format wie der Scraper
"""

import xml.etree.ElementTree as ET
import json
import re
import logging
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
import html

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('xml_converter.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class Match:
    """Single match data"""
    date: str
    time: str
    home_team: str
    away_team: str
    home_goals: Optional[int]
    away_goals: Optional[int]
    matchday: int
    status: str


@dataclass
class TeamStats:
    """Team statistics for table calculation"""
    team_name: str
    played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0
    goal_diff: int = 0
    points: int = 0
    
    def calculate_derived(self):
        """Calculate goal difference and points"""
        self.goal_diff = self.goals_for - self.goals_against
        self.points = (self.wins * 3) + self.draws


class WordPressXMLConverter:
    """Convert WordPress XML export to BIW JSON format"""
    
    # XML namespaces
    NS = {
        'wp': 'http://wordpress.org/export/1.2/',
        'content': 'http://purl.org/rss/1.0/modules/content/',
        'excerpt': 'http://wordpress.org/export/1.2/excerpt/',
        'dc': 'http://purl.org/dc/elements/1.1/'
    }
    
    def __init__(self, xml_file: str):
        self.xml_file = xml_file
        self.team_id_to_name: Dict[str, str] = {}
        self.errors = []
        self.stats = {
            'total_items': 0,
            'sp_events': 0,
            'sp_teams': 0,
            'matches_parsed': 0,
            'errors': 0
        }
        
    def parse_php_serialized_result(self, serialized: str) -> Tuple[Optional[int], Optional[int], str]:
        """
        Parse PHP serialized sp_results string
        Example: a:3:{i:0;s:0:"";i:81;a:2:{s:5:"goals";s:1:"2";...}i:2986;a:2:{s:5:"goals";s:1:"1";...}}
        """
        try:
            # Extract team IDs and their goals
            # Pattern: i:TEAM_ID;a:2:{s:5:"goals";s:1:"GOALS";
            pattern = r'i:(\d+);a:2:\{s:5:"goals";s:\d+:"(\d+)"'
            matches = re.findall(pattern, serialized)
            
            if len(matches) >= 2:
                team1_id, team1_goals = matches[0]
                team2_id, team2_goals = matches[1]
                
                return int(team1_goals), int(team2_goals), "played"
            
            return None, None, "scheduled"
            
        except Exception as e:
            logger.debug(f"Failed to parse result: {e}")
            return None, None, "scheduled"
    
    def extract_season_number(self, season_str: str) -> Optional[int]:
        """Extract season number from string like 'Saison 46' or 'saison-46'"""
        match = re.search(r'(\d+)', season_str)
        if match:
            return int(match.group(1))
        return None
    
    def extract_group_letter(self, league_str: str) -> Optional[str]:
        """Extract group letter from string like 'BIW-46-A' or 'biw-46-a'"""
        match = re.search(r'-([A-Pa-p])$', league_str, re.IGNORECASE)
        if match:
            return match.group(1).upper()
        return None
    
    def parse_matchday(self, day_str: str) -> int:
        """Parse matchday from string like 'SP2' or 'Spieltag 2'"""
        match = re.search(r'(\d+)', day_str)
        if match:
            return int(match.group(1))
        return 1
    
    def parse_item(self, item: ET.Element) -> Optional[Dict]:
        """Parse a single <item> element"""
        self.stats['total_items'] += 1
        
        # Check if it's an sp_event (match)
        post_type = item.find('.//wp:post_type', self.NS)
        if post_type is None or post_type.text != 'sp_event':
            return None
        
        self.stats['sp_events'] += 1
        
        try:
            # Extract basic info
            title = item.find('title').text or ""
            post_date = item.find('.//wp:post_date', self.NS)
            
            # Extract season and league (group)
            season_elem = item.find('.//category[@domain="sp_season"]')
            league_elem = item.find('.//category[@domain="sp_league"]')
            
            if season_elem is None or league_elem is None:
                logger.warning(f"Missing season or league for match: {title}")
                return None
            
            season_str = season_elem.text
            league_str = league_elem.text
            
            season_num = self.extract_season_number(season_str)
            group_letter = self.extract_group_letter(league_str)
            
            if not season_num or not group_letter:
                logger.warning(f"Could not parse season/group: {season_str}/{league_str}")
                return None
            
            # Extract team IDs
            team_metas = item.findall('.//wp:postmeta[wp:meta_key="sp_team"]', self.NS)
            if len(team_metas) < 2:
                logger.warning(f"Missing teams for match: {title}")
                return None
            
            team1_id = team_metas[0].find('wp:meta_value', self.NS).text
            team2_id = team_metas[1].find('wp:meta_key', self.NS).text
            team2_id = team_metas[1].find('wp:meta_value', self.NS).text
            
            # Extract result
            result_meta = item.find('.//wp:postmeta[wp:meta_key="sp_results"]/wp:meta_value', self.NS)
            home_goals, away_goals, status = None, None, "scheduled"
            
            if result_meta is not None and result_meta.text:
                serialized_result = html.unescape(result_meta.text)
                home_goals, away_goals, status = self.parse_php_serialized_result(serialized_result)
            
            # Extract matchday
            day_meta = item.find('.//wp:postmeta[wp:meta_key="sp_day"]/wp:meta_value', self.NS)
            matchday = 1
            if day_meta is not None and day_meta.text:
                matchday = self.parse_matchday(day_meta.text)
            
            # Parse date/time
            date_str = ""
            time_str = "10:00"
            if post_date is not None and post_date.text:
                # Format: 2025-07-30 10:00:00
                dt_parts = post_date.text.split()
                if len(dt_parts) >= 2:
                    date_str = dt_parts[0]
                    time_str = dt_parts[1][:5]  # HH:MM
            
            # Extract team names from title
            # Title format: "Team A vs Team B"
            teams = title.split(' vs ')
            if len(teams) != 2:
                logger.warning(f"Could not parse team names from title: {title}")
                return None
            
            home_team = teams[0].strip()
            away_team = teams[1].strip()
            
            # Store team ID -> name mapping
            self.team_id_to_name[team1_id] = home_team
            self.team_id_to_name[team2_id] = away_team
            
            return {
                'season': season_num,
                'group': group_letter,
                'date': date_str,
                'time': time_str,
                'home_team': home_team,
                'away_team': away_team,
                'home_goals': home_goals,
                'away_goals': away_goals,
                'matchday': matchday,
                'status': status
            }
            
        except Exception as e:
            error = f"Error parsing item: {str(e)}"
            logger.error(error)
            self.errors.append(error)
            self.stats['errors'] += 1
            return None
    
    def calculate_table(self, matches: List[Dict]) -> List[TeamStats]:
        """Calculate standings table from matches"""
        teams_stats = defaultdict(lambda: TeamStats(team_name=""))
        
        for match in matches:
            if match['status'] != 'played' or match['home_goals'] is None:
                continue
            
            home_team = match['home_team']
            away_team = match['away_team']
            
            # Initialize team names
            if not teams_stats[home_team].team_name:
                teams_stats[home_team].team_name = home_team
            if not teams_stats[away_team].team_name:
                teams_stats[away_team].team_name = away_team
            
            # Update stats
            home_stats = teams_stats[home_team]
            away_stats = teams_stats[away_team]
            
            home_stats.played += 1
            away_stats.played += 1
            
            home_stats.goals_for += match['home_goals']
            home_stats.goals_against += match['away_goals']
            away_stats.goals_for += match['away_goals']
            away_stats.goals_against += match['home_goals']
            
            # Determine result
            if match['home_goals'] > match['away_goals']:
                home_stats.wins += 1
                away_stats.losses += 1
            elif match['home_goals'] < match['away_goals']:
                away_stats.wins += 1
                home_stats.losses += 1
            else:
                home_stats.draws += 1
                away_stats.draws += 1
        
        # Calculate derived stats and sort
        table = list(teams_stats.values())
        for team in table:
            team.calculate_derived()
        
        # Sort by: Points DESC, Goal Diff DESC, Goals For DESC
        table.sort(key=lambda t: (-t.points, -t.goal_diff, -t.goals_for))
        
        return table
    
    def convert(self) -> Dict:
        """Convert XML to JSON format"""
        logger.info(f"Loading XML file: {self.xml_file}")
        
        try:
            tree = ET.parse(self.xml_file)
            root = tree.getroot()
        except Exception as e:
            logger.error(f"Failed to parse XML: {e}")
            return {}
        
        # Find all items
        items = root.findall('.//item')
        logger.info(f"Found {len(items)} items in XML")
        
        # Parse all matches
        all_matches = []
        for item in items:
            match_data = self.parse_item(item)
            if match_data:
                all_matches.append(match_data)
                self.stats['matches_parsed'] += 1
        
        logger.info(f"Parsed {len(all_matches)} matches")
        
        # Group by season and group
        season_groups: Dict[int, Dict[str, List[Dict]]] = defaultdict(lambda: defaultdict(list))
        
        for match in all_matches:
            season = match.pop('season')
            group = match.pop('group')
            season_groups[season][group].append(match)
        
        # Build final structure
        result = {
            'metadata': {
                'source': 'wordpress_xml',
                'converted_at': None,  # Will be set when saving
                'total_matches': len(all_matches),
                'total_errors': len(self.errors)
            },
            'seasons': []
        }
        
        # Sort seasons
        for season_num in sorted(season_groups.keys()):
            groups = season_groups[season_num]
            
            season_data = {
                'season': season_num,
                'groups': []
            }
            
            # Sort groups alphabetically
            for group_letter in sorted(groups.keys()):
                matches = groups[group_letter]
                table = self.calculate_table(matches)
                
                # Convert Match dicts to proper format
                formatted_matches = []
                for m in matches:
                    formatted_matches.append({
                        'date': m['date'],
                        'time': m['time'],
                        'home_team': m['home_team'],
                        'away_team': m['away_team'],
                        'home_goals': m['home_goals'],
                        'away_goals': m['away_goals'],
                        'matchday': m['matchday'],
                        'status': m['status']
                    })
                
                group_data = {
                    'group': group_letter,
                    'matches': formatted_matches,
                    'table': [asdict(t) for t in table],
                    'errors': []
                }
                
                season_data['groups'].append(group_data)
            
            result['seasons'].append(season_data)
        
        return result
    
    def save_results(self, data: Dict, output_dir: str = 'output'):
        """Save results to JSON files"""
        from datetime import datetime
        
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Add timestamp
        data['metadata']['converted_at'] = datetime.now().isoformat()
        
        # Determine season range
        seasons = [s['season'] for s in data['seasons']]
        season_range = f"{min(seasons)}-{max(seasons)}" if seasons else "empty"
        
        # Save main data
        data_file = output_path / f'biw_data_xml_{season_range}.json'
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"✓ Data saved to {data_file}")
        
        # Save error log
        if self.errors:
            error_file = output_path / f'errors_xml_{season_range}.json'
            with open(error_file, 'w', encoding='utf-8') as f:
                json.dump(self.errors, f, indent=2, ensure_ascii=False)
            logger.warning(f"✓ Error log saved to {error_file} ({len(self.errors)} errors)")
        
        # Generate summary
        summary = self.generate_summary(data)
        summary_file = output_path / f'summary_xml_{season_range}.txt'
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(summary)
        logger.info(f"✓ Summary saved to {summary_file}")
    
    def generate_summary(self, data: Dict) -> str:
        """Generate human-readable summary"""
        lines = [
            "=" * 60,
            "BIW POKAL XML CONVERSION SUMMARY",
            "=" * 60,
            f"Converted at: {data['metadata']['converted_at']}",
            f"Total matches: {data['metadata']['total_matches']}",
            "",
            "XML PARSING STATS:",
            "-" * 60,
            f"Total items scanned: {self.stats['total_items']}",
            f"SP Events found: {self.stats['sp_events']}",
            f"Matches parsed: {self.stats['matches_parsed']}",
            f"Parse errors: {self.stats['errors']}",
            "",
            "SEASON BREAKDOWN:",
            "-" * 60
        ]
        
        total_groups = 0
        total_teams = set()
        
        for season_data in data['seasons']:
            season = season_data['season']
            groups = season_data['groups']
            season_matches = sum(len(g['matches']) for g in groups)
            season_teams = set()
            
            for group in groups:
                for match in group['matches']:
                    season_teams.add(match['home_team'])
                    season_teams.add(match['away_team'])
            
            lines.append(f"Season {season}: {len(groups)} groups, {season_matches} matches, {len(season_teams)} teams")
            
            total_groups += len(groups)
            total_teams.update(season_teams)
        
        lines.extend([
            "",
            "-" * 60,
            f"TOTALS:",
            f"  Seasons: {len(data['seasons'])}",
            f"  Groups: {total_groups}",
            f"  Matches: {data['metadata']['total_matches']}",
            f"  Unique teams: {len(total_teams)}",
            f"  Errors: {data['metadata']['total_errors']}",
            "=" * 60
        ])
        
        return '\n'.join(lines)


def main():
    """Main execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Convert WordPress XML to BIW JSON')
    parser.add_argument('xml_file', help='Path to WordPress XML export file')
    parser.add_argument('--output-dir', default='output',
                       help='Output directory (default: output)')
    
    args = parser.parse_args()
    
    # Verify file exists
    xml_path = Path(args.xml_file)
    if not xml_path.exists():
        logger.error(f"XML file not found: {args.xml_file}")
        return
    
    converter = WordPressXMLConverter(args.xml_file)
    
    try:
        logger.info("=" * 60)
        logger.info("STARTING XML CONVERSION")
        logger.info("=" * 60)
        
        data = converter.convert()
        
        if data and data['seasons']:
            converter.save_results(data, args.output_dir)
            
            logger.info("")
            logger.info("=" * 60)
            logger.info("CONVERSION COMPLETED SUCCESSFULLY")
            logger.info(f"Seasons: {len(data['seasons'])}")
            logger.info(f"Matches: {data['metadata']['total_matches']}")
            logger.info(f"Errors: {len(converter.errors)}")
            logger.info("=" * 60)
        else:
            logger.error("No data extracted from XML")
        
    except KeyboardInterrupt:
        logger.warning("Conversion interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)


if __name__ == "__main__":
    main()
