"""
Simplified PBP parser.
Since full BBRef play-by-play scraping is fragile, this module
returns best-effort defaults (position-based) that the calculator
can refine with available tracking data.
"""


_POSITION_DEFAULTS = {
    "PG": {
        "stepback_mid":     0.4,
        "stepback_3":       0.3,
        "spin_jumper":      0.1,
        "spin_layup":       0.3,
        "euro_step":        0.4,
        "hop_step":         0.3,
        "floater":          0.5,
        "step_through":     0.1,
        "alley_oop_finish": 0.1,
        "alley_oop_pass":   0.2,
    },
    "SG": {
        "stepback_mid":     0.3,
        "stepback_3":       0.3,
        "spin_jumper":      0.1,
        "spin_layup":       0.3,
        "euro_step":        0.3,
        "hop_step":         0.3,
        "floater":          0.3,
        "step_through":     0.1,
        "alley_oop_finish": 0.2,
        "alley_oop_pass":   0.1,
    },
    "SF": {
        "stepback_mid":     0.2,
        "stepback_3":       0.2,
        "spin_jumper":      0.1,
        "spin_layup":       0.2,
        "euro_step":        0.2,
        "hop_step":         0.2,
        "floater":          0.2,
        "step_through":     0.2,
        "alley_oop_finish": 0.2,
        "alley_oop_pass":   0.1,
    },
    "PF": {
        "stepback_mid":     0.1,
        "stepback_3":       0.1,
        "spin_jumper":      0.1,
        "spin_layup":       0.2,
        "euro_step":        0.2,
        "hop_step":         0.2,
        "floater":          0.1,
        "step_through":     0.2,
        "alley_oop_finish": 0.3,
        "alley_oop_pass":   0.0,
    },
    "C": {
        "stepback_mid":     0.0,
        "stepback_3":       0.0,
        "spin_jumper":      0.0,
        "spin_layup":       0.2,
        "euro_step":        0.1,
        "hop_step":         0.1,
        "floater":          0.0,
        "step_through":     0.3,
        "alley_oop_finish": 0.5,
        "alley_oop_pass":   0.0,
    },
}

_DEFAULT = _POSITION_DEFAULTS["SG"]


def parse_pbp_moves(bbref_id, season_year="2024", position=None):
    """
    Returns per-game move counts.
    Uses position-based defaults as a best-effort estimation.
    """
    pos = (position or "SG").upper()
    defaults = _POSITION_DEFAULTS.get(pos, _DEFAULT)
    return dict(defaults)
