import os
import json
import glob

def combine_learning_resources():
    search_pattern = "data/learning_resources_*.json"
    files = glob.glob(search_pattern)
    
    master_data = {
        "metadata": {
            "generated_for": "AI_JobRecomender",
            "dataset_used": "data/jobs.csv",
            "taxonomy_used": "data/skills_taxonomy.json",
            "generation_date": "2026-05-19",
            "version": "learning-resources-master",
            "online_verification": True,
            "parts_combined": len(files)
        },
        "resources": [],
        "learning_paths": [],
        "new_skill_candidates": []
    }
    
    # Merge all individual arrays
    for file in files:
        with open(file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            master_data["resources"].extend(data.get("resources", []))
            master_data["learning_paths"].extend(data.get("learning_paths", []))
            master_data["new_skill_candidates"].extend(data.get("new_skill_candidates", []))
            
    # Save the master payload
    with open('data/learning_resources.json', 'w', encoding='utf-8') as f:
        json.dump(master_data, f, indent=2)
        
    print(f"Aggregated {len(files)} files.")
    print(f"Total Resources: {len(master_data['resources'])}")
    print(f"Total Learning Paths: {len(master_data['learning_paths'])}")
    print(f"Total New Skill Candidates: {len(master_data['new_skill_candidates'])}")

if __name__ == "__main__":
    combine_learning_resources()
