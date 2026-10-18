import json
import os
import time
import threading
import schedule
from datetime import datetime, timedelta
from flask import Flask, request, jsonify

from like import (
    login, check_all_accounts, get_player_info,
    send_likes_once, _session
)

app = Flask(__name__)

VIP_FILE = "vip.json"

STATE = {
    "working": [],
    "last_refresh": None,
    "last_autolike": {},
    "autolike_jobs": {},
    "autolike_history": {},
    "lock": threading.Lock()
}

REFRESH_INTERVAL_HOURS = 6
AUTOLIKE_HOUR = 4


def load_vip():
    if not os.path.exists(VIP_FILE):
        return {}
    try:
        with open(VIP_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
            return {}
    except Exception as e:
        print(f"[vip] load error: {e}")
        return {}


def save_vip():
    try:
        with STATE["lock"]:
            data = json.loads(json.dumps(STATE["autolike_jobs"]))
        with open(VIP_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[vip] save error: {e}")


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


def run_autolike_for(uid):
    with STATE["lock"]:
        working = list(STATE["working"])

    if not working:
        print(f"[autolike] {uid} -> no working accounts")
        return

    jwts = [w["jwt"] for w in working if w.get("jwt")]

    if not jwts:
        print(f"[autolike] {uid} -> no valid JWT")
        return

    print(f"[autolike] {uid} -> using {len(jwts)} accounts")

    added = 0
    before = 0
    after = 0
    sent = 0

    try:
        nick, before, after, sent = send_likes_once(uid, jwts)
        added = max(0, after - before)
        print(f"[autolike] {uid} -> +{added} likes (used {sent} tokens)")
    except Exception as e:
        print(f"[autolike] {uid} -> error: {e}")

    now_iso = datetime.now().isoformat()

    with STATE["lock"]:
        STATE["last_autolike"][uid] = now_iso

        if uid in STATE["autolike_jobs"]:
            job = STATE["autolike_jobs"][uid]
            job["runs"] = job.get("runs", 0) + 1
            job["total_likes"] = job.get("total_likes", 0) + added
            job["last_likes"] = added
            job["last_run"] = now_iso

        STATE["autolike_history"].setdefault(uid, []).append({
            "timestamp": now_iso,
            "likes_added": added,
            "before": before,
            "after": after,
            "tokens_used": sent,
            "accounts_total": len(jwts)
        })

        if uid in STATE["autolike_jobs"]:
            if STATE["autolike_jobs"][uid].get("runs", 0) >= STATE["autolike_jobs"][uid].get("days", 0):
                STATE["autolike_jobs"][uid]["finished"] = True

    save_vip()


def schedule_autolike(uid, days):
    tag = "autolike_" + str(uid)
    schedule.clear(tag)

    now = datetime.now()

    with STATE["lock"]:
        existing = STATE["autolike_jobs"].get(uid, {})
        runs_done = existing.get("runs", 0) if existing.get("tag") == tag else 0
        total_likes_done = existing.get("total_likes", 0) if existing.get("tag") == tag else 0
        created = existing.get("created", now.isoformat()) if existing.get("tag") == tag else now.isoformat()

        STATE["autolike_jobs"][uid] = {
            "target_uid": uid,
            "days": days,
            "runs": runs_done,
            "total_likes": total_likes_done,
            "last_likes": existing.get("last_likes", 0),
            "last_run": existing.get("last_run"),
            "created": created,
            "end_date": (now + timedelta(days=days)).isoformat(),
            "tag": tag,
            "finished": False,
            "active": True
        }

    def daily_job():
        with STATE["lock"]:
            job = STATE["autolike_jobs"].get(uid)
            if not job:
                return
            runs = job.get("runs", 0)
            if runs >= days:
                schedule.clear(tag)
                job["finished"] = True
                job["active"] = False
                print(f"[autolike] {uid} -> finished after {days} days")
                return

        print(f"[autolike] {uid} -> run {runs + 1}/{days}")
        run_autolike_for(uid)

    schedule.every().day.at(str(AUTOLIKE_HOUR).zfill(2) + ":00").do(daily_job).tag(tag)
    print(f"[autolike] {uid} -> scheduled for {days} days at {AUTOLIKE_HOUR}:00")

    save_vip()

    threading.Thread(target=daily_job, daemon=True).start()


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
            "GET /autolike?uid=3455565444&days=30",
            "POST /refresh",
            "GET /status",
            "GET /accounts",
            "GET /targets",
            "GET /viplog",
            "GET /viplog?uid=18724269473",
            "POST /viplog/delete?uid=18724269473"
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
    days = request.args.get("days", "30").strip()

    if not uid.isdigit():
        return jsonify({"ok": False, "error": "uid must be numeric"}), 400

    if not days.isdigit() or int(days) < 1:
        return jsonify({"ok": False, "error": "days must be positive int"}), 400

    days = int(days)

    with STATE["lock"]:
        working_count = len(STATE["working"])

    schedule_autolike(uid, days)

    return jsonify({
        "uid": uid,
        "days": days,
        "accounts_per_day": working_count,
        "total_likes_expected": days * working_count,
        "schedule": f"every day at {AUTOLIKE_HOUR}:00",
        "saved_to": VIP_FILE,
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

    job_details = {}
    for uid, job in jobs.items():
        days = job.get("days", 0)
        runs = job.get("runs", 0)
        job_details[uid] = {
            "days_total": days,
            "runs_done": runs,
            "days_remaining": max(0, days - runs),
            "accounts_per_day": len(working),
            "total_likes_expected": days * len(working),
            "total_likes_done": job.get("total_likes", 0),
            "last_likes": job.get("last_likes", 0),
            "created": job.get("created"),
            "end_date": job.get("end_date"),
            "last_run": last_autolike.get(uid, "never"),
            "active": job.get("active", False),
            "finished": job.get("finished", False)
        }

    return jsonify({
        "working_accounts": len(working),
        "last_refresh": last_refresh,
        "refresh_interval_hours": REFRESH_INTERVAL_HOURS,
        "autolike_hour": AUTOLIKE_HOUR,
        "autolike_jobs": job_details
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


@app.route("/targets", methods=["GET"])
def api_targets():
    with STATE["lock"]:
        jobs = dict(STATE["autolike_jobs"])
        working = list(STATE["working"])

    targets = []
    for uid, job in jobs.items():
        days = job.get("days", 0)
        runs = job.get("runs", 0)
        targets.append({
            "target_uid": uid,
            "days_total": days,
            "runs_done": runs,
            "days_remaining": max(0, days - runs),
            "accounts_per_day": len(working),
            "total_likes_expected": days * len(working),
            "total_likes_done": job.get("total_likes", 0),
            "created": job.get("created"),
            "end_date": job.get("end_date"),
            "active": job.get("active", False),
            "finished": job.get("finished", False)
        })

    return jsonify({
        "count": len(targets),
        "targets": targets
    })


@app.route("/viplog", methods=["GET"])
def api_viplog():
    uid_filter = request.args.get("uid", "").strip()

    with STATE["lock"]:
        jobs = json.loads(json.dumps(STATE["autolike_jobs"]))
        history = json.loads(json.dumps(STATE["autolike_history"]))
        working = list(STATE["working"])

    working_count = len(working)

    now = datetime.now()

    def build_entry(uid, job):
        days = job.get("days", 0)
        runs = job.get("runs", 0)
        remaining_days = max(0, days - runs)
        created_str = job.get("created")
        end_date_str = job.get("end_date")

        try:
            created_dt = datetime.fromisoformat(created_str) if created_str else now
        except Exception:
            created_dt = now

        try:
            end_dt = datetime.fromisoformat(end_date_str) if end_date_str else now + timedelta(days=days)
        except Exception:
            end_dt = now + timedelta(days=days)

        if job.get("finished"):
            status = "finished"
        elif job.get("active"):
            status = "active"
        else:
            status = "inactive"

        total_likes = job.get("total_likes", 0)
        total_expected = days * working_count
        started_days_ago = (now - created_dt).days

        uid_history = history.get(uid, [])

        return {
            "target_uid": uid,
            "status": status,
            "started_at": created_str,
            "started_days_ago": started_days_ago,
            "end_date": end_date_str,
            "days_total": days,
            "days_completed": runs,
            "days_remaining": remaining_days,
            "accounts_per_day": working_count,
            "total_likes_expected": total_expected,
            "total_likes_added": total_likes,
            "progress_percent": round((runs / days) * 100, 1) if days > 0 else 0,
            "last_run": job.get("last_run"),
            "last_likes_added": job.get("last_likes", 0),
            "history_runs": len(uid_history),
            "history": uid_history[-10:]
        }

    if uid_filter:
        if not uid_filter.isdigit():
            return jsonify({"ok": False, "error": "uid must be numeric"}), 400
        if uid_filter not in jobs:
            return jsonify({"ok": False, "error": "uid not found in autolike"}), 404
        return jsonify(build_entry(uid_filter, jobs[uid_filter]))

    all_entries = [build_entry(uid, job) for uid, job in jobs.items()]
    all_entries.sort(key=lambda x: x.get("started_at") or "", reverse=True)

    active = [e for e in all_entries if e["status"] == "active"]
    finished = [e for e in all_entries if e["status"] == "finished"]

    return jsonify({
        "vip_file": VIP_FILE,
        "total_targets": len(all_entries),
        "active_count": len(active),
        "finished_count": len(finished),
        "working_accounts": working_count,
        "now": now.isoformat(),
        "targets": all_entries
    })


@app.route("/viplog/delete", methods=["POST", "GET"])
def api_viplog_delete():
    uid = request.args.get("uid", "").strip()

    if not uid.isdigit():
        return jsonify({"ok": False, "error": "uid must be numeric"}), 400

    with STATE["lock"]:
        if uid in STATE["autolike_jobs"]:
            removed = STATE["autolike_jobs"].pop(uid)
            STATE["autolike_history"].pop(uid, None)
            STATE["last_autolike"].pop(uid, None)
            schedule.clear("autolike_" + str(uid))
            ok = True
        else:
            removed = None
            ok = False

    save_vip()

    return jsonify({
        "ok": ok,
        "uid": uid,
        "removed": removed
    })


@app.route("/viplog/history", methods=["GET"])
def api_viplog_history():
    uid = request.args.get("uid", "").strip()

    with STATE["lock"]:
        history = json.loads(json.dumps(STATE["autolike_history"]))

    if uid:
        if not uid.isdigit():
            return jsonify({"ok": False, "error": "uid must be numeric"}), 400
        return jsonify({
            "uid": uid,
            "history": history.get(uid, [])
        })

    return jsonify({
        "count": len(history),
        "history": history
    })


def restore_from_vip():
    data = load_vip()
    if not data:
        print("[vip] no saved jobs to restore")
        return

    print(f"[vip] restoring {len(data)} jobs from {VIP_FILE}")

    for uid, job in data.items():
        try:
            days = job.get("days", 0)
            runs = job.get("runs", 0)
            remaining = days - runs

            if remaining <= 0 or job.get("finished"):
                with STATE["lock"]:
                    STATE["autolike_jobs"][uid] = job
                    STATE["autolike_jobs"][uid]["finished"] = True
                    STATE["autolike_jobs"][uid]["active"] = False
                print(f"[vip] {uid} already finished ({runs}/{days})")
                continue

            if not uid.isdigit():
                continue

            tag = "autolike_" + str(uid)
            schedule.clear(tag)

            with STATE["lock"]:
                STATE["autolike_jobs"][uid] = job
                STATE["autolike_jobs"][uid]["active"] = True
                STATE["autolike_jobs"][uid]["finished"] = False

            def make_daily_job(target_uid, total_days, job_tag):
                def daily_job():
                    with STATE["lock"]:
                        j = STATE["autolike_jobs"].get(target_uid)
                        if not j:
                            return
                        r = j.get("runs", 0)
                        if r >= total_days:
                            schedule.clear(job_tag)
                            j["finished"] = True
                            j["active"] = False
                            print(f"[autolike] {target_uid} -> finished")
                            save_vip()
                            return
                    print(f"[autolike] {target_uid} -> run {r + 1}/{total_days}")
                    run_autolike_for(target_uid)
                return daily_job

            schedule.every().day.at(str(AUTOLIKE_HOUR).zfill(2) + ":00").do(
                make_daily_job(uid, days, tag)
            ).tag(tag)

            print(f"[vip] {uid} restored ({runs}/{days} done, {remaining} days left)")

        except Exception as e:
            print(f"[vip] restore error for {uid}: {e}")


def start_background_threads():
    refresh_all_accounts()
    restore_from_vip()

    t1 = threading.Thread(target=job_refresh_loop, daemon=True)
    t1.start()

    t2 = threading.Thread(target=schedule_loop, daemon=True)
    t2.start()

    print("[start] background threads ready")
    print(f"[start] vip file: {VIP_FILE}")


if __name__ == "__main__":
    start_background_threads()
    app.run(host="0.0.0.0", port=8080, debug=False, threaded=True)
