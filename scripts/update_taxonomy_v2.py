import json
import os

TAXONOMY_PATH = r'c:\Users\zuko\Documents\a\AI_JobRecomender\data\skills_taxonomy.json'

# New specific skills to add
new_skills_to_add = [
    {"skill_id": "sm-galileo", "canonical_name": "Galileo GDS", "aliases": ["galileo", "galileo certified", "galileo system certified", "galileo system certification"], "domain": "Hospitality & Services", "category": "Hospitality & Culinary", "weight": 1.1, "differentiation_tags": ["travel", "hospitality"]},
    {"skill_id": "soft-math", "canonical_name": "Mathematics", "aliases": ["math", "mathematics", "basic mathematical skills", "numeracy"], "domain": "Soft Skills & Languages", "category": "Soft Skills", "weight": 1.0, "differentiation_tags": ["soft-skill"]},
]

# Aliases to add to existing skills
alias_mapping = {
    "soft-comm": [
        "strong communication and persuasion skills", 
        "excellent communication and organizational skills", 
        "excellent interpersonal and communication skills",
        "compassion and interpersonal skills",
        "communication processes",
        "good communication skill",
        "excellent verbal and written communication skills"
    ],
    "soft-nego": [
        "negotiation and closing techniques"
    ],
    "soft-problem": [
        "result-oriented and self-motivated",
        "strategic thinking and analytical skills",
        "motivational"
    ],
    "dm-pr": [
        "proficiency in adobe premiere pro or final cut pro"
    ],
    "dm-vedit": [
        "knowledge of video formats and compression",
        "creative storytelling and rhythmic sense"
    ],
    "ba-msoffice": [
        "proficiency in microsoft office suite",
        "basic computer skills",
        "basic computer skill",
        "basic computer knowledge",
        "microsoft office skills"
    ],
    "soft-cust": [
        "customer service orientation"
    ],
    "hosp-culinary": [
        "culinary school degree or equivalent experience"
    ],
    "soft-lead": [
        "leadership and team management",
        "leadership and communication"
    ],
    "soft-timemgmt": [
        "punctuality and responsibility",
        "ability to work in a fast-paced environment",
        "organization: ability to manage multiple tasks and deadlines effectively"
    ],
    "sm-market": [
        "knowledge of digital and traditional marketing"
    ],
    "soft-attention": [
        "strong attention to detail and ethics",
        "punctuality and attention to detail"
    ],
    "fa-peach": [
        "peachtree software",
        "peachtree expertise"
    ],
    "fa-acc": [
        "accounting degree"
    ],
    "soft-mgmt": [
        "experience with kids" # Often mentioned as person management in tutor/kg sub-jobs
    ]
}

def main():
    if not os.path.exists(TAXONOMY_PATH):
        print(f"Taxonomy file not found at {TAXONOMY_PATH}")
        return

    with open(TAXONOMY_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    existing_skills = data.get("skills", [])
    existing_ids = {s["skill_id"] for s in existing_skills}

    # Add new skills
    added_skills = 0
    for sk in new_skills_to_add:
        if sk["skill_id"] not in existing_ids:
            existing_skills.append(sk)
            added_skills += 1
            print(f"Added new skill: {sk['skill_id']}")

    # Add aliases
    updated_aliases = 0
    for sk in existing_skills:
        skill_id = sk["skill_id"]
        if skill_id in alias_mapping:
            current_aliases = set(a.lower() for a in sk.get("aliases", []))
            for new_alias in alias_mapping[skill_id]:
                if new_alias.lower() not in current_aliases:
                    sk["aliases"].append(new_alias)
                    updated_aliases += 1
                    print(f"Added alias to {skill_id}: {new_alias}")

    if added_skills > 0 or updated_aliases > 0:
        with open(TAXONOMY_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\nSuccessfully added {added_skills} skills and {updated_aliases} aliases.")
    else:
        print("No updates needed.")

if __name__ == '__main__':
    main()
