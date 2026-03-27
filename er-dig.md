erDiagram
    MATCHES {
        int match_id PK
        string series_name
        string match_type
        string venue
        string city
        string team_won
        string won_stat
        string manofthematch
        string umpire_1
        string umpire_2
    }
    
    MATCH_INNINGS {
        int match_id PK, FK
        int innings PK
        string batting_team
        string bowling_team
        int total_score
    }

    PLAYERS {
        int player_id PK
        string player_name
        string country
        date dob
        string playing_role
        string batting_style
        string bowling_style
    }

    BAT_SCORECARD {
        int match_id PK, FK
        int innings PK, FK
        int player_id PK, FK
        int runs_scored "NULL if Did Not Bat"
        int fours
        int sixes
    }

    BOWL_SCORECARD {
        int match_id PK, FK
        int innings PK, FK
        int player_id PK, FK
        float overs_bowled
        int maidens
        int runs_conceded
        int wickets_taken
    }

    MATCHES ||--o{ MATCH_INNINGS : "has"
    MATCH_INNINGS ||--o{ BAT_SCORECARD : "contains"
    MATCH_INNINGS ||--o{ BOWL_SCORECARD : "contains"
    PLAYERS ||--o{ BAT_SCORECARD : "bats in"
    PLAYERS ||--o{ BOWL_SCORECARD : "bowls in"