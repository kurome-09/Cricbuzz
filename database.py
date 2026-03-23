from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Float
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

class Team(Base):
    __tablename__ = 'teams'
    team_id = Column(Integer, primary_key=True)
    team_name = Column(String, nullable=False)

class Player(Base):
    __tablename__ = 'players'
    player_id = Column(Integer, primary_key=True)
    player_name = Column(String, nullable=False)
    country = Column(String)
    dob = Column(String)
    playing_role = Column(String)
    batting_style = Column(String)
    bowling_style = Column(String)

class Match(Base):
    __tablename__ = 'matches'
    match_id = Column(Integer, primary_key=True)
    series_name = Column(String)
    match_type = Column(String)
    venue = Column(String)
    city = Column(String)
    umpires = Column(String)
    match_result_text = Column(String)
    man_of_the_match_name = Column(String)

class MatchInnings(Base):
    __tablename__ = 'match_innings'
    innings_id = Column(String, primary_key=True)
    match_id = Column(Integer, ForeignKey('matches.match_id'))
    innings_number = Column(Integer)
    batting_team_name = Column(String)
    total_score = Column(String)

class BattingScorecard(Base):
    __tablename__ = 'batting_scorecard'
    batting_id = Column(String, primary_key=True)
    innings_id = Column(String, ForeignKey('match_innings.innings_id'))
    player_id = Column(Integer, ForeignKey('players.player_id'))
    dismissal_info = Column(String)
    runs_scored = Column(Integer)
    balls_faced = Column(Integer)
    fours = Column(Integer)
    sixes = Column(Integer)
    strike_rate = Column(Float)

class BowlingScorecard(Base):
    __tablename__ = 'bowling_scorecard'
    bowling_id = Column(String, primary_key=True)
    innings_id = Column(String, ForeignKey('match_innings.innings_id'))
    player_id = Column(Integer, ForeignKey('players.player_id'))
    overs_bowled = Column(Float)
    maidens = Column(Integer)
    runs_conceded = Column(Integer)
    wickets_taken = Column(Integer)
    economy_rate = Column(Float)

# Database Setup
engine = create_engine('sqlite:///cricket_data.db', echo=False)
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)