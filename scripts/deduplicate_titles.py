import pandas as pd
import re

def clean_title(t):
    if not isinstance(t, str):
        return ""
    # Remove leading/trailing quotes
    t = t.strip('\"\'')
    # Remove leading common prefixes like #, *, -, 1., 2) etc.
    # We want to keep bits like .Net, so we only remove leading punctuation if it's followed by space or is a standard list bullet
    t = re.sub(r'^[#*\-\d\s.,:/]+', '', t)
    # Strip again
    t = t.strip()
    # Normalize case
    t = t.title()
    return t

def main():
    try:
        df = pd.read_csv('jobtittle.csv')
        if 'job_title' not in df.columns:
            print("Error: 'job_title' column not found.")
            return
        
        titles = df['job_title'].dropna().tolist()
        cleaned_set = set()
        for t in titles:
            cleaned = clean_title(t)
            if len(cleaned) > 2:
                cleaned_set.add(cleaned)
        
        cleaned_list = sorted(list(cleaned_set))
        output_df = pd.DataFrame({'job_title': cleaned_list})
        output_df.to_csv('jobtittle.csv', index=False)
        print(f"Successfully deduplicated. Original count: {len(titles)}, New count: {len(cleaned_list)}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == '__main__':
    main()
