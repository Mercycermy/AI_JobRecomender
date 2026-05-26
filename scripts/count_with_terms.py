import sqlite3

conn = sqlite3.connect("data/jobs.db")
cursor = conn.cursor()

ROLE_LABELS = {
    "frontend-dev": ["frontend developer", "react developer", "web developer"],
    "backend-dev": ["backend developer", "api developer", "software developer"],
    "fullstack-dev": ["full stack developer", "fullstack developer"],
    "mobile-dev": ["mobile developer", "flutter developer"],
    "devops": ["devops", "devops engineer"],
    "data-analyst": ["data analyst", "business analyst"],
    "data-scientist": ["data scientist"],
    "ml-engineer": ["machine learning engineer", "ml engineer"],
    "graphic-designer": ["graphic designer", "graphics designer"],
    "ui-ux-designer": ["ui designer", "ux designer", "ui/ux designer"],
    "video-editor": ["video editor"],
    "sales": ["sales", "sales representative"],
    "digital-marketer": ["digital marketer", "marketing"],
    "accounting": ["accountant", "accounting", "cashier"],
    "finance": ["finance", "banking"],
    "admin": ["admin", "secretary", "office manager", "hr"],
    "project-manager": ["project manager"],
    "architect": ["architect", "site engineer", "civil engineer"],
    # added from the user request
    "teacher": ["teacher"],
    "trainer": ["trainer"],
    "education": ["education"],
    "medical": ["medical", "healthcare"],
    "transport": ["transport", "logistics", "driving"],
    "general": ["general"]
}

def _role_search_terms(role):
    terms = [role, role.replace("-", " ")]
    terms.extend(ROLE_LABELS.get(role, []))
    return list(dict.fromkeys(term for term in terms if term))

print("Role Matching Counts with search terms:")
for role in ROLE_LABELS.keys():
    terms = _role_search_terms(role)
    clauses = []
    params = []
    for term in terms:
        clauses.append("role_targets LIKE ?")
        params.append(f"%{term}%")
        clauses.append("job_evidence LIKE ?")
        params.append(f"%{term}%")
    
    query = f"SELECT COUNT(*) FROM questions WHERE ({' OR '.join(clauses)})"
    count = cursor.execute(query, params).fetchone()[0]
    print(f"  {role}: {count} matches (terms: {terms})")

conn.close()
