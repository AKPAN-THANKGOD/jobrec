"""Unit tests for the matching engine, taxonomy and data-access layer.
Run: python -m unittest -v   (uses a throwaway in-memory database per test,
never touches jobrec.db). Stdlib only — no extra install needed."""
import sqlite3
import unittest

from db import SCHEMA
from engine import Taxonomy, Recommender, level
import store


def make_con():
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    skills = [
        ("Python", "Programming", "python3,py"), ("SQL", "Database", ""),
        ("Docker", "Tools", "containers"), ("Statistics", "Data Science", "stats"),
        ("Communication", "Soft Skill", ""),
    ]
    con.executemany("INSERT INTO skills(skill_name, category, aliases) VALUES(?,?,?)", skills)
    con.execute("INSERT INTO users(full_name, email, password_hash, role) VALUES('Ada','ada@x.com','h','Job Seeker')")
    return con


def add_job(con, title, description):
    tax = Taxonomy(con.execute("SELECT skill_name, aliases FROM skills").fetchall())
    jid = con.execute("INSERT INTO jobs(title, company, location, description) VALUES(?,?,?,?)",
                      (title, "Co", "Remote", description)).lastrowid
    for name in tax.standardise(description):
        con.execute("INSERT INTO job_skills SELECT ?, skill_id FROM skills WHERE skill_name=?", (jid, name))
    return jid


class EngineTestCase(unittest.TestCase):
    def setUp(self):
        self.con = make_con()

    def tearDown(self):
        self.con.close()

    # ---------------------------------------------------------- Taxonomy
    def test_whole_word_matching_avoids_false_positives(self):
        tax = Taxonomy(self.con.execute("SELECT skill_name, aliases FROM skills").fetchall())
        self.assertEqual(tax.standardise("Pythonic code style"), set())  # must not match "Python"
        self.assertEqual(tax.standardise("I know Python and SQL"), {"Python", "SQL"})

    def test_aliases_resolve_to_canonical_name(self):
        tax = Taxonomy(self.con.execute("SELECT skill_name, aliases FROM skills").fetchall())
        self.assertEqual(tax.standardise("solid py and containers experience"), {"Python", "Docker"})

    def test_duplicate_alias_across_skills_is_rejected(self):
        rows = [dict(r) for r in self.con.execute("SELECT skill_name, aliases FROM skills").fetchall()]
        rows.append({"skill_name": "Scripting", "aliases": "py"})  # 'py' already = Python
        with self.assertRaises(ValueError):
            Taxonomy(rows)

    def test_level_thresholds(self):
        self.assertEqual(level(0), "Low")
        self.assertEqual(level(39.9), "Low")
        self.assertEqual(level(40), "Moderate")
        self.assertEqual(level(69.9), "Moderate")
        self.assertEqual(level(70), "Strong")
        self.assertEqual(level(100), "Strong")

    # -------------------------------------------------------- Recommender
    def test_recommend_ranks_best_match_first(self):
        add_job(self.con, "Data Job", "Needs Python, SQL and Statistics")
        add_job(self.con, "Ops Job", "Needs Docker only")
        rec = Recommender(self.con)
        results = rec.recommend(rec.tax.standardise("python, sql, statistics"))
        self.assertEqual(results[0]["title"], "Data Job")
        self.assertEqual(results[0]["match_pct"], 100.0)
        self.assertEqual(results[0]["missing"], [])

    def test_recommend_reports_missing_skills_heaviest_first(self):
        add_job(self.con, "Data Job", "Needs Python, SQL, Statistics and Communication")
        rec = Recommender(self.con)
        results = rec.recommend(rec.tax.standardise("python"))
        missing = [m["skill"] for m in results[0]["missing"]]
        weights = [m["weight"] for m in results[0]["missing"]]
        self.assertEqual(set(missing), {"SQL", "Statistics", "Communication"})
        self.assertEqual(weights, sorted(weights, reverse=True))  # heaviest gap first

    def test_recommend_empty_skills_returns_no_results(self):
        add_job(self.con, "Data Job", "Needs Python")
        rec = Recommender(self.con)
        self.assertEqual(rec.recommend(set()), [])

    def test_recommend_with_no_jobs_in_db_is_safe(self):
        rec = Recommender(self.con)
        self.assertEqual(rec.recommend({"Python"}), [])

    def test_zero_similarity_jobs_are_excluded(self):
        add_job(self.con, "Data Job", "Needs Python and SQL")
        add_job(self.con, "Design Job", "Needs Communication only")
        rec = Recommender(self.con)
        titles = [r["title"] for r in rec.recommend(rec.tax.standardise("python, sql"))]
        self.assertEqual(titles, ["Data Job"])  # shares no skills -> similarity 0, dropped

    # ------------------------------------------------------------- store
    def test_register_rejects_short_password(self):
        with self.assertRaises(ValueError):
            store.register(self.con, "Bob", "bob@x.com", "123")

    def test_register_and_authenticate_roundtrip(self):
        store.register(self.con, "Bob", "bob@x.com", "secret1")
        self.assertIsNotNone(store.authenticate(self.con, "bob@x.com", "secret1"))
        self.assertIsNone(store.authenticate(self.con, "bob@x.com", "wrongpass"))

    def test_register_duplicate_email_rejected(self):
        store.register(self.con, "Bob", "bob@x.com", "secret1")
        with self.assertRaises(ValueError):
            store.register(self.con, "Bob2", "bob@x.com", "secret2")

    def test_save_and_get_profile(self):
        uid = self.con.execute("SELECT user_id FROM users WHERE email='ada@x.com'").fetchone()[0]
        found, unknown = store.save_profile(self.con, uid, ["python", "not-a-real-skill"])
        self.assertEqual(found, ["Python"])
        self.assertEqual(unknown, ["not-a-real-skill"])
        self.assertEqual(store.get_profile(self.con, uid), ["Python"])

    def test_save_job_rejects_no_recognised_skills(self):
        with self.assertRaises(ValueError):
            store.save_job(self.con, None, "Mystery Job", "Co", "Remote", "Needs telepathy", ["telepathy"])

    def test_save_skill_rejects_alias_clash(self):
        with self.assertRaises(ValueError):
            store.save_skill(self.con, None, "Scripting", "Programming", "py")  # 'py' already = Python

    def test_save_skill_allows_editing_its_own_aliases(self):
        sid = self.con.execute("SELECT skill_id FROM skills WHERE skill_name='Python'").fetchone()[0]
        store.save_skill(self.con, sid, "Python", "Programming", "python3,py,py3")  # must not clash with itself
        row = next(s for s in store.list_skills(self.con) if s["skill_name"] == "Python")
        self.assertIn("py3", row["aliases"])

    def test_delete_skill_removes_links(self):
        add_job(self.con, "Data Job", "Needs Python and SQL")
        sid = self.con.execute("SELECT skill_id FROM skills WHERE skill_name='Python'").fetchone()[0]
        store.delete_skill(self.con, sid)
        names = [s["skill_name"] for s in store.list_skills(self.con)]
        self.assertNotIn("Python", names)
        links = self.con.execute("SELECT 1 FROM job_skills js JOIN skills s ON s.skill_id=js.skill_id "
                                 "WHERE s.skill_name='Python'").fetchall()
        self.assertEqual(links, [])

    # -------------------------------------------------------- Network layer
    def _second_user(self, skills=("python",)):
        store.register(self.con, "Bob", "bob@x.com", "secret1")
        bob = self.con.execute("SELECT user_id FROM users WHERE email='bob@x.com'").fetchone()[0]
        ada = self.con.execute("SELECT user_id FROM users WHERE email='ada@x.com'").fetchone()[0]
        if skills:
            store.save_profile(self.con, bob, list(skills))
        return ada, bob

    def test_connection_request_accept_roundtrip(self):
        ada, bob = self._second_user()
        self.assertEqual(store.connection_status(self.con, ada, bob), "none")
        store.send_connection_request(self.con, bob, ada)
        self.assertEqual(store.connection_status(self.con, ada, bob), "pending_incoming")
        self.assertEqual(store.connection_status(self.con, bob, ada), "pending_outgoing")
        store.respond_connection_request(self.con, ada, bob, True)
        self.assertEqual(store.connection_status(self.con, ada, bob), "accepted")
        self.assertEqual([c["user_id"] for c in store.list_connections(self.con, ada)], [bob])

    def test_duplicate_connection_request_rejected(self):
        ada, bob = self._second_user()
        store.send_connection_request(self.con, bob, ada)
        with self.assertRaises(ValueError):
            store.send_connection_request(self.con, bob, ada)

    def test_self_connection_rejected(self):
        with self.assertRaises(ValueError):
            store.send_connection_request(self.con, 1, 1)

    def test_suggestions_are_explained_by_shared_skills(self):
        ada, bob = self._second_user(skills=["python", "sql"])
        store.save_profile(self.con, ada, ["python", "docker"])
        suggestions = store.suggest_connections(self.con, ada)
        self.assertEqual(suggestions[0]["user_id"], bob)
        self.assertEqual(suggestions[0]["shared_skills"], ["Python"])

    def test_message_blocked_unless_connected(self):
        ada, bob = self._second_user()
        with self.assertRaises(ValueError):
            store.send_message(self.con, bob, ada, "hi")
        store.send_connection_request(self.con, bob, ada)
        store.respond_connection_request(self.con, ada, bob, True)
        store.send_message(self.con, bob, ada, "hi")  # now allowed
        thread = store.list_conversation(self.con, ada, bob)
        self.assertEqual(thread[0]["content"], "hi")

    def test_feed_shows_only_own_and_connections_posts(self):
        ada, bob = self._second_user()
        store.create_post(self.con, bob, "Bob's update")
        self.assertEqual(store.list_feed(self.con, ada), [])  # not connected yet
        store.send_connection_request(self.con, bob, ada)
        store.respond_connection_request(self.con, ada, bob, True)
        feed = store.list_feed(self.con, ada)
        self.assertEqual(len(feed), 1)
        self.assertEqual(feed[0]["content"], "Bob's update")

    def test_like_toggles(self):
        ada, _ = self._second_user()
        pid = store.create_post(self.con, ada, "Hello")
        self.assertTrue(store.toggle_like(self.con, ada, pid))
        self.assertFalse(store.toggle_like(self.con, ada, pid))

    def test_empty_post_and_comment_rejected(self):
        ada, _ = self._second_user()
        with self.assertRaises(ValueError):
            store.create_post(self.con, ada, "   ")
        pid = store.create_post(self.con, ada, "Hello")
        with self.assertRaises(ValueError):
            store.add_comment(self.con, ada, pid, "")


if __name__ == "__main__":
    unittest.main()
