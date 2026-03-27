from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Float, Date
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

class Player(Base):
    __tablename__ = 'players'
    player_id = Column(Integer, primary_key=True, autoincrement=False)
    player_name = Column(String, nullable=False)
    country = Column(String)
    dob = Column(Date) 
    playing_role = Column(String)
    batting_style = Column(String)
    bowling_style = Column(String)

class Match(Base):
    __tablename__ = 'matches'
    match_id = Column(Integer, primary_key=True, autoincrement=False)
    series_name = Column(String)
    match_type = Column(String)
    venue = Column(String)
    city = Column(String)
    team_won = Column(String) 
    won_stat = Column(String) 
    manofthematch = Column(String)
    
    umpire_1 = Column(String)
    umpire_2 = Column(String)

class MatchInnings(Base):
    __tablename__ = 'match_innings'
    match_id = Column(Integer, ForeignKey('matches.match_id'), primary_key=True)
    innings = Column(Integer, primary_key=True) 
    batting_team = Column(String) 
    bowling_team = Column(String) 
    total_score = Column(Integer) 

class BatScorecard(Base):
    __tablename__ = 'bat_scorecard' 
    match_id = Column(Integer, ForeignKey('match_innings.match_id'), primary_key=True)
    innings = Column(Integer, ForeignKey('match_innings.innings'), primary_key=True)
    player_id = Column(Integer, ForeignKey('players.player_id'), primary_key=True)
    runs_scored = Column(Integer, nullable=True) # NULL indicates "Did Not Bat"
    fours = Column(Integer, nullable=True)
    sixes = Column(Integer, nullable=True)

class BowlScorecard(Base):
    __tablename__ = 'bowl_scorecard' 
    match_id = Column(Integer, ForeignKey('match_innings.match_id'), primary_key=True)
    innings = Column(Integer, ForeignKey('match_innings.innings'), primary_key=True)
    player_id = Column(Integer, ForeignKey('players.player_id'), primary_key=True)
    overs_bowled = Column(Float)
    maidens = Column(Integer)
    runs_conceded = Column(Integer)
    wickets_taken = Column(Integer)

# Database Setup
engine = create_engine('sqlite:///cricket_data.db', echo=False)
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)