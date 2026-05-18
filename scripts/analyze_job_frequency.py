import pandas as pd
import re

def clean_title(t):
    if not isinstance(t, str):
        return ""
    # Remove leading/trailing quotes and nonsense
    t = t.strip('\"\'\t\n\r ')
    # Remove leading common prefixes like #, *, -, 1., 2) etc.
    t = re.sub(r'^[#*\-\d\s.,:/]+', '', t)
    # Strip again
    t = t.strip()
    # Normalize case to Title Case
    t = t.title()
    return t

def main():
    try:
        print("Reading data/jobs.csv...")
        # Use low_memory=False if the file is large
        df = pd.read_csv('data/jobs.csv', low_memory=False)
        
        if 'job_title' not in df.columns:
            print("Error: 'job_title' column not found in jobs.csv")
            return
        
        print("Cleaning and counting job titles...")
        # Apply cleaning
        df['cleaned_title'] = df['job_title'].apply(clean_title)
        
        # Filter out empty or very short titles
        df = df[df['cleaned_title'].str.len() > 2]
        
        # Count occurrences
        counts = df['cleaned_title'].value_counts().reset_index()
        counts.columns = ['job_title', 'count']
        
        # Sort by count descending then title
        counts = counts.sort_values(by=['count', 'job_title'], ascending=[False, True])
        
        print(f"Saving {len(counts)} unique titles to jobtittle.csv...")
        counts.to_csv('jobtittle.csv', index=False)
        
        print("Top 10 job titles:")
        print(counts.head(10))
        
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == '__main__':
    main()
