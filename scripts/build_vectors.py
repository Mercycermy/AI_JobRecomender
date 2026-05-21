import sqlite3
import json
import os
import sys
import numpy as np

# Resolve paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "db.sqlite3")
INDEX_PATH = os.path.join(BASE_DIR, "data", "jobs_faiss.index")
MAPPER_PATH = os.path.join(BASE_DIR, "data", "jobs_id_map.json")

def main():
    print("Checking for required libraries...")
    try:
        from sentence_transformers import SentenceTransformer
        import faiss
    except ImportError as e:
        print(f"Error: Missing required dependency. Please run 'pip install -r requirements.txt'. Detail: {e}")
        sys.exit(1)

    if not os.path.exists(DB_PATH):
        print(f"Error: Database file not found at {DB_PATH}. Please run seed_db.py first.")
        sys.exit(1)

    print("Connecting to SQLite database...")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print("Fetching jobs from database...")
    cur.execute("SELECT job_id, job_title, description FROM jobs")
    rows = cur.fetchall()
    conn.close()

    if not rows:
        print("No jobs found in the database. Please seed the database first.")
        sys.exit(1)

    print(f"Loaded {len(rows)} jobs.")

    job_ids = []
    job_texts = []
    for job_id, title, desc in rows:
        job_ids.append(job_id)
        # Combine title and description for richer semantic matching
        combined_text = f"{title}. {desc}"
        job_texts.append(combined_text)

    print("Loading Sentence Transformer model ('all-MiniLM-L6-v2')...")
    # This downloads the ~80MB model if not already cached locally
    model = SentenceTransformer('all-MiniLM-L6-v2')

    print("Encoding job descriptions (this may take a few minutes on CPU)...")
    # Encode with normalized embeddings so dot product equals cosine similarity
    embeddings = model.encode(
        job_texts,
        batch_size=64,
        show_progress_bar=True,
        normalize_embeddings=True
    )
    embeddings = np.array(embeddings).astype('float32')

    print(f"Generated embeddings matrix with shape: {embeddings.shape}")

    print("Building FAISS index...")
    dimension = embeddings.shape[1] # should be 384 for all-MiniLM-L6-v2
    # IndexFlatIP uses Inner Product (IP), which calculates cosine similarity on normalized vectors
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)

    print(f"Saving FAISS index to {INDEX_PATH}...")
    faiss.write_index(index, INDEX_PATH)

    print(f"Saving job ID mapping list to {MAPPER_PATH}...")
    with open(MAPPER_PATH, 'w', encoding='utf-8') as f:
        json.dump(job_ids, f, indent=2)

    print("Vector build complete! Ready for fast semantic recommendation querying.")

if __name__ == "__main__":
    main()
