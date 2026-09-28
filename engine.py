"""Matching engine: skill standardisation (3.8.1), TF-IDF vectors (3.8.2),
cosine ranking (3.8.3), skill gap analysis + explanation (3.8.4)."""
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class Taxonomy:
    def __init__(self, rows):
        self.term_to_skill = {}
        for r in rows:
            for t in [r["skill_name"]] + (r["aliases"] or "").split(","):
                t = t.strip().lower()
                if t and self.term_to_skill.setdefault(t, r["skill_name"]) != r["skill_name"]:
                    raise ValueError(f"Alias '{t}' belongs to more than one skill")
        # longest terms first; whole-word match only, '+', '#' count as word characters
        self.patterns = [(re.compile(r"(?<![\w+#])" + re.escape(t) + r"(?![\w+#])"), s)
                         for t, s in sorted(self.term_to_skill.items(), key=lambda x: -len(x[0]))]

    def standardise(self, text):
        text = re.sub(r"[,;:()\n]", " ", text.lower())
        found = set()
        for pat, skill in self.patterns:
            if pat.search(text):
                found.add(skill)
                text = pat.sub(" ", text)  # blank out so shorter aliases can't re-match
        return found


def level(pct):
    return "Strong" if pct >= 70 else "Moderate" if pct >= 40 else "Low"


class Recommender:
    def __init__(self, con):
        self.tax = Taxonomy(con.execute("SELECT skill_name, aliases FROM skills").fetchall())
        self.names = sorted(r[0] for r in con.execute("SELECT skill_name FROM skills"))
        req = {}
        for jid, name in con.execute("SELECT js.job_id, s.skill_name FROM job_skills js "
                                     "JOIN skills s ON s.skill_id = js.skill_id"):
            req.setdefault(jid, set()).add(name)
        self.jobs = [dict(r, req=req[r["job_id"]]) for r in
                     con.execute("SELECT job_id, title, company, location FROM jobs")
                     if r["job_id"] in req]
        # binary term frequency; smoothed idf = ln((1+N)/(1+df)) + 1; L2-normalised
        self.vec = TfidfVectorizer(analyzer=list, lowercase=False, vocabulary=self.names)
        self.matrix = self.vec.fit_transform([j["req"] for j in self.jobs]) if self.jobs else None
        self.idf = dict(zip(self.names, self.vec.idf_)) if self.jobs else {}

    def recommend(self, skills, k=10):
        S = set(skills)
        if not S or not self.jobs:
            return []
        sims = cosine_similarity(self.vec.transform([S]), self.matrix)[0]
        out = []
        for j, sim in sorted(zip(self.jobs, sims), key=lambda x: (-x[1], x[0]["title"])):
            if sim <= 0:
                continue
            R = j["req"]
            matched = sorted(S & R)
            missing = sorted(R - S, key=lambda s: (-self.idf[s], s))  # heaviest gap first
            pct = 100 * sum(self.idf[s] for s in matched) / sum(self.idf[s] for s in R)
            text = (f"{j['title']} is recommended because your skills in {', '.join(matched)} "
                    f"match its requirements. Your skills cover {pct:.1f}% of its weighted "
                    f"requirements ({level(pct)} match).")
            text += (f" To qualify fully, you need to acquire: {', '.join(missing)}." if missing
                     else " You already meet all of its listed requirements.")
            out.append({"job_id": j["job_id"], "title": j["title"], "company": j["company"],
                        "location": j["location"], "cosine": round(float(sim), 3),
                        "match_pct": round(pct, 1), "level": level(pct), "matched": matched,
                        "missing": [{"skill": s, "weight": round(float(self.idf[s]), 2)} for s in missing],
                        "explanation": text})
        return out[:k]
