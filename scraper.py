from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import re
import logging
import time

class CricbuzzScraper:
    def __init__(self):
        self.driver = None

    def init_browser(self):
        chrome_options = Options()
        # Uncomment the line below if you want the browser to run invisibly
        # chrome_options.add_argument("--headless") 
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        # Block images to speed up scraping significantly
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
            logging.info("Filtering by 'International' matches...")
            intl_tab = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//div[text()='International']")))
            intl_tab.click()
            time.sleep(2) 
        except Exception as e:
            logging.warning(f"Could not click International tab: {e}")

        match_links = []
        
        elements = self.driver.find_elements(By.CSS_SELECTOR, 'a[href*="/live-cricket-scores/"]')
        
        for el in elements:
            if el.is_displayed():
                href = el.get_attribute('href')
                match = re.search(r'/live-cricket-scores/(\d+)/', href)
                if match:
                    match_id = match.group(1)
                    scorecard_url = href.replace('/live-cricket-scores/', '/live-cricket-scorecard/')
                    if not any(m['id'] == match_id for m in match_links):
                        # WE NOW SAVE BOTH URLS!
                        match_links.append({
                            "id": match_id, 
                            "live_url": href, 
                            "scorecard_url": scorecard_url
                        })
                        if limit and len(match_links) >= limit: 
                            break
                            
        return match_links

    def scrape_match_data(self, match_info):
        match_id = match_info['id']
        
        data = {
            "match_id": int(match_id),
            "series_name": "Unknown",
            "match_type": "Unknown",
            "venue": "Unknown",
            "city": "Unknown",
            "umpires": "Unknown",
            "match_result_text": "Unknown",
            "mom": "Unknown",
            "innings":[],
            "players_to_scrape": set()
        }

        # ==========================================
        # STEP 1: VISIT LIVE PAGE FOR MOM & RESULT
        # ==========================================
        logging.info(f"Visiting Live Page for MOM: {match_info['live_url']}")
        self.driver.get(match_info['live_url'])
        soup_live = BeautifulSoup(self.driver.page_source, 'html.parser')

        # Extract Match Result
        result_div = soup_live.find('div', class_='text-cbTextLink')
        if result_div:
            data["match_result_text"] = result_div.get_text(strip=True)

        # Extract Player of the Match
        for el in soup_live.find_all(['div', 'span']):
            text = el.get_text(strip=True).upper()
            if "PLAYER OF THE MATCH" in text:
                next_profile_link = el.find_next('a', href=re.compile(r'/profiles/\d+/'))
                if next_profile_link:
                    title = next_profile_link.get('title', '')
                    if title.lower().startswith('view profile of '):
                        data["mom"] = title[16:].strip()
                    else:
                        data["mom"] = next_profile_link.get_text(strip=True)
                break

        # ==========================================
        # STEP 2: VISIT SCORECARD PAGE FOR INNINGS
        # ==========================================
        logging.info(f"Visiting Scorecard Page for Innings: {match_info['scorecard_url']}")
        self.driver.get(match_info['scorecard_url'])
        
        try:
            self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'scorecard-bat-grid')))
        except:
            pass 
            
        soup_scorecard = BeautifulSoup(self.driver.page_source, 'html.parser')

        # Extract Match Info Table
        for row in soup_scorecard.find_all('div', class_=re.compile('facts-row-grid')):
            label_div = row.find('div', class_='font-bold')
            if label_div:
                label = label_div.get_text(strip=True)
                val_tag = label_div.find_next_sibling() 
                if val_tag:
                    val = val_tag.get_text(separator=' ', strip=True)
                    if label == "Match":
                        parts = val.split('•')
                        if len(parts) >= 2: data["match_type"] = parts[1].strip()
                        else: data["match_type"] = val
                    elif label == "Series": data["series_name"] = val
                    elif label == "Umpires": data["umpires"] = val
                    elif label == "Venue":
                        if "," in val:
                            v_parts = val.split(",")
                            data["city"] = v_parts[-1].strip()
                            data["venue"] = ",".join(v_parts[:-1]).strip()
                        else:
                            data["city"] = val
                            data["venue"] = val

        # Extract Innings & Scorecards
        innings_divs = soup_scorecard.find_all('div', id=re.compile(r'^team-\d+-innings-\d+$'))
        
        for idx, inn_div in enumerate(innings_divs):
            inn_data = {"innings_number": idx + 1, "batters": [], "bowlers":[], "batting_team": "Unknown", "score": ""}
            
            team_name_div = inn_div.find('div', class_=lambda c: c and 'hidden' in c and 'tb:block' in c and 'font-bold' in c)
            if team_name_div:
                inn_data["batting_team"] = team_name_div.get_text(strip=True)
            else:
                for bold_div in inn_div.find_all('div', class_=lambda c: c and 'font-bold' in c):
                    text = bold_div.get_text(strip=True)
                    if text and not any(char.isdigit() for char in text):
                        inn_data["batting_team"] = text
                        break
                    
            score_div = inn_div.find('div', class_=lambda c: c and 'gap-4' in c)
            if score_div:
                inn_data["score"] = score_div.get_text(separator=' ', strip=True)

            scard_container = inn_div.find_next_sibling('div', id=re.compile(r'^scard-team-'))
            if not scard_container: continue

            # Batters
            bat_rows = scard_container.find_all('div', class_=re.compile('scorecard-bat-grid'))
            for row in bat_rows:
                cols = row.find_all('div', recursive=False)
                if len(cols) >= 6 and cols[1].text.strip() != 'R': 
                    a_tag = cols[0].find('a')
                    if not a_tag: continue
                    p_id = int(re.search(r'/profiles/(\d+)/', a_tag['href']).group(1))
                    data["players_to_scrape"].add(p_id)
                    dismissal = cols[0].find('div', class_=re.compile('text-cbTxtSec'))
                    
                    inn_data["batters"].append({
                        "player_id": p_id,
                        "dismissal_info": dismissal.text.strip() if dismissal else "not out",
                        "runs_scored": int(cols[1].text.strip() or 0),
                        "balls_faced": int(cols[2].text.strip() or 0),
                        "fours": int(cols[3].text.strip() or 0),
                        "sixes": int(cols[4].text.strip() or 0),
                        "strike_rate": float(cols[5].text.strip() or 0.0)
                    })

            # Bowlers
            bowl_rows = scard_container.find_all('div', class_=re.compile('scorecard-bowl-grid'))
            for row in bowl_rows:
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
                        "wickets_taken": int(children[4].text.strip() or 0),
                        "economy_rate": float(children[7].text.strip() or 0.0)
                    })

            data["innings"].append(inn_data)
        return data

    def scrape_player_profile(self, player_id, retries=2):
        url = f"https://www.cricbuzz.com/profiles/{player_id}/"
        profile = {
            "player_id": player_id,
            "player_name": "Unknown",
            "country": "Unknown",
            "dob": "Unknown",
            "playing_role": "Unknown",
            "batting_style": "Unknown",
            "bowling_style": "Unknown"
        }

        for attempt in range(retries):
            try:
                self.driver.get(url)
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')

                name_span = soup.find('span', class_=lambda c: c and 'text-xl' in c and 'font-bold' in c)
                if name_span:
                    profile["player_name"] = name_span.get_text(strip=True)
                    
                country_span = soup.find('span', class_=lambda c: c and 'text-base' in c and 'text-gray-800' in c)
                if country_span:
                    profile["country"] = country_span.get_text(strip=True)

                for label_text in["Born", "Role", "Batting Style", "Bowling Style"]:
                    lbl_tag = soup.find('div', string=re.compile(f"^{label_text}$", re.IGNORECASE))
                    if lbl_tag:
                        val_tag = lbl_tag.find_next_sibling('div')
                        if val_tag:
                            val = val_tag.text.strip()
                            if label_text == "Born": profile["dob"] = val
                            elif label_text == "Role": profile["playing_role"] = val
                            elif label_text == "Batting Style": profile["batting_style"] = val
                            elif label_text == "Bowling Style": profile["bowling_style"] = val

                return profile
                
            except Exception as e:
                logging.warning(f"Attempt {attempt + 1} failed for player {player_id}: {e}")
                if attempt == retries - 1:
                    raise e
                time.sleep(2)