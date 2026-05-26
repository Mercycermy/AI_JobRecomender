import sqlite3
import json

conn = sqlite3.connect("data/jobs.db")
cursor = conn.cursor()

roles = [
    "backend-dev", "frontend-dev", "fullstack-dev", "mobile-dev", "architect", "devops", "tech",
    "data-analyst", "data-scientist", "ml-engineer",
    "graphic-designer", "ui-ux-designer", "video-editor", "creative",
    "admin", "project-manager", "finance", "accounting",
    "sales", "digital-marketer", "sales_marketing",
    "teacher", "trainer", "education",
    "medical", "transport", "general"
]

print("Question Counts by Role & Difficulty:")
for role in roles:
    beg_count = cursor.execute("SELECT COUNT(*) FROM questions WHERE role_targets LIKE ? AND difficulty='beginner'", (f'%"{role}"%',)).fetchone()[0]
    int_count = cursor.execute("SELECT COUNT(*) FROM questions WHERE role_targets LIKE ? AND difficulty='intermediate'", (f'%"{role}"%',)).fetchone()[0]
    adv_count = cursor.execute("SELECT COUNT(*) FROM questions WHERE role_targets LIKE ? AND difficulty='advanced'", (f'%"{role}"%',)).fetchone()[0]
    print(f"  {role}: beginner={beg_count}, intermediate={int_count}, advanced={adv_count}")

conn.close()
