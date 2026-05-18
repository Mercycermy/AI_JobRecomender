import pandas as pd
from pathlib import Path

df = pd.read_csv('c:/Users/zuko/Documents/a/AI_JobRecomender/data/jobs.csv')
total_unique = df['job_title'].dropna().nunique()

top_jobs = df['job_title'].value_counts().head(100)

markdown = f"""# Top Job Titles in Dataset

There are **{total_unique:,}** unique job titles across the dataset (out of {len(df):,} total rows). 

Many of these are slight variations of the same roles (e.g. "Sales", "Sales Representative", "Sales person"). 

Here are the **Top 100 most frequently strictly-matched job titles**:

| Rank | Job Title | Occurrences |
| :--- | :--- | :--- |
"""

for i, (title, count) in enumerate(top_jobs.items(), start=1):
    markdown += f"| {i} | {title} | {count:,} |\n"

artifact_path = r"C:\Users\zuko\.gemini\antigravity\brain\32e85708-96a8-47ab-afc8-7c4575c22623\job_titles_summary.md"
with open(artifact_path, "w", encoding="utf-8") as f:
    f.write(markdown)
