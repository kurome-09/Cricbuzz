import logging
from database import SessionLocal, Match, MatchInnings, BattingScorecard, BowlingScorecard, Player
from scraper import CricbuzzScraper

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_scraped_match_ids(db):
    """Helper function to get matches we've already saved to the database."""
    return {match.match_id for match in db.query(Match.match_id).all()}

def main():
    scraper = CricbuzzScraper()
    scraper.init_browser()
    db = SessionLocal()

    try:
        logging.info("Finding recent International matches...")
        match_links = scraper.get_recent_match_ids(limit=None) 
        
        if not match_links:
            logging.error("No match links were found!")
            return
            
        logging.info(f"Found {len(match_links)} International matches.")

        already_scraped = get_scraped_match_ids(db)

        for match_info in match_links:
            match_id = int(match_info['id'])
            
            if match_id in already_scraped:
                logging.info(f"Skipping Match {match_id} (Already in database)")
                continue

            try:
                logging.info(f"--- Starting Scrape for Match {match_id} ---")
                match_data = scraper.scrape_match_data(match_info)
                
                # 1. Upsert Match
                db_match = Match(
                    match_id=match_data["match_id"],
                    series_name=match_data["series_name"],
                    match_type=match_data["match_type"],
                    venue=match_data["venue"],
                    city=match_data["city"],
                    umpires=match_data["umpires"],
                    match_result_text=match_data["match_result_text"],
                    man_of_the_match_name=match_data["mom"]
                )
                db.merge(db_match)
                
                # 2. Upsert Players
                logging.info(f"Scraping {len(match_data['players_to_scrape'])} players...")
                for p_id in match_data["players_to_scrape"]:
                    p_data = scraper.scrape_player_profile(p_id)
                    db_player = Player(**p_data)
                    db.merge(db_player)

                # 3. Upsert Innings & Scorecards
                for inn in match_data["innings"]:
                    inn_id = f"{match_data['match_id']}_inn{inn['innings_number']}"
                    
                    db_inn = MatchInnings(
                        innings_id=inn_id,
                        match_id=match_data["match_id"],
                        innings_number=inn['innings_number'],
                        batting_team_name=inn.get('batting_team', 'Unknown'),
                        total_score=inn.get('score', '')
                    )
                    db.merge(db_inn)

                    for bat in inn["batters"]:
                        db_bat = BattingScorecard(
                            batting_id=f"{match_data['match_id']}_{bat['player_id']}",
                            innings_id=inn_id,
                            **bat
                        )
                        db.merge(db_bat)

                    for bowl in inn["bowlers"]:
                        db_bowl = BowlingScorecard(
                            bowling_id=f"{match_data['match_id']}_{bowl['player_id']}",
                            innings_id=inn_id,
                            **bowl
                        )
                        db.merge(db_bowl)

                db.commit()
                logging.info(f"Match {match_data['match_id']} successfully saved!")

            except Exception as e:
                logging.error(f"Failed to scrape match {match_id}: {e}")
                db.rollback() 
                    
    except Exception as e:
        logging.error(f"A critical error occurred: {e}", exc_info=True)
    finally:
        scraper.close()
        db.close()

if __name__ == "__main__":
    main()