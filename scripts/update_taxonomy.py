import json
import os

TAXONOMY_PATH = r'c:\Users\zuko\Documents\a\AI_JobRecomender\data\skills_taxonomy.json'

new_skills = [
    # Mobile Development  
    {"skill_id": "mob-flutter", "canonical_name": "Flutter", "aliases": ["flutter", "flutter-dart", "dart"], "domain": "Software Engineering", "category": "Mobile Development", "weight": 1.3, "differentiation_tags": ["mobile", "frontend"]},
    {"skill_id": "mob-android", "canonical_name": "Android Development", "aliases": ["android", "android studio", "android development"], "domain": "Software Engineering", "category": "Mobile Development", "weight": 1.3, "differentiation_tags": ["mobile"]},
    {"skill_id": "mob-ios", "canonical_name": "iOS Development", "aliases": ["ios", "ios development", "xcode"], "domain": "Software Engineering", "category": "Mobile Development", "weight": 1.2, "differentiation_tags": ["mobile"]},
    {"skill_id": "mob-reactnative", "canonical_name": "React Native", "aliases": ["react native", "react-native"], "domain": "Software Engineering", "category": "Mobile Development", "weight": 1.2, "differentiation_tags": ["mobile", "frontend"]},

    # Networking & Infrastructure
    {"skill_id": "net-networking", "canonical_name": "Networking", "aliases": ["networking", "computer networking", "network administration", "networking and hardware setup"], "domain": "Software Engineering", "category": "Networking & Infrastructure", "weight": 1.3, "differentiation_tags": ["infra", "devops"]},
    {"skill_id": "net-cisco", "canonical_name": "Cisco", "aliases": ["cisco", "cisco networking"], "domain": "Software Engineering", "category": "Networking & Infrastructure", "weight": 1.2, "differentiation_tags": ["infra"]},
    {"skill_id": "net-ccna", "canonical_name": "CCNA", "aliases": ["ccna", "cisco certified network associate"], "domain": "Software Engineering", "category": "Networking & Infrastructure", "weight": 1.2, "differentiation_tags": ["infra", "certification"]},
    {"skill_id": "net-ccnp", "canonical_name": "CCNP", "aliases": ["ccnp", "cisco certified network professional"], "domain": "Software Engineering", "category": "Networking & Infrastructure", "weight": 1.3, "differentiation_tags": ["infra", "certification"]},
    {"skill_id": "net-winserver", "canonical_name": "Windows Server", "aliases": ["windows server", "windows server administration"], "domain": "Software Engineering", "category": "Networking & Infrastructure", "weight": 1.1, "differentiation_tags": ["infra"]},
    {"skill_id": "net-vmware", "canonical_name": "VMware", "aliases": ["vmware", "virtualization", "vsphere"], "domain": "Software Engineering", "category": "Networking & Infrastructure", "weight": 1.1, "differentiation_tags": ["infra", "devops"]},

    # Additional Frontend/Web
    {"skill_id": "fe-ajax", "canonical_name": "AJAX", "aliases": ["ajax", "xmlhttprequest"], "domain": "Software Engineering", "category": "Frontend Development", "weight": 0.9, "differentiation_tags": ["frontend"]},

    # Database (already have specific DBs, adding general concept)
    {"skill_id": "db-general", "canonical_name": "Database Management", "aliases": ["database", "database management", "database administration", "db"], "domain": "Software Engineering", "category": "Database & Storage", "weight": 1.3, "differentiation_tags": ["backend", "data"]},

    # CRM & Business Tools
    {"skill_id": "ba-crm", "canonical_name": "CRM", "aliases": ["crm", "customer relationship management (crm)", "crm software", "salesforce"], "domain": "Business & Management", "category": "Business & Administration", "weight": 1.3, "differentiation_tags": ["business", "sales"]},
    {"skill_id": "ba-pos", "canonical_name": "POS Systems", "aliases": ["pos", "pos systems", "ability to handle cash and use pos systems", "cash register", "cash register operation"], "domain": "Business & Management", "category": "Business & Administration", "weight": 1.0, "differentiation_tags": ["retail"]},

    # Human Resources
    {"skill_id": "hr-mgmt", "canonical_name": "Human Resources Management", "aliases": ["human resources management", "hr management", "hr", "human resources"], "domain": "Business & Management", "category": "Human Resources", "weight": 1.3, "differentiation_tags": ["hr"]},
    {"skill_id": "hr-benefits", "canonical_name": "Benefits Administration", "aliases": ["benefits administration", "compensation and wage structure", "compensation"], "domain": "Business & Management", "category": "Human Resources", "weight": 1.1, "differentiation_tags": ["hr"]},
    {"skill_id": "hr-recruit", "canonical_name": "Recruitment & Staffing", "aliases": ["recruitment", "staffing", "classifying employees", "talent acquisition"], "domain": "Business & Management", "category": "Human Resources", "weight": 1.2, "differentiation_tags": ["hr"]},

    # Project Management
    {"skill_id": "pm-projmgmt", "canonical_name": "Project Management", "aliases": ["project management", "project management and communication", "project planning"], "domain": "Business & Management", "category": "Project Management", "weight": 1.4, "differentiation_tags": ["management"]},

    # Soft Skills (additional)
    {"skill_id": "soft-attention", "canonical_name": "Attention to Detail", "aliases": ["attention to detail", "attention to detail and accuracy", "attention to detail and analytical skills", "attention to visual detail"], "domain": "Soft Skills & Languages", "category": "Soft Skills", "weight": 1.2, "differentiation_tags": ["soft-skill"]},
    {"skill_id": "soft-creative", "canonical_name": "Creative Thinking", "aliases": ["creative thinking", "creative thinking and artistic ability", "creativity", "creativity and trend awareness"], "domain": "Soft Skills & Languages", "category": "Soft Skills", "weight": 1.2, "differentiation_tags": ["soft-skill"]},
    {"skill_id": "soft-timemgmt", "canonical_name": "Time Management", "aliases": ["time management", "multi-tasking", "multi-tasking and time management", "organization"], "domain": "Soft Skills & Languages", "category": "Soft Skills", "weight": 1.1, "differentiation_tags": ["soft-skill"]},
    {"skill_id": "soft-teamwork", "canonical_name": "Teamwork", "aliases": ["teamwork", "team player", "collaboration"], "domain": "Soft Skills & Languages", "category": "Soft Skills", "weight": 1.1, "differentiation_tags": ["soft-skill"]},
    {"skill_id": "soft-problem", "canonical_name": "Problem Solving", "aliases": ["problem solving", "critical thinking", "analytical skills", "strategic thinking and analytical skills"], "domain": "Soft Skills & Languages", "category": "Soft Skills", "weight": 1.3, "differentiation_tags": ["soft-skill"]},

    # Teaching & Education
    {"skill_id": "edu-teaching", "canonical_name": "Teaching", "aliases": ["teaching", "tutoring", "teaching and communication skills", "adaptability to different learning styles"], "domain": "Education & Training", "category": "Teaching & Education", "weight": 1.3, "differentiation_tags": ["education"]},
    {"skill_id": "edu-curriculum", "canonical_name": "Curriculum Development", "aliases": ["curriculum development", "lesson planning", "deep knowledge of the subject matter"], "domain": "Education & Training", "category": "Teaching & Education", "weight": 1.2, "differentiation_tags": ["education"]},

    # Healthcare
    {"skill_id": "hc-nursing", "canonical_name": "Nursing", "aliases": ["nursing", "clinical assessment and emergency care", "clinical nursing"], "domain": "Healthcare", "category": "Healthcare & Medical", "weight": 1.3, "differentiation_tags": ["healthcare"]},
    {"skill_id": "hc-pharmacy", "canonical_name": "Pharmacy", "aliases": ["pharmacy", "pharmacology", "knowledge of pharmacology and clinical pharmacy", "patient counseling and communication"], "domain": "Healthcare", "category": "Healthcare & Medical", "weight": 1.2, "differentiation_tags": ["healthcare"]},
    {"skill_id": "hc-medical", "canonical_name": "Medical Equipment", "aliases": ["medical equipment", "knowledge of medical equipment and procedures", "medical equipment sales/distribution knowledge"], "domain": "Healthcare", "category": "Healthcare & Medical", "weight": 1.1, "differentiation_tags": ["healthcare"]},

    # Hospitality & Culinary
    {"skill_id": "hosp-culinary", "canonical_name": "Culinary Arts", "aliases": ["culinary", "cooking", "knowledge of various cooking techniques and cuisines", "creativity in food presentation"], "domain": "Hospitality & Services", "category": "Hospitality & Culinary", "weight": 1.2, "differentiation_tags": ["hospitality"]},
    {"skill_id": "hosp-barista", "canonical_name": "Barista / Coffee", "aliases": ["barista", "coffee", "knowledge of coffee blends and brewing methods"], "domain": "Hospitality & Services", "category": "Hospitality & Culinary", "weight": 1.0, "differentiation_tags": ["hospitality"]},

    # Transport & Logistics
    {"skill_id": "tl-driving", "canonical_name": "Driving", "aliases": ["driving", "professional driving", "valid driving license with clean record", "knowledge of local routes and navigation"], "domain": "Logistics & Transport", "category": "Transport & Logistics", "weight": 1.2, "differentiation_tags": ["transport"]},
    {"skill_id": "tl-vehicle", "canonical_name": "Vehicle Maintenance", "aliases": ["vehicle maintenance", "basic vehicle maintenance knowledge"], "domain": "Logistics & Transport", "category": "Transport & Logistics", "weight": 1.0, "differentiation_tags": ["transport"]},

    # Design (additional)
    {"skill_id": "dm-graphdes", "canonical_name": "Graphic Design", "aliases": ["graphic design", "graphics design", "proficiency in adobe creative suite (photoshop, illustrator, indesign)"], "domain": "Creative & Design", "category": "Graphic & Video Design", "weight": 1.3, "differentiation_tags": ["design"]},
    {"skill_id": "dm-typography", "canonical_name": "Typography & Color Theory", "aliases": ["typography", "color theory", "typography and color theory knowledge"], "domain": "Creative & Design", "category": "Graphic & Video Design", "weight": 1.0, "differentiation_tags": ["design"]},

    # Content Creation
    {"skill_id": "cc-content", "canonical_name": "Content Creation", "aliases": ["content creation", "content creation and copywriting", "content development"], "domain": "Creative & Design", "category": "Content Creation", "weight": 1.2, "differentiation_tags": ["digital-marketing", "design"]},
    {"skill_id": "cc-smanalytics", "canonical_name": "Social Media Analytics", "aliases": ["social media analytics", "social media analytics and tools", "knowledge of social media platforms (fb, ig, linkedin, etc.)"], "domain": "Creative & Design", "category": "Content Creation", "weight": 1.1, "differentiation_tags": ["digital-marketing"]},

    # Architecture & Construction
    {"skill_id": "eng-buildcodes", "canonical_name": "Building Codes & Regulations", "aliases": ["building codes", "knowledge of building codes and regulations", "building regulations"], "domain": "Engineering & Architecture", "category": "Architecture & Construction", "weight": 1.1, "differentiation_tags": ["engineering"]},
    {"skill_id": "eng-techdrawing", "canonical_name": "Technical Drawing", "aliases": ["technical drawing", "creative design and technical drawing skills", "drafting"], "domain": "Engineering & Architecture", "category": "Architecture & Construction", "weight": 1.1, "differentiation_tags": ["engineering"]},

    # Tailoring / Fashion
    {"skill_id": "craft-tailoring", "canonical_name": "Tailoring & Fashion", "aliases": ["tailoring", "fashion design", "pattern cutting", "garment design software"], "domain": "Creative & Design", "category": "Fashion & Crafts", "weight": 1.0, "differentiation_tags": ["craft"]},

    # Reception & Front Office
    {"skill_id": "ba-reception", "canonical_name": "Front Desk / Reception", "aliases": ["reception", "receptionist", "switchboard operation and data entry", "professional appearance and demeanor", "organization and customer service focus"], "domain": "Business & Management", "category": "Business & Administration", "weight": 1.1, "differentiation_tags": ["office"]},
]

def main():
    if not os.path.exists(TAXONOMY_PATH):
        print(f"Taxonomy file not found at {TAXONOMY_PATH}")
        return

    with open(TAXONOMY_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    existing_ids = {s["skill_id"] for s in data.get("skills", [])}

    added = 0
    for new_sk in new_skills:
        if new_sk["skill_id"] not in existing_ids:
            data["skills"].append(new_sk)
            added += 1
            print(f"Added {new_sk['skill_id']}: {new_sk['canonical_name']}")

    if added > 0:
        with open(TAXONOMY_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\nSuccessfully added {added} new skills. Total: {len(data['skills'])}")
    else:
        print("No new skills to add.")

if __name__ == '__main__':
    main()
