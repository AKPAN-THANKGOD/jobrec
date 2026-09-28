"""Populate the database with a small, realistic demo network.
Run: python seed_demo.py
Idempotent — safe to run multiple times. Existing users with the same emails
are left in place; their skills, connections, posts, and messages are replaced.
"""
from db import connect
from werkzeug.security import generate_password_hash

USERS = [
    ("Adaeze Okafor", "adaeze@example.com", "Backend Developer · Python & SQL",
     "Backend engineer building REST APIs with Python and Django. Interested in data pipelines and cloud deployment.",
     ["Python", "Django", "SQL", "PostgreSQL", "Docker", "Git", "REST API"]),
    ("Obi Emmanuel", "obi@example.com", "Data Analyst · Power BI & SQL",
     "Turning business data into decisions. I like clean dashboards and honest metrics.",
     ["Python", "SQL", "Pandas", "Power BI", "Microsoft Excel", "Statistics", "Data Visualization"]),
    ("Chiamaka Eze", "chiamaka@example.com", "Frontend Engineer · React & TypeScript",
     "Frontend engineer who cares about design systems and accessibility.",
     ["JavaScript", "React", "TypeScript", "CSS", "HTML", "Git", "UI/UX Design"]),
    ("Tunde Bakare", "tunde@example.com", "ML Engineer · TensorFlow & PyTorch",
     "Machine learning engineer shipping NLP and computer-vision models to production.",
     ["Python", "Machine Learning", "TensorFlow", "PyTorch", "NLP", "Statistics", "SQL"]),
    ("Ngozi Adeyemi", "ngozi@example.com", "DevOps Engineer · Kubernetes & AWS",
     "Keeping the pipeline green. Kubernetes, Terraform, and a strong opinion on CI/CD.",
     ["Docker", "Kubernetes", "AWS", "Terraform", "Linux", "CI/CD", "Python"]),
    ("Kelechi Nwosu", "kelechi@example.com", "QA Engineer · Test Automation",
     "QA engineer who prefers to prevent bugs rather than report them. Selenium, pytest, and a bit of Python.",
     ["QA Testing", "Test Automation", "Python", "SQL", "Git", "Problem Solving"]),
]

CONNECTIONS = [
    ("adaeze@example.com", "obi@example.com"),
    ("adaeze@example.com", "chiamaka@example.com"),
    ("obi@example.com", "tunde@example.com"),
    ("chiamaka@example.com", "ngozi@example.com"),
    ("tunde@example.com", "kelechi@example.com"),
    ("ngozi@example.com", "adaeze@example.com"),
]

POSTS = [
    ("adaeze@example.com", "Wrapped up a two-week sprint on our billing service. The quiet win was replacing a hand-rolled queue with a proper one — 400 fewer lines of code and no more 3am pages."),
    ("obi@example.com", "Reminder to myself: a slightly better metric definition beats a fancier model almost every time. Spent yesterday agreeing what 'active user' actually means."),
    ("chiamaka@example.com", "Spent the afternoon in the component library instead of Figma. Designing directly in the real tokens caught six inconsistencies a static mock would have missed."),
    ("tunde@example.com", "Small win: got our NER model's F1 from 0.79 to 0.86 by fixing the tokenizer, not by touching the architecture."),
    ("ngozi@example.com", "Cut our CI pipeline from 18 minutes to 6 by parallelising the test suites. Nobody claps for build speed but everyone notices when they get their afternoon back."),
    ("kelechi@example.com", "A user wrote in to say the new offline mode saved their commute. That single message is worth more than any release metric I've stared at this quarter."),
]

COMMENTS = [
    ("obi@example.com", "adaeze@example.com", "Which queue did you go with? We're evaluating the same move."),
    ("tunde@example.com", "obi@example.com", "Preach. Definition debt is real debt."),
    ("adaeze@example.com", "ngozi@example.com", "Six minutes is a dream. Well done."),
    ("chiamaka@example.com", "tunde@example.com", "The tokenizer fix is the most underrated debugging story of the year."),
]

MESSAGES = [
    ("obi@example.com", "adaeze@example.com", "Ada, do you still have that Django REST starter repo? Would love to borrow the auth setup."),
    ("adaeze@example.com", "obi@example.com", "Yes! Sending it now. The auth part is the piece I'm happiest with."),
    ("obi@example.com", "adaeze@example.com", "Perfect. Thank you. I owe you a coffee."),
    ("tunde@example.com", "obi@example.com", "Saw your post about metric definitions. Would you be up for a quick chat about how you framed it with stakeholders?"),
    ("chiamaka@example.com", "ngozi@example.com", "Ngozi, is the staging environment back up yet?"),
    ("ngozi@example.com", "chiamaka@example.com", "Yes, up since this morning. Ping me if anything looks off."),
]


def main():
    con = connect()
    by_email = {}

    for name, email, headline, bio, skills in USERS:
        row = con.execute("SELECT user_id FROM users WHERE email=?", (email,)).fetchone()
        if row is None:
            con.execute(
                "INSERT INTO users(full_name, email, password_hash, role, headline, bio) "
                "VALUES(?,?,?,?,?,?)",
                (name, email, generate_password_hash("password123"), "Job Seeker", headline, bio),
            )
            uid = con.execute("SELECT last_insert_rowid()").fetchone()[0]
        else:
            uid = row["user_id"]
            con.execute("UPDATE users SET headline=?, bio=? WHERE user_id=?", (headline, bio, uid))
        by_email[email] = uid

    for name, email, headline, bio, skills in USERS:
        uid = by_email[email]
        con.execute("DELETE FROM user_skills WHERE user_id=?", (uid,))
        for s in skills:
            con.execute("INSERT INTO user_skills(user_id, skill_id) "
                        "SELECT ?, skill_id FROM skills WHERE skill_name=?", (uid, s))

    for a_email, b_email in CONNECTIONS:
        a, b = by_email[a_email], by_email[b_email]
        con.execute("DELETE FROM connections WHERE (requester_id=? AND addressee_id=?) "
                    "OR (requester_id=? AND addressee_id=?)", (a, b, b, a))
        con.execute("INSERT INTO connections(requester_id, addressee_id, status) "
                    "VALUES(?,?, 'accepted')", (a, b))

    for name, email, *_ in USERS:
        con.execute("DELETE FROM posts WHERE user_id=?", (by_email[email],))
    post_ids = {}
    for email, content in POSTS:
        uid = by_email[email]
        pid = con.execute("INSERT INTO posts(user_id, content) VALUES(?,?)",
                          (uid, content)).lastrowid
        post_ids[email] = pid

    for commenter_email, author_email, text in COMMENTS:
        pid = post_ids.get(author_email)
        if pid:
            con.execute("INSERT INTO post_comments(post_id, user_id, content) VALUES(?,?,?)",
                        (pid, by_email[commenter_email], text))

    for a_email, b_email, content in MESSAGES:
        con.execute("INSERT INTO messages(sender_id, recipient_id, content) VALUES(?,?,?)",
                    (by_email[a_email], by_email[b_email], content))

    con.commit()
    print("Demo network seeded. Sign in with any of these accounts:")
    for _, email, *_ in USERS:
        print(f"  {email}  /  password123")
    con.close()


if __name__ == "__main__":
    main()