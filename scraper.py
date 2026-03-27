from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
import re
import logging
import time
import datetime

class CricbuzzScraper:
    def __init__(self):
        self.driver = None
        self.wait = None

    def init_browser(self):
        chrome_options = Options()
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        prefs = {"profile.managed_default_content_settings.images": 2}
        chrome_options.add_experimental_option("prefs", prefs)
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 15)

    def close(self):
        if self.driver:
            self.driver.quit()

    def get_recent_match_ids(self, limit=None):
        url = "https://www.cricbuzz.com/cricket-match/live-scores/recent-matches"
        logging.info(f"Navigating to {url}")
        self.driver.get(url)
        
        try:
            intl_tab = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//*[text()='International']")))
            intl_tab.click()
            time.sleep(3) 
        except TimeoutException:
            logging.warning("Timeout clicking 'International' tab.")

        match_links = []
        elements = self.driver.find_elements(By.CSS_SELECTOR, 'a[href*="/live-cricket-scores/"]')
        
        for el in elements:
            if el.is_displayed():
                href = el.get_attribute('href')
                match = re.search(r'/live-cricket-scores/(\d+)/', href)
                if match:
                    match_id = match.group(1)
                    scorecard_url = href.replace('/live-cricket-scores/', '/live-cricket-scorecard/')
                    squads_url = href.replace('/live-cricket-scores/', '/cricket-match-squads/')
                    
                    if not any(m['id'] == match_id for m in match_links):
                        match_links.append({
                            "id": match_id, 
                            "live_url": href, 
                            "scorecard_url": scorecard_url,
                            "squads_url": squads_url
                        })
                        if limit and len(match_links) >= limit: 
                            break
                            
        return match_links

    def scrape_match_data(self, match_info):
        match_id = match_info['id']
        data = {
            "match_id": int(match_id), "series_name": "Unknown", "match_type": "Unknown",
            "venue": "Unknown", "city": "Unknown", 
            "umpire_1": "", "umpire_2": "",
            "team_won": "Unknown", "won_stat": "Unknown", "manofthematch": "Unknown",
            "innings":[], "players_to_scrape": set()
        }

        # 1. Live Page Parsing (Result & MOM)
        self.driver.get(match_info['live_url'])
        soup_live = BeautifulSoup(self.driver.page_source, 'html.parser')

        result_div = soup_live.find('div', class_='text-cbTextLink')
        if result_div:
            match_result_text = result_div.get_text(strip=True)
            win_match = re.search(r'^(.*?)\s+won by\s+(.*)$', match_result_text, re.IGNORECASE)
            if win_match:
                data["team_won"] = win_match.group(1).strip()
                data["won_stat"] = win_match.group(2).strip()
            else:
                data["won_stat"] = match_result_text

        mom_tag = soup_live.find(string=re.compile("PLAYER OF THE MATCH", re.IGNORECASE))
        if mom_tag:
            next_profile_link = mom_tag.find_next('a', href=re.compile(r'/profiles/\d+/'))
            if next_profile_link:
                title = next_profile_link.get('title', '')
                data["manofthematch"] = title[16:].strip() if title.lower().startswith('view profile of ') else next_profile_link.get_text(strip=True)

        # 2. Squads Page Parsing (Discovers the 22 Playing XI players)
        self.driver.get(match_info['squads_url'])
        soup_squads = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        xi_headers = soup_squads.find_all(string=re.compile(r'Playing XI', re.IGNORECASE))
        team_idx = 1
        for header in xi_headers:
            if team_idx > 2: break
            container = header.parent.find_next('div')
            if container:
                for a in container.find_all('a', href=re.compile(r'/profiles/(\d+)/')):
                    p_id = int(re.search(r'/profiles/(\d+)/', a['href']).group(1))
                    data["players_to_scrape"].add(p_id) 
            team_idx += 1

        # 3. Scorecard Page Parsing (Umpires, Venue, Innings, DNB)
        self.driver.get(match_info['scorecard_url'])
        try:
            self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'scorecard-bat-grid')))
        except TimeoutException:
            logging.warning(f"Scorecard grid not found for match {match_id}. Match might be abandoned.")
            return data 
            
        soup_scorecard = BeautifulSoup(self.driver.page_source, 'html.parser')

        # Match Info Table
        for row in soup_scorecard.find_all('div', class_=re.compile('facts-row-grid')):
            label_div = row.find('div', class_='font-bold')
            if label_div:
                label = label_div.get_text(strip=True)
                val_tag = label_div.find_next_sibling() 
                if val_tag:
                    val = val_tag.get_text(separator=' ', strip=True)
                    if label == "Match":
                        parts = val.split('•')
                        data["match_type"] = parts[1].strip() if len(parts) >= 2 else val
                    elif label == "Series": data["series_name"] = val
                    elif label == "Umpires": 
                        umps = [u.strip() for u in val.split(',')]
                        data["umpire_1"] = umps[0] if len(umps) > 0 else ""
                        data["umpire_2"] = umps[1] if len(umps) > 1 else ""
                    elif label == "Venue":
                        v_parts = val.split(",")
                        data["city"] = v_parts[-1].strip()
                        data["venue"] = ",".join(v_parts[:-1]).strip() if len(v_parts) > 1 else val

        # Innings Extraction
        innings_divs = soup_scorecard.find_all('div', id=re.compile(r'^team-\d+-innings-\d+$'))
        
        for idx, inn_div in enumerate(innings_divs):
            if idx >= 2: break
                
            inn_data = {"innings_number": idx + 1, "batters": [], "bowlers":[], "batting_team": "Unknown", "bowling_team": "Unknown", "score": 0}
            
            team_name_div = inn_div.find('div', class_=re.compile(r'font-bold'))
            if team_name_div:
                text = team_name_div.get_text(strip=True)
                inn_data["batting_team"] = text.replace('Innings', '').strip() if not any(char.isdigit() for char in text) else "Unknown"
                
                parent_text = team_name_div.parent.get_text(separator=' ')
                score_match = re.search(r'\b(\d+)(?:[-/]\d+)?\b', parent_text.replace(text, ''))
                if score_match:
                    inn_data["score"] = int(score_match.group(1))
                    
            scard_container = inn_div.find_next_sibling('div', id=re.compile(r'^scard-team-'))
            if not scard_container: continue

            # Batters
            for row in scard_container.find_all('div', class_=re.compile('scorecard-bat-grid')):
                try:
                    cols = row.find_all('div', recursive=False)
                    if len(cols) >= 6 and cols[1].text.strip() != 'R': 
                        a_tag = cols[0].find('a')
                        if not a_tag: continue
                        p_id = int(re.search(r'/profiles/(\d+)/', a_tag['href']).group(1))
                        data["players_to_scrape"].add(p_id)
                        
                        inn_data["batters"].append({
                            "player_id": p_id,
                            "runs_scored": int(cols[1].text.strip() or 0),
                            "fours": int(cols[3].text.strip() or 0),
                            "sixes": int(cols[4].text.strip() or 0)
                        })
                except Exception as e:
                    logging.warning(f"Skipped a batter row due to parsing error: {e}")

            # Did Not Bat Extraction
            dnb_tag = scard_container.find(string=re.compile(r'Did not Bat', re.IGNORECASE))
            if dnb_tag:
                dnb_row = dnb_tag.find_parent('div')
                if dnb_row and dnb_row.parent:
                    for a_tag in dnb_row.parent.find_all('a', href=re.compile(r'/profiles/(\d+)/')):
                        p_id = int(re.search(r'/profiles/(\d+)/', a_tag['href']).group(1))
                        data["players_to_scrape"].add(p_id)
                        inn_data["batters"].append({
                            "player_id": p_id,
                            "runs_scored": None, 
                            "fours": None,
                            "sixes": None
                        })

            # Bowlers
            for row in scard_container.find_all('div', class_=re.compile('scorecard-bowl-grid')):
                try:
                    children = row.find_all(['a', 'div'], recursive=False)
                    if len(children) >= 8 and children[1].text.strip() != 'O': 
                        a_tag = children[0]
                        if a_tag.name != 'a': continue
                        p_id = int(re.search(r'/profiles/(\d+)/', a_tag['href']).group(1))
                        data["players_to_scrape"].add(p_id)
                        
                        inn_data["bowlers"].append({
                            "player_id": p_id,
                            "overs_bowled": float(children[1].text.strip() or 0),
                            "maidens": int(children[2].text.strip() or 0),
                            "runs_conceded": int(children[3].text.strip() or 0),
                            "wickets_taken": int(children[4].text.strip() or 0)
                        })
                except Exception as e:
                    logging.warning(f"Skipped a bowler row due to parsing error: {e}")

            data["innings"].append(inn_data)
            
        if len(data["innings"]) == 2:
            data["innings"][0]["bowling_team"] = data["innings"][1]["batting_team"]
            data["innings"][1]["bowling_team"] = data["innings"][0]["batting_team"]

        return data

    def scrape_player_profile(self, player_id, retries=2):
        url = f"https://www.cricbuzz.com/profiles/{player_id}/"
        profile = {"player_id": player_id, "player_name": "Unknown", "country": "Unknown", "dob": None, "playing_role": "Unknown", "batting_style": "Unknown", "bowling_style": "Unknown"}

        for attempt in range(retries):
            try:
                self.driver.get(url)
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')

                name_span = soup.find('span', class_=re.compile(r'text-xl|font-bold'))
                if not name_span:
                    logging.warning(f"Player {player_id} returned a 404 or missing data. Skipping.")
                    return None 

                profile["player_name"] = name_span.get_text(strip=True)
                    
                country_span = soup.find('span', class_=re.compile(r'text-gray-800'))
                if country_span:
                    profile["country"] = country_span.get_text(strip=True)

                for label_text in["Born", "Role", "Batting Style", "Bowling Style"]:
                    lbl_tag = soup.find('div', string=re.compile(f"^{label_text}$", re.IGNORECASE))
                    if lbl_tag:
                        val_tag = lbl_tag.find_next_sibling('div')
                        if val_tag:
                            val = val_tag.text.strip()
                            if label_text == "Born": 
                                # THE FIX: Bulletproof Regex. Extracts exactly "Month DD, YYYY" ignoring all noise.
                                date_match = re.search(r'([a-zA-Z]+\s\d{1,2},\s\d{4})', val)
                                if date_match:
                                    clean_date_str = date_match.group(1)
                                    try:
                                        profile["dob"] = datetime.datetime.strptime(clean_date_str, "%b %d, %Y").date()
                                    except ValueError:
                                        try:
                                            # Fallback just in case month is fully spelled out
                                            profile["dob"] = datetime.datetime.strptime(clean_date_str, "%B %d, %Y").date()
                                        except ValueError:
                                            profile["dob"] = None
                            elif label_text == "Role": profile["playing_role"] = val
                            elif label_text == "Batting Style": profile["batting_style"] = val
                            elif label_text == "Bowling Style": profile["bowling_style"] = val

                return profile
                
            except Exception as e:
                logging.warning(f"Attempt {attempt + 1} failed for player {player_id}: {e}")
                time.sleep(2)
                
        return None