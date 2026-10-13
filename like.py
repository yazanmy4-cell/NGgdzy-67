import json
import os
import time
import threading
import schedule
from datetime import datetime
from flask import Flask, request, jsonify

from like import (
    login, check_all_accounts, get_player_info,
    send_likes_once, _session
)

app = Flask(__name__)

STATE = {
    "working": [],
    "last_refresh": None,
    "last_autolike": {},
    "autolike_jobs": {},
    "lock": threading.Lock()
}

REFRESH_INTERVAL_HOURS = 6
AUTOLIKE_HOUR = 4


def refresh_all_accounts():
    print("[refresh] start " + datetime.now().isoformat())
    try:
        working = check_all_accounts()
        with STATE["lock"]:
            STATE["working"] = working
            STATE["last_refresh"] = datetime.now().isoformat()
        print("[refresh] done working=" + str(len(working)))
        return len(working)
    except Exception as e:
        print("[refresh] error " + str(e))
        return 0


def job_refresh_loop():
    while True:
        time.sleep(REFRESH_INTERVAL_HOURS * 3600)
        refresh_all_accounts()


def run_autolike_for(uid, dys):
    with STATE["lock"]:
        working = list(STATE["working"])

    if not working:
        print("[autolike] no tokens for " + str(uid))
        return

    limit = max(1, min(dys, len(working)))
    selected = working[:limit]
    jwts = [w["jwt"] for w in selected if w.get("jwt")]

    if not jwts:
        print("[autolike] no jwt for " + str(uid))
        return

    print("[autolike] " + str(uid) + " tokens=" + str(len(jwts)))
    send_likes_once(uid, jwts)

    with STATE["lock"]:
        STATE["last_autolike"][uid] = datetime.now().isoformat()


def schedule_autolike(uid, dys):
    tag = "autolike_" + str(uid)
    schedule.clear(tag)
    schedule.every().day.at(str(AUTOLIKE_HOUR).zfill(2) + ":00").do(
        run_autolike_for, uid=uid, dys=dys
    ).tag(tag)

    with STATE["lock"]:
        STATE["autolike_jobs"][uid] = {
            "dys": dys,
            "created": datetime.now().isoformat(),
            "tag": tag
        }


def schedule_loop():
    while True:
        schedule.run_pending()
        time.sleep(30)


@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "service": "FF Like API",
        "endpoints": [
            "GET /like?uid=123456677",
            "GET /autolike?uid=3455565444&dys=30",
            "POST /refresh",
            "GET /status",
            "GET /accounts"
        ]
    })


@app.route("/like", methods=["GET"])
def api_like():
    uid = request.args.get("uid", "").strip()

    if not uid.isdigit():
        return jsonify({"ok": False, "error": "uid must be numeric"}), 400

    with STATE["lock"]:
        working = list(STATE["working"])

    jwts = [w["jwt"] for w in working if w.get("jwt")]

    if not jwts:
        return jsonify({"ok": False, "error": "no tokens"}), 503

    try:
        nick, before, after, sent = send_likes_once(uid, jwts)

        if nick is None:
            return jsonify({"ok": False, "error": "target not found"}), 404

        return jsonify({
            "Name": nick,
            "Like Before": before,
            "Like After": after,
            "Likes Added": after - before,
            "Tokens Used": sent,
            "Total Tokens": len(jwts)
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/autolike", methods=["GET"])
def api_autolike():
    uid = request.args.get("uid", "").strip()
    dys = request.args.get("dys", "30").strip()

    if not uid.isdigit():
        return jsonify({"ok": False, "error": "uid must be numeric"}), 400

    if not dys.isdigit() or int(dys) < 1:
        return jsonify({"ok": False, "error": "dys must be positive int"}), 400

    dys = int(dys)

    schedule_autolike(uid, dys)

    threading.Thread(
        target=run_autolike_for,
        args=(uid, dys),
        daemon=True
    ).start()

    return jsonify({
        "uid": uid,
        "dys": dys,
        "schedule": "every day at 04:00",
        "status": "scheduled"
    })


@app.route("/refresh", methods=["POST", "GET"])
def api_refresh():
    n = refresh_all_accounts()
    return jsonify({
        "status": "refreshed",
        "working": n,
        "last_refresh": STATE["last_refresh"]
    })


@app.route("/status", methods=["GET"])
def api_status():
    with STATE["lock"]:
        working = list(STATE["working"])
        jobs = dict(STATE["autolike_jobs"])
        last_refresh = STATE["last_refresh"]
        last_autolike = dict(STATE["last_autolike"])

    return jsonify({
        "working_accounts": len(working),
        "last_refresh": last_refresh,
        "refresh_interval_hours": REFRESH_INTERVAL_HOURS,
        "autolike_hour": AUTOLIKE_HOUR,
        "autolike_jobs": jobs,
        "last_autolike": last_autolike
    })


@app.route("/accounts", methods=["GET"])
def api_accounts():
    with STATE["lock"]:
        working = list(STATE["working"])

    return jsonify({
        "count": len(working),
        "accounts": [
            {
                "uid": w["uid"],
                "account_id": w.get("account_id"),
                "chat_host": w.get("chat_host"),
                "has_jwt": bool(w.get("jwt"))
            }
            for w in working
        ]
    })


def start_background_threads():
    refresh_all_accounts()

    t1 = threading.Thread(target=job_refresh_loop, daemon=True)
    t1.start()

    t2 = threading.Thread(target=schedule_loop, daemon=True)
    t2.start()

    print("[start] background threads ready")


if __name__ == "__main__":
    start_background_threads()
    app.run(host="0.0.0.0", port=8080, debug=False, threaded=True)