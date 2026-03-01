import io
import os

import pandas as pd
from flask import Flask, jsonify, request, send_file, send_from_directory

app = Flask(__name__, static_folder="static")

# Max players processed in a single bulk request.
# Players beyond this limit are silently skipped; the caller receives only the
# first BULK_GENERATION_LIMIT results.  Increase with caution — each player
# requires several external API calls and can take several seconds.
BULK_GENERATION_LIMIT = 30


def _cors(response):
    response.headers["Access-Control-Allow-Origin"]  = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


@app.after_request
def after_request(response):
    return _cors(response)


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/search")
def api_search():
    q = request.args.get("q", "").strip()
    if not q or len(q) < 2:
        return jsonify([])
    try:
        from engine.player_search import search_players
        results = search_players(q, limit=10)
        sanitized = [
            {
                "name":      str(r.get("name", ""))[:100],
                "team":      str(r.get("team", ""))[:10],
                "position":  str(r.get("position", ""))[:10],
                "player_id": int(r.get("player_id", 0)),
            }
            for r in results
        ]
        return jsonify(sanitized)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/generate", methods=["POST", "OPTIONS"])
def api_generate():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    try:
        body      = request.get_json(force=True) or {}
        player_id = body.get("player_id")
        player_name = body.get("player_name", "")
        season    = body.get("season", "2024-25")

        if not player_id and not player_name:
            return jsonify({"error": "player_id or player_name required"}), 400

        from engine.tendency_calculator import generate_tendencies_for_player
        result = generate_tendencies_for_player(
            player_id=int(player_id) if player_id else 0,
            player_name=player_name,
            season=season,
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/refresh-roster")
def api_refresh_roster():
    try:
        from engine.player_search import refresh_cache
        players = refresh_cache()
        return jsonify({"status": "ok", "count": len(players)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/export/csv", methods=["POST", "OPTIONS"])
def api_export_csv():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    try:
        body       = request.get_json(force=True) or {}
        name       = body.get("name", "player")
        tendencies = body.get("tendencies", {})

        rows = [{"Tendency": k, "Value": v} for k, v in tendencies.items()]
        df   = pd.DataFrame(rows)

        buf = io.StringIO()
        df.to_csv(buf, index=False)
        buf.seek(0)

        safe_name = name.replace(" ", "_")
        return send_file(
            io.BytesIO(buf.getvalue().encode()),
            mimetype="text/csv",
            as_attachment=True,
            download_name=f"{safe_name}_tendencies.csv",
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/export/excel", methods=["POST", "OPTIONS"])
def api_export_excel():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    try:
        body       = request.get_json(force=True) or {}
        name       = body.get("name", "player")
        tendencies = body.get("tendencies", {})

        rows = [{"Tendency": k, "Value": v} for k, v in tendencies.items()]
        df   = pd.DataFrame(rows)

        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Tendencies")
        buf.seek(0)

        safe_name = name.replace(" ", "_")
        return send_file(
            buf,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=f"{safe_name}_tendencies.xlsx",
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/bulk-generate", methods=["POST", "OPTIONS"])
def api_bulk_generate():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    try:
        body   = request.get_json(force=True) or {}
        team   = body.get("team")
        do_all = body.get("all", False)
        season = body.get("season", "2024-25")

        from engine.player_search import get_all_players
        from engine.tendency_calculator import generate_tendencies_for_player

        players = get_all_players(season=season)

        if team:
            players = [p for p in players if p.get("team_abbrev", "") == team]
        elif not do_all:
            return jsonify({"error": "Provide team or set all=true"}), 400

        results = []
        for p in players[:BULK_GENERATION_LIMIT]:
            try:
                r = generate_tendencies_for_player(
                    player_id=p["id"],
                    player_name=p["name"],
                    season=season,
                )
                results.append(r)
            except Exception:
                pass

        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/debug-raw", methods=["POST", "OPTIONS"])
def api_debug_raw():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    try:
        body = request.get_json(force=True) or {}
        player_id = int(body.get("player_id", 0))
        player_name = body.get("player_name", "")
        season = body.get("season", "2024-25")

        from engine import nba_stats, shotdetail_loader

        result = {
            "player_id": player_id,
            "player_name": player_name,
            "position": "",
            "team": "",
            "data_sources": {},
        }

        # 1. Player info
        try:
            info = nba_stats.get_player_info(player_id)
            result["position"] = info.get("position", "")
            result["team"] = info.get("team", "")
            result["player_name"] = info.get("name") if info.get("name") is not None else player_name
        except Exception as e:
            result["data_sources"]["player_info"] = {"status": "FAILED", "error": str(e), "data": {}}

        # 2. Per-game and advanced stats
        try:
            per_game, advanced = nba_stats.get_player_per_game_stats(player_id, season=season)
            result["data_sources"]["nba_api_per_game"] = {
                "status": "OK" if per_game else "EMPTY",
                "data": per_game or {},
            }
            result["data_sources"]["nba_api_advanced"] = {
                "status": "OK" if advanced else "EMPTY",
                "data": advanced or {},
            }
        except Exception as e:
            result["data_sources"]["nba_api_per_game"] = {"status": "FAILED", "error": str(e), "data": {}}
            result["data_sources"]["nba_api_advanced"] = {"status": "FAILED", "error": str(e), "data": {}}

        # 3. Tracking stats
        try:
            tracking = nba_stats.get_tracking_stats(player_id, season=season)
            has_data = any(v is not None for v in tracking.values())
            result["data_sources"]["nba_api_tracking"] = {
                "status": "OK" if has_data else "ALL_NULL",
                "data": tracking,
            }
        except Exception as e:
            result["data_sources"]["nba_api_tracking"] = {"status": "FAILED", "error": str(e), "data": {}}

        # 4. Shot zones
        try:
            zones = nba_stats.get_shot_zones(player_id, season=season)
            result["data_sources"]["nba_api_shot_zones"] = {
                "status": "OK" if zones else "EMPTY",
                "data": zones or {},
            }
        except Exception as e:
            result["data_sources"]["nba_api_shot_zones"] = {"status": "FAILED", "error": str(e), "data": {}}

        # 5. Shotdetail CSV
        try:
            season_year = int(season.split("-")[0])
            sd = shotdetail_loader.load_player_shotdetail(player_id, season_year=season_year)
            if sd:
                sd_stats = shotdetail_loader.estimate_per_game_stats(sd)
                action_counts = sd.get("action_counts", {})
                top_actions = sorted(action_counts.items(), key=lambda x: x[1], reverse=True)[:20]

                sd_data = {
                    "total_fga": sd.get("total_fga", 0),
                    "total_fgm": sd.get("total_fgm", 0),
                    "games_played": sd.get("games_played", 0),
                    "shooting_splits": sd.get("shooting_splits", {}),
                    "zone_area_mid": sd.get("zone_area_mid", {}),
                    "zone_area_three": sd.get("zone_area_three", {}),
                    "zone_area_close": sd.get("zone_area_close", {}),
                    "top_action_types": top_actions,
                    "estimated_stats": sd_stats or {},
                }

                if action_counts:
                    merged_counts = dict(action_counts)
                    merged_counts["_stepback_2pt"] = sd.get("stepback_2pt_count", 0)
                    merged_counts["_stepback_3pt"] = sd.get("stepback_3pt_count", 0)
                    move_freqs = shotdetail_loader.extract_move_frequencies(
                        merged_counts,
                        sd.get("total_fga", 1),
                        games_played=sd.get("games_played"),
                    )
                    sd_data["move_frequencies"] = move_freqs

                result["data_sources"]["shotdetail_csv"] = {"status": "OK", "data": sd_data}
            else:
                result["data_sources"]["shotdetail_csv"] = {"status": "NO_DATA", "data": {}}
        except Exception as e:
            result["data_sources"]["shotdetail_csv"] = {"status": "FAILED", "error": str(e), "data": {}}

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=5000, debug=debug_mode)
