"""
Main tendency calculation engine.
"""
import math

from engine.caps_enforcer import enforce_caps
from engine.constants import HARD_CAPS, TENDENCY_ORDER

# ── Helpers ────────────────────────────────────────────────────────────────


def _round5(v):
    return round(v / 5) * 5


def _clamp(v, lo=0, hi=100):
    return max(lo, min(hi, v))


def _safe(v, default=0):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return default
    try:
        return float(v)
    except Exception:
        return default


def percentile_to_tendency(value, all_values, cap, min_val=0):
    """
    Map *value* into [min_val, cap] based on its percentile in all_values.
    Returns a value rounded to nearest 5.
    """
    if not all_values:
        return _round5(_clamp(min_val, min_val, cap))
    cleaned = [v for v in all_values if v is not None and not math.isnan(v)]
    if not cleaned:
        return _round5(_clamp(min_val, min_val, cap))
    pct = sum(1 for x in cleaned if x <= value) / len(cleaned)
    raw = min_val + pct * (cap - min_val)
    return _round5(_clamp(raw, min_val, cap))


# ── Position helpers ────────────────────────────────────────────────────────

def _is_big(pos):
    return pos in ("C", "PF")


def _is_guard(pos):
    return pos in ("PG", "SG")


def _is_wing(pos):
    return pos in ("SF",)


# ── Reference distributions (rough league-wide baselines for percentile calc) ─

_USG_DIST    = [15, 17, 18, 20, 21, 22, 23, 24, 25, 27, 30, 33]
_TOUCH_DIST  = [20, 30, 40, 50, 60, 70, 80, 90]
_FGA_DIST    = [6, 8, 10, 12, 14, 16, 18, 20]
_DRIVES_DIST = [0, 1, 2, 3, 5, 7, 10, 15]
_STL_DIST    = [0.3, 0.5, 0.7, 0.9, 1.1, 1.5, 2.0]
_BLK_DIST    = [0.1, 0.3, 0.5, 0.8, 1.2, 2.0, 3.0]
_PF_DIST     = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
_AST_PCT_DIST = [5, 10, 15, 20, 25, 30, 35, 40]


# ── Core calculator ────────────────────────────────────────────────────────

def calculate_tendencies(player_data):
    pos      = str(player_data.get("position") or "SG").upper().strip()
    per_game = player_data.get("per_game")       or {}
    adv      = player_data.get("advanced")       or {}
    splits   = player_data.get("shooting_splits") or {}
    tracking = player_data.get("tracking")        or {}
    pbp      = player_data.get("pbp_moves")       or {}

    # Guard against non-dict types
    if not isinstance(per_game, dict): per_game = {}
    if not isinstance(adv,      dict): adv      = {}
    if not isinstance(splits,   dict): splits   = {}
    if not isinstance(tracking, dict): tracking = {}
    if not isinstance(pbp,      dict): pbp      = {}

    # ── Raw stats ──────────────────────────────────────────────────
    pts      = _safe(per_game.get("pts"),     15.0)
    reb      = _safe(per_game.get("reb"),      4.0)
    ast      = _safe(per_game.get("ast"),      3.0)
    stl      = _safe(per_game.get("stl"),      0.8)
    blk      = _safe(per_game.get("blk"),      0.5)
    pf       = _safe(per_game.get("pf"),       2.5)
    fga      = _safe(per_game.get("fga"),     12.0)
    fg3a     = _safe(per_game.get("fg3a"),     3.0)
    fta      = _safe(per_game.get("fta"),      3.0)
    ft_pct   = _safe(per_game.get("ft_pct"),   0.75)
    mp       = _safe(per_game.get("mp"),      25.0)
    g        = _safe(per_game.get("g"),        60.0)

    usg_pct  = _safe(adv.get("usg_pct"),      20.0)
    ast_pct  = _safe(adv.get("ast_pct"),      15.0)
    orb_pct  = _safe(adv.get("orb_pct"),       5.0)
    ts_pct   = _safe(adv.get("ts_pct"),        0.55)
    per      = _safe(adv.get("per"),          15.0)
    bpm      = _safe(adv.get("bpm"),           0.0)

    p0_3    = _safe(splits.get("pct_fga_0_3"),    None)
    p3_10   = _safe(splits.get("pct_fga_3_10"),   None)
    p10_16  = _safe(splits.get("pct_fga_10_16"),  None)
    p16_3pt = _safe(splits.get("pct_fga_16_3pt"), None)
    p3pt    = _safe(splits.get("pct_fga_3pt"),    None)

    # Position-based split defaults when data is missing
    if p0_3 is None:
        if _is_big(pos):   p0_3 = 0.35
        elif _is_guard(pos): p0_3 = 0.25
        else:              p0_3 = 0.28
    if p3_10 is None:
        if _is_big(pos):   p3_10 = 0.20
        else:              p3_10 = 0.15
    if p10_16 is None:
        p10_16 = 0.12 if _is_guard(pos) else 0.14
    if p16_3pt is None:
        p16_3pt = 0.12 if _is_guard(pos) else 0.10
    if p3pt is None:
        if _is_big(pos):   p3pt = 0.05
        elif _is_guard(pos): p3pt = 0.38
        else:              p3pt = 0.30

    touches   = _safe(tracking.get("touches_per_game"),      None)
    drives    = _safe(tracking.get("drives_per_game"),        None)
    pull_mid  = _safe(tracking.get("pull_up_mid_fga"),        None)
    pull_3    = _safe(tracking.get("pull_up_3_fga"),          None)
    cs_mid    = _safe(tracking.get("catch_shoot_mid_fga"),    None)
    cs_3      = _safe(tracking.get("catch_shoot_3_fga"),      None)
    os_fga    = _safe(tracking.get("off_screen_fga"),         None)
    os_3_fga  = _safe(tracking.get("off_screen_3_fga"),       None)
    su_drive  = _safe(tracking.get("spot_up_drive_freq"),     None)
    os_drive  = _safe(tracking.get("off_screen_drive_freq"),  None)
    con_mid   = _safe(tracking.get("contested_mid_fga_pct"),  None)
    con_3     = _safe(tracking.get("contested_3_fga_pct"),    None)
    trans_3   = _safe(tracking.get("transition_3_fga"),       None)
    post_freq = _safe(tracking.get("post_up_freq"),           None)
    iso_freq  = _safe(tracking.get("iso_freq"),               None)
    roll_pct  = _safe(tracking.get("pnr_roll_pct"),           None)
    avg_drib  = _safe(tracking.get("avg_dribbles_before_shot"), None)
    and1      = _safe(tracking.get("and1_rate"),              None)
    deflects  = _safe(tracking.get("deflections_per_game"),   None)
    contested = _safe(tracking.get("contested_shots_per_game"), None)
    charges   = _safe(tracking.get("charges_drawn_per_game"), None)

    # Position-based tracking defaults
    if touches is None:
        if _is_guard(pos):   touches = 60.0
        elif _is_wing(pos):  touches = 45.0
        else:                touches = 40.0
    if drives is None:
        if pos == "PG":      drives = 8.0
        elif pos == "SG":    drives = 5.0
        elif pos == "SF":    drives = 4.0
        else:                drives = 2.0

    # PBP moves
    stepback_mid    = _safe(pbp.get("stepback_mid"),    0)
    stepback_3      = _safe(pbp.get("stepback_3"),      0)
    spin_jumper     = _safe(pbp.get("spin_jumper"),     0)
    spin_layup      = _safe(pbp.get("spin_layup"),      0)
    euro_step       = _safe(pbp.get("euro_step"),       0)
    hop_step        = _safe(pbp.get("hop_step"),        0)
    floater_pbp     = _safe(pbp.get("floater"),         0)
    step_through    = _safe(pbp.get("step_through"),    0)
    ao_finish       = _safe(pbp.get("alley_oop_finish"), 0)
    ao_pass         = _safe(pbp.get("alley_oop_pass"),  0)

    T = {}  # tendencies dict

    # ──────────────────────────────────────────────────────────────
    # 1. SHOT (75)
    T["Shot"] = _round5(_clamp(usg_pct * 0.75 * (75 / 33), 20, 75))

    # 2. TOUCH (65)
    T["Touch"] = percentile_to_tendency(touches, _TOUCH_DIST, 65, 20)

    # 3. SHOT CLOSE (60) – pct_fga_3_10
    T["Shot Close"] = _round5(_clamp(p3_10 * 180, 10, 60))

    # 4. SHOT UNDER (60) – pct_fga_0_3
    T["Shot Under"] = _round5(_clamp(p0_3 * 180, 15, 60))

    # 5. SHOT MID (55)
    mid_pct = p10_16 + p16_3pt
    T["Shot Mid"] = _round5(_clamp(mid_pct * 200, 10, 55))

    # 6. SPOT-UP SHOT MID (45) <= Shot Mid
    cs_mid_val = cs_mid if cs_mid is not None else fga * 0.15
    T["Spot-Up Shot Mid"] = _round5(_clamp(cs_mid_val * 5, 10, 45))

    # 7. OFF-SCREEN MID (40) <= Shot Mid
    os_val = os_fga if os_fga is not None else fga * 0.08
    T["Off-Screen Mid"] = _round5(_clamp(os_val * 6, 5, 40))

    # 8. SHOT THREE (60)
    three_ratio = fg3a / fga if fga > 0 else 0
    T["Shot Three"] = _round5(_clamp(three_ratio * 120, 5, 60))

    # 9. SPOT-UP THREE (60)
    cs_3_val = cs_3 if cs_3 is not None else fg3a * 0.4
    T["Spot-Up Three"] = _round5(_clamp(cs_3_val * 8, 5, 60))

    # 10. OFF-SCREEN THREE (55)
    os_3_val = os_3_fga if os_3_fga is not None else fg3a * 0.1
    T["Off-Screen Three"] = _round5(_clamp(os_3_val * 10, 5, 55))

    # 11. CONTESTED JUMPER MID (45)
    con_mid_v = con_mid if con_mid is not None else 0.25
    T["Contested Jumper Mid"] = _round5(_clamp(con_mid_v * 100, 10, 45))

    # 12. CONTESTED JUMPER THREE (40)
    con_3_v = con_3 if con_3 is not None else 0.20
    T["Contested Jumper Three"] = _round5(_clamp(con_3_v * 80, 5, 40))

    # 13. STEP-BACK MID (40 LOCKED)
    T["Step-Back Jumper Mid"] = _round5(_clamp(stepback_mid * 30, 5, 40))

    # 14. STEP-BACK THREE (35 LOCKED)
    T["Step-Back Jumper Three"] = _round5(_clamp(stepback_3 * 25, 5, 35))

    # 15. SPIN JUMPER (45)
    T["Spin Jumper"] = _round5(_clamp(spin_jumper * 40, 5, 45))

    # 16. TRANSITION PULL-UP THREE (45)
    trans_3_v = trans_3 if trans_3 is not None else fg3a * 0.05
    T["Transition Pull-Up Three"] = _round5(_clamp(trans_3_v * 15, 5, 45))

    # 17. DRIBBLE PULL-UP MID (50)
    pull_mid_v = pull_mid if pull_mid is not None else fga * 0.15
    T["Dribble Pull-Up Mid"] = _round5(_clamp(pull_mid_v * 6, 10, 50))

    # 18. DRIBBLE PULL-UP THREE (40)
    pull_3_v = pull_3 if pull_3 is not None else fg3a * 0.10
    T["Dribble Pull-Up Three"] = _round5(_clamp(pull_3_v * 8, 5, 40))

    # 19. DRIVE (60)
    T["Drive"] = percentile_to_tendency(drives, _DRIVES_DIST, 60, 15)

    # 20. SPOT-UP DRIVE (55)
    su_v = su_drive if su_drive is not None else (drives * 0.1)
    T["Spot-Up Drive"] = _round5(_clamp(su_v * 50, 10, 55))

    # 21. OFF-SCREEN DRIVE (50)
    os_drive_v = os_drive if os_drive is not None else (drives * 0.05)
    T["Off-Screen Drive"] = _round5(_clamp(os_drive_v * 50, 5, 50))

    # 22. USE GLASS (55) – position default
    if pos == "C":     T["Use Glass"] = 25
    elif pos == "PF":  T["Use Glass"] = 20
    elif pos == "SF":  T["Use Glass"] = 20
    else:              T["Use Glass"] = 15

    # 23. STEP THROUGH SHOT (45)
    T["Step Through Shot"] = _round5(_clamp(step_through * 40, 5, 45))

    # 24. SPIN LAYUP (55)
    T["Spin Layup"] = _round5(_clamp(spin_layup * 40, 5, 55))

    # 25. EUROSTEP LAYUP (55)
    T["Eurostep Layup"] = _round5(_clamp(euro_step * 40, 5, 55))

    # 26. HOP STEP LAYUP (55)
    T["Hop Step Layup"] = _round5(_clamp(hop_step * 40, 5, 55))

    # 27. FLOATER (55)
    floater_v = floater_pbp if floater_pbp > 0 else (0.5 if _is_guard(pos) else 0.2)
    T["Floater"] = _round5(_clamp(floater_v * 50, 5, 55))

    # 28. STAND & DUNK (60)
    base_stand_dunk = {"C": 40, "PF": 35, "SF": 20, "SG": 15, "PG": 10}.get(pos, 15)
    if p0_3 > 0.3:
        base_stand_dunk = min(base_stand_dunk + 10, 60)
    T["Stand & Dunk"] = _round5(base_stand_dunk)

    # 29. DRIVE & DUNK (60)
    drive_dunk = percentile_to_tendency(drives, _DRIVES_DIST, 60, 10) * 0.6
    T["Drive & Dunk"] = _round5(_clamp(drive_dunk, 5, 60))

    # 30. FLASHY DUNK (55 LOCKED)
    flashy = 15
    if drives >= 7 and not _is_big(pos):
        flashy = 25
    elif drives >= 5:
        flashy = 20
    T["Flashy Dunk"] = _round5(_clamp(flashy, 5, 55))

    # 31. ALLEY-OOP (55 LOCKED)
    T["Alley-Oop"] = _round5(_clamp(ao_finish * 50, 5, 55))

    # 32. PUTBACK (55 LOCKED)
    T["Putback"] = _round5(_clamp(orb_pct * 3, 5, 55))

    # 33. CRASH (55)
    crash = 20
    if _is_big(pos):   crash = 30
    elif drives >= 6:  crash = 25
    T["Crash"] = _round5(_clamp(crash, 5, 55))

    # 34. DRIVE RIGHT (80) – no direct stat
    T["Drive Right"] = 55

    # 35-38. TRIPLE THREAT
    if _is_guard(pos):
        T["Triple Threat Pump Fake"] = 25
        T["Triple Threat Jab Step"]  = 20
    elif _is_wing(pos):
        T["Triple Threat Pump Fake"] = 20
        T["Triple Threat Jab Step"]  = 20
    else:
        T["Triple Threat Pump Fake"] = 15
        T["Triple Threat Jab Step"]  = 15
    T["Triple Threat Idle"]  = 20
    cs_shooter = (cs_3 or 0) + (cs_mid or 0)
    if cs_shooter > 3:
        T["Triple Threat Shoot"] = 35
    elif cs_shooter > 1:
        T["Triple Threat Shoot"] = 25
    else:
        T["Triple Threat Shoot"] = 20

    # 39-41. DRIBBLE SETUP
    is_creator = usg_pct >= 25 and drives >= 5
    if is_creator:
        T["Set Up with Size Up"]   = _round5(_clamp(usg_pct * 1.2, 20, 55))
        T["Set Up with Hesitation"] = _round5(_clamp(usg_pct * 1.1, 20, 55))
    else:
        T["Set Up with Size Up"]   = 15 if _is_big(pos) else 20
        T["Set Up with Hesitation"] = 15 if _is_big(pos) else 20

    # No Set Up Dribble – inverse of creativity
    avg_drib_v = avg_drib if avg_drib is not None else (1.5 if is_creator else 3.0)
    no_setup_raw = _clamp((5 - avg_drib_v) * 5 + 10, 15, 35)
    T["No Set Up Dribble"] = _round5(no_setup_raw)

    # 42-49. DRIVE MOVES
    if is_creator:
        base_drive_move = 30
    elif _is_guard(pos):
        base_drive_move = 20
    elif _is_wing(pos):
        base_drive_move = 15
    else:
        base_drive_move = 10

    T["Drive and Crossover"]           = _round5(_clamp(base_drive_move,      5, 55))
    T["Drive and Double Crossover"]     = _round5(_clamp(base_drive_move - 10, 5, 55))
    T["Drive and Spin"]                = _round5(_clamp(base_drive_move - 10, 5, 55))
    T["Drive and Half Spin"]           = _round5(_clamp(base_drive_move - 5,  5, 55))
    T["Drive and Step Back"]           = _round5(_clamp(base_drive_move - 5,  5, 55))
    T["Drive and Behind the Back"]     = _round5(_clamp(base_drive_move - 10, 5, 55))
    T["Drive and Dribble Hesitation"]  = _round5(_clamp(base_drive_move - 5,  5, 55))
    T["Drive and In and Out"]          = _round5(_clamp(base_drive_move - 10, 5, 55))

    # 50. NO DRIVE & DRIBBLE MOVE (85)
    if _is_big(pos):        no_drive_move = 60
    elif is_creator:        no_drive_move = 35
    elif _is_guard(pos):    no_drive_move = 40
    else:                   no_drive_move = 50
    T["No Drive & Dribble Move"] = _round5(no_drive_move)

    # 51. ATTACK STRONG ON DRIVE (60)
    attack_strong = 35 if not _is_big(pos) else 25
    T["Attack Strong on Drive"] = _round5(attack_strong)

    # 52. DISH TO OPEN MAN (55)
    T["Dish to Open Man"] = percentile_to_tendency(ast_pct, _AST_PCT_DIST, 55, 15)

    # 53. FLASHY PASS (55)
    T["Flashy Pass"] = 15

    # 54. ALLEY-OOP PASS (55)
    T["Alley-Oop Pass"] = _round5(_clamp(ao_pass * 50, 5, 55))

    # 55. ROLL VS POP (85)
    if roll_pct is not None:
        T["Roll vs Pop"] = _round5(_clamp(roll_pct * 85, 20, 85))
    else:
        T["Roll vs Pop"] = 60 if _is_big(pos) else 40

    # 56. TRANSITION SPOT UP VS CUT (85)
    spot_up_tend = cs_3_val / max(fg3a, 1) if fg3a > 0 else 0.5
    T["Transition Spot Up vs Cut to Basket"] = _round5(_clamp(40 + spot_up_tend * 40, 30, 85))

    # 57-60. ISOLATION
    if iso_freq is not None:
        iso_base = _clamp(iso_freq * 4, 5, 55)
    else:
        iso_base = 30 if is_creator else 15
    T["Isolation vs Elite"]   = _round5(_clamp(iso_base * 0.5, 5, 55))
    T["Isolation vs Good"]    = _round5(_clamp(iso_base * 0.7, 5, 55))
    T["Isolation vs Average"] = _round5(_clamp(iso_base * 0.85, 5, 55))
    T["Isolation vs Poor"]    = _round5(_clamp(iso_base, 5, 55))

    # 61. PLAY DISCIPLINE (75)
    ast_to = ast / max(per_game.get("tov", ast * 0.3) if isinstance(per_game, dict) else ast * 0.3, 0.1)
    disc = _clamp(40 + ast_to * 5, 35, 70)
    T["Play Discipline"] = _round5(disc)

    # 62-77. POST
    if post_freq is not None:
        post_up_val = _clamp(post_freq * 100, 5, 60)
    else:
        post_up_val = {"C": 40, "PF": 30, "SF": 15, "SG": 10, "PG": 10}.get(pos, 10)
    T["Post Up"] = _round5(post_up_val)

    # Distribute sub-tendencies based on post_up_val
    post_base = _round5(post_up_val * 0.7)
    post_low  = max(_round5(post_up_val * 0.4), 10)
    is_post_player = post_up_val >= 25

    T["Post Back Down"]              = _round5(_clamp(post_base, 10, 60))
    T["Post Aggressive Back Down"]   = _round5(_clamp(post_low,  10, 60))
    T["Post Face Up"]                = _round5(_clamp(post_low,  10, 55))
    T["Post Spin"]                   = _round5(_clamp(post_low,  10, 60))
    T["Post Drive"]                  = _round5(_clamp(post_low,  10, 60))
    T["Post Drop Step"]              = _round5(_clamp(post_base if _is_big(pos) else post_low, 10, 60))
    T["Shoot From Post"]             = _round5(_clamp(post_base, 10, 60))
    T["Post Hook Left"]              = _round5(_clamp(post_base if _is_big(pos) else post_low, 10, 60))
    T["Post Hook Right"]             = _round5(_clamp(post_base if _is_big(pos) else post_low, 10, 60))
    T["Post Fade Left"]              = _round5(_clamp(post_low,  10, 60))
    T["Post Fade Right"]             = _round5(_clamp(post_low,  10, 60))
    T["Post Shimmy Shot"]            = _round5(_clamp(post_low,  10, 60))
    T["Post Hop Shot"]               = _round5(_clamp(post_low,  10, 60))
    T["Post Step Back Shot"]         = _round5(_clamp(post_low,  10, 60))
    T["Post Up and Under"]           = _round5(_clamp(post_low,  10, 60))

    # 78. TAKES CHARGE (60)
    charges_v = charges if charges is not None else 0.1
    T["Takes Charge"] = _round5(_clamp(charges_v * 100, 5, 60))

    # 79. FOUL (60)
    T["Foul"] = percentile_to_tendency(pf, _PF_DIST, 60, 10)

    # 80. HARD FOUL (55)
    T["Hard Foul"] = 15 if pf < 3 else 20

    # 81. PASS INTERCEPTION (60)
    defl_v = deflects if deflects is not None else stl * 0.8
    T["Pass Interception"] = _round5(_clamp(defl_v * 40, 10, 60))

    # 82. ON-BALL STEAL (60)
    T["On-Ball Steal"] = percentile_to_tendency(stl, _STL_DIST, 60, 10)

    # 83. BLOCKED SHOT (60)
    T["Blocked Shot"] = percentile_to_tendency(blk, _BLK_DIST, 60, 5)

    # 84. CONTEST SHOT (60)
    cont_v = contested if contested is not None else (_clamp(blk * 2 + stl, 0.5, 6))
    T["Contest Shot"] = _round5(_clamp(cont_v * 8, 10, 60))

    # ── Enforce caps and ordering ──────────────────────────────────
    T = enforce_caps(T)

    # Return in canonical order
    return {name: T.get(name, 0) for name in TENDENCY_ORDER}


# ── Orchestration function ────────────────────────────────────────────────

def generate_tendencies_for_player(player_id, player_name, season="2024-25"):
    """
    Orchestrates all data fetching and calculation.
    Always returns a valid result even if external APIs are down.
    """
    from engine import nba_stats, scraper, pbp_parser, zone_distributor

    tracking   = {}
    shot_zones = {}
    bbref_data = {}
    pbp_moves  = {}
    player_info = {"name": player_name, "team": "", "position": "SG"}

    # Fetch player info
    try:
        player_info = nba_stats.get_player_info(player_id)
        if not player_info.get("name"):
            player_info["name"] = player_name
    except Exception:
        pass

    position = player_info.get("position") or "SG"
    # Normalize position (sometimes comes as "Guard" or multi-position)
    pos_map = {"Guard": "SG", "Forward": "SF", "Center": "C",
               "Point Guard": "PG", "Shooting Guard": "SG",
               "Small Forward": "SF", "Power Forward": "PF"}
    position = pos_map.get(position, position)
    if "-" in position:
        position = position.split("-")[0].strip()
    if "/" in position:
        position = position.split("/")[0].strip()

    # Fetch tracking stats
    try:
        tracking = nba_stats.get_tracking_stats(player_id, season=season)
    except Exception:
        pass

    # Fetch shot zones
    try:
        shot_zones = nba_stats.get_shot_zones(player_id, season=season)
    except Exception:
        pass

    # Fetch BBRef stats
    try:
        bbref_data = scraper.get_player_stats(player_name, player_id=player_id, season=season)
    except Exception:
        pass

    # PBP moves
    try:
        pbp_moves = pbp_parser.parse_pbp_moves(None, season_year=season.split("-")[0], position=position)
    except Exception:
        pass

    # Build player_data dict
    player_data = {
        "player_id": player_id,
        "name":      player_info.get("name", player_name),
        "position":  position,
        "team":      player_info.get("team", ""),
        "per_game":  bbref_data.get("per_game",        {}),
        "advanced":  bbref_data.get("advanced",        {}),
        "shooting_splits": bbref_data.get("shooting_splits", {}),
        "tracking":  tracking,
        "shot_zones": shot_zones,
        "pbp_moves": pbp_moves,
    }

    tendencies = calculate_tendencies(player_data)

    return {
        "player_id": player_id,
        "name":      player_data["name"],
        "team":      player_data["team"],
        "position":  position,
        "tendencies": tendencies,
    }
