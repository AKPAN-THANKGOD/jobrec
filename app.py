import os
from functools import wraps
from flask import Flask, abort, jsonify, redirect, render_template, request, session, url_for
from db import connect, init_db
from engine import Recommender
import store

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-change-me")
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")
init_db()


@app.context_processor
def inject_session_globals():
    uid = session.get("uid")
    counts = {"new_feed": False, "new_messages": False, "new_network": False,
              "unread_notifications": 0}
    if uid:
        counts = store.nav_counts(connect(), uid)
    return {
        "session_uid": uid,
        "name": session.get("name"),
        "admin": session.get("role") == "Administrator",
        "nav_counts": counts,
    }


def login_required(f):
    @wraps(f)
    def wrapper(*a, **k):
        if "uid" not in session:
            if request.path.startswith(("/api", "/admin/api")):
                return jsonify(error="Please log in"), 401
            return redirect(url_for("login"))
        return f(*a, **k)
    return wrapper


def admin_required(f):
    @wraps(f)
    @login_required
    def wrapper(*a, **k):
        if session.get("role") != "Administrator":
            abort(403)
        return f(*a, **k)
    return wrapper


def safe(fn):
    try:
        return jsonify(fn(connect()))
    except ValueError as e:
        return jsonify(error=str(e)), 400


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        u = store.authenticate(connect(), request.form["email"], request.form["password"])
        if u:
            session.clear()
            session.update(uid=u["user_id"], role=u["role"], name=u["full_name"])
            return redirect(url_for("index"))
        error = "Invalid email or password"
    return render_template("login.html", error=error)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html", error=None)
    f = request.form
    try:
        store.register(connect(), f["name"], f["email"], f["password"])
    except ValueError as e:
        return render_template("register.html", error=str(e)), 400
    return login()


@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.get("/")
@login_required
def index():
    return render_template("index.html")


@app.get("/api/skills")
@login_required
def skills():
    return jsonify([s["skill_name"] for s in store.list_skills(connect())])


@app.route("/api/profile", methods=["GET", "PUT"])
@login_required
def profile():
    con = connect()
    if request.method == "GET":
        return jsonify(store.get_profile(con, session["uid"]))
    saved, unknown = store.save_profile(con, session["uid"], request.get_json(force=True).get("skills", []))
    return jsonify(saved=saved, unrecognised=unknown)


@app.post("/api/recommend")
@login_required
def recommend():
    data = request.get_json(force=True)
    con = connect()
    rec = Recommender(con)
    known, unknown = set(), []
    for tag in data.get("skills", []):
        found = rec.tax.standardise(str(tag))
        known |= found
        if not found:
            unknown.append(tag)
    results = rec.recommend(known, int(data.get("k", 10)))
    saved = store.saved_job_ids(con, session["uid"])
    for r in results:
        r["saved"] = r["job_id"] in saved
    msg = ("No skill was recognised. Try picking from the suggestions." if not known
           else "No matching vacancy was found." if not results else "")
    return jsonify(skills=sorted(known), unrecognised=unknown, results=results, message=msg)


# ---------- administrator area ----------
@app.get("/admin")
@admin_required
def admin():
    return render_template("admin.html")


@app.post("/admin/api/extract")
@admin_required
def extract():
    con = connect()
    return jsonify(sorted(Recommender(con).tax.standardise(request.get_json(force=True).get("text", ""))))


@app.get("/admin/api/jobs")
@admin_required
def jobs_list():
    return jsonify(store.list_jobs(connect()))


@app.post("/admin/api/jobs")
@app.put("/admin/api/jobs/<int:jid>")
@admin_required
def jobs_save(jid=None):
    d = request.get_json(force=True)

    def _do(con):
        result = dict(zip(("job_id", "unrecognised"), store.save_job(
            con, jid, d.get("title", ""), d.get("company", ""), d.get("location", ""),
            d.get("description", ""), d.get("skills", []))))
        store.notify_matching_users(con, result["job_id"])
        return result

    return safe(_do)


@app.delete("/admin/api/jobs/<int:jid>")
@admin_required
def jobs_delete(jid):
    return safe(lambda con: store.delete_job(con, jid) or {"ok": True})


@app.get("/admin/api/skills")
@admin_required
def skills_list():
    return jsonify(store.list_skills(connect()))


@app.post("/admin/api/skills")
@app.put("/admin/api/skills/<int:sid>")
@admin_required
def skills_save(sid=None):
    d = request.get_json(force=True)
    return safe(lambda con: store.save_skill(con, sid, d.get("skill_name", ""), d.get("category", ""),
                                             d.get("aliases", "")) or {"ok": True})


@app.delete("/admin/api/skills/<int:sid>")
@admin_required
def skills_delete(sid):
    return safe(lambda con: store.delete_skill(con, sid) or {"ok": True})


# ---------- network layer: profiles, connections, feed, messaging ----------
@app.get("/u/<int:uid>")
@login_required
def profile_view(uid):
    con = connect()
    profile = store.get_profile_page(con, uid)
    if profile is None:
        abort(404)
    status = store.connection_status(con, session["uid"], uid)
    return render_template("profile.html", profile=profile, status=status)


@app.route("/profile/edit", methods=["GET", "POST"])
@login_required
def profile_edit():
    con = connect()
    error = None
    if request.method == "POST":
        try:
            store.update_headline_bio(con, session["uid"], request.form.get("headline", ""),
                                      request.form.get("bio", ""))
            return redirect(url_for("profile_view", uid=session["uid"]))
        except ValueError as e:
            error = str(e)
    profile = store.get_profile_page(con, session["uid"])
    return render_template("profile_edit.html", profile=profile, error=error)


@app.post("/profile/history")
@login_required
def profile_history_add():
    d = request.form
    return safe(lambda con: store.add_work_history(
        con, session["uid"], d.get("title", ""), d.get("company", ""),
        d.get("start_year", ""), d.get("end_year", ""), d.get("description", "")) or {"ok": True})


@app.delete("/profile/history/<int:entry_id>")
@login_required
def profile_history_delete(entry_id):
    return safe(lambda con: store.delete_work_history(con, session["uid"], entry_id) or {"ok": True})


@app.get("/network")
@login_required
def network():
    con = connect()
    store.mark_seen(con, session["uid"], "network")
    return render_template("network.html",
                           connections=store.list_connections(con, session["uid"]),
                           pending=store.list_pending_incoming(con, session["uid"]),
                           suggestions=store.suggest_connections(con, session["uid"]))


@app.get("/api/people/search")
@login_required
def people_search():
    q = request.args.get("q", "")
    if len(q.strip()) < 2:
        return jsonify([])
    return jsonify(store.search_people(connect(), q, session["uid"]))


@app.post("/connect/<int:uid>")
@login_required
def connect_request(uid):
    return safe(lambda con: store.send_connection_request(con, session["uid"], uid) or {"ok": True})


@app.post("/connect/<int:uid>/accept")
@login_required
def connect_accept(uid):
    return safe(lambda con: store.respond_connection_request(con, session["uid"], uid, True) or {"ok": True})


@app.post("/connect/<int:uid>/reject")
@login_required
def connect_reject(uid):
    return safe(lambda con: store.respond_connection_request(con, session["uid"], uid, False) or {"ok": True})


@app.post("/connect/<int:uid>/cancel")
@login_required
def connect_cancel(uid):
    return safe(lambda con: store.cancel_connection_request(con, session["uid"], uid) or {"ok": True})


@app.get("/feed")
@login_required
def feed():
    store.mark_seen(connect(), session["uid"], "feed")
    return render_template("feed.html")


@app.get("/api/feed")
@login_required
def feed_list():
    return jsonify(store.list_feed(connect(), session["uid"]))


@app.post("/api/feed")
@login_required
def feed_post():
    d = request.get_json(force=True)
    return safe(lambda con: {"post_id": store.create_post(con, session["uid"], d.get("content", ""))})


@app.post("/api/feed/<int:post_id>/like")
@login_required
def feed_like(post_id):
    return safe(lambda con: {"liked": store.toggle_like(con, session["uid"], post_id)})


@app.post("/api/feed/<int:post_id>/comments")
@login_required
def feed_comment(post_id):
    d = request.get_json(force=True)
    return safe(lambda con: store.add_comment(con, session["uid"], post_id, d.get("content", "")) or {"ok": True})


@app.get("/messages")
@login_required
def messages():
    con = connect()
    store.mark_seen(con, session["uid"], "messages")
    return render_template("messages.html",
                           conversations=store.list_conversations(con, session["uid"]))


@app.get("/messages/<int:uid>")
@login_required
def conversation(uid):
    con = connect()
    store.mark_seen(con, session["uid"], "messages")
    try:
        thread = store.list_conversation(con, session["uid"], uid)
    except ValueError:
        abort(403)
    other = con.execute("SELECT full_name FROM users WHERE user_id=?", (uid,)).fetchone()
    return render_template("conversation.html",
                           other_uid=uid,
                           other_name=other["full_name"] if other else "Unknown",
                           thread=thread)


@app.post("/api/messages/<int:uid>")
@login_required
def message_send(uid):
    d = request.get_json(force=True)
    return safe(lambda con: store.send_message(con, session["uid"], uid, d.get("content", "")) or {"ok": True})


# ---------- notifications ----------
@app.get("/notifications")
@login_required
def notifications_page():
    con = connect()
    items = store.list_notifications(con, session["uid"])
    store.mark_all_notifications_read(con, session["uid"])
    return render_template("notifications.html", items=items)


# ---------- saved jobs ----------
@app.post("/api/saved/<int:job_id>/toggle")
@login_required
def saved_toggle(job_id):
    con = connect()
    is_now_saved = store.toggle_saved_job(con, session["uid"], job_id)
    return jsonify(saved=is_now_saved)


@app.get("/saved")
@login_required
def saved_page():
    con = connect()
    jobs = store.list_saved_jobs(con, session["uid"])
    return render_template("saved.html", jobs=jobs)


if __name__ == "__main__":
    app.run(debug=True)