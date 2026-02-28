import json
import os
import re
import time

import requests
from bs4 import BeautifulSoup

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
BBREF_DELAY = 3  # seconds between Basketball Reference requests


def _bbref_sleep():
    time.sleep(BBREF_DELAY)


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def _cache_path(player_id):
    return os.path.join(DATA_DIR, f"cache_{player_id}.json")


def _load_cached(player_id):
    p = _cache_path(player_id)
    if os.path.exists(p):
        try:
            with open(p) as f:
                return json.load(f)
        except Exception:
            pass
    return None


def _save_cached(player_id, data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(_cache_path(player_id), "w") as f:
        json.dump(data, f)


def _bbref_id_from_search(player_name):
    """Return the BBRef player ID by scraping the search page."""
    try:
        url = f"https://www.basketball-reference.com/search/search.fcgi?search={requests.utils.quote(player_name)}"
        _bbref_sleep()
        resp = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        # If we were redirected to a player page directly
        if "/players/" in resp.url and resp.url.endswith(".html"):
            m = re.search(r"/players/[a-z]/([a-z0-9]+)\.html", resp.url)
            if m:
                return m.group(1)
        soup = BeautifulSoup(resp.text, "lxml")
        # Search results
        for link in soup.select("div.search-item-url"):
            text = link.get_text()
            m = re.search(r"/players/[a-z]/([a-z0-9]+)\.html", text)
            if m:
                return m.group(1)
        for a in soup.select("a"):
            href = a.get("href", "")
            m = re.search(r"/players/[a-z]/([a-z0-9]+)\.html", href)
            if m:
                return m.group(1)
    except Exception:
        pass
    return None


def _fetch_per_game(soup, season_label="2024-25"):
    data = {}
    try:
        table = soup.find("table", {"id": "per_game"})
        if not table:
            return data
        for row in table.select("tbody tr"):
            if row.get("class") and "thead" in row.get("class", []):
                continue
            season_cell = row.find("th", {"data-stat": "season"})
            if not season_cell:
                continue
            if season_label not in season_cell.get_text():
                continue
            td = lambda s: (row.find("td", {"data-stat": s}) or {})
            def val(stat):
                el = row.find("td", {"data-stat": stat})
                if el:
                    txt = el.get_text().strip()
                    try:
                        return float(txt)
                    except Exception:
                        pass
                return None

            data = {
                "pts":     val("pts_per_g"),
                "reb":     val("trb_per_g"),
                "ast":     val("ast_per_g"),
                "stl":     val("stl_per_g"),
                "blk":     val("blk_per_g"),
                "pf":      val("pf_per_g"),
                "fga":     val("fga_per_g"),
                "fg_pct":  val("fg_pct"),
                "fg3a":    val("fg3a_per_g"),
                "fg3_pct": val("fg3_pct"),
                "fta":     val("fta_per_g"),
                "ft_pct":  val("ft_pct"),
                "mp":      val("mp_per_g"),
                "g":       val("g"),
            }
            break
    except Exception:
        pass
    return data


def _fetch_advanced(soup, season_label="2024-25"):
    data = {}
    try:
        table = soup.find("table", {"id": "advanced"})
        if not table:
            return data
        for row in table.select("tbody tr"):
            season_cell = row.find("th", {"data-stat": "season"})
            if not season_cell:
                continue
            if season_label not in season_cell.get_text():
                continue
            def val(stat):
                el = row.find("td", {"data-stat": stat})
                if el:
                    txt = el.get_text().strip().rstrip("%")
                    try:
                        return float(txt)
                    except Exception:
                        pass
                return None

            data = {
                "usg_pct":  val("usg_pct"),
                "ast_pct":  val("ast_pct"),
                "tov_pct":  val("tov_pct"),
                "ts_pct":   val("ts_pct"),
                "orb_pct":  val("orb_pct"),
                "drb_pct":  val("drb_pct"),
                "per":      val("per"),
                "bpm":      val("bpm"),
            }
            break
    except Exception:
        pass
    return data


def _fetch_shooting_splits(bbref_id, season_year="2024"):
    """Fetch shot distance distribution from BBRef shooting page."""
    splits = {
        "pct_fga_0_3":    None,
        "pct_fga_3_10":   None,
        "pct_fga_10_16":  None,
        "pct_fga_16_3pt": None,
        "pct_fga_3pt":    None,
    }
    try:
        letter = bbref_id[0]
        url = f"https://www.basketball-reference.com/players/{letter}/{bbref_id}/shooting/{season_year}"
        _bbref_sleep()
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "lxml")
        table = soup.find("table", {"id": "shooting"})
        if not table:
            return splits
        # Look for the distance distribution row
        headers = [th.get_text().strip() for th in table.select("thead tr th")]
        for row in table.select("tbody tr"):
            cells = row.find_all(["td", "th"])
            if not cells:
                continue
            label = cells[0].get_text().strip()
            if "% of FGA" in label or "Dist." in label:
                continue
            # Try to parse column values
            def get_col(col_name):
                try:
                    idx = headers.index(col_name)
                    txt = cells[idx].get_text().strip().rstrip("%")
                    return float(txt) / 100
                except Exception:
                    return None

            # BBRef columns: %FGA 0-3, %FGA 3-10, %FGA 10-16, %FGA 16-3P, %FGA 3P
            splits["pct_fga_0_3"]    = get_col("%FGA\xa00-3")    or get_col("0-3")
            splits["pct_fga_3_10"]   = get_col("%FGA\xa03-10")   or get_col("3-10")
            splits["pct_fga_10_16"]  = get_col("%FGA\xa010-16")  or get_col("10-16")
            splits["pct_fga_16_3pt"] = get_col("%FGA\xa016-3P")  or get_col("16-3P")
            splits["pct_fga_3pt"]    = get_col("%FGA\xa03P")     or get_col("3P")
            break
    except Exception:
        pass
    return splits


def _fetch_pbp_moves(bbref_id, season_year="2024"):
    """Return move frequency per game from BBRef play-by-play page."""
    moves = {
        "stepback_mid":       0,
        "stepback_3":         0,
        "spin_jumper":        0,
        "spin_layup":         0,
        "euro_step":          0,
        "hop_step":           0,
        "floater":            0,
        "step_through":       0,
        "alley_oop_finish":   0,
        "alley_oop_pass":     0,
    }
    try:
        letter = bbref_id[0]
        url = f"https://www.basketball-reference.com/players/{letter}/{bbref_id}.html"
        _bbref_sleep()
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "lxml")
        # Look for pbp table
        pbp_table = soup.find("table", {"id": "pbp"})
        if not pbp_table:
            return moves
        # Parse rows to find move-type columns
        for row in pbp_table.select("tbody tr"):
            season_cell = row.find("th", {"data-stat": "season"})
            if not season_cell or season_year not in season_cell.get_text():
                continue
            def val(stat):
                el = row.find("td", {"data-stat": stat})
                if el:
                    try:
                        return float(el.get_text().strip())
                    except Exception:
                        pass
                return 0

            g = val("g") or 1
            moves["alley_oop_finish"] = round(val("and1") / max(g, 1), 2)
            break
    except Exception:
        pass
    return moves


def get_player_stats(player_name, player_id=None, season="2024-25"):
    cache_key = player_id or player_name.replace(" ", "_").lower()
    cached = _load_cached(cache_key)
    if cached and "per_game" in cached:
        return cached

    result = {
        "per_game":        {},
        "advanced":        {},
        "shooting_splits": {},
        "pbp_moves":       {},
    }

    bbref_id = _bbref_id_from_search(player_name)
    if not bbref_id:
        return result

    season_year = season.split("-")[0]
    letter = bbref_id[0]

    try:
        url = f"https://www.basketball-reference.com/players/{letter}/{bbref_id}.html"
        _bbref_sleep()
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "lxml")

        result["per_game"] = _fetch_per_game(soup, season_label=season)
        result["advanced"] = _fetch_advanced(soup, season_label=season)
    except Exception:
        pass

    result["shooting_splits"] = _fetch_shooting_splits(bbref_id, season_year)
    result["pbp_moves"] = _fetch_pbp_moves(bbref_id, season_year)

    _save_cached(cache_key, result)
    return result
