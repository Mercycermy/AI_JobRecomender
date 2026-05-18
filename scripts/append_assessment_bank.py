import json
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
OUT = DATA / "questions_v2.json"

with open(OUT, "r", encoding="utf-8") as f:
    bank = json.load(f)

Q = bank.get("questions", [])

def mcq(id, gate, scope, roles, diff, exp, stem, context, opts, routing, evidence, mins):
    return {
        "id": id, "gate": gate, "domain_scope": scope,
        "question_type": "multiple_choice",
        "role_targets": roles, "difficulty": diff, "experience_level_target": exp,
        "stem": stem, "context": context, "answer_mode": "single_choice",
        "options": opts, "practical_task": None,
        "scoring": {"max_score":100,"pass_score":70,
            "category_weights":{r:25 for r in roles},
            "skill_weights":{},
            "rubric":[],"red_flags":[],"partial_credit_rules":[]},
        "ai_evaluation_prompt": None,
        "job_evidence": evidence,
        "routing": routing, "estimated_minutes": mins
    }

def practical(id, gate, scope, qtype, roles, diff, exp, stem, context, ans_mode, task, scoring, ai_prompt, evidence, routing, mins):
    return {
        "id": id, "gate": gate, "domain_scope": scope,
        "question_type": qtype,
        "role_targets": roles, "difficulty": diff, "experience_level_target": exp,
        "stem": stem, "context": context, "answer_mode": ans_mode,
        "options": None, "practical_task": task,
        "scoring": scoring,
        "ai_evaluation_prompt": ai_prompt,
        "job_evidence": evidence,
        "routing": routing, "estimated_minutes": mins
    }

def jev(cat, titles, skills, freq):
    return {"category":cat,"job_titles":titles,"evidence_skills":skills,
            "dataset_frequency_note":freq,"source_url":None,"source_note":"Dataset-derived"}


# ──────────────────────────────────────────────────────────────────────
# NEW QUESTIONS
# ──────────────────────────────────────────────────────────────────────

# --- Mobile (Flutter) Task ---
Q.append(practical(
    "Q_TECH_MOBILE_FLUTTER_001", 1, "SOFTWARE", "code_task",
    ["mobile-dev"], "intermediate", "mid",
    "Write the Flutter/Dart code for a stateless widget that displays a user's profile card.",
    "The card should have a circular avatar image, a title (user name), and a subtitle (user role). The card should have rounded corners and a subtle drop shadow.",
    "code",
    {"language":"Dart",
     "starter_code":"import 'package:flutter/material.dart';\n\nclass UserProfileCard extends StatelessWidget {\n  final String name;\n  final String role;\n  final String imageUrl;\n\n  const UserProfileCard({Key? key, required this.name, required this.role, required this.imageUrl}) : super(key: key);\n\n  @override\n  Widget build(BuildContext context) {\n    // Return your widget here\n  }\n}",
     "expected_output":"A Card widget containing a ListTile with CircleAvatar leading, Text title, and Text subtitle.",
     "constraints":["Must use Flutter material widgets","Design should match typical Material Design specs"],
     "edge_cases":["Long names overflowing"],
     "tools_allowed":["Flutter"]},
    {"max_score":100,"pass_score":70,
     "category_weights":{"mobile-dev":30},
     "skill_weights":{"mobile-flutter":30,"lang-dart":20},
     "rubric":[
         {"criterion":"Uses Card widget with shape and elevation","points":30,"strong_evidence":"Card(elevation: 4, shape: RoundedRectangleBorder(...))","weak_evidence":"Just returns a Container with no styling"},
         {"criterion":"Layout structure","points":30,"strong_evidence":"Uses ListTile with leading, title, subtitle or a well-structured Row/Column","weak_evidence":"Messy absolute positioning"},
         {"criterion":"Image implementation","points":20,"strong_evidence":"Uses CircleAvatar(backgroundImage: NetworkImage(imageUrl))","weak_evidence":"Just uses Image.network without circular clipping"},
         {"criterion":"Text styling","points":20,"strong_evidence":"Uses Theme.of(context).textTheme or robust TextStyles","weak_evidence":"Hardcoded text sizes and fonts"}],
     "red_flags":["Uses StatefulWidget unnecessarily"],
     "partial_credit_rules":["50% for correct layout but no styling/shadows","80% for good design but image not circular"]},
    "Evaluate Flutter widget code. Check for Card, ListTile/Row, CircleAvatar, and proper Dart syntax. Return JSON.",
    [jev("mobile-dev",["Flutter Developer","Mobile Developer"],["Flutter","Dart"],"High — Flutter Developer is the #2 IT role (62 jobs)")],
    {"strong":"Q_TECH_MOBILE_ADV_001","partial":"Q_TECH_MOBILE_FLUTTER_002","weak":"Q_TECH_MOBILE_BASICS_001"},
    10
))

# --- DevOps Task ---
Q.append(practical(
    "Q_TECH_DEVOPS_DOCKER_001", 1, "SOFTWARE", "code_task",
    ["devops","backend-dev"], "intermediate", "junior",
    "Write a Dockerfile to containerize a basic Node.js Express application.",
    "The app uses package.json for dependencies and runs on port 3000.",
    "code",
    {"language":"Dockerfile",
     "starter_code":"# Write your Dockerfile here\n",
     "expected_output":"Optimized Dockerfile starting from node:alpine, copying files, npm install, and CMD node app.js.",
     "constraints":["Must expose port 3000","Must copy package.json before src files to leverage caching"],
     "edge_cases":["Running as non-root user","Installing production dependencies only"],
     "tools_allowed":["Docker"]},
    {"max_score":100,"pass_score":70,
     "category_weights":{"devops":30,"backend-dev":10},
     "skill_weights":{"ops-docker":30},
     "rubric":[
         {"criterion":"Base image selection","points":20,"strong_evidence":"Uses an alpine or slim node image (e.g., node:18-alpine)","weak_evidence":"Uses standard heavy node image"},
         {"criterion":"Layer caching optimization","points":40,"strong_evidence":"COPY package*.json first, then RUN npm install, then COPY . .","weak_evidence":"COPY . . immediately followed by npm install"},
         {"criterion":"Port exposure","points":15,"strong_evidence":"EXPOSE 3000","weak_evidence":"Missing EXPOSE"},
         {"criterion":"Start command","points":25,"strong_evidence":"CMD [\"node\", \"app.js\"] or [\"npm\", \"start\"]","weak_evidence":"Missing or invalid CMD"}],
     "red_flags":["Syntax errors in Dockerfile"],
     "partial_credit_rules":["60% if works but layer caching is poor"]},
    "Evaluate Dockerfile. Check base image, COPY sequence (layer caching), EXPOSE, and CMD. Return JSON.",
    [jev("devops",["DevOps Engineer","Backend Developer"],["Docker","Containerization"],"Medium — Docker is essential for modern deployments")],
    {"strong":"Q_TECH_DEVOPS_CI_001","partial":"Q_TECH_DEVOPS_DOCKER_002","weak":"Q_TECH_DEVOPS_BASICS_001"},
    8
))

# --- UI/UX / Product Design ---
Q.append(practical(
    "Q_CREATIVE_UIUX_FIGMA_001", 1, "CREATIVE", "tool_task",
    ["ui-ux-designer"], "intermediate", "mid",
    "Describe your workflow in Figma to design a scalable \"Primary Button\" component for a multi-theme design system.",
    "The system needs to support Light and Dark modes. The button has Default, Hover, and Disabled states. It contains text and an optional leading icon.",
    "free_text",
    {"language":"none","starter_code":None,
     "expected_output":"Step-by-step covering Auto Layout, Variants (States), Component Properties (boolean for icon), and Figma Variables / Color Styles.",
     "constraints":["Must use modern Figma features (Variables, Auto Layout v4)"],
     "edge_cases":["Variable vs Style limitations"],
     "tools_allowed":["Figma"]},
    {"max_score":100,"pass_score":70,
     "category_weights":{"ui-ux-designer":35},
     "skill_weights":{"fe-figma":30,"des-design-system":20},
     "rubric":[
         {"criterion":"Auto Layout usage","points":30,"strong_evidence":"Mentions hugging contents, padding, spacing between icon and text","weak_evidence":"Does not mention Auto Layout"},
         {"criterion":"Component Properties","points":30,"strong_evidence":"Uses variant properties for State (Default/Hover/Disabled) and boolean properties for Icon visibility","weak_evidence":"Creates separate detached buttons instead of variants"},
         {"criterion":"Theming strategy","points":25,"strong_evidence":"Mentions Figma Variables (modes for light/dark) or swapping Color Styles","weak_evidence":"Ignores the multi-theme requirement"},
         {"criterion":"Naming conventions","points":15,"strong_evidence":"Clear naming like Button / Primary / Default","weak_evidence":"Messy naming"}],
     "red_flags":["Describes using Photoshop or Illustrator","Does not use components"],
     "partial_credit_rules":["60% for good variants but no dark mode support"]},
    "Evaluate Figma workflow. Check mentions of Auto Layout, Component Properties/Variants, and Variables/Styles for theming. Return JSON.",
    [jev("ui-ux-designer",["UI/UX Designer","Product Designer"],["Figma","Design Systems"],"High — UI/UX Designer is a top IT role (50 jobs)")],
    {"strong":"Q_CREATIVE_UIUX_ADV_001","partial":"Q_CREATIVE_UIUX_FIGMA_002","weak":"Q_CREATIVE_UIUX_BASICS_001"},
    8
))

# --- Project Management Task ---
Q.append(practical(
    "Q_BIZ_PM_AGILE_001", 1, "BUSINESS", "case_study",
    ["project-manager"], "intermediate", "mid",
    "As a Project Manager leading an Agile software team, how do you handle a critical new feature request injected halfway through a 2-week sprint?",
    "The VP of product says this feature is 'urgent' to close a big deal next month. Replacing sprint scope will guarantee the current sprint goal fails.",
    "free_text",
    {"language":"none","starter_code":None,
     "expected_output":"Negotiation strategy: assess true urgency, protect the team, swap scope if mandatory, or add to backlog for next sprint.",
     "constraints":["Should follow Agile/Scrum principles but show business pragmatism"],
     "edge_cases":["VP pulling rank","Technical debt accumulation"],
     "tools_allowed":["None"]},
    {"max_score":100,"pass_score":70,
     "category_weights":{"project-manager":30},
     "skill_weights":{"soft-agile":25,"soft-leadership":25},
     "rubric":[
         {"criterion":"Assessing impact","points":30,"strong_evidence":"Gathers requirements, sizes the effort with the tech lead before agreeing","weak_evidence":"Immediately says 'yes' without sizing"},
         {"criterion":"Scope negotiation (Sprint protection)","points":30,"strong_evidence":"Offers to swap out equivalent points from current sprint OR pushes it to next sprint (only 1 week away)","weak_evidence":"Just forces team to work overtime"},
         {"criterion":"Stakeholder communication","points":20,"strong_evidence":"Explains trade-offs to VP (delaying other features)","weak_evidence":"Refuses rudely or caves completely"},
         {"criterion":"Agile principles adherence","points":20,"strong_evidence":"Notes that sprints should ideally be locked, handles exception formally","weak_evidence":"Does not understand sprint boundaries"}],
     "red_flags":["Tells the team to 'just work weekends'","Ignores the VP entirely"],
     "partial_credit_rules":["50% for good communication but poor agile framework understanding"]},
    "Evaluate project manager response. Check impact assessment, scope negotiation (swapping), stakeholder management, and agile principles. Return JSON.",
    [jev("project-manager",["Project Manager","Product Manager"],["Agile","Scrum","Stakeholder Management"],"High — Project Manager is a key Business role")],
    {"strong":"Q_BIZ_PM_ADV_001","partial":"Q_BIZ_PM_AGILE_002","weak":"Q_BIZ_PM_BASICS_001"},
    8
))

# --- Education/Training Task ---
Q.append(practical(
    "Q_EDU_TEACHING_PLAN_001", 1, "EDUCATION", "case_study",
    ["teacher","trainer"], "beginner", "any",
    "Design a 45-minute lesson plan introducing complete beginners to the concept of variables in programming.",
    "Your audience is high school students with no prior coding experience. You have a whiteboard and students have laptops.",
    "free_text",
    {"language":"none","starter_code":None,
     "expected_output":"Structured lesson plan with hook/intro, analogy, direct instruction, guided practice, and assessment/wrap-up.",
     "constraints":["Must use non-technical analogies","Must include active student participation"],
     "edge_cases":["Students failing to grasp the concept of data types"],
     "tools_allowed":["None"]},
    {"max_score":100,"pass_score":70,
     "category_weights":{"teacher":35,"trainer":20},
     "skill_weights":{"soft-communication":20},
     "rubric":[
         {"criterion":"Structure/Timing","points":25,"strong_evidence":"Breaks 45 mins into Intro (10m), Teach (15m), Practice (15m), Review (5m)","weak_evidence":"Unstructured monologue"},
         {"criterion":"Use of analogy","points":30,"strong_evidence":"Compares variable to a labeled box, bucket, or name tag","weak_evidence":"Uses highly technical definitions (memory addresses) for beginners"},
         {"criterion":"Active learning","points":25,"strong_evidence":"Students write their first variable on laptops or pair programming","weak_evidence":"Just lecturing for 45 minutes"},
         {"criterion":"Formative assessment","points":20,"strong_evidence":"Checks for understanding via quick questions, exit ticket, or observing screens","weak_evidence":"No check for understanding"}],
     "red_flags":["Lecturing memory allocation to beginners"],
     "partial_credit_rules":["60% for a good lesson but poor timing"]},
    "Evaluate lesson plan. Check structure, use of analogies, active learning, and assessment. Return JSON.",
    [jev("teacher",["English Teacher","Teacher","Tutor"],["Lesson Planning","Instruction","Communication"],"Very High — Education category has 3,368 jobs")],
    {"strong":"Q_EDU_ADV_001","partial":"Q_EDU_TEACHING_PLAN_002","weak":"Q_EDU_BASICS_001"},
    10
))

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(bank, f, indent=2, ensure_ascii=False)

print(f"Added 5 new questions. Total questions now: {len(Q)}")
