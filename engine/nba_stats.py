import time

from engine.constants import SEASON


def _sleep():
    time.sleep(1.0)


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
        "transition_freq":        None,
        "post_up_freq":           None,
        "iso_freq":               None,
        "pnr_roll_pct":           None,
        "avg_dribbles_before_shot": None,
        "and1_rate":              None,
        "deflections_per_game":   None,
        "contested_shots_per_game": None,
        "charges_drawn_per_game": None,
        "avg_speed":              None,
    }

    try:
        from nba_api.stats.endpoints import playerdashptshots
        _sleep()
        shot_data = playerdashptshots.PlayerDashPtShots(
            team_id=0,
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
    except Exception as e:
        print(f"[nba_stats] PlayerDashPtShots failed: {e}")

    try:
        from nba_api.stats.endpoints import playerdashptpass
        _sleep()
        pass_data = playerdashptpass.PlayerDashPtPass(
            team_id=0,
            player_id=player_id,
            season=season,
            per_mode_simple="PerGame",
        )
        _sleep()
        dfs = pass_data.get_data_frames()
        if len(dfs) > 1 and not dfs[1].empty:
            pass  # pass-received DataFrame not used currently; reserved for future expansion
    except Exception as e:
        print(f"[nba_stats] PlayerDashPtPass failed: {e}")

    try:
        from nba_api.stats.endpoints import playerdashptreb
        _sleep()
    except Exception as e:
        print(f"[nba_stats] playerdashptreb import failed: {e}")

    # Drives
    try:
        from nba_api.stats.endpoints import playerdashptshotdefend
        _sleep()
    except Exception as e:
        print(f"[nba_stats] playerdashptshotdefend import failed: {e}")

    try:
        from nba_api.stats.endpoints import playerestimatedmetrics
        _sleep()
    except Exception as e:
        print(f"[nba_stats] playerestimatedmetrics import failed: {e}")

    # Try synergy-style endpoints
    try:
        from nba_api.stats.endpoints import synergyplaytypes
        _sleep()
        syn = synergyplaytypes.SynergyPlayTypes(
            season=season,
            play_type_nullable="Isolation",
            per_mode_simple="PerGame",
            player_or_team_abbreviation="P",
            season_type_all_star="Regular Season",
            type_grouping_nullable="offensive",
        )
        _sleep()
        dfs = syn.get_data_frames()
        if dfs and not dfs[0].empty:
            df = dfs[0]
            rows = df[df["PLAYER_ID"] == int(player_id)]
            if not rows.empty:
                row = rows.iloc[0]
                result["iso_freq"] = _safe_float(row, "POSS_PCT")
    except Exception as e:
        print(f"[nba_stats] Isolation synergy failed: {e}")

    try:
        from nba_api.stats.endpoints import synergyplaytypes
        _sleep()
        syn = synergyplaytypes.SynergyPlayTypes(
            season=season,
            play_type_nullable="Postup",
            per_mode_simple="PerGame",
            player_or_team_abbreviation="P",
            season_type_all_star="Regular Season",
            type_grouping_nullable="offensive",
        )
        _sleep()
        dfs = syn.get_data_frames()
        if dfs and not dfs[0].empty:
            df = dfs[0]
            rows = df[df["PLAYER_ID"] == int(player_id)]
            if not rows.empty:
                row = rows.iloc[0]
                result["post_up_freq"] = _safe_float(row, "POSS_PCT")
    except Exception as e:
        print(f"[nba_stats] Postup synergy failed: {e}")

    try:
        from nba_api.stats.endpoints import synergyplaytypes
        _sleep()
        syn = synergyplaytypes.SynergyPlayTypes(
            season=season,
            play_type_nullable="PRRollMan",
            per_mode_simple="PerGame",
            player_or_team_abbreviation="P",
            season_type_all_star="Regular Season",
            type_grouping_nullable="offensive",
        )
        _sleep()
        dfs = syn.get_data_frames()
        if dfs and not dfs[0].empty:
            df = dfs[0]
            rows = df[df["PLAYER_ID"] == int(player_id)]
            if not rows.empty:
                row = rows.iloc[0]
                result["pnr_roll_pct"] = _safe_float(row, "POSS_PCT")
    except Exception as e:
        print(f"[nba_stats] PRRollMan synergy failed: {e}")

    # Drives
    try:
        from nba_api.stats.endpoints import leaguedashptstats
        _sleep()
        drv = leaguedashptstats.LeagueDashPtStats(
            season=season,
            pt_measure_type="Drives",
            per_mode_simple="PerGame",
            player_or_team="Player",
        )
        _sleep()
        dfs = drv.get_data_frames()
        if dfs and not dfs[0].empty:
            df = dfs[0]
            rows = df[df["PLAYER_ID"] == int(player_id)]
            if not rows.empty:
                row = rows.iloc[0]
                result["drives_per_game"] = _safe_float(row, "DRIVES")
    except Exception as e:
        print(f"[nba_stats] Drives tracking failed: {e}")

    # Touches (with retry and fallback measure type)
    for attempt in range(2):
        try:
            from nba_api.stats.endpoints import leaguedashptstats
            _sleep()
            touches = leaguedashptstats.LeagueDashPtStats(
                season=season,
                pt_measure_type="Passing",
                per_mode_simple="PerGame",
                player_or_team="Player",
            )
            _sleep()
            dfs = touches.get_data_frames()
            if dfs and not dfs[0].empty:
                df = dfs[0]
                if "PLAYER_ID" in df.columns:
                    rows = df[df["PLAYER_ID"] == int(player_id)]
                    if not rows.empty:
                        row = rows.iloc[0]
                        if result["touches_per_game"] is None:
                            t = _safe_float(row, "TOUCHES")
                            if t is None:
                                t = _safe_float(row, "FRONT_CT_TOUCHES")
                            if t is None:
                                t = _safe_float(row, "TIME_OF_POSS")
                            result["touches_per_game"] = t
            break
        except Exception as e:
            print(f"[nba_stats] Touches tracking attempt {attempt + 1} failed: {e}")
            if attempt == 0:
                time.sleep(3.0)

    # PullUpShot
    try:
        from nba_api.stats.endpoints import leaguedashptstats
        _sleep()
        pullups = leaguedashptstats.LeagueDashPtStats(
            season=season,
            pt_measure_type="PullUpShot",
            per_mode_simple="PerGame",
            player_or_team="Player",
        )
        _sleep()
        dfs = pullups.get_data_frames()
        if dfs and not dfs[0].empty:
            df = dfs[0]
            rows = df[df["PLAYER_ID"] == int(player_id)]
            if not rows.empty:
                row = rows.iloc[0]
                total_pullup_fga = _safe_float(row, "PULL_UP_FGA")
                pullup_3 = _safe_float(row, "PULL_UP_FG3A")
                if total_pullup_fga is not None and pullup_3 is not None:
                    result["pull_up_mid_fga"] = round(total_pullup_fga - pullup_3, 1)
                elif total_pullup_fga is not None:
                    result["pull_up_mid_fga"] = total_pullup_fga
                result["pull_up_3_fga"] = pullup_3
    except Exception as e:
        print(f"[nba_stats] PullUpShot tracking failed: {e}")

    # Average dribbles — from Possessions measure type
    if result["avg_dribbles_before_shot"] is None:
        try:
            from nba_api.stats.endpoints import leaguedashptstats
            _sleep()
            poss = leaguedashptstats.LeagueDashPtStats(
                season=season,
                pt_measure_type="Possessions",
                per_mode_simple="PerGame",
                player_or_team="Player",
            )
            _sleep()
            dfs = poss.get_data_frames()
            if dfs and not dfs[0].empty:
                df = dfs[0]
                if "PLAYER_ID" in df.columns:
                    rows = df[df["PLAYER_ID"] == int(player_id)]
                    if not rows.empty:
                        row = rows.iloc[0]
                        result["avg_dribbles_before_shot"] = (
                            _safe_float(row, "AVG_DRIB_PER_TOUCH")
                            if _safe_float(row, "AVG_DRIB_PER_TOUCH") is not None
                            else _safe_float(row, "AVG_SEC_PER_TOUCH")
                        )
        except Exception as e:
            print(f"[nba_stats] Possessions (dribbles) failed: {e}")

    # CatchShoot
    try:
        from nba_api.stats.endpoints import leaguedashptstats
        _sleep()
        catchshoot = leaguedashptstats.LeagueDashPtStats(
            season=season,
            pt_measure_type="CatchShoot",
            per_mode_simple="PerGame",
            player_or_team="Player",
        )
        _sleep()
        dfs = catchshoot.get_data_frames()
        if dfs and not dfs[0].empty:
            df = dfs[0]
            rows = df[df["PLAYER_ID"] == int(player_id)]
            if not rows.empty:
                row = rows.iloc[0]
                result["catch_shoot_3_fga"] = _safe_float(row, "CATCH_SHOOT_FG3A")
                total_cs_fga = _safe_float(row, "CATCH_SHOOT_FGA")
                cs_3 = result["catch_shoot_3_fga"]
                if total_cs_fga is not None and cs_3 is not None:
                    result["catch_shoot_mid_fga"] = round(total_cs_fga - cs_3, 1)
                elif total_cs_fga is not None:
                    result["catch_shoot_mid_fga"] = total_cs_fga
    except Exception as e:
        print(f"[nba_stats] CatchShoot tracking failed: {e}")

    # Defense
    try:
        from nba_api.stats.endpoints import leaguedashptstats
        _sleep()
        defended = leaguedashptstats.LeagueDashPtStats(
            season=season,
            pt_measure_type="Defense",
            per_mode_simple="PerGame",
            player_or_team="Player",
            player_id_nullable=player_id,
        )
        _sleep()
        dfs = defended.get_data_frames()
        if dfs and not dfs[0].empty:
            df = dfs[0]
            id_col = None
            for col_name in ["PLAYER_ID", "player_id", "Player_ID"]:
                if col_name in df.columns:
                    id_col = col_name
                    break
            if id_col:
                rows = df[df[id_col] == int(player_id)]
                if not rows.empty:
                    row = rows.iloc[0]
                    defl = _safe_float(row, "DEFLECTIONS")
                    result["deflections_per_game"] = (
                        defl if defl is not None else _safe_float(row, "DEF_LOOSE_BALLS_RECOVERED")
                    )
                    cont = _safe_float(row, "CONTESTED_SHOTS")
                    result["contested_shots_per_game"] = (
                        cont if cont is not None else _safe_float(row, "D_FGA")
                    )
                    result["charges_drawn_per_game"] = _safe_float(row, "CHARGES_DRAWN")
            else:
                print(f"[nba_stats] Defense DataFrame columns: {list(df.columns)}")
    except Exception as e:
        print(f"[nba_stats] Defense tracking failed: {e}")

    # SpeedDistance
    try:
        from nba_api.stats.endpoints import leaguedashptstats
        _sleep()
        speed = leaguedashptstats.LeagueDashPtStats(
            season=season,
            pt_measure_type="SpeedDistance",
            per_mode_simple="PerGame",
            player_or_team="Player",
        )
        _sleep()
        dfs = speed.get_data_frames()
        if dfs and not dfs[0].empty:
            df = dfs[0]
            rows = df[df["PLAYER_ID"] == int(player_id)]
            if not rows.empty:
                row = rows.iloc[0]
                result["avg_speed"] = _safe_float(row, "AVG_SPEED")
    except Exception as e:
        print(f"[nba_stats] SpeedDistance tracking failed: {e}")

    # Transition synergy
    try:
        from nba_api.stats.endpoints import synergyplaytypes
        _sleep()
        syn = synergyplaytypes.SynergyPlayTypes(
            season=season,
            play_type_nullable="Transition",
            per_mode_simple="PerGame",
            player_or_team_abbreviation="P",
            season_type_all_star="Regular Season",
            type_grouping_nullable="offensive",
        )
        _sleep()
        dfs = syn.get_data_frames()
        if dfs and not dfs[0].empty:
            df = dfs[0]
            rows = df[df["PLAYER_ID"] == int(player_id)]
            if not rows.empty:
                row = rows.iloc[0]
                trans_freq = _safe_float(row, "POSS_PCT") or 0
                result["transition_freq"] = trans_freq
                # Rough per-game estimate: transition POSS_PCT (0-1) * ~10 possessions scale
                result["transition_3_fga"] = trans_freq * 10
    except Exception as e:
        print(f"[nba_stats] Transition synergy failed: {e}")

    # Spot-Up synergy
    try:
        from nba_api.stats.endpoints import synergyplaytypes
        _sleep()
        syn = synergyplaytypes.SynergyPlayTypes(
            season=season,
            play_type_nullable="Spotup",
            per_mode_simple="PerGame",
            player_or_team_abbreviation="P",
            season_type_all_star="Regular Season",
            type_grouping_nullable="offensive",
        )
        _sleep()
        dfs = syn.get_data_frames()
        if dfs and not dfs[0].empty:
            df = dfs[0]
            rows = df[df["PLAYER_ID"] == int(player_id)]
            if not rows.empty:
                row = rows.iloc[0]
                result["spot_up_drive_freq"] = _safe_float(row, "POSS_PCT")
    except Exception as e:
        print(f"[nba_stats] SpotUp synergy failed: {e}")

    # OffScreen synergy
    try:
        from nba_api.stats.endpoints import synergyplaytypes
        _sleep()
        syn = synergyplaytypes.SynergyPlayTypes(
            season=season,
            play_type_nullable="OffScreen",
            per_mode_simple="PerGame",
            player_or_team_abbreviation="P",
            season_type_all_star="Regular Season",
            type_grouping_nullable="offensive",
        )
        _sleep()
        dfs = syn.get_data_frames()
        if dfs and not dfs[0].empty:
            df = dfs[0]
            rows = df[df["PLAYER_ID"] == int(player_id)]
            if not rows.empty:
                row = rows.iloc[0]
                off_screen_freq = _safe_float(row, "POSS_PCT") or 0
                # ~30% of off-screen plays result in drives
                result["off_screen_drive_freq"] = off_screen_freq * 0.3
                if result["off_screen_fga"] is None:
                    # Fallback: estimate ~5 FGA per unit of off-screen frequency
                    result["off_screen_fga"] = _safe_float(row, "FGA") or off_screen_freq * 5
                if result["off_screen_3_fga"] is None:
                    # ~60% of off-screen FGA are three-pointers
                    result["off_screen_3_fga"] = (result["off_screen_fga"] or 0) * 0.6
    except Exception as e:
        print(f"[nba_stats] OffScreen synergy failed: {e}")

    # Apply league-average defaults for contested shot percentages if still unavailable
    if result["contested_mid_fga_pct"] is None:
        result["contested_mid_fga_pct"] = 0.25  # league-average contested mid-range FGA pct
    if result["contested_3_fga_pct"] is None:
        result["contested_3_fga_pct"] = 0.20  # league-average contested 3-point FGA pct

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
    except Exception as e:
        print(f"[nba_stats] get_shot_zones failed: {e}")
    return zones


def get_player_info(player_id):
    info = {"name": "", "team": "", "position": "", "height": "", "weight": ""}
    try:
        from nba_api.stats.endpoints import playerprofilev2
        _sleep()
        profile = playerprofilev2.PlayerProfileV2(player_id=player_id, timeout=60)
        _sleep()
        dfs = profile.get_data_frames()
        if dfs and not dfs[0].empty:
            row = dfs[0].iloc[0]
            info["name"]   = str(row.get("DISPLAY_FIRST_LAST", ""))
            info["team"]   = str(row.get("TEAM_ABBREVIATION", ""))
    except Exception as e:
        print(f"[nba_stats] PlayerProfileV2 failed: {e}")

    try:
        from nba_api.stats.static import players
        ps = players.find_player_by_id(player_id)
        if ps:
            info["name"] = ps.get("full_name", info["name"])
    except Exception as e:
        print(f"[nba_stats] players.find_player_by_id failed: {e}")

    try:
        from nba_api.stats.endpoints import commonplayerinfo
        _sleep()
        cpi = commonplayerinfo.CommonPlayerInfo(player_id=player_id, timeout=60)
        _sleep()
        dfs = cpi.get_data_frames()
        if dfs and not dfs[0].empty:
            row = dfs[0].iloc[0]
            info["name"]     = str(row.get("DISPLAY_FIRST_LAST", info["name"]))
            info["team"]     = str(row.get("TEAM_ABBREVIATION", info["team"]))
            info["position"] = str(row.get("POSITION", ""))
            info["height"]   = str(row.get("HEIGHT", ""))
            info["weight"]   = str(row.get("WEIGHT", ""))
    except Exception as e:
        print(f"[nba_stats] CommonPlayerInfo failed: {e}")

    return info


def get_player_per_game_stats(player_id, season=SEASON):
    """
    Fetch per-game and advanced stats using nba_api.
    Returns (per_game_dict, advanced_dict) matching the format
    expected by tendency_calculator.calculate_tendencies().

    per_game keys: pts, reb, ast, stl, blk, pf, tov, fga, fg3a, fta,
                   ft_pct (decimal 0-1), mp, g
    advanced keys: usg_pct, ast_pct, orb_pct (all as percentages, e.g. 30.0 for 30%),
                   ts_pct (decimal 0-1), per
    """
    per_game = {}
    advanced = {}

    # Try PlayerCareerStats for per-game stats (reliable, player-scoped)
    try:
        from nba_api.stats.endpoints import playercareerstats
        _sleep()
        career = playercareerstats.PlayerCareerStats(
            player_id=player_id,
            per_mode36="PerGame",
        )
        _sleep()
        dfs = career.get_data_frames()
        if dfs and not dfs[0].empty:
            df = dfs[0]
            season_rows = df[df["SEASON_ID"] == season]
            if season_rows.empty:
                season_rows = df.tail(1)
            if not season_rows.empty:
                row = season_rows.iloc[0]
                per_game = {
                    "pts":    _safe_float(row, "PTS"),
                    "reb":    _safe_float(row, "REB"),
                    "ast":    _safe_float(row, "AST"),
                    "stl":    _safe_float(row, "STL"),
                    "blk":    _safe_float(row, "BLK"),
                    "pf":     _safe_float(row, "PF"),
                    "tov":    _safe_float(row, "TOV"),
                    "fga":    _safe_float(row, "FGA"),
                    "fg3a":   _safe_float(row, "FG3A"),
                    "fta":    _safe_float(row, "FTA"),
                    "ft_pct": _safe_float(row, "FT_PCT"),
                    "mp":     _safe_float(row, "MIN"),
                    "g":      _safe_float(row, "GP"),
                }
                per_game = {k: v for k, v in per_game.items() if v is not None}
    except Exception as e:
        print(f"[nba_stats] PlayerCareerStats failed: {e}")

    # Fallback to LeagueDashPlayerStats for per-game stats
    if not per_game:
        try:
            from nba_api.stats.endpoints import leaguedashplayerstats
            _sleep()
            dash = leaguedashplayerstats.LeagueDashPlayerStats(
                season=season,
                per_mode_detailed="PerGame",
            )
            _sleep()
            dfs = dash.get_data_frames()
            if dfs and not dfs[0].empty:
                df = dfs[0]
                rows = df[df["PLAYER_ID"] == int(player_id)]
                if not rows.empty:
                    row = rows.iloc[0]
                    per_game = {
                        "pts":    _safe_float(row, "PTS"),
                        "reb":    _safe_float(row, "REB"),
                        "ast":    _safe_float(row, "AST"),
                        "stl":    _safe_float(row, "STL"),
                        "blk":    _safe_float(row, "BLK"),
                        "pf":     _safe_float(row, "PF"),
                        "tov":    _safe_float(row, "TOV"),
                        "fga":    _safe_float(row, "FGA"),
                        "fg3a":   _safe_float(row, "FG3A"),
                        "fta":    _safe_float(row, "FTA"),
                        "ft_pct": _safe_float(row, "FT_PCT"),
                        "mp":     _safe_float(row, "MIN"),
                        "g":      _safe_float(row, "GP"),
                    }
                    per_game = {k: v for k, v in per_game.items() if v is not None}
        except Exception as e:
            print(f"[nba_stats] LeagueDashPlayerStats (per-game fallback) failed: {e}")

    # Try LeagueDashPlayerStats (Advanced) for advanced metrics
    # nba_api returns decimals (e.g. 0.30 = 30% USG); multiply by 100 for percentage
    try:
        from nba_api.stats.endpoints import leaguedashplayerstats
        _sleep()
        adv_dash = leaguedashplayerstats.LeagueDashPlayerStats(
            season=season,
            per_mode_detailed="PerGame",
            measure_type_detailed_defense="Advanced",
        )
        _sleep()
        dfs = adv_dash.get_data_frames()
        if dfs and not dfs[0].empty:
            df = dfs[0]
            rows = df[df["PLAYER_ID"] == int(player_id)]
            if not rows.empty:
                row = rows.iloc[0]
                usg     = _safe_float(row, "USG_PCT")
                ast_pct = _safe_float(row, "AST_PCT")
                orb_pct = _safe_float(row, "OREB_PCT")
                ts_pct  = _safe_float(row, "TS_PCT")
                advanced = {
                    "usg_pct": round(usg * 100, 1)     if usg     is not None else None,
                    "ast_pct": round(ast_pct * 100, 1) if ast_pct is not None else None,
                    "orb_pct": round(orb_pct * 100, 1) if orb_pct is not None else None,
                    "ts_pct":  ts_pct,
                }
                advanced = {k: v for k, v in advanced.items() if v is not None}
    except Exception as e:
        print(f"[nba_stats] LeagueDashPlayerStats (advanced) failed: {e}")

    # Fallback to PlayerEstimatedMetrics for advanced metrics
    if not advanced:
        try:
            from nba_api.stats.endpoints import playerestimatedmetrics
            _sleep()
            est = playerestimatedmetrics.PlayerEstimatedMetrics(season=season)
            _sleep()
            dfs = est.get_data_frames()
            if dfs and not dfs[0].empty:
                df = dfs[0]
                rows = df[df["PLAYER_ID"] == int(player_id)]
                if not rows.empty:
                    row = rows.iloc[0]
                    usg     = _safe_float(row, "E_USG_PCT")
                    ast_pct = _safe_float(row, "E_AST_PCT")
                    orb_pct = _safe_float(row, "E_OREB_PCT")
                    ts_pct  = _safe_float(row, "E_TRUE_SHOOTING_PCT")
                    per     = _safe_float(row, "E_PER")
                    advanced = {
                        "usg_pct": round(usg * 100, 1)     if usg     is not None else None,
                        "ast_pct": round(ast_pct * 100, 1) if ast_pct is not None else None,
                        "orb_pct": round(orb_pct * 100, 1) if orb_pct is not None else None,
                        "ts_pct":  ts_pct,
                        "per":     per,
                    }
                    advanced = {k: v for k, v in advanced.items() if v is not None}
        except Exception as e:
            print(f"[nba_stats] PlayerEstimatedMetrics (advanced fallback) failed: {e}")

    return per_game, advanced


def _safe_float(row, col):
    try:
        v = row[col]
        if v is None or str(v).strip() in ("", "None"):
            return None
        return float(v)
    except Exception:
        return None
