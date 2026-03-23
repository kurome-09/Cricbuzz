# Cricbuzz International Match Scraper

An automated web scraping pipeline that extracts live and recent International cricket match data, scorecards, and player profiles from Cricbuzz. Built with Python, Selenium, BeautifulSoup, and SQLAlchemy.

## Features
* **Smart Filtering:** Automatically filters and scrapes only "International" matches, ignoring domestic/league noise.
* **Two-Step Scraping:** Intelligently navigates between "Live" tabs (for Match Results and Player of the Match) and "Scorecard" tabs (for detailed innings data).
* **Resilient Extraction:** Uses DOM traversal to bypass dynamic React/Next.js wrapper classes.
* **Relational Database:** Stores data in a structured SQLite database using SQLAlchemy ORM.
* **Crash Recovery:** Includes retry mechanisms for network timeouts and skips already-scraped matches.

## Tech Stack
* **Scraping:** Selenium WebDriver, BeautifulSoup4
* **Database:** SQLite, SQLAlchemy
* **Language:** Python 3.x

## Setup & Installation
1. Clone the repository.
2. Create a virtual environment: `python -m venv .venv`
3. Activate the environment: `source .venv/bin/activate` (Linux/Mac) or `.venv\Scripts\activate` (Windows)
4. Install dependencies: `pip install selenium beautifulsoup4 sqlalchemy`
5. Run the scraper: `python main.py`

## Database Schema
* `matches`: Match metadata (Venue, Result, Player of the Match).
* `match_innings`: Innings data (Team scores, overs).
* `batting_scorecard`: Ball-by-ball batter statistics.
* `bowling_scorecard`: Over-by-over bowler statistics.
* `players`: Detailed player profiles (DOB, Role, Batting/Bowling styles).