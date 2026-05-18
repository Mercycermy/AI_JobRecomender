import json
import pandas as pd
import uuid

def categorize_job(title):
    t = title.lower()
    if any(x in t for x in ['developer', 'engineer', 'architect', 'tech', 'software', 'app']):
        return 'tech'
    elif any(x in t for x in ['accountant', 'finance', 'cashier', 'purchaser']):
        return 'finance'
    elif any(x in t for x in ['sales', 'marketer', 'marketing']):
        return 'sales_marketing'
    elif any(x in t for x in ['admin', 'manager', 'secretary', 'assistant', 'reception', 'officer']):
        return 'admin'
    elif any(x in t for x in ['designer', 'editor', 'creator']):
        return 'creative'
    elif any(x in t for x in ['nurse', 'doctor', 'medical', 'pharmacist', 'clinic']):
        return 'medical'
    elif any(x in t for x in ['tutor', 'teacher', 'instructor']):
        return 'education'
    else:
        return 'general'

def generate_questions_for_job(title, category, index):
    q_id_1 = f"Q_AUTO_{index}_1_{uuid.uuid4().hex[:6].upper()}"
    q_id_2 = f"Q_AUTO_{index}_2_{uuid.uuid4().hex[:6].upper()}"
    
    questions = []
    
    # Question 1: Practical/Behavioral
    q1 = {
        "id": q_id_1,
        "gate": 2,
        "domain_scope": category.upper(),
        "question_type": "free_response",
        "role_targets": [category],
        "difficulty": "intermediate",
        "experience_level_target": "mid",
        "stem": f"Based on your experience as a {title}, describe a situation where you had to solve a significant and unexpected challenge.",
        "context": f"This question evaluates your practical problem-solving skills specific to the {title} role.",
        "answer_mode": "free_text",
        "options": None,
        "practical_task": None,
        "scoring": {
            "max_score": 100,
            "pass_score": 70,
            "category_weights": {category: 50},
            "skill_weights": {},
            "rubric": [
                {"criterion": "Relevance to role", "points": 30, "strong_evidence": f"Clearly describes a scenario typical for a {title}."},
                {"criterion": "Problem Solving", "points": 40, "strong_evidence": "Logical, methodical approach to resolving the unexpected challenge."},
                {"criterion": "Outcome Focus", "points": 30, "strong_evidence": "Demonstrates a positive or educational outcome."}
            ],
            "red_flags": ["Vague answer without specific details", "Irrelevant scenario"],
            "partial_credit_rules": []
        },
        "ai_evaluation_prompt": f"Evaluate this response from a candidate for a {title} position. Look for clear problem-solving skills and domain relevance.",
        "job_evidence": [
            {
                "category": category,
                "job_titles": [title],
                "evidence_skills": "Problem Solving",
                "dataset_frequency_note": "Dataset Job (Rank 101-200)",
                "source_url": None,
                "source_note": "Dataset-derived"
            }
        ],
        "routing": {"strong": "PASS", "partial": "PASS", "weak": "FAIL"},
        "estimated_minutes": 5
    }
    questions.append(q1)

    # Question 2: Technical/Process (domain specific templates)
    stem_map = {
        'tech': f"As a {title}, how do you ensure the quality and maintainability of your core deliverables (e.g., code, architecture, systems)?",
        'finance': f"As a {title}, describe your process for ensuring accuracy and dealing with discrepancies in financial records or transactions.",
        'sales_marketing': f"As a {title}, how do you approach a situation where you are failing to meet your core targets or facing rejection?",
        'admin': f"As a {title}, how do you prioritize competing requests from multiple stakeholders while maintaining efficiency?",
        'creative': f"As a {title}, how do you handle critical feedback from a client or stakeholder who wants to change your core design/output?",
        'medical': f"As a {title}, describe your approach to ensuring patient safety and strict adherence to protocols under pressure.",
        'education': f"As a {title}, how do you adapt your methods for a student or group that is struggling to grasp the material?",
        'general': f"As a {title}, describe the standard process you follow to ensure your daily work meets quality standards."
    }
    
    q2 = {
        "id": q_id_2,
        "gate": 2,
        "domain_scope": category.upper(),
        "question_type": "free_response",
        "role_targets": [category],
        "difficulty": "intermediate",
        "experience_level_target": "mid",
        "stem": stem_map[category],
        "context": f"This question looks at your standard operating procedures as a {title}.",
        "answer_mode": "free_text",
        "options": None,
        "practical_task": None,
        "scoring": {
            "max_score": 100,
            "pass_score": 70,
            "category_weights": {category: 50},
            "skill_weights": {},
            "rubric": [
                {"criterion": "Domain Process", "points": 50, "strong_evidence": "Mentions specific tools, methodologies, or standard practices relevant to the domain."},
                {"criterion": "Resilience/Adaptability", "points": 50, "strong_evidence": "Shows flexibility and professionalism in handling the situation."}
            ],
            "red_flags": ["Lack of specific methodologies", "Unprofessional approach"],
            "partial_credit_rules": []
        },
        "ai_evaluation_prompt": f"Evaluate this response from a {title}. Assess their knowledge of standard processes and their professionalism.",
        "job_evidence": [
            {
                "category": category,
                "job_titles": [title],
                "evidence_skills": "Core Domain Process",
                "dataset_frequency_note": "Dataset Job (Rank 101-200)",
                "source_url": None,
                "source_note": "Dataset-derived"
            }
        ],
        "routing": {"strong": "PASS", "partial": "PASS", "weak": "FAIL"},
        "estimated_minutes": 5
    }
    questions.append(q2)
    
    return questions

def main():
    try:
        df = pd.read_csv('jobtittle.csv')
        # Slice for rank 101 to 200 (index 100 to 200 in 0-indexed pandas)
        batch = df.iloc[100:200]['job_title'].tolist()
        
        with open('data/questions.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        existing_questions = data.get('questions', [])
        
        new_questions = []
        for i, title in enumerate(batch, 101):
            cat = categorize_job(title)
            qs = generate_questions_for_job(title, cat, i)
            new_questions.extend(qs)
            
        data['questions'] = existing_questions + new_questions
        
        with open('data/questions.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
            
        print(f"Generated and appended {len(new_questions)} questions for jobs 101-200.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main()
