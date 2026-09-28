"""SQLite schema (Tables 3.4-3.7) and seed data. Run `python db.py` to (re)build."""
import os, sqlite3
from werkzeug.security import generate_password_hash
from engine import Taxonomy

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jobrec.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
  user_id INTEGER PRIMARY KEY AUTOINCREMENT,
  full_name TEXT,
  email TEXT UNIQUE,
  password_hash TEXT,
  role TEXT,
  headline TEXT,
  bio TEXT,
  last_seen_feed DATETIME,
  last_seen_messages DATETIME,
  last_seen_network DATETIME,
  date_created DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS skills(skill_id INTEGER PRIMARY KEY AUTOINCREMENT, skill_name TEXT UNIQUE,
  category TEXT, aliases TEXT);
CREATE TABLE IF NOT EXISTS jobs(job_id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, company TEXT,
  location TEXT, description TEXT, date_posted DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS user_skills(user_id INTEGER REFERENCES users, skill_id INTEGER REFERENCES skills,
  PRIMARY KEY(user_id, skill_id));
CREATE TABLE IF NOT EXISTS job_skills(job_id INTEGER REFERENCES jobs, skill_id INTEGER REFERENCES skills,
  PRIMARY KEY(job_id, skill_id));
CREATE TABLE IF NOT EXISTS work_history(entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER REFERENCES users, title TEXT, company TEXT, start_year TEXT, end_year TEXT, description TEXT);
CREATE TABLE IF NOT EXISTS connections(requester_id INTEGER REFERENCES users, addressee_id INTEGER REFERENCES users,
  status TEXT DEFAULT 'pending', created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY(requester_id, addressee_id));
CREATE TABLE IF NOT EXISTS posts(post_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER REFERENCES users,
  content TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS post_likes(post_id INTEGER REFERENCES posts, user_id INTEGER REFERENCES users,
  PRIMARY KEY(post_id, user_id));
CREATE TABLE IF NOT EXISTS post_comments(comment_id INTEGER PRIMARY KEY AUTOINCREMENT,
  post_id INTEGER REFERENCES posts, user_id INTEGER REFERENCES users, content TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS messages(message_id INTEGER PRIMARY KEY AUTOINCREMENT,
  sender_id INTEGER REFERENCES users, recipient_id INTEGER REFERENCES users, content TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS notifications(
  notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER REFERENCES users,
  kind TEXT,
  ref_id INTEGER,
  title TEXT,
  body TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  read_at DATETIME
);
CREATE TABLE IF NOT EXISTS saved_jobs(
  user_id INTEGER REFERENCES users,
  job_id INTEGER REFERENCES jobs,
  saved_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY(user_id, job_id)
);
"""

from seed_data import EXTRA_SKILLS, JOBS

SKILLS = [  # name, category, aliases
    ("Python", "Programming", "python3,py"), ("JavaScript", "Programming", "js,ecmascript"),
    ("Java", "Programming", ""), ("C++", "Programming", "cpp"), ("HTML", "Web", "html5"),
    ("CSS", "Web", "css3"), ("React", "Web", "reactjs,react.js"), ("Node.js", "Web", "nodejs,node.js"),
    ("Flask", "Web", ""), ("Django", "Web", ""), ("REST API", "Web", "rest apis,restful api,rest api"),
    ("SQL", "Database", "structured query language"), ("Database Design", "Database", "data modelling,data modeling,database modelling"),
    ("Git", "Tools", "github,version control"), ("Docker", "Tools", "containers"), ("Linux", "Systems", "unix"),
    ("AWS", "Cloud", "amazon web services"), ("Networking", "Systems", "computer networking"),
    ("Cybersecurity", "Security", "cyber security,information security"),
    ("Machine Learning", "Data Science", "ml"), ("Statistics", "Data Science", "statistical analysis"),
    ("Pandas", "Data Science", ""), ("Data Visualization", "Data Science", "data viz,data visualisation"),
    ("Power BI", "Data Science", "powerbi"), ("Microsoft Excel", "Productivity Tools", "excel,ms excel"),
    ("Project Management", "Management", ""), ("Communication", "Soft Skill", "communication skills,verbal communication"),
    ("Teamwork", "Soft Skill", "team work,collaboration"), ("Problem Solving", "Soft Skill", "problem-solving"),
] + EXTRA_SKILLS


def connect():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


def add_job(con, title, company, location, description):
    tax = Taxonomy(con.execute("SELECT skill_name, aliases FROM skills").fetchall())
    jid = con.execute("INSERT INTO jobs(title, company, location, description) VALUES(?,?,?,?)",
                      (title, company, location, description)).lastrowid
    for name in tax.standardise(description):
        con.execute("INSERT INTO job_skills SELECT ?, skill_id FROM skills WHERE skill_name=?", (jid, name))
    return jid


def create_user(con, name, email, password, role="Job Seeker"):
    con.execute("INSERT INTO users(full_name, email, password_hash, role) VALUES(?,?,?,?)",
                (name, email.strip().lower(), generate_password_hash(password), role))


def init_db():
    with connect() as con:
        con.executescript(SCHEMA)
        if not con.execute("SELECT 1 FROM skills LIMIT 1").fetchone():
            con.executemany("INSERT INTO skills(skill_name, category, aliases) VALUES(?,?,?)", SKILLS)
            for job in JOBS:
                add_job(con, *job)
        if not con.execute("SELECT 1 FROM users WHERE role='Administrator'").fetchone():
            create_user(con, "Administrator", "admin@example.com", "admin123", "Administrator")


if __name__ == "__main__":
    if os.path.exists(DB):
        os.remove(DB)
    init_db()
    print("Database built:", DB)