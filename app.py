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


if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=5000, debug=debug_mode)
