"""
Compute directional shot tendency values from NBA API shot-zone data.
"""


def _round5(v):
    return max(0, round(v / 5) * 5)


def _zone_cap(parent_value):
    """Compute the dynamic cap for a directional zone: max(parent - 10, 15), rounded to 5."""
    return max((parent_value - 10) // 5 * 5, 15)


def _zone_stats(shot_zones, basic_filter, area_filter=None):
    """Sum fga/fgm for zones matching the given filters."""
    fga = fgm = 0
    for key, data in shot_zones.items():
        parts = key.split("|")
        basic = parts[0] if len(parts) > 0 else ""
        area  = parts[1] if len(parts) > 1 else ""
        if basic_filter and basic_filter.lower() not in basic.lower():
            continue
        if area_filter and area_filter.lower() not in area.lower():
            continue
        fga += data.get("fga", 0)
        fgm += data.get("fgm", 0)
    return fga, fgm


def compute_zone_tendencies(
    shot_zones,
    parent_shot=None,
    parent_mid=None,
    parent_three=None,
    zone_area_close=None,
    zone_area_mid=None,
    zone_area_three=None,
):
    """
    Compute directional shot tendency values.

    When zone_area_* dicts are provided (from shotdetail_loader), they supply
    real L/LC/C/RC/R frequency percentages and are used as the primary source
    for distributing zone tendencies.  The NBA-API shot_zones dict remains the
    fallback for volume/accuracy weighting when the area dicts are absent.
    """
    parent_shot  = parent_shot  or 50
    parent_mid   = parent_mid   or 30
    parent_three = parent_three or 40

    cap_close = _zone_cap(parent_shot)
    cap_mid   = _zone_cap(parent_mid)
    cap_three = _zone_cap(parent_three)

    # ── Close zones ────────────────────────────────────────────────
    if zone_area_close:
        close_results = _distribute_from_area(
            zone_area_close,
            {
                "shot_close_left":   "Left Side(L)",
                "shot_close_middle": "Center(C)",
                "shot_close_right":  "Right Side(R)",
            },
            cap_close,
        )
    elif shot_zones:
        close_groups = {
            "shot_close_left":   ("Restricted Area", "Left Side(L)"),
            "shot_close_middle": ("Restricted Area", "Center(C)"),
            "shot_close_right":  ("Restricted Area", "Right Side(R)"),
        }
        close_results = _distribute_group(shot_zones, close_groups, cap_close)
    else:
        close_results = {k: cap_close for k in ("shot_close_left", "shot_close_middle", "shot_close_right")}

    # ── Mid zones ──────────────────────────────────────────────────
    if zone_area_mid:
        mid_results = _distribute_from_area(
            zone_area_mid,
            {
                "shot_mid_left":         "Left Side(L)",
                "shot_mid_left_center":  "Left Side Center(LC)",
                "shot_mid_center":       "Center(C)",
                "shot_mid_right_center": "Right Side Center(RC)",
                "shot_mid_right":        "Right Side(R)",
            },
            cap_mid,
        )
    elif shot_zones:
        mid_groups = {
            "shot_mid_left":         ("Mid-Range", "Left Side(L)"),
            "shot_mid_left_center":  ("Mid-Range", "Left Side Center(LC)"),
            "shot_mid_center":       ("Mid-Range", "Center(C)"),
            "shot_mid_right_center": ("Mid-Range", "Right Side Center(RC)"),
            "shot_mid_right":        ("Mid-Range", "Right Side(R)"),
        }
        mid_results = _distribute_group(shot_zones, mid_groups, cap_mid)
    else:
        mid_results = {
            k: cap_mid
            for k in ("shot_mid_left", "shot_mid_left_center", "shot_mid_center",
                      "shot_mid_right_center", "shot_mid_right")
        }

    # ── Three zones ────────────────────────────────────────────────
    if zone_area_three:
        three_results = _distribute_from_area(
            zone_area_three,
            {
                "shot_three_left":         "Left Side(L)",
                "shot_three_left_center":  "Left Side Center(LC)",
                "shot_three_center":       "Center(C)",
                "shot_three_right_center": "Right Side Center(RC)",
                "shot_three_right":        "Right Side(R)",
            },
            cap_three,
        )
    elif shot_zones:
        three_groups = {
            "shot_three_left":         ("Left Corner 3", None),
            "shot_three_left_center":  ("Above the Break 3", "Left Side Center(LC)"),
            "shot_three_center":       ("Above the Break 3", "Center(C)"),
            "shot_three_right_center": ("Above the Break 3", "Right Side Center(RC)"),
            "shot_three_right":        ("Right Corner 3", None),
        }
        three_results = _distribute_group(shot_zones, three_groups, cap_three)
    else:
        three_results = {
            k: cap_three
            for k in ("shot_three_left", "shot_three_left_center", "shot_three_center",
                      "shot_three_right_center", "shot_three_right")
        }

    return {**close_results, **mid_results, **three_results}


def _distribute_from_area(zone_area, label_to_area, cap):
    """
    Distribute zone tendencies using real area frequency percentages.
    zone_area: dict mapping area name -> frequency (0..1)
    label_to_area: dict mapping output label -> area name key
    """
    total_freq = sum(zone_area.get(a, 0) for a in label_to_area.values())
    results = {}
    for label, area_name in label_to_area.items():
        freq = zone_area.get(area_name, 0)
        vol = freq / total_freq if total_freq > 0 else 1 / len(label_to_area)  # equal split when no data
        raw = vol * cap * len(label_to_area)
        results[label] = _round5(max(min(raw, cap), 0))
    return results


def _distribute_group(shot_zones, groups, cap):
    raw_scores = {}
    total_fga = 0
    for label, (basic_f, area_f) in groups.items():
        fga, fgm = _zone_stats(shot_zones, basic_f, area_f)
        fg_pct = fgm / fga if fga > 0 else 0
        raw_scores[label] = {"fga": fga, "fg_pct": fg_pct}
        total_fga += fga

    results = {}
    for label, data in raw_scores.items():
        vol  = data["fga"] / total_fga if total_fga > 0 else 1 / len(groups)
        pref = 0.7 * vol + 0.3 * data["fg_pct"]
        # Scale: pref is in [0,1] roughly; map to [0, cap]
        raw = pref * cap * len(groups)
        capped = min(raw, cap)
        results[label] = _round5(max(capped, 0))

    return results


def _equal_defaults(parent_shot, parent_mid, parent_three):
    parent_shot  = parent_shot  or 50
    parent_mid   = parent_mid   or 30
    parent_three = parent_three or 40

    cap_close = _zone_cap(parent_shot)
    cap_mid   = _zone_cap(parent_mid)
    cap_three = _zone_cap(parent_three)

    return {
        "shot_close_left":         cap_close,
        "shot_close_middle":       cap_close,
        "shot_close_right":        cap_close,
        "shot_mid_left":           cap_mid,
        "shot_mid_left_center":    cap_mid,
        "shot_mid_center":         cap_mid,
        "shot_mid_right_center":   cap_mid,
        "shot_mid_right":          cap_mid,
        "shot_three_left":         cap_three,
        "shot_three_left_center":  cap_three,
        "shot_three_center":       cap_three,
        "shot_three_right_center": cap_three,
        "shot_three_right":        cap_three,
    }
