import json
import os

TAXONOMY_PATH = r'c:\Users\zuko\Documents\a\AI_JobRecomender\data\skills_taxonomy.json'

new_skills = [
    # Languages
    {"skill_id": "lang-amh", "canonical_name": "Amharic", "aliases": ["amharic", "amharic language"], "domain": "Soft Skills & Languages", "category": "Languages", "weight": 1.5, "differentiation_tags": ["language"]},
    {"skill_id": "lang-eng", "canonical_name": "English", "aliases": ["english", "english language", "english fluency"], "domain": "Soft Skills & Languages", "category": "Languages", "weight": 1.5, "differentiation_tags": ["language"]},
    {"skill_id": "lang-oro", "canonical_name": "Oromiffa (Oromo)", "aliases": ["oromo", "oromiffa", "afaan oromo", "oromeffa fluency"], "domain": "Soft Skills & Languages", "category": "Languages", "weight": 1.2, "differentiation_tags": ["language"]},
    {"skill_id": "lang-tig", "canonical_name": "Tigrinya", "aliases": ["tigrinya", "tigrigna"], "domain": "Soft Skills & Languages", "category": "Languages", "weight": 1.1, "differentiation_tags": ["language"]},
    {"skill_id": "lang-fre", "canonical_name": "French", "aliases": ["french", "french language"], "domain": "Soft Skills & Languages", "category": "Languages", "weight": 1.0, "differentiation_tags": ["language"]},
    {"skill_id": "lang-ara", "canonical_name": "Arabic", "aliases": ["arabic", "arabic language", "arabic and english languages"], "domain": "Soft Skills & Languages", "category": "Languages", "weight": 1.1, "differentiation_tags": ["language"]},
    
    # Soft Skills
    {"skill_id": "soft-comm", "canonical_name": "Communication", "aliases": ["communication", "communication skills", "strong communication", "excellent communication", "interpersonal skills", "listening", "verbal"], "domain": "Soft Skills & Languages", "category": "Soft Skills", "weight": 1.5, "differentiation_tags": ["soft-skill"]},
    {"skill_id": "soft-mgmt", "canonical_name": "Management", "aliases": ["management", "people management", "team management"], "domain": "Soft Skills & Languages", "category": "Soft Skills", "weight": 1.4, "differentiation_tags": ["soft-skill", "leadership"]},
    {"skill_id": "soft-lead", "canonical_name": "Leadership", "aliases": ["leadership", "leading"], "domain": "Soft Skills & Languages", "category": "Soft Skills", "weight": 1.4, "differentiation_tags": ["soft-skill", "leadership"]},
    {"skill_id": "soft-write", "canonical_name": "Writing", "aliases": ["writing", "copywriting", "writing skills", "report writing"], "domain": "Soft Skills & Languages", "category": "Soft Skills", "weight": 1.2, "differentiation_tags": ["soft-skill"]},
    {"skill_id": "soft-cust", "canonical_name": "Customer Service", "aliases": ["customer service", "customer handling", "customer relationship"], "domain": "Soft Skills & Languages", "category": "Soft Skills", "weight": 1.3, "differentiation_tags": ["soft-skill"]},
    {"skill_id": "soft-nego", "canonical_name": "Negotiation", "aliases": ["negotiation", "negotiating", "closing techniques"], "domain": "Soft Skills & Languages", "category": "Soft Skills", "weight": 1.3, "differentiation_tags": ["soft-skill"]},

    # Sales & Marketing
    {"skill_id": "sm-market", "canonical_name": "Marketing", "aliases": ["marketing", "marketing management", "digital marketing", "marketing strategies"], "domain": "Business & Management", "category": "Sales & Marketing", "weight": 1.5, "differentiation_tags": ["business"]},
    {"skill_id": "sm-sales", "canonical_name": "Sales", "aliases": ["sales", "selling", "sales skills", "sales presentation"], "domain": "Business & Management", "category": "Sales & Marketing", "weight": 1.5, "differentiation_tags": ["business"]},
    {"skill_id": "sm-seo", "canonical_name": "SEO", "aliases": ["seo", "search engine optimization"], "domain": "Business & Management", "category": "Sales & Marketing", "weight": 1.2, "differentiation_tags": ["digital-marketing"]},
    {"skill_id": "sm-social", "canonical_name": "Social Media Management", "aliases": ["social media", "social media management", "social media marketing"], "domain": "Business & Management", "category": "Sales & Marketing", "weight": 1.3, "differentiation_tags": ["digital-marketing"]},

    # Business & Administration
    {"skill_id": "ba-excel", "canonical_name": "Microsoft Excel", "aliases": ["excel", "ms excel", "microsoft excel", "spreadsheet", "excel proficiency"], "domain": "Business & Management", "category": "Business & Administration", "weight": 1.4, "differentiation_tags": ["office"]},
    {"skill_id": "ba-word", "canonical_name": "Microsoft Word", "aliases": ["word", "ms word", "microsoft word"], "domain": "Business & Management", "category": "Business & Administration", "weight": 1.2, "differentiation_tags": ["office"]},
    {"skill_id": "ba-msoffice", "canonical_name": "Microsoft Office", "aliases": ["ms office", "microsoft office", "office suite"], "domain": "Business & Management", "category": "Business & Administration", "weight": 1.4, "differentiation_tags": ["office"]},
    {"skill_id": "ba-admin", "canonical_name": "Office Administration", "aliases": ["administration", "office administration", "administrative", "data entry", "office administration and secretarial science"], "domain": "Business & Management", "category": "Business & Administration", "weight": 1.2, "differentiation_tags": ["office"]},

    # Finance & Accounting
    {"skill_id": "fa-acc", "canonical_name": "Accounting", "aliases": ["accounting", "basic accounting", "financial accounting", "proficiency in accounting software (e.g., peachtree, quickbooks)"], "domain": "Business & Management", "category": "Finance & Accounting", "weight": 1.4, "differentiation_tags": ["finance"]},
    {"skill_id": "fa-fin", "canonical_name": "Finance", "aliases": ["finance", "financial management", "knowledge of financial regulations and gaap"], "domain": "Business & Management", "category": "Finance & Accounting", "weight": 1.3, "differentiation_tags": ["finance"]},
    {"skill_id": "fa-peach", "canonical_name": "Peachtree", "aliases": ["peachtree", "peachtree accounting software"], "domain": "Business & Management", "category": "Finance & Accounting", "weight": 1.2, "differentiation_tags": ["finance"]},
    {"skill_id": "fa-ifrs", "canonical_name": "IFRS", "aliases": ["ifrs", "international financial reporting standards"], "domain": "Business & Management", "category": "Finance & Accounting", "weight": 1.1, "differentiation_tags": ["finance"]},
    {"skill_id": "fa-tax", "canonical_name": "Tax Reporting", "aliases": ["tax", "tax reporting", "tax processing"], "domain": "Business & Management", "category": "Finance & Accounting", "weight": 1.1, "differentiation_tags": ["finance"]},

    # Design & Multimedia
    {"skill_id": "dm-ps", "canonical_name": "Adobe Photoshop", "aliases": ["photoshop", "adobe photoshop"], "domain": "Creative & Design", "category": "Graphic & Video Design", "weight": 1.4, "differentiation_tags": ["design"]},
    {"skill_id": "dm-ill", "canonical_name": "Adobe Illustrator", "aliases": ["illustrator", "adobe illustrator"], "domain": "Creative & Design", "category": "Graphic & Video Design", "weight": 1.3, "differentiation_tags": ["design"]},
    {"skill_id": "dm-ind", "canonical_name": "Adobe InDesign", "aliases": ["indesign", "adobe indesign", "proficiency in adobe creative suite (photoshop, illustrator, indesign)"], "domain": "Creative & Design", "category": "Graphic & Video Design", "weight": 1.1, "differentiation_tags": ["design"]},
    {"skill_id": "dm-pr", "canonical_name": "Adobe Premiere Pro", "aliases": ["premiere", "premiere pro", "adobe premiere", "adobe premiere pro"], "domain": "Creative & Design", "category": "Graphic & Video Design", "weight": 1.3, "differentiation_tags": ["video"]},
    {"skill_id": "dm-ae", "canonical_name": "Adobe After Effects", "aliases": ["after effects", "adobe after effects"], "domain": "Creative & Design", "category": "Graphic & Video Design", "weight": 1.2, "differentiation_tags": ["video"]},
    {"skill_id": "dm-cad", "canonical_name": "AutoCAD", "aliases": ["autocad", "cad", "archicad", "revit", "proficiency in autocad, revit, or archicad"], "domain": "Creative & Design", "category": "Graphic & Video Design", "weight": 1.2, "differentiation_tags": ["engineering-design"]},
    {"skill_id": "dm-photo", "canonical_name": "Photography", "aliases": ["photography", "product photography", "photo shooting"], "domain": "Creative & Design", "category": "Graphic & Video Design", "weight": 1.1, "differentiation_tags": ["design"]},
    {"skill_id": "dm-vedit", "canonical_name": "Video Editing", "aliases": ["video editing", "video editor", "video production"], "domain": "Creative & Design", "category": "Graphic & Video Design", "weight": 1.2, "differentiation_tags": ["video"]},
]

def main():
    if not os.path.exists(TAXONOMY_PATH):
        print(f"Taxonomy file not found at {TAXONOMY_PATH}")
        return

    with open(TAXONOMY_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Convert existing skills to an easier lookup dictionary by skill_id
    existing_skills_by_id = {s["skill_id"]: s for s in data.get("skills", [])}

    added = 0
    for new_sk in new_skills:
        # Check if already exists via skill_id (or similar logic)
        if new_sk["skill_id"] not in existing_skills_by_id:
            data["skills"].append(new_sk)
            added += 1
            print(f"Added {new_sk['skill_id']}: {new_sk['canonical_name']}")

    if added > 0:
        with open(TAXONOMY_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Successfully added {added} new skills.")
    else:
        print("No new skills to add (all exist).")

if __name__ == '__main__':
    main()
