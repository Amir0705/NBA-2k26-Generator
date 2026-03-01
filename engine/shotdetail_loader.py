"""
Downloads and parses shufinskiy/nba_data shotdetail CSV to extract
per-player shooting statistics for tendency generation.

Data source: https://github.com/shufinskiy/nba_data
The dataset is downloaded as a .tar.xz archive and cached locally in data/.
"""

import os
import tarfile
import pandas as pd
from io import BytesIO
from urllib.request import urlopen, Request

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

# Rough average FGA per game for a starter; used to estimate games_played when GAME_ID is missing
_ESTIMATED_FGA_PER_GAME = 16
# Floor for estimated games_played to avoid extreme per-game rates for low-game samples
_MIN_ESTIMATED_GAMES = 40


def _get_shotdetail_path(season_year=2024):
    """Return path to cached shotdetail CSV."""
    return os.path.join(DATA_DIR, f"shotdetail_{season_year}.csv")


def _download_shotdetail(season_year=2024):
    """
    Download shotdetail CSV from shufinskiy/nba_data if not cached.
    The file list is at: https://raw.githubusercontent.com/shufinskiy/nba_data/main/list_data.txt
    Each line is like: shotdetail_2024=https://github.com/shufinskiy/nba_data/releases/download/...
    """
    csv_path = _get_shotdetail_path(season_year)
    if os.path.exists(csv_path):
        print(f"[shotdetail] Using cached {csv_path}")
        return csv_path

    os.makedirs(DATA_DIR, exist_ok=True)

    # Fetch list_data.txt to find the download URL
    list_url = "https://raw.githubusercontent.com/shufinskiy/nba_data/main/list_data.txt"
    print(f"[shotdetail] Fetching file list from {list_url}")
    try:
        req = Request(list_url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=30) as resp:
            lines = resp.read().decode("utf-8").strip().split("\n")
    except Exception as e:
        print(f"[shotdetail] ERROR: Could not fetch file list: {e}")
        return None

    target_key = f"shotdetail_{season_year}"
    download_url = None
    for line in lines:
        if line.startswith(target_key + "="):
            download_url = line.split("=", 1)[1].strip()
            break

    if not download_url:
        print(f"[shotdetail] WARNING: No URL found for {target_key}")
        return None

    print(f"[shotdetail] Downloading {target_key} from {download_url}")
    try:
        req = Request(download_url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=120) as resp:
            content = resp.read()
    except Exception as e:
        print(f"[shotdetail] ERROR: Download failed: {e}")
        return None

    # Extract CSV from tar.xz
    try:
        with tarfile.open(fileobj=BytesIO(content), mode="r:xz") as tar:
            csv_name = f"{target_key}.csv"
            csv_file = tar.extractfile(csv_name)
            if csv_file:
                with open(csv_path, "wb") as f:
                    f.write(csv_file.read())
                print(f"[shotdetail] Saved to {csv_path}")
                return csv_path
    except Exception as e:
        print(f"[shotdetail] ERROR: Could not extract archive: {e}")
        return None

    print(f"[shotdetail] ERROR: Could not extract {csv_name} from archive")
    return None


def load_player_shotdetail(player_id, season_year=2024):
    """
    Load all shot attempts for a specific player from the shotdetail CSV.
    Returns a dict with:
      - total_fga, total_fgm
      - shooting_splits (pct_fga by distance zone)
      - shot_zones (by SHOT_ZONE_BASIC + SHOT_ZONE_AREA for zone_distributor)
      - action_counts (ACTION_TYPE -> count)
      - zone_area_mid, zone_area_three, zone_area_close (L/LC/C/RC/R percentages)
    Returns None if data cannot be loaded.
    """
    csv_path = _download_shotdetail(season_year)
    if not csv_path or not os.path.exists(csv_path):
        return None

    print(f"[shotdetail] Loading data for player_id={player_id}")

    # Read CSV in chunks — filter by PLAYER_ID early to handle large files
    try:
        chunks = []
        for chunk in pd.read_csv(csv_path, chunksize=50000):
            player_chunk = chunk[chunk["PLAYER_ID"] == int(player_id)]
            if not player_chunk.empty:
                chunks.append(player_chunk)
    except Exception as e:
        print(f"[shotdetail] ERROR: Could not read CSV: {e}")
        return None

    if not chunks:
        print(f"[shotdetail] No shots found for player_id={player_id}")
        return None

    df = pd.concat(chunks, ignore_index=True)
    total_shots = len(df)
    print(f"[shotdetail] Found {total_shots} shots for player_id={player_id}")

    result = {
        "total_fga": total_shots,
        "total_fgm": int(df["EVENT_TYPE"].eq("Made Shot").sum()),
        "shooting_splits": {},
        "shot_zones": {},
        "action_counts": {},
        "zone_area_mid": {},
        "zone_area_three": {},
        "zone_area_close": {},
    }

    # Count unique games — GAME_ID column tells us exactly how many games the player played
    if "GAME_ID" in df.columns:
        result["games_played"] = int(df["GAME_ID"].nunique())
    else:
        result["games_played"] = max(int(total_shots / _ESTIMATED_FGA_PER_GAME), _MIN_ESTIMATED_GAMES)

    # --- Shooting splits by distance zone ---
    range_counts = df["SHOT_ZONE_RANGE"].value_counts()
    less8  = int(range_counts.get("Less Than 8 ft.", 0))
    r8_16  = int(range_counts.get("8-16 ft.", 0))
    r16_24 = int(range_counts.get("16-24 ft.", 0))
    r24plus = int(range_counts.get("24+ ft.", 0))

    zone_basic_counts = df["SHOT_ZONE_BASIC"].value_counts()
    paint        = int(zone_basic_counts.get("In The Paint (Non-RA)", 0))
    above3       = int(zone_basic_counts.get("Above the Break 3", 0))
    left_corner3 = int(zone_basic_counts.get("Left Corner 3", 0))
    right_corner3 = int(zone_basic_counts.get("Right Corner 3", 0))
    three_shots  = above3 + left_corner3 + right_corner3

    if total_shots > 0:
        result["shooting_splits"] = {
            "pct_fga_0_3":    less8  / total_shots,   # < 8 ft (restricted area)
            "pct_fga_3_10":   paint  / total_shots,   # In The Paint (Non-RA)
            "pct_fga_10_16":  r8_16  / total_shots,   # 8-16 ft mid-range
            "pct_fga_16_3pt": r16_24 / total_shots,   # 16-24 ft mid-range
            "pct_fga_3pt":    three_shots / total_shots,
        }

    # --- Shot zones for zone_distributor (SHOT_ZONE_BASIC|SHOT_ZONE_AREA) ---
    zone_groups = df.groupby(["SHOT_ZONE_BASIC", "SHOT_ZONE_AREA"])
    for (basic, area), group in zone_groups:
        fga = len(group)
        fgm = int(group["EVENT_TYPE"].eq("Made Shot").sum())
        key = f"{basic}|{area}"
        result["shot_zones"][key] = {
            "fga": fga,
            "fgm": fgm,
            "fg_pct": fgm / fga if fga > 0 else 0,
        }

    # --- Action type counts for move tendencies ---
    result["action_counts"] = df["ACTION_TYPE"].value_counts().to_dict()

    # --- Zone area distribution for L/LC/C/RC/R ---
    area_names = [
        "Left Side(L)", "Left Side Center(LC)", "Center(C)",
        "Right Side Center(RC)", "Right Side(R)",
    ]

    mid_df = df[df["SHOT_ZONE_BASIC"] == "Mid-Range"]
    if not mid_df.empty:
        mid_area = mid_df["SHOT_ZONE_AREA"].value_counts()
        mid_total = len(mid_df)
        for area_name in area_names:
            result["zone_area_mid"][area_name] = (
                mid_area.get(area_name, 0) / mid_total if mid_total > 0 else 0
            )

    three_df = df[df["SHOT_TYPE"] == "3PT Field Goal"]
    if not three_df.empty:
        three_area = three_df["SHOT_ZONE_AREA"].value_counts()
        three_total = len(three_df)
        for area_name in area_names:
            result["zone_area_three"][area_name] = (
                three_area.get(area_name, 0) / three_total if three_total > 0 else 0
            )

    close_df = df[df["SHOT_ZONE_BASIC"].isin(["Restricted Area", "In The Paint (Non-RA)"])]
    if not close_df.empty:
        close_area = close_df["SHOT_ZONE_AREA"].value_counts()
        close_total = len(close_df)
        for area_name in area_names:
            result["zone_area_close"][area_name] = (
                close_area.get(area_name, 0) / close_total if close_total > 0 else 0
            )

    # --- Step-back 2pt/3pt split using SHOT_TYPE column ---
    stepback_df = df[df["ACTION_TYPE"].str.contains("Step Back", case=False, na=False)]
    if not stepback_df.empty:
        result["stepback_2pt_count"] = int(
            len(stepback_df[stepback_df["SHOT_TYPE"] == "2PT Field Goal"])
        )
        result["stepback_3pt_count"] = int(
            len(stepback_df[stepback_df["SHOT_TYPE"] == "3PT Field Goal"])
        )
    else:
        result["stepback_2pt_count"] = 0
        result["stepback_3pt_count"] = 0

    return result


def extract_move_frequencies(action_counts, total_fga, games_played=None):
    """
    Convert ACTION_TYPE counts to per-game move frequency estimates.
    Maps NBA action types to 2K tendency move names.

    Uses games_played if provided; otherwise estimates from total_fga.
    """
    games = games_played if games_played and games_played > 0 else max(total_fga / _ESTIMATED_FGA_PER_GAME, _MIN_ESTIMATED_GAMES)

    def freq(keywords):
        """Sum counts for action types containing any keyword."""
        total = 0
        for action, count in action_counts.items():
            action_lower = str(action).lower()
            if any(kw.lower() in action_lower for kw in keywords):
                total += count
        return round(total / games, 3)

    # Step-back: use pre-computed 2pt/3pt counts when available (keyed with underscore prefix),
    # otherwise fall back to keyword-based approximation.
    sb_2pt_count = action_counts.get("_stepback_2pt", None)
    sb_3pt_count = action_counts.get("_stepback_3pt", None)
    if sb_2pt_count is not None and sb_3pt_count is not None:
        stepback_mid = round(sb_2pt_count / games, 3)
        stepback_3   = round(sb_3pt_count / games, 3)
    else:
        stepback_all = freq(["step back"])
        # "step back jump shot" matches ALL step-back jump shots (both 2pt and 3pt),
        # so without SHOT_TYPE we cannot reliably split; keep legacy approximation.
        stepback_jump = freq(["step back jump shot"])
        stepback_mid  = max(round(stepback_all - stepback_jump, 3), 0)
        stepback_3    = stepback_jump

    return {
        "stepback_mid":      stepback_mid,
        "stepback_3":        stepback_3,
        # "turnaround" covers turnaround fadeaways which are post moves, not 2K spin jumpers.
        # There is no reliable NBA action type that maps to 2K's spin jumper concept.
        "spin_jumper":       0,
        "spin_layup":        freq(["reverse layup", "reverse dunk"]),
        "euro_step":         freq(["euro"]),
        "hop_step":          freq(["hop"]),
        # "Floating Jump Shot" is too broad — only count true floaters (keyword "floater").
        "floater":           freq(["floater"]),
        "step_through":      freq(["step through"]),
        "alley_oop_finish":  freq(["alley oop"]),
        "driving_layup":     freq(["driving layup", "driving finger roll"]),
        "driving_dunk":      freq(["driving dunk"]),
        "pullup_mid":        freq(["pullup"]),
        "pullup_3":          freq(["pullup jump shot"]),
        "fadeaway":          freq(["fadeaway"]),
        "hook":              freq(["hook"]),
        "putback":           freq(["putback"]),
        "tip":               freq(["tip"]),
        "dunk":              freq(["dunk"]),
        "layup":             freq(["layup"]),
    }
