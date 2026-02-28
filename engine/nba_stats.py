import time

from engine.constants import SEASON


def _sleep():
    time.sleep(0.6)


def get_tracking_stats(player_id, season=SEASON):
    result = {
        "touches_per_game":       None,
        "drives_per_game":        None,
        "pull_up_mid_fga":        None,
        "pull_up_3_fga":          None,
        "catch_shoot_mid_fga":    None,
        "catch_shoot_3_fga":      None,
        "off_screen_fga":         None,
        "off_screen_3_fga":       None,
        "spot_up_drive_freq":     None,
        "off_screen_drive_freq":  None,
        "contested_mid_fga_pct":  None,
        "contested_3_fga_pct":    None,
        "transition_3_fga":       None,
        "post_up_freq":           None,
        "iso_freq":               None,
        "pnr_roll_pct":           None,
        "avg_dribbles_before_shot": None,
        "and1_rate":              None,
        "deflections_per_game":   None,
        "contested_shots_per_game": None,
        "charges_drawn_per_game": None,
    }

    try:
        from nba_api.stats.endpoints import playerdashptstats
        _sleep()
        touch_data = playerdashptstats.PlayerDashPtStats(
            player_id=player_id,
            season=season,
            per_mode_simple="PerGame",
        )
        _sleep()
        dfs = touch_data.get_data_frames()
        if dfs:
            df = dfs[0]
            if not df.empty:
                row = df.iloc[0]
                result["touches_per_game"] = _safe_float(row, "TOUCHES")
    except Exception:
        pass

    try:
        from nba_api.stats.endpoints import playerdashptshots
        _sleep()
        shot_data = playerdashptshots.PlayerDashPtShots(
            player_id=player_id,
            season=season,
            per_mode_simple="PerGame",
        )
        _sleep()
        dfs = shot_data.get_data_frames()
        for df in dfs:
            if df.empty:
                continue
            if "SHOT_TYPE" not in df.columns and "GENERAL_RANGE" not in df.columns:
                continue
            if "GENERAL_RANGE" in df.columns:
                for _, row in df.iterrows():
                    rng = str(row.get("GENERAL_RANGE", ""))
                    fga = _safe_float(row, "FGA_FREQUENCY") or 0
                    if "Pull-Ups" in rng or "Pullups" in rng:
                        # split by distance
                        result["pull_up_mid_fga"] = (result["pull_up_mid_fga"] or 0) + fga
                    if "Catch" in rng:
                        result["catch_shoot_mid_fga"] = (result["catch_shoot_mid_fga"] or 0) + fga
    except Exception:
        pass

    try:
        from nba_api.stats.endpoints import playerdashptpass
        _sleep()
        pass_data = playerdashptpass.PlayerDashPtPass(
            player_id=player_id,
            season=season,
            per_mode_simple="PerGame",
        )
        _sleep()
        dfs = pass_data.get_data_frames()
        if len(dfs) > 1 and not dfs[1].empty:
            pass  # pass-received DataFrame not used currently; reserved for future expansion
    except Exception:
        pass  # silently skip — optional supplemental data

    try:
        from nba_api.stats.endpoints import playerdashptreb
        _sleep()
    except Exception:
        pass

    # Drives
    try:
        from nba_api.stats.endpoints import playerdashptshotdefend
        _sleep()
    except Exception:
        pass

    try:
        from nba_api.stats.endpoints import playerestimatedmetrics
        _sleep()
    except Exception:
        pass

    # Try synergy-style endpoints
    try:
        from nba_api.stats.endpoints import synergyplaytypes
        _sleep()
        syn = synergyplaytypes.SynergyPlayTypes(
            player_id=player_id,
            season=season,
            per_mode_simple="PerGame",
            play_type_nullable="Isolation",
        )
        _sleep()
        dfs = syn.get_data_frames()
        if dfs and not dfs[0].empty:
            row = dfs[0].iloc[0]
            result["iso_freq"] = _safe_float(row, "POSS_PCT")
    except Exception:
        pass

    try:
        from nba_api.stats.endpoints import synergyplaytypes
        _sleep()
        syn = synergyplaytypes.SynergyPlayTypes(
            player_id=player_id,
            season=season,
            per_mode_simple="PerGame",
            play_type_nullable="Postup",
        )
        _sleep()
        dfs = syn.get_data_frames()
        if dfs and not dfs[0].empty:
            row = dfs[0].iloc[0]
            result["post_up_freq"] = _safe_float(row, "POSS_PCT")
    except Exception:
        pass

    try:
        from nba_api.stats.endpoints import synergyplaytypes
        _sleep()
        syn = synergyplaytypes.SynergyPlayTypes(
            player_id=player_id,
            season=season,
            per_mode_simple="PerGame",
            play_type_nullable="PRRollMan",
        )
        _sleep()
        dfs = syn.get_data_frames()
        if dfs and not dfs[0].empty:
            row = dfs[0].iloc[0]
            result["pnr_roll_pct"] = _safe_float(row, "POSS_PCT")
    except Exception:
        pass

    try:
        from nba_api.stats.endpoints import playertracking
        _sleep()
        drv = playertracking.PlayerTracking(
            season=season,
            pt_measure_type="Drives",
            per_mode_simple="PerGame",
        )
        _sleep()
        dfs = drv.get_data_frames()
        if dfs and not dfs[0].empty:
            df = dfs[0]
            rows = df[df["PLAYER_ID"] == int(player_id)]
            if not rows.empty:
                row = rows.iloc[0]
                result["drives_per_game"] = _safe_float(row, "DRIVES")
    except Exception:
        pass

    try:
        from nba_api.stats.endpoints import playertracking
        _sleep()
        touches = playertracking.PlayerTracking(
            season=season,
            pt_measure_type="Touches",
            per_mode_simple="PerGame",
        )
        _sleep()
        dfs = touches.get_data_frames()
        if dfs and not dfs[0].empty:
            df = dfs[0]
            rows = df[df["PLAYER_ID"] == int(player_id)]
            if not rows.empty:
                row = rows.iloc[0]
                if result["touches_per_game"] is None:
                    result["touches_per_game"] = _safe_float(row, "TOUCHES")
    except Exception:
        pass

    try:
        from nba_api.stats.endpoints import playertracking
        _sleep()
        pullups = playertracking.PlayerTracking(
            season=season,
            pt_measure_type="PullUpShot",
            per_mode_simple="PerGame",
        )
        _sleep()
        dfs = pullups.get_data_frames()
        if dfs and not dfs[0].empty:
            df = dfs[0]
            rows = df[df["PLAYER_ID"] == int(player_id)]
            if not rows.empty:
                row = rows.iloc[0]
                result["pull_up_mid_fga"] = _safe_float(row, "PULL_UP_2_FGA")
                result["pull_up_3_fga"]   = _safe_float(row, "PULL_UP_3_FGA")
                result["avg_dribbles_before_shot"] = _safe_float(row, "AVG_DRIBBLES")
    except Exception:
        pass

    try:
        from nba_api.stats.endpoints import playertracking
        _sleep()
        catchshoot = playertracking.PlayerTracking(
            season=season,
            pt_measure_type="CatchShoot",
            per_mode_simple="PerGame",
        )
        _sleep()
        dfs = catchshoot.get_data_frames()
        if dfs and not dfs[0].empty:
            df = dfs[0]
            rows = df[df["PLAYER_ID"] == int(player_id)]
            if not rows.empty:
                row = rows.iloc[0]
                result["catch_shoot_3_fga"] = _safe_float(row, "CATCH_SHOOT_FGA")
    except Exception:
        pass

    try:
        from nba_api.stats.endpoints import playertracking
        _sleep()
        offscreen = playertracking.PlayerTracking(
            season=season,
            pt_measure_type="ElbowTouch",
            per_mode_simple="PerGame",
        )
    except Exception:
        pass

    try:
        from nba_api.stats.endpoints import playertracking
        _sleep()
        defended = playertracking.PlayerTracking(
            season=season,
            pt_measure_type="Defense",
            per_mode_simple="PerGame",
        )
        _sleep()
        dfs = defended.get_data_frames()
        if dfs and not dfs[0].empty:
            df = dfs[0]
            rows = df[df["PLAYER_ID"] == int(player_id)]
            if not rows.empty:
                row = rows.iloc[0]
                result["deflections_per_game"] = _safe_float(row, "DEFLECTIONS")
                result["contested_shots_per_game"] = _safe_float(row, "CONTESTED_SHOTS")
    except Exception:
        pass

    return result


def get_shot_zones(player_id, season=SEASON):
    zones = {}
    try:
        from nba_api.stats.endpoints import shotchartdetail
        _sleep()
        chart = shotchartdetail.ShotChartDetail(
            team_id=0,
            player_id=player_id,
            season_nullable=season,
            context_measure_simple="FGA",
        )
        _sleep()
        dfs = chart.get_data_frames()
        if not dfs or dfs[0].empty:
            return zones
        df = dfs[0]

        # Aggregate by zone_basic + zone_area
        for _, row in df.iterrows():
            basic = str(row.get("SHOT_ZONE_BASIC", ""))
            area  = str(row.get("SHOT_ZONE_AREA", ""))
            made  = int(row.get("SHOT_MADE_FLAG", 0))
            key = f"{basic}|{area}"
            if key not in zones:
                zones[key] = {"fga": 0, "fgm": 0}
            zones[key]["fga"] += 1
            zones[key]["fgm"] += made

        for key in zones:
            fga = zones[key]["fga"]
            fgm = zones[key]["fgm"]
            zones[key]["fg_pct"] = fgm / fga if fga > 0 else 0
    except Exception:
        pass
    return zones


def get_player_info(player_id):
    info = {"name": "", "team": "", "position": "", "height": "", "weight": ""}
    try:
        from nba_api.stats.endpoints import playerprofilev2
        _sleep()
        profile = playerprofilev2.PlayerProfileV2(player_id=player_id)
        _sleep()
        dfs = profile.get_data_frames()
        if dfs and not dfs[0].empty:
            row = dfs[0].iloc[0]
            info["name"]   = str(row.get("DISPLAY_FIRST_LAST", ""))
            info["team"]   = str(row.get("TEAM_ABBREVIATION", ""))
    except Exception:
        pass

    try:
        from nba_api.stats.static import players
        ps = players.find_player_by_id(player_id)
        if ps:
            info["name"] = ps.get("full_name", info["name"])
    except Exception:
        pass

    try:
        from nba_api.stats.endpoints import commonplayerinfo
        _sleep()
        cpi = commonplayerinfo.CommonPlayerInfo(player_id=player_id)
        _sleep()
        dfs = cpi.get_data_frames()
        if dfs and not dfs[0].empty:
            row = dfs[0].iloc[0]
            info["name"]     = str(row.get("DISPLAY_FIRST_LAST", info["name"]))
            info["team"]     = str(row.get("TEAM_ABBREVIATION", info["team"]))
            info["position"] = str(row.get("POSITION", ""))
            info["height"]   = str(row.get("HEIGHT", ""))
            info["weight"]   = str(row.get("WEIGHT", ""))
    except Exception:
        pass

    return info


def _safe_float(row, col):
    try:
        v = row[col]
        if v is None or str(v).strip() in ("", "None"):
            return None
        return float(v)
    except Exception:
        return None
