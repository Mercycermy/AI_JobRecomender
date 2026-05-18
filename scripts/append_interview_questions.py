import json
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
OUT = DATA / "questions_v2.json"

with open(OUT, "r", encoding="utf-8") as f:
    bank = json.load(f)

Q = bank.get("questions", [])

def interview(id, gate, scope, roles, diff, exp, stem, context, scoring, ai_prompt, evidence, mins):
    return {
        "id": id, "gate": gate, "domain_scope": scope,
        "question_type": "case_study",
        "role_targets": roles, "difficulty": diff, "experience_level_target": exp,
        "stem": stem, "context": context, "answer_mode": "free_text",
        "options": None,
        "practical_task": {
            "language": "none",
            "starter_code": None,
            "expected_output": "A thoughtful, professional response that balances customer/client needs with company policy and safety/accuracy.",
            "constraints": ["Must sound like a real interview answer"],
            "edge_cases": [],
            "tools_allowed": ["None"]
        },
        "scoring": scoring,
        "ai_evaluation_prompt": ai_prompt,
        "job_evidence": evidence,
        "routing": {"strong": None, "partial": None, "weak": None},
        "estimated_minutes": mins
    }

def jev(cat, titles, skills, freq):
    return {"category":cat,"job_titles":titles,"evidence_skills":skills,
            "dataset_frequency_note":freq,"source_url":None,"source_note":"Dataset-derived"}


# 1. ACCOUNTANT INTERVIEW
Q.append(interview(
    "Q_INT_ACCOUNTANT_001", 1, "ACCOUNTING", ["accounting"], "intermediate", "mid",
    "Interview Scenario: Reconciling Discrepancies",
    "You are closing the month-end books. You notice a recurrent ETB 20,000 discrepancy between the bank statement and the general ledger that has been carrying over for three months. Your manager is pressing you to just 'write it off' to close the books today. What do you do?",
    {"max_score":100,"pass_score":70,
     "category_weights":{"accounting":40},
     "skill_weights":{"fin-accounting":30,"soft-communication":20},
     "rubric":[
         {"criterion":"Ethical stance","points":40,"strong_evidence":"Refuses to arbitrarily write it off without investigation, citing accounting standards/audit risk","weak_evidence":"Agrees to write it off to please the manager"},
         {"criterion":"Investigation plan","points":35,"strong_evidence":"Suggests tracing back to the first month it appeared, checking uncleared checks or bank errors","weak_evidence":"Vague 'I will look into it'"},
         {"criterion":"Communication","points":25,"strong_evidence":"Communicates calmly with the manager, offering a timeline to resolve it rather than just saying no","weak_evidence":"Combative or submissive"}],
     "red_flags":["Commits fraud/writes it off blindly"],
     "partial_credit_rules":[]},
    "Evaluate Accountant interview answer for ethics, proactive investigation, and professional pushback. Return JSON.",
    [jev("accounting",["Accountant","Senior Accountant","Junior Accountant"],["Accounting","Auditing","Ethics"],"Highest Volume — Top 1 job in dataset (655 jobs)")],
    8
))

# 2. SECRETARY / RECEPTIONIST INTERVIEW
Q.append(interview(
    "Q_INT_SECRETARY_001", 1, "ADMIN", ["admin"], "beginner", "junior",
    "Interview Scenario: Prioritizing Urgent Chaos",
    "You are alone at the front desk. The office phone is ringing, a VIP client just walked in and looks annoyed they aren't being greeted, and your boss just emailed you asking for an urgent document printout. How do you handle this exact moment?",
    {"max_score":100,"pass_score":70,
     "category_weights":{"admin":40},
     "skill_weights":{"ba-admin":30,"soft-communication":20},
     "rubric":[
         {"criterion":"Triage / Prioritization","points":40,"strong_evidence":"Greets the VIP immediately (in-person takes precedence), asks them to wait gracefully, then answers phone and puts them on hold, then prints document","weak_evidence":"Ignores VIP to answer phone, or ignores phone entirely"},
         {"criterion":"Customer Service Tone","points":30,"strong_evidence":"Uses polite, calming language ('I apologize for the wait, I will be right with you')","weak_evidence":"Sounds stressed or snaps at the client"},
         {"criterion":"Action orientation","points":30,"strong_evidence":"Provides a clear chronological sequence of actions rather than theoretical concepts","weak_evidence":"Vague"}],
     "red_flags":["Leaves desk","Hangs up on caller violently"],
     "partial_credit_rules":[]},
    "Evaluate Secretary/Receptionist interview answer for prioritization (in-person vs phone vs email), composure, and customer service. Return JSON.",
    [jev("admin",["Secretary","Receptionist","Office Assistant"],["Office Administration","Customer Service","Time Management"],"Top 3, 4, and 5 business roles in dataset")],
    5
))

# 3. SALES REPRESENTATIVE INTERVIEW
Q.append(interview(
    "Q_INT_SALES_001", 1, "SALES_MKT", ["sales"], "intermediate", "mid",
    "Interview Scenario: Overcoming the Price Objection",
    "You are pitching a software solution to a prospect who currently uses a competitor. The prospect says: 'Your product looks slightly better, but your competitor is 30% cheaper. I can't justify the switch.' Connect this to a real tactic you would use to close them.",
    {"max_score":100,"pass_score":70,
     "category_weights":{"sales":40},
     "skill_weights":{"biz-sales":30,"soft-negotiation":20},
     "rubric":[
         {"criterion":"Value vs Price","points":40,"strong_evidence":"Pivots from price to Total Cost of Ownership (TCO) or ROI (e.g., time saved, extra revenue generated)","weak_evidence":"Immediately drops price to match competitor"},
         {"criterion":"Discovery / Probing","points":30,"strong_evidence":"Asks questions like 'What is the cheaper product currently costing you in lost time?'","weak_evidence":"Gets defensive about the product features"},
         {"criterion":"Closing confidence","points":30,"strong_evidence":"Maintains authority, offers a pilot or ROI calculation rather than giving up","weak_evidence":"Apologizes for the price"}],
     "red_flags":["Insults the competitor aggressively","Instantly caves on price"],
     "partial_credit_rules":[]},
    "Evaluate Sales interview answer for value proposition pitching, objection handling (TCO/ROI), and avoiding immediate price discounting. Return JSON.",
    [jev("sales",["Sales","Sales Representative","Sales person"],["Sales","Negotiation","Objection Handling"],"Top 2 role overall in dataset (423+ jobs)")],
    8
))

# 4. CASHIER INTERVIEW
Q.append(interview(
    "Q_INT_CASHIER_001", 1, "ACCOUNTING", ["accounting","admin"], "beginner", "any",
    "Interview Scenario: Disputed Change",
    "A customer buys an item for ETB 150. They hand you a 500 ETB note. You give them ETB 350 in change. The customer immediately claims they gave you a 1,000 ETB note and demands more change. A line of other customers is forming. How do you handle it?",
    {"max_score":100,"pass_score":70,
     "category_weights":{"accounting":20,"admin":10},
     "skill_weights":{"fa-acc":20,"soft-communication":20},
     "rubric":[
         {"criterion":"De-escalation","points":35,"strong_evidence":"Remains calm, does not accuse the customer of lying, speaks politely","weak_evidence":"Argues with the customer or yells"},
         {"criterion":"Standard Procedure","points":40,"strong_evidence":"Leaves the note on the register (if standard) or calls a manager to audit the till immediately before giving cash","weak_evidence":"Just gives the customer the extra money out of fear"},
         {"criterion":"Queue Management","points":25,"strong_evidence":"Apologizes to the line, asks another cashier to open a lane, or handles swiftly with manager","weak_evidence":"Ignores the growing line"}],
     "red_flags":["Accuses customer of being a thief","Opens till and hands over cash without verification"],
     "partial_credit_rules":[]},
    "Evaluate Cashier interview answer for de-escalation, adherence to strict till-audit policy, and queue management. Return JSON.",
    [jev("accounting",["Cashier","Betting cashier"],["Cash Handling","Customer Service"],"Cashiers account for ~400 jobs in the dataset")],
    5
))

# 5. DRIVER INTERVIEW
Q.append(interview(
    "Q_INT_DRIVER_001", 1, "LOGISTICS", ["transport"], "beginner", "any",
    "Interview Scenario: Route Deviation and Safety",
    "You are driving for a company logistics delivery. You are behind schedule. Your manager calls and tells you to speed and ignore a minor road closure to get the delivery there on time. What is your response?",
    {"max_score":100,"pass_score":70,
     "category_weights":{"transport":50},
     "skill_weights":{"tl-driving":40,"soft-communication":10},
     "rubric":[
         {"criterion":"Safety / Legal Compliance","points":50,"strong_evidence":"Refuses to break the law, prioritizes safety over speed, will not drive on closed roads","weak_evidence":"Agrees to speed to save the job"},
         {"criterion":"Communication","points":30,"strong_evidence":"Explains the legal/safety risk calmly to the manager, offers alternative routes","weak_evidence":"Hangs up on manager or fights"},
         {"criterion":"Problem Solving","points":20,"strong_evidence":"Looks for the next fastest legal route, updates client on realistic ETA","weak_evidence":"Just says 'no' and stops driving"}],
     "red_flags":["Agrees to break the law","Violates safety protocols"],
     "partial_credit_rules":[]},
    "Evaluate Driver interview answer. The absolute requirement is prioritizing legal/safety compliance over manager pressure. Return JSON.",
    [jev("transport",["Driver","Truck Driver","Delivery Driver"],["Driving","Safety","Logistics"],"Driver is a top 20 job overall with 144 jobs")],
    5
))

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(bank, f, indent=2, ensure_ascii=False)

print(f"Added 5 new INTERVIEW questions. Total questions now: {len(Q)}")
