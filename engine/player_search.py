import json
import os
import time

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
CACHE_FILE = os.path.join(DATA_DIR, "players_cache.json")

_players_cache = None


def _load_cache():
    global _players_cache
    if _players_cache is not None:
        return _players_cache
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                _players_cache = json.load(f)
            return _players_cache
        except Exception:
            pass
    return None


def _save_cache(players):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(players, f)


def get_all_players(season="2024-25"):
    cached = _load_cache()
    if cached:
        return cached

    players = []
    try:
        from nba_api.stats.static import players as static_players
        from nba_api.stats.endpoints import commonallplayers
        import time

        time.sleep(0.6)
        all_players_data = commonallplayers.CommonAllPlayers(
            is_only_current_season=1,
            league_id="00",
            season=season,
        )
        time.sleep(0.6)
        df = all_players_data.get_data_frames()[0]

        for _, row in df.iterrows():
            players.append({
                "id":         int(row.get("PERSON_ID", 0)),
                "name":       str(row.get("DISPLAY_FIRST_LAST", "")),
                "team_abbrev": str(row.get("TEAM_ABBREVIATION", "")),
                "position":   str(row.get("ROSTERSTATUS", "")),
            })
    except Exception:
        # Fall back to static players list
        try:
            from nba_api.stats.static import players as static_players
            time.sleep(0.3)
            active = static_players.get_active_players()
            for p in active:
                players.append({
                    "id":          int(p.get("id", 0)),
                    "name":        str(p.get("full_name", "")),
                    "team_abbrev": "",
                    "position":    "",
                })
        except Exception:
            pass

    if players:
        _save_cache(players)
        global _players_cache
        _players_cache = players

    return players


def search_players(query, limit=10):
    players = get_all_players()
    if not players:
        return []

    query_lower = query.lower()
    results = []
    for p in players:
        name = p.get("name", "")
        if query_lower in name.lower():
            results.append({
                "name":      name,
                "team":      p.get("team_abbrev", ""),
                "position":  p.get("position", ""),
                "player_id": p.get("id", 0),
            })
        if len(results) >= limit:
            break

    # Prioritize starts-with matches
    results.sort(key=lambda x: (0 if x["name"].lower().startswith(query_lower) else 1, x["name"]))
    return results[:limit]


def refresh_cache():
    global _players_cache
    _players_cache = None
    if os.path.exists(CACHE_FILE):
        os.remove(CACHE_FILE)
    return get_all_players()
