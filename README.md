# NBA 2K26 Tendency Generator

Automatically generate realistic NBA 2K26 player tendency values from real NBA stats.

## Features

- **Real data** – pulls from NBA Stats API and Basketball Reference
- **84 tendencies** – covers shooting, driving, finishing, post, passing, defense, and more
- **Hard cap enforcement** – all values respect the official 2K26 cap rules
- **Web UI** – search any active player, view generated tendencies grouped by category
- **Override inputs** – manually adjust any tendency (must end in 0 or 5)
- **Export** – download as CSV or Excel
- **Bulk mode** – generate all players for a selected team

## Quick Start

### Windows
```bat
start.bat
```

### Mac / Linux
```bash
chmod +x start.sh
./start.sh
```

### Manual
```bash
pip install -r requirements.txt
python app.py          # or python3 app.py
```

Then open **http://localhost:5000** in your browser.

## Project Structure

```
├── app.py                          # Flask web server
├── requirements.txt
├── start.bat / start.sh
├── engine/
│   ├── constants.py                # Tendency definitions & caps
│   ├── player_search.py            # NBA player lookup + cache
│   ├── scraper.py                  # Basketball Reference scraper
│   ├── nba_stats.py                # NBA Stats API (tracking, zones)
│   ├── pbp_parser.py               # Play-by-play move defaults
│   ├── zone_distributor.py         # Shot-zone → directional tendencies
│   ├── caps_enforcer.py            # Hard cap + rule enforcement
│   └── tendency_calculator.py     # Main calculation engine
├── static/
│   ├── index.html
│   ├── style.css
│   └── script.js
└── data/                           # Cache directory (auto-created)
```

## Notes

- The NBA Stats API and Basketball Reference have rate limits; the app adds
  automatic delays between requests (0.6 s for NBA API, 3 s for BBRef).
- All scraped/API data is cached locally in `data/` so subsequent lookups
  are instant.
- The system works even when external APIs are down – it falls back to
  position-based defaults and any previously cached data.
