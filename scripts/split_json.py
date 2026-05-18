import json
import os

def main():
    json_path = 'data/questions.json'
    
    if not os.path.exists(json_path):
        print("questions.json not found.")
        return

    print("Loading large JSON... This might take a few moments.")
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    questions = data.get('questions', [])
    total_q = len(questions)
    print(f"Total questions found: {total_q}")

    chunk_size = 15000
    for i in range(0, total_q, chunk_size):
        chunk = questions[i:i+chunk_size]
        part_num = (i // chunk_size) + 1
        out_name = f'data/questions_part{part_num}.json'
        
        chunk_data = {"questions": chunk}
        print(f"Writing {len(chunk)} questions to {out_name}...")
        
        with open(out_name, 'w', encoding='utf-8') as f:
            json.dump(chunk_data, f, indent=4)
            
    print("Removing massive questions.json file to clear space...")
    os.remove(json_path)
    print("Files successfully split and original removed.")

if __name__ == "__main__":
    main()
