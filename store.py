"""Data-access helpers for accounts, profiles, vacancies and the taxonomy."""
import sqlite3
from werkzeug.security import check_password_hash
from db import create_user
from engine import Taxonomy


def register(con, name, email, password):
    if not name.strip() or "@" not in email or len(password) < 6:
        raise ValueError("Enter a name, a valid email and a password of at least 6 characters")
    try:
        with con:
            create_user(con, name.strip(), email, password)
    except sqlite3.IntegrityError:
        raise ValueError("That email is already registered")


def authenticate(con, email, password):
    u = con.execute("SELECT * FROM users WHERE email=?", (email.strip().lower(),)).fetchone()
    return u if u and check_password_hash(u["password_hash"], password) else None


def canonical(con, names):
    tax = Taxonomy(con.execute("SELECT skill_name, aliases FROM skills").fetchall())
    found, unknown = set(), []
    for n in names:
        f = tax.standardise(str(n))
        found |= f
        if not f:
            unknown.append(n)
    return sorted(found), unknown


def _link(con, table, key, kid, names):
    con.execute(f"DELETE FROM {table} WHERE {key}=?", (kid,))
    for n in names:
        con.execute(f"INSERT INTO {table} SELECT ?, skill_id FROM skills WHERE skill_name=?", (kid, n))


def get_profile(con, uid):
    return [r[0] for r in con.execute("SELECT s.skill_name FROM user_skills u JOIN skills s "
                                      "ON s.skill_id=u.skill_id WHERE u.user_id=? ORDER BY 1", (uid,))]


def save_profile(con, uid, names):
    found, unknown = canonical(con, names)
    with con:
        _link(con, "user_skills", "user_id", uid, found)
    return found, unknown


def list_jobs(con):
    jobs = [dict(r) for r in con.execute(
        "SELECT job_id, title, company, location, description FROM jobs ORDER BY job_id DESC")]
    for j in jobs:
        j["skills"] = [r[0] for r in con.execute(
            "SELECT s.skill_name FROM job_skills js JOIN skills s ON s.skill_id=js.skill_id "
            "WHERE js.job_id=? ORDER BY 1", (j["job_id"],))]
    return jobs


def save_job(con, jid, title, company, location, description, skills):
    if not title.strip() or not description.strip():
        raise ValueError("Title and description are required")
    found, unknown = canonical(con, skills)
    if not found:
        raise ValueError("A vacancy needs at least one recognised skill")
    with con:
        if jid is None:
            jid = con.execute("INSERT INTO jobs(title, company, location, description) VALUES(?,?,?,?)",
                              (title, company, location, description)).lastrowid
        else:
            con.execute("UPDATE jobs SET title=?, company=?, location=?, description=? WHERE job_id=?",
                        (title, company, location, description, jid))
        _link(con, "job_skills", "job_id", jid, found)
    return jid, unknown


def delete_job(con, jid):
    with con:
        con.execute("DELETE FROM job_skills WHERE job_id=?", (jid,))
        con.execute("DELETE FROM jobs WHERE job_id=?", (jid,))


def list_skills(con):
    return [dict(r) for r in con.execute(
        "SELECT skill_id, skill_name, category, aliases FROM skills ORDER BY skill_name")]


def save_skill(con, sid, name, category, aliases):
    name = name.strip()
    if not name:
        raise ValueError("Skill name is required")
    rows = [r for r in list_skills(con) if r["skill_id"] != sid] + [{"skill_name": name, "aliases": aliases}]
    Taxonomy(rows)
    with con:
        if sid is None:
            con.execute("INSERT INTO skills(skill_name, category, aliases) VALUES(?,?,?)", (name, category, aliases))
        else:
            con.execute("UPDATE skills SET skill_name=?, category=?, aliases=? WHERE skill_id=?",
                        (name, category, aliases, sid))


def delete_skill(con, sid):
    with con:
        for t in ("job_skills", "user_skills"):
            con.execute(f"DELETE FROM {t} WHERE skill_id=?", (sid,))
        con.execute("DELETE FROM skills WHERE skill_id=?", (sid,))


# ============================================================
# Network layer: profiles, connections, feed, messaging
# ============================================================

def get_profile_page(con, uid):
    u = con.execute("SELECT user_id, full_name, headline, bio FROM users WHERE user_id=?", (uid,)).fetchone()
    if u is None:
        return None
    skills = get_profile(con, uid)
    history = con.execute(
        "SELECT entry_id, title, company, start_year, end_year, description FROM work_history "
        "WHERE user_id=? ORDER BY start_year DESC", (uid,)).fetchall()
    return {"user_id": u["user_id"], "full_name": u["full_name"], "headline": u["headline"] or "",
            "bio": u["bio"] or "", "skills": skills, "history": [dict(h) for h in history]}


def update_headline_bio(con, uid, headline, bio):
    with con:
        con.execute("UPDATE users SET headline=?, bio=? WHERE user_id=?", (headline.strip(), bio.strip(), uid))


def add_work_history(con, uid, title, company, start_year, end_year, description):
    if not title.strip():
        raise ValueError("A title is required for a work history entry")
    with con:
        con.execute("INSERT INTO work_history(user_id, title, company, start_year, end_year, description) "
                    "VALUES(?,?,?,?,?,?)", (uid, title.strip(), company.strip(), start_year.strip(),
                                            end_year.strip(), description.strip()))


def delete_work_history(con, uid, entry_id):
    with con:
        con.execute("DELETE FROM work_history WHERE entry_id=? AND user_id=?", (entry_id, uid))


def search_people(con, query, exclude_uid):
    q = f"%{query.strip()}%"
    rows = con.execute("SELECT user_id, full_name, headline FROM users WHERE role='Job Seeker' "
                       "AND user_id != ? AND (full_name LIKE ? OR headline LIKE ?)",
                       (exclude_uid, q, q)).fetchall()
    return [dict(r) for r in rows]


# ------------------------------------------------------------- Connections
def connection_status(con, a, b):
    if a == b:
        return "self"
    row = con.execute("SELECT requester_id, status FROM connections WHERE "
                      "(requester_id=? AND addressee_id=?) OR (requester_id=? AND addressee_id=?)",
                      (a, b, b, a)).fetchone()
    if row is None:
        return "none"
    if row["status"] == "accepted":
        return "accepted"
    return "pending_outgoing" if row["requester_id"] == a else "pending_incoming"


def send_connection_request(con, from_uid, to_uid):
    if from_uid == to_uid:
        raise ValueError("You cannot connect with yourself")
    if connection_status(con, from_uid, to_uid) != "none":
        raise ValueError("A connection or request already exists between these users")
    with con:
        con.execute("INSERT INTO connections(requester_id, addressee_id, status) VALUES(?,?,'pending')",
                    (from_uid, to_uid))


def respond_connection_request(con, uid, other_uid, accept):
    row = con.execute("SELECT status FROM connections WHERE requester_id=? AND addressee_id=?",
                      (other_uid, uid)).fetchone()
    if row is None or row["status"] != "pending":
        raise ValueError("No pending request from this user")
    with con:
        if accept:
            con.execute("UPDATE connections SET status='accepted' WHERE requester_id=? AND addressee_id=?",
                        (other_uid, uid))
        else:
            con.execute("DELETE FROM connections WHERE requester_id=? AND addressee_id=?", (other_uid, uid))


def cancel_connection_request(con, from_uid, to_uid):
    row = con.execute("SELECT status FROM connections WHERE requester_id=? AND addressee_id=?",
                      (from_uid, to_uid)).fetchone()
    if row is None or row["status"] != "pending":
        raise ValueError("No pending request to cancel")
    with con:
        con.execute("DELETE FROM connections WHERE requester_id=? AND addressee_id=?",
                    (from_uid, to_uid))


def list_connections(con, uid):
    rows = con.execute(
        "SELECT u.user_id, u.full_name, u.headline FROM connections c "
        "JOIN users u ON u.user_id = (CASE WHEN c.requester_id=? THEN c.addressee_id ELSE c.requester_id END) "
        "WHERE (c.requester_id=? OR c.addressee_id=?) AND c.status='accepted'", (uid, uid, uid)).fetchall()
    return [dict(r) for r in rows]


def list_pending_incoming(con, uid):
    rows = con.execute("SELECT u.user_id, u.full_name, u.headline FROM connections c "
                       "JOIN users u ON u.user_id = c.requester_id "
                       "WHERE c.addressee_id=? AND c.status='pending'", (uid,)).fetchall()
    return [dict(r) for r in rows]


def suggest_connections(con, uid, limit=5):
    my_skills = set(get_profile(con, uid))
    if not my_skills:
        return []
    excluded = {uid}
    for row in con.execute("SELECT requester_id, addressee_id FROM connections "
                           "WHERE requester_id=? OR addressee_id=?", (uid, uid)):
        excluded.add(row["requester_id"])
        excluded.add(row["addressee_id"])
    candidates = con.execute("SELECT user_id, full_name, headline FROM users WHERE role='Job Seeker'").fetchall()
    out = []
    for c in candidates:
        if c["user_id"] in excluded:
            continue
        shared = my_skills & set(get_profile(con, c["user_id"]))
        if shared:
            out.append({"user_id": c["user_id"], "full_name": c["full_name"], "headline": c["headline"] or "",
                        "shared_skills": sorted(shared)})
    out.sort(key=lambda x: -len(x["shared_skills"]))
    return out[:limit]


# -------------------------------------------------------------------- Feed
def create_post(con, uid, content):
    if not content.strip():
        raise ValueError("A post cannot be empty")
    with con:
        pid = con.execute("INSERT INTO posts(user_id, content) VALUES(?,?)", (uid, content.strip())).lastrowid
    return pid


def list_feed(con, uid, limit=30):
    ids = [uid] + [c["user_id"] for c in list_connections(con, uid)]
    placeholders = ",".join("?" * len(ids))
    posts = con.execute(
        f"SELECT p.post_id, p.user_id, u.full_name, u.headline, p.content, p.created_at "
        f"FROM posts p JOIN users u ON u.user_id = p.user_id "
        f"WHERE p.user_id IN ({placeholders}) ORDER BY p.created_at DESC LIMIT ?", (*ids, limit)).fetchall()
    out = []
    for p in posts:
        likes = con.execute("SELECT COUNT(*) FROM post_likes WHERE post_id=?", (p["post_id"],)).fetchone()[0]
        liked = con.execute("SELECT 1 FROM post_likes WHERE post_id=? AND user_id=?",
                            (p["post_id"], uid)).fetchone() is not None
        comments = con.execute(
            "SELECT c.user_id, u.full_name, c.content, c.created_at FROM post_comments c "
            "JOIN users u ON u.user_id = c.user_id WHERE c.post_id=? ORDER BY c.created_at",
            (p["post_id"],)).fetchall()
        out.append({**dict(p), "likes": likes, "liked_by_me": liked, "comments": [dict(cm) for cm in comments]})
    return out


def toggle_like(con, uid, post_id):
    with con:
        if con.execute("SELECT 1 FROM post_likes WHERE post_id=? AND user_id=?", (post_id, uid)).fetchone():
            con.execute("DELETE FROM post_likes WHERE post_id=? AND user_id=?", (post_id, uid))
            return False
        con.execute("INSERT INTO post_likes(post_id, user_id) VALUES(?,?)", (post_id, uid))
        return True


def add_comment(con, uid, post_id, content):
    if not content.strip():
        raise ValueError("A comment cannot be empty")
    with con:
        con.execute("INSERT INTO post_comments(post_id, user_id, content) VALUES(?,?,?)",
                    (post_id, uid, content.strip()))


# --------------------------------------------------------------- Messaging
def send_message(con, from_uid, to_uid, content):
    if connection_status(con, from_uid, to_uid) != "accepted":
        raise ValueError("You can only message accepted connections")
    if not content.strip():
        raise ValueError("A message cannot be empty")
    with con:
        con.execute("INSERT INTO messages(sender_id, recipient_id, content) VALUES(?,?,?)",
                    (from_uid, to_uid, content.strip()))


def list_conversations(con, uid):
    out = []
    for c in list_connections(con, uid):
        last = con.execute(
            "SELECT content, created_at, sender_id FROM messages WHERE "
            "(sender_id=? AND recipient_id=?) OR (sender_id=? AND recipient_id=?) "
            "ORDER BY created_at DESC LIMIT 1", (uid, c["user_id"], c["user_id"], uid)).fetchone()
        out.append({**c, "last_message": dict(last) if last else None})
    out.sort(key=lambda c: c["last_message"]["created_at"] if c["last_message"] else "", reverse=True)
    return out


def list_conversation(con, uid, other_uid):
    if connection_status(con, uid, other_uid) != "accepted":
        raise ValueError("You are not connected with this user")
    rows = con.execute(
        "SELECT sender_id, content, created_at FROM messages WHERE "
        "(sender_id=? AND recipient_id=?) OR (sender_id=? AND recipient_id=?) ORDER BY created_at",
        (uid, other_uid, other_uid, uid)).fetchall()
    return [dict(r) for r in rows]


# ----------------------------------------------------- Nav activity indicators
def nav_counts(con, uid):
    """Which nav sections have new activity for this user since they last opened them."""
    row = con.execute(
        "SELECT last_seen_feed, last_seen_messages, last_seen_network "
        "FROM users WHERE user_id=?", (uid,)
    ).fetchone()
    if row is None:
        return {"new_feed": False, "new_messages": False, "new_network": False,
                "unread_notifications": 0}

    conn_ids = [c["user_id"] for c in list_connections(con, uid)]

    new_feed = False
    if conn_ids:
        placeholders = ",".join("?" * len(conn_ids))
        latest = con.execute(
            f"SELECT MAX(created_at) FROM posts WHERE user_id IN ({placeholders})",
            conn_ids
        ).fetchone()[0]
        if latest:
            seen = row["last_seen_feed"]
            new_feed = (seen is None) or (latest > seen)

    new_messages = False
    if conn_ids:
        placeholders = ",".join("?" * len(conn_ids))
        latest = con.execute(
            f"SELECT MAX(created_at) FROM messages "
            f"WHERE sender_id IN ({placeholders}) AND recipient_id=?",
            (*conn_ids, uid)
        ).fetchone()[0]
        if latest:
            seen = row["last_seen_messages"]
            new_messages = (seen is None) or (latest >= seen)

    new_network = False
    latest = con.execute(
        "SELECT MAX(created_at) FROM connections "
        "WHERE addressee_id=? AND status='pending'", (uid,)
    ).fetchone()[0]
    if latest:
        seen = row["last_seen_network"]
        new_network = (seen is None) or (latest >= seen)

    return {"new_feed": new_feed, "new_messages": new_messages,
            "new_network": new_network,
            "unread_notifications": unread_notification_count(con, uid)}


def mark_seen(con, uid, section):
    """Stamp a user's last_seen_<section> column to now.
    section must be one of: 'feed', 'messages', 'network'."""
    column = {"feed": "last_seen_feed",
              "messages": "last_seen_messages",
              "network": "last_seen_network"}.get(section)
    if column is None:
        raise ValueError(f"Unknown section: {section}")
    with con:
        con.execute(f"UPDATE users SET {column}=CURRENT_TIMESTAMP WHERE user_id=?", (uid,))


# --------------------------------------------------------------- Notifications
def create_notification(con, user_id, kind, ref_id, title, body):
    with con:
        con.execute(
            "INSERT INTO notifications(user_id, kind, ref_id, title, body) VALUES(?,?,?,?,?)",
            (user_id, kind, ref_id, title, body)
        )


def notify_matching_users(con, job_id):
    """After a job is created or updated, notify every job seeker whose skills overlap
    with the job's required skills. One notification per user per job — re-saves
    are skipped so users aren't spammed with duplicates."""
    job = con.execute("SELECT title, company FROM jobs WHERE job_id=?", (job_id,)).fetchone()
    if job is None:
        return 0
    job_skills = {r[0] for r in con.execute(
        "SELECT s.skill_name FROM job_skills js JOIN skills s ON s.skill_id=js.skill_id WHERE js.job_id=?",
        (job_id,))}
    if not job_skills:
        return 0
    candidates = con.execute("SELECT user_id FROM users WHERE role='Job Seeker'").fetchall()
    created = 0
    for row in candidates:
        uid = row["user_id"]
        existing = con.execute(
            "SELECT 1 FROM notifications WHERE user_id=? AND kind='job' AND ref_id=?",
            (uid, job_id)).fetchone()
        if existing:
            continue
        user_skills = set(get_profile(con, uid))
        shared = job_skills & user_skills
        if not shared:
            continue
        pct = round(100 * len(shared) / len(job_skills))
        body = (f"Matches {pct}% of your skills — you already have "
                f"{', '.join(sorted(shared))}.")
        create_notification(con, uid, "job", job_id,
                            f"New vacancy: {job['title']} at {job['company'] or 'a company'}",
                            body)
        created += 1
    return created


def list_notifications(con, uid, limit=50):
    rows = con.execute(
        "SELECT notification_id, kind, ref_id, title, body, created_at, read_at "
        "FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
        (uid, limit)).fetchall()
    return [dict(r) for r in rows]


def unread_notification_count(con, uid):
    row = con.execute(
        "SELECT COUNT(*) FROM notifications WHERE user_id=? AND read_at IS NULL",
        (uid,)).fetchone()
    return row[0] if row else 0


def mark_all_notifications_read(con, uid):
    with con:
        con.execute("UPDATE notifications SET read_at=CURRENT_TIMESTAMP "
                    "WHERE user_id=? AND read_at IS NULL", (uid,))






                    # ---------------------------------------------------------------- Saved jobs
def toggle_saved_job(con, uid, job_id):
    """Return True if the job is now saved, False if it was just removed."""
    with con:
        row = con.execute(
            "SELECT 1 FROM saved_jobs WHERE user_id=? AND job_id=?", (uid, job_id)
        ).fetchone()
        if row:
            con.execute("DELETE FROM saved_jobs WHERE user_id=? AND job_id=?", (uid, job_id))
            return False
        con.execute("INSERT INTO saved_jobs(user_id, job_id) VALUES(?,?)", (uid, job_id))
        return True


def is_saved(con, uid, job_id):
    return con.execute(
        "SELECT 1 FROM saved_jobs WHERE user_id=? AND job_id=?", (uid, job_id)
    ).fetchone() is not None


def list_saved_jobs(con, uid):
    """Full job details for every saved job, newest saved first."""
    rows = con.execute(
        "SELECT j.job_id, j.title, j.company, j.location, j.description, s.saved_at "
        "FROM saved_jobs s JOIN jobs j ON j.job_id = s.job_id "
        "WHERE s.user_id=? ORDER BY s.saved_at DESC", (uid,)
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["skills"] = [x[0] for x in con.execute(
            "SELECT sk.skill_name FROM job_skills js JOIN skills sk ON sk.skill_id=js.skill_id "
            "WHERE js.job_id=? ORDER BY 1", (d["job_id"],)
        )]
        out.append(d)
    return out


def saved_job_ids(con, uid):
    """Set of job_ids this user has saved."""
    return {r[0] for r in con.execute("SELECT job_id FROM saved_jobs WHERE user_id=?", (uid,))}