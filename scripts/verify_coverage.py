import json
import pandas as pd
import os
import glob

def main():
    # 1. Load all job titles from jobtittle.csv
    try:
        df = pd.read_csv('jobtittle.csv')
        all_csv_jobs = set(df['job_title'].astype(str).tolist())
        total_csv_jobs = len(all_csv_jobs)
        print(f"Total unique job titles in CSV: {total_csv_jobs}")
    except Exception as e:
        print(f"Error loading CSV: {e}")
        return

    # 2. Collect all job titles from the split JSON files
    json_jobs = set()
    parts = glob.glob('data/questions_part*.json')
    
    if not parts:
        # Check if questions.json exists instead
        if os.path.exists('data/questions.json'):
            parts = ['data/questions.json']
        else:
            print("No question data found.")
            return

    for part in parts:
        print(f"Checking {part}...")
        with open(part, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for q in data.get('questions', []):
                # Check role_targets or job_evidence
                # From generate_batch_questions.py, job_titles is in job_evidence
                if 'job_evidence' in q and q['job_evidence']:
                    for evidence in q['job_evidence']:
                        titles = evidence.get('job_titles', [])
                        if isinstance(titles, list):
                            json_jobs.update(str(t) for t in titles)
                        elif isinstance(titles, str):
                            json_jobs.add(titles)
                
                # Also check role_targets for good measure
                if 'role_targets' in q and q['role_targets']:
                    json_jobs.update(str(t) for t in q['role_targets'])

    print(f"Total unique job titles found in JSON files: {len(json_jobs)}")

    # 3. Compare and find index ranges
    missing_indices = []
    for idx, row in df.iterrows():
        if str(row['job_title']) not in json_jobs:
            missing_indices.append(idx)
    
    covered_count = total_csv_jobs - len(missing_indices)
    
    print(f"\nCoverage Summary:")
    print(f"Jobs in CSV: {total_csv_jobs}")
    print(f"Jobs with Questions: {covered_count}")
    print(f"Coverage Percentage: {(covered_count/total_csv_jobs)*100:.2f}%")
    
    if missing_indices:
        print(f"\nMissing {len(missing_indices)} jobs.")
        # Find continuous ranges
        if missing_indices:
            ranges = []
            if not missing_indices:
                pass
            else:
                start = missing_indices[0]
                prev = missing_indices[0]
                for i in range(1, len(missing_indices)):
                    if missing_indices[i] == prev + 1:
                        prev = missing_indices[i]
                    else:
                        ranges.append((start, prev))
                        start = missing_indices[i]
                        prev = missing_indices[i]
                ranges.append((start, prev))
                
            print("Missing index ranges (0-based, inclusive):")
            for r in ranges:
                # Add 2 to convert to 1-based row number (including header)
                print(f"- Indices {r[0]} to {r[1]} (Rows {r[0]+2} to {r[1]+2})")
    else:
        print("\nAll job titles from CSV are covered!")

if __name__ == "__main__":
    main()
