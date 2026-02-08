#!/usr/bin/env python3
"""
BIW Pokal Gruppenphase Scraper
Extrahiert Matches aus HTML-Kalendern (Saison 12-50) und berechnet Tabellen
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
import json
import time
import logging
from pathlib import Path

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('biw_scraper.log'),
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
    status: str  # 'played' or 'scheduled'
    

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


@dataclass
class GroupData:
    """Complete group data"""
    season: int
    group: str
    matches: List[Match]
    table: List[TeamStats]
    errors: List[str]


class BIWScaper:
    """Scraper for BIW Pokal group stage data"""
    
    BASE_URL = "https://biw-pokal.de/calendar/biw-{season}-{group}/"
    GROUPS = list("abcdefghijklmnop")  # a-p
    
    def __init__(self, start_season: int = 12, end_season: int = 50):
        self.start_season = start_season
        self.end_season = end_season
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; BIW-Scraper/1.0)'
        })
        self.error_log = []
        
    def fetch_calendar(self, season: int, group: str) -> Optional[str]:
        """Fetch calendar HTML for a specific season and group"""
        url = self.BASE_URL.format(season=season, group=group)
        
        try:
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 404:
                logger.debug(f"Group {group.upper()} does not exist for Season {season}")
                return None
                
            response.raise_for_status()
            return response.text
            
        except requests.RequestException as e:
            error_msg = f"Failed to fetch S{season}-{group.upper()}: {str(e)}"
            logger.error(error_msg)
            self.error_log.append({
                'season': season,
                'group': group,
                'error': error_msg,
                'type': 'network_error'
            })
            return None
    
    def parse_matches(self, html: str, season: int, group: str) -> Tuple[List[Match], List[str]]:
        """Parse matches from HTML table"""
        matches = []
        errors = []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find the matches table
            table = soup.find('table')
            if not table:
                error = f"No match table found for S{season}-{group.upper()}"
                logger.warning(error)
                errors.append(error)
                return matches, errors
            
            rows = table.find_all('tr')[1:]  # Skip header
            
            for idx, row in enumerate(rows, 1):
                try:
                    cols = row.find_all('td')
                    if len(cols) < 5:
                        continue
                    
                    # Extract date/time
                    date_str = cols[0].get_text(strip=True)
                    date_parts = date_str.split()
                    match_date = ' '.join(date_parts[:-1]) if len(date_parts) > 1 else date_str
                    match_time = date_parts[-1] if len(date_parts) > 1 else '10:00'
                    
                    # Extract teams
                    home_team = cols[1].get_text(strip=True)
                    away_team = cols[3].get_text(strip=True)
                    
                    # Extract result
                    result_text = cols[2].get_text(strip=True)
                    home_goals, away_goals, status = self.parse_result(result_text)
                    
                    # Extract matchday
                    matchday_text = cols[5].get_text(strip=True) if len(cols) > 5 else '1'
                    matchday = self.extract_matchday(matchday_text)
                    
                    match = Match(
                        date=match_date,
                        time=match_time,
                        home_team=home_team,
                        away_team=away_team,
                        home_goals=home_goals,
                        away_goals=away_goals,
                        matchday=matchday,
                        status=status
                    )
                    matches.append(match)
                    
                except Exception as e:
                    error = f"S{season}-{group.upper()} Row {idx}: Parse error - {str(e)}"
                    logger.warning(error)
                    errors.append(error)
                    continue
            
            logger.info(f"S{season}-{group.upper()}: Parsed {len(matches)} matches")
            
        except Exception as e:
            error = f"S{season}-{group.upper()}: Fatal parse error - {str(e)}"
            logger.error(error)
            errors.append(error)
        
        return matches, errors
    
    def parse_result(self, result_text: str) -> Tuple[Optional[int], Optional[int], str]:
        """Parse match result string"""
        result_text = result_text.strip()
        
        # Check for time format (scheduled match)
        if ':' in result_text and len(result_text) <= 8:
            return None, None, 'scheduled'
        
        # Parse score
        if '-' in result_text:
            try:
                parts = result_text.split('-')
                home_goals = int(parts[0].strip())
                away_goals = int(parts[1].strip())
                return home_goals, away_goals, 'played'
            except ValueError:
                return None, None, 'scheduled'
        
        return None, None, 'scheduled'
    
    def extract_matchday(self, matchday_text: str) -> int:
        """Extract matchday number from text"""
        try:
            # Try to extract number from text like "W1", "Spieltag 1", etc.
            import re
            match = re.search(r'\d+', matchday_text)
            if match:
                return int(match.group())
            return 1
        except:
            return 1
    
    def calculate_table(self, matches: List[Match]) -> List[TeamStats]:
        """Calculate standings table from matches"""
        teams_stats = defaultdict(lambda: TeamStats(team_name=""))
        
        for match in matches:
            if match.status != 'played' or match.home_goals is None:
                continue
            
            # Initialize team names
            if not teams_stats[match.home_team].team_name:
                teams_stats[match.home_team].team_name = match.home_team
            if not teams_stats[match.away_team].team_name:
                teams_stats[match.away_team].team_name = match.away_team
            
            # Update stats
            home_stats = teams_stats[match.home_team]
            away_stats = teams_stats[match.away_team]
            
            home_stats.played += 1
            away_stats.played += 1
            
            home_stats.goals_for += match.home_goals
            home_stats.goals_against += match.away_goals
            away_stats.goals_for += match.away_goals
            away_stats.goals_against += match.home_goals
            
            # Determine result
            if match.home_goals > match.away_goals:
                home_stats.wins += 1
                away_stats.losses += 1
            elif match.home_goals < match.away_goals:
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
    
    def scrape_group(self, season: int, group: str) -> Optional[GroupData]:
        """Scrape complete group data"""
        logger.info(f"Scraping Season {season} - Group {group.upper()}...")
        
        html = self.fetch_calendar(season, group)
        if not html:
            return None
        
        matches, errors = self.parse_matches(html, season, group)
        
        if not matches:
            error = f"No matches found for S{season}-{group.upper()}"
            logger.warning(error)
            errors.append(error)
            return None
        
        table = self.calculate_table(matches)
        
        return GroupData(
            season=season,
            group=group.upper(),
            matches=matches,
            table=table,
            errors=errors
        )
    
    def scrape_season(self, season: int) -> List[GroupData]:
        """Scrape all groups for a season (auto-detect)"""
        logger.info(f"========== SEASON {season} ==========")
        groups_data = []
        
        for group in self.GROUPS:
            group_data = self.scrape_group(season, group)
            
            if group_data:
                groups_data.append(group_data)
                time.sleep(0.5)  # Be nice to the server
            else:
                # If we hit a 404, assume no more groups for this season
                if not group_data:
                    logger.info(f"Season {season}: Found {len(groups_data)} groups (A-{self.GROUPS[len(groups_data)-1].upper()})")
                    break
        
        return groups_data
    
    def scrape_all(self) -> Dict:
        """Scrape all seasons and groups"""
        logger.info(f"Starting scrape: Seasons {self.start_season}-{self.end_season}")
        
        all_data = {
            'metadata': {
                'scraped_at': datetime.now().isoformat(),
                'start_season': self.start_season,
                'end_season': self.end_season,
                'total_errors': 0
            },
            'seasons': []
        }
        
        for season in range(self.start_season, self.end_season + 1):
            groups_data = self.scrape_season(season)
            
            if groups_data:
                season_data = {
                    'season': season,
                    'groups': []
                }
                
                for group_data in groups_data:
                    season_data['groups'].append({
                        'group': group_data.group,
                        'matches': [asdict(m) for m in group_data.matches],
                        'table': [asdict(t) for t in group_data.table],
                        'errors': group_data.errors
                    })
                
                all_data['seasons'].append(season_data)
            
            time.sleep(1)  # Pause between seasons
        
        all_data['metadata']['total_errors'] = len(self.error_log)
        
        return all_data
    
    def save_results(self, data: Dict, output_dir: str = 'output'):
        """Save results to JSON files"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Save main data
        data_file = output_path / f'biw_data_{self.start_season}-{self.end_season}.json'
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Data saved to {data_file}")
        
        # Save error log
        if self.error_log:
            error_file = output_path / f'errors_{self.start_season}-{self.end_season}.json'
            with open(error_file, 'w', encoding='utf-8') as f:
                json.dump(self.error_log, f, indent=2, ensure_ascii=False)
            logger.warning(f"Error log saved to {error_file} ({len(self.error_log)} errors)")
        
        # Generate summary
        summary = self.generate_summary(data)
        summary_file = output_path / f'summary_{self.start_season}-{self.end_season}.txt'
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(summary)
        logger.info(f"Summary saved to {summary_file}")
    
    def generate_summary(self, data: Dict) -> str:
        """Generate human-readable summary"""
        lines = [
            "=" * 60,
            "BIW POKAL SCRAPING SUMMARY",
            "=" * 60,
            f"Scraped at: {data['metadata']['scraped_at']}",
            f"Seasons: {data['metadata']['start_season']}-{data['metadata']['end_season']}",
            "",
            "RESULTS:",
            "-" * 60
        ]
        
        total_groups = 0
        total_matches = 0
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
            total_matches += season_matches
            total_teams.update(season_teams)
        
        lines.extend([
            "",
            "-" * 60,
            f"TOTALS:",
            f"  Seasons processed: {len(data['seasons'])}",
            f"  Total groups: {total_groups}",
            f"  Total matches: {total_matches}",
            f"  Unique teams: {len(total_teams)}",
            f"  Errors: {data['metadata']['total_errors']}",
            "=" * 60
        ])
        
        return '\n'.join(lines)


def main():
    """Main execution"""
    scraper = BIWScaper(start_season=12, end_season=50)
    
    try:
        data = scraper.scrape_all()
        scraper.save_results(data)
        
        logger.info("=" * 60)
        logger.info("SCRAPING COMPLETED SUCCESSFULLY")
        logger.info(f"Processed {len(data['seasons'])} seasons")
        logger.info(f"Total errors: {len(scraper.error_log)}")
        logger.info("=" * 60)
        
    except KeyboardInterrupt:
        logger.warning("Scraping interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)


if __name__ == "__main__":
    main()
