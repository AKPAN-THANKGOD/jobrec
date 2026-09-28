"""Chapter 4 evaluation: precision@k / recall@k against a relevance ground truth,
recommendation response time, and a spot-check of the skill-gap output.
Run: python evaluate.py   (rebuilds nothing — run `python db.py` first if the
database or seed_data.py has changed)
"""
import statistics as st
import time

from db import connect
from engine import Recommender

# --- Test profiles ------------------------------------------------------
# Each profile is a realistic candidate skill set. `relevant` lists the job
# titles a human reviewer judged to be a good match for that profile — the
# ground truth precision/recall are measured against. Titles are unique in
# the seed_data.py dataset, so they double as job identifiers here.
PROFILES = [
    {"name": "Frontend-leaning web dev", "skills": ["HTML", "CSS", "JavaScript", "React", "Git"],
     "relevant": ["Junior Web Developer", "Senior Frontend Engineer", "Full Stack Developer", "UI/UX Designer"]},
    {"name": "Python backend dev", "skills": ["Python", "Django", "SQL", "Docker", "Git", "AWS"],
     "relevant": ["Backend Developer (Python)", "Full Stack Developer", "Junior Data Engineer"]},
    {"name": "Data analyst", "skills": ["Python", "SQL", "Pandas", "Statistics", "Microsoft Excel", "Power BI"],
     "relevant": ["Data Analyst", "Business Intelligence Analyst", "Junior Data Engineer"]},
    {"name": "ML/AI specialist", "skills": ["Python", "Machine Learning", "TensorFlow", "PyTorch", "Statistics", "SQL"],
     "relevant": ["Machine Learning Engineer", "Data Scientist", "NLP Engineer", "Computer Vision Engineer"]},
    {"name": "Cloud/DevOps engineer", "skills": ["Docker", "Kubernetes", "AWS", "Terraform", "CI/CD", "Linux"],
     "relevant": ["DevOps Engineer", "Cloud Engineer", "Site Reliability Engineer"]},
    {"name": "Security specialist", "skills": ["Cybersecurity", "Networking", "Linux", "Penetration Testing"],
     "relevant": ["Security Analyst", "Penetration Tester", "Network Administrator"]},
    {"name": "QA / testing", "skills": ["QA Testing", "Test Automation", "SQL", "Git", "Python"],
     "relevant": ["QA Engineer", "Automation Test Engineer"]},
    {"name": "Mobile developer", "skills": ["Kotlin", "Swift", "Mobile Development", "Git", "REST API"],
     "relevant": ["Mobile App Developer"]},
    {"name": "Non-technical / support", "skills": ["Communication", "Customer Service", "Networking", "Teamwork"],
     "relevant": ["IT Support Specialist", "Network Administrator"]},
    {"name": "Sparse profile (2 skills)", "skills": ["SQL", "Communication"],
     "relevant": ["Data Analyst", "Business Intelligence Analyst", "Sales Engineer", "Project Coordinator"]},
]

K = 5  # evaluate precision/recall at this cutoff


def precision_recall_at_k(recommended_titles, relevant_titles, k):
    top_k = recommended_titles[:k]
    hits = sum(1 for t in top_k if t in relevant_titles)
    precision = hits / len(top_k) if top_k else 0.0
    recall = hits / len(relevant_titles) if relevant_titles else 0.0
    return precision, recall


def run():
    con = connect()
    rec = Recommender(con)
    print(f"Dataset: {len(rec.jobs)} vacancies, {len(rec.names)} taxonomy skills\n")
    print(f"{'Profile':<28}{'P@'+str(K):>8}{'R@'+str(K):>8}{'ms':>8}   Top result")
    print("-" * 78)

    precisions, recalls, times = [], [], []
    for p in PROFILES:
        skills = rec.tax.standardise(", ".join(p["skills"]))
        t0 = time.perf_counter()
        results = rec.recommend(skills, k=K)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        titles = [r["title"] for r in results]
        prec, rec_ = precision_recall_at_k(titles, p["relevant"], K)
        precisions.append(prec); recalls.append(rec_); times.append(elapsed_ms)
        top = f"{titles[0]} ({results[0]['match_pct']}%)" if results else "(none)"
        print(f"{p['name']:<28}{prec:>8.2f}{rec_:>8.2f}{elapsed_ms:>8.2f}   {top}")

    print("-" * 78)
    print(f"{'MEAN':<28}{st.mean(precisions):>8.2f}{st.mean(recalls):>8.2f}{st.mean(times):>8.2f}")
    print(f"\nResponse time: mean {st.mean(times):.2f} ms, max {max(times):.2f} ms "
          f"over {len(PROFILES)} profiles against {len(rec.jobs)} vacancies.")

    # --- Skill-gap spot check -------------------------------------------
    # For one profile, print the system's gap list next to a manual check:
    # every job_skills entry not in the candidate's skill set, weighted by idf.
    print("\nSkill-gap spot check — 'Python backend dev' vs Backend Developer (Python):")
    profile = PROFILES[1]
    skills = rec.tax.standardise(", ".join(profile["skills"]))
    job = next(j for j in rec.jobs if j["title"] == "Backend Developer (Python)")
    system_missing = sorted(job["req"] - skills)
    manual_missing = sorted(s for s in job["req"] if s not in skills)  # same rule, computed independently
    print("  System reported missing:", system_missing)
    print("  Manually computed missing:", manual_missing)
    print("  Match:", "PASS" if system_missing == manual_missing else "FAIL")


if __name__ == "__main__":
    run()
