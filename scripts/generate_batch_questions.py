import json
import pandas as pd
import uuid

def categorize_job(title):
    t = title.lower()
    if any(x in t for x in ['developer', 'engineer', 'architect', 'tech', 'software', 'app', 'it', 'network', 'system', 'data']):
        return 'tech'
    elif any(x in t for x in ['accountant', 'finance', 'cashier', 'purchaser', 'auditor', 'bank', 'teller', 'economics']):
        return 'finance'
    elif any(x in t for x in ['sales', 'marketer', 'marketing', 'promotion', 'agent', 'broker']):
        return 'sales_marketing'
    elif any(x in t for x in ['admin', 'manager', 'secretary', 'assistant', 'reception', 'officer', 'clerk', 'hr', 'human resource']):
        return 'admin'
    elif any(x in t for x in ['designer', 'editor', 'creator', 'animator', 'video', 'photo', 'graphic', 'ui', 'ux']):
        return 'creative'
    elif any(x in t for x in ['nurse', 'doctor', 'medical', 'pharmacist', 'clinic', 'health']):
        return 'medical'
    elif any(x in t for x in ['tutor', 'teacher', 'instructor', 'lecturer']):
        return 'education'
    else:
        return 'general'

def generate_questions_for_job(title, category, index):
    q_id_1 = f"Q_AUTO_INT_{index}_1_{uuid.uuid4().hex[:6].upper()}"
    q_id_2 = f"Q_AUTO_INT_{index}_2_{uuid.uuid4().hex[:6].upper()}"
    
    questions = []
    
    # Online Interview Style Q1: Experience & Fit
    q1 = {
        "id": q_id_1,
        "gate": 2,
        "domain_scope": category.upper(),
        "question_type": "free_response",
        "role_targets": [category],
        "difficulty": "beginner",
        "experience_level_target": "any",
        "stem": f"Can you walk me through your previous experience and explain why you believe you're a strong fit for a {title} position?",
        "context": "This is a classic opening interview question that asks you to connect your past experience directly to the role.",
        "answer_mode": "free_text",
        "options": None,
        "practical_task": None,
        "scoring": {
            "max_score": 100,
            "pass_score": 70,
            "category_weights": {category: 50},
            "skill_weights": {},
            "rubric": [
                {"criterion": "Relevance", "points": 50, "strong_evidence": f"Applicant clearly connects past work, studies, or projects directly to the skills needed for a {title}."},
                {"criterion": "Communication", "points": 50, "strong_evidence": "Answer is structured, confident, and focuses on value added to the employer."}
            ],
            "red_flags": ["Does not mention relevant experience", "Focuses only on what the company can do for them rather than what they bring"],
            "partial_credit_rules": []
        },
        "ai_evaluation_prompt": f"Evaluate this interview response for a {title} role. Assess how well they map their past experience to this specific position.",
        "job_evidence": [
            {
                "category": category,
                "job_titles": [title],
                "evidence_skills": "Communication, Self-Assessment",
                "dataset_frequency_note": "Dataset Job (Rank 10001-15000)",
                "source_url": None,
                "source_note": "Dataset-derived (Online Interview Style)"
            }
        ],
        "routing": {"strong": "PASS", "partial": "PASS", "weak": "FAIL"},
        "estimated_minutes": 5
    }
    questions.append(q1)

    # Online Interview Style Q2: Behavioral / Mistake
    q2 = {
        "id": q_id_2,
        "gate": 2,
        "domain_scope": category.upper(),
        "question_type": "free_response",
        "role_targets": [category],
        "difficulty": "intermediate",
        "experience_level_target": "mid",
        "stem": f"Tell me about a time you made a mistake or faced a major setback while working as a {title} (or in a similar role). How did you handle it, and what did you learn?",
        "context": "Behavioral interview question focusing on accountability and resilience.",
        "answer_mode": "free_text",
        "options": None,
        "practical_task": None,
        "scoring": {
            "max_score": 100,
            "pass_score": 70,
            "category_weights": {category: 50},
            "skill_weights": {},
            "rubric": [
                {"criterion": "Accountability", "points": 40, "strong_evidence": "Candidly admits to a mistake or setback without blaming others unreasonably."},
                {"criterion": "Resolution", "points": 30, "strong_evidence": "Explains the actionable steps taken to fix the immediate issue."},
                {"criterion": "Learning", "points": 30, "strong_evidence": "Highlights a systemic change or personal lesson learned to prevent future occurrences."}
            ],
            "red_flags": ["Claims they have never made a mistake", "Blames coworkers or management entirely"],
            "partial_credit_rules": []
        },
        "ai_evaluation_prompt": f"Evaluate this behavioral response from a {title} candidate. Look for strong accountability, problem resolution, and lessons learned.",
        "job_evidence": [
            {
                "category": category,
                "job_titles": [title],
                "evidence_skills": "Accountability, Resilience",
                "dataset_frequency_note": "Dataset Job (Rank 10001-15000)",
                "source_url": None,
                "source_note": "Dataset-derived (Online Interview Style)"
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
        # Slice for rank 10001 to 15000 (index 10000 to 15000 in 0-indexed pandas)
        batch = df.iloc[10000:15000]['job_title'].tolist()
        
        with open('data/questions.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        existing_questions = data.get('questions', [])
        
        new_questions = []
        for i, title in enumerate(batch, 10001):
            cat = categorize_job(title)
            qs = generate_questions_for_job(title, cat, i)
            new_questions.extend(qs)
            
        data['questions'] = existing_questions + new_questions
        
        with open('data/questions.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
            
        print(f"Generated and appended {len(new_questions)} online-interview questions for jobs 10001-15000.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main()
