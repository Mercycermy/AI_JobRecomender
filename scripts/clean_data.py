import os
import json
import csv
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAXONOMY_PATH = os.path.join(BASE_DIR, "data", "skills_taxonomy.json")
JOBS_PATH = os.path.join(BASE_DIR, "data", "jobs.csv")
RESOURCES_PATH = os.path.join(BASE_DIR, "data", "learning_resources.json")

def validate_taxonomy():
    print(f"Validating {TAXONOMY_PATH}...")
    try:
        with open(TAXONOMY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        if "skills" not in data:
            print("Error: Missing 'skills' array in taxonomy.")
            return False
            
        skills = data["skills"]
        seen_ids = set()
        
        for idx, s in enumerate(skills):
            for required_field in ["skill_id", "canonical_name", "domain", "category"]:
                if required_field not in s or not s[required_field]:
                    print(f"Error: Missing {required_field} in skill at index {idx}.")
                    return False
            
            if s["skill_id"] in seen_ids:
                print(f"Error: Duplicate skill_id '{s['skill_id']}' found.")
                return False
            seen_ids.add(s["skill_id"])
            
        print(f"Success: Validated {len(skills)} skills in taxonomy. No duplicates.")
        return True
    except Exception as e:
        print(f"Failed to validate taxonomy: {e}")
        return False

def validate_jobs():
    print(f"\nValidating {JOBS_PATH}...")
    try:
        seen_ids = set()
        valid_rows = 0
        
        with open(JOBS_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader):
                for required_field in ["job_id", "job_title", "description", "category"]:
                    if required_field not in row or not row[required_field].strip():
                        print(f"Error: Missing {required_field} in row {idx}.")
                        return False
                
                if row["job_id"] in seen_ids:
                    print(f"Error: Duplicate job_id '{row['job_id']}' found.")
                    return False
                seen_ids.add(row["job_id"])
                valid_rows += 1
                
        print(f"Success: Validated {valid_rows} unique jobs in CSV.")
        return True
    except Exception as e:
        print(f"Failed to validate jobs.csv: {e}")
        return False

def validate_resources():
    print(f"\nValidating {RESOURCES_PATH}...")
    try:
        with open(RESOURCES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        if "resources" not in data:
            print("Error: Missing 'resources' array in learning_resources.")
            return False
            
        resources = data["resources"]
        seen_ids = set()
        
        for idx, r in enumerate(resources):
            for required_field in ["resource_id", "skill_id", "title"]:
                if required_field not in r or not r[required_field]:
                    print(f"Error: Missing {required_field} in resource at index {idx}.")
                    return False
                    
            if r["resource_id"] in seen_ids:
                print(f"Error: Duplicate resource_id '{r['resource_id']}' found.")
                return False
            seen_ids.add(r["resource_id"])
            
        print(f"Success: Validated {len(resources)} learning resources. No duplicates.")
        return True
    except Exception as e:
        print(f"Failed to validate learning resources: {e}")
        return False

if __name__ == "__main__":
    t_ok = validate_taxonomy()
    j_ok = validate_jobs()
    r_ok = validate_resources()
    
    if t_ok and j_ok and r_ok:
        print("\nAll data files validated successfully. Ready for DB seeding.")
        sys.exit(0)
    else:
        print("\nValidation failures detected. Fix data files before seeding.")
        sys.exit(1)
