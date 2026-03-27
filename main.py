import logging
from database import SessionLocal, Match, MatchInnings, BatScorecard, BowlScorecard, Player
from scraper import CricbuzzScraper

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_saved_match_status(db):
    return {match.match_id: match.won_stat for match in db.query(Match.match_id, Match.won_stat).all()}

def is_match_finished(won_stat_text):
    if not won_stat_text or won_stat_text == "Unknown": return False
    text = won_stat_text.lower()
    finished_keywords =["by", "drawn", "tied", "abandoned", "no result"]
    return any(kw in text for kw in finished_keywords)

def main():
    scraper = CricbuzzScraper()
    scraper.init_browser()
    db = SessionLocal()
    
    try:
        match_links = scraper.get_recent_match_ids() 
        saved_matches = get_saved_match_status(db)
        matches_processed = 0

        for m_info in match_links:
            m_id = int(m_info['id'])
            
            if m_id in saved_matches:
                if is_match_finished(saved_matches[m_id]):
                    logging.info(f"Skipping Match {m_id} (Already finished and saved)")
                    continue
                else:
                    logging.info(f"Match {m_id} is in DB but appears LIVE/unfinished. Updating data...")
            
            if matches_processed >= 15:
                logging.info("Restarting browser to prevent memory bloat...")
                scraper.close(); scraper.init_browser(); matches_processed = 0

            logging.info(f"Scraping Match {m_id}...")
            data = scraper.scrape_match_data(m_info)
            
            # 1. Upsert Match
            db.merge(Match(
                match_id=data["match_id"], 
                series_name=data["series_name"], 
                match_type=data["match_type"], 
                venue=data["venue"], 
                city=data["city"], 
                team_won=data["team_won"], 
                won_stat=data["won_stat"], 
                manofthematch=data["manofthematch"],
                umpire_1=data["umpire_1"],
                umpire_2=data["umpire_2"]
            ))

            # 2. Upsert Players 
            for p_id in data["players_to_scrape"]:
                p_data = scraper.scrape_player_profile(p_id)
                if p_data: db.merge(Player(**p_data))
                
            # 3. Upsert Innings & Scorecards
            for inn in data["innings"]:
                db.merge(MatchInnings(
                    match_id=data["match_id"], 
                    innings=inn['innings_number'], 
                    batting_team=inn['batting_team'], 
                    bowling_team=inn['bowling_team'], 
                    total_score=inn['score']
                ))
                for bat in inn["batters"]: 
                    db.merge(BatScorecard(match_id=data["match_id"], innings=inn['innings_number'], **bat))
                for bowl in inn["bowlers"]: 
                    db.merge(BowlScorecard(match_id=data["match_id"], innings=inn['innings_number'], **bowl))

            db.commit()
            matches_processed += 1
            logging.info(f"Saved Match {m_id} Score: {[i['score'] for i in data['innings']]}")

    except Exception as e: 
        logging.error(f"Critical error: {e}", exc_info=True)
    finally: 
        scraper.close(); db.close()

if __name__ == "__main__": 
    main()