import pandas as pd
import numpy as np
import os
import sys

# Ensure stdout handles UTF-8
sys.stdout.reconfigure(encoding='utf-8')

# Mapping for common job titles to descriptions (Tasks and Skills)
DESCRIPTION_TEMPLATES = {
    'Accountant': """Tasks:
- Prepare and maintain financial records
- Reconcile bank statements and ledger accounts
- Process tax payments and returns
- Prepare monthly and annual financial reports

Skills:
- Proficiency in accounting software (e.g., Peachtree, QuickBooks)
- Knowledge of financial regulations and GAAP
- Attention to detail and analytical skills
- Excel proficiency""",
    
    'Sales': """Tasks:
- Identify and reach out to prospective clients
- Present and demonstrate products or services
- Negotiate and close sales deals
- Maintain customer relationships and follow up

Skills:
- Strong communication and persuasion skills
- Customer relationship management (CRM)
- Negotiation and closing techniques
- Result-oriented and self-motivated""",
    
    'Cashier': """Tasks:
- Process customer transactions and handle payments
- Issue receipts, refunds, or change accurately
- Maintain a clean and organized checkout area
- Provide basic customer service and handle inquiries

Skills:
- Basic mathematical skills
- Attention to detail and accuracy
- Customer service orientation
- Ability to handle cash and use POS systems""",
    
    'Graphics Designer': """Tasks:
- Create visual concepts and layouts for various media
- Design logos, brochures, and marketing materials
- Edit images and graphics using design software
- Collaborate with clients or teams to meet project goals

Skills:
- Proficiency in Adobe Creative Suite (Photoshop, Illustrator, InDesign)
- Creative thinking and artistic ability
- Typography and color theory knowledge
- Portfolio of previous design work""",
    
    'Secretary': """Tasks:
- Manage office correspondence and phone calls
- Schedule appointments and maintain calendars
- Organize and file documents efficiently
- Assist in basic administrative and clerical tasks

Skills:
- Office administration and secretarial science
- Proficiency in Microsoft Office Suite
- Excellent communication and organizational skills
- Multi-tasking and time management""",
    
    'Driver': """Tasks:
- Transport goods or people safely to destinations
- Maintain vehicle cleanliness and perform basic checks
- Follow traffic laws and optimized routes
- Keep logs of trips and deliveries

Skills:
- Valid driving license with clean record
- Knowledge of local routes and navigation
- Punctuality and responsibility
- Basic vehicle maintenance knowledge""",

    'Architect': """Tasks:
- Design building plans and detailed drawings
- Oversee construction projects and ensure compliance
- Consult with clients on design requirements and budgets
- Research building codes and materials

Skills:
- Proficiency in AutoCAD, Revit, or Archicad
- Creative design and technical drawing skills
- Knowledge of building codes and regulations
- Project management and communication""",

    'Video Editor': """Tasks:
- Assemble recorded footage into finished projects
- Add music, dialogues, and sound effects
- Apply color correction and transitions
- Review final cuts for quality and consistency

Skills:
- Proficiency in Adobe Premiere Pro or Final Cut Pro
- Knowledge of video formats and compression
- Creative storytelling and rhythmic sense
- Attention to visual detail""",

    'Receptionist': """Tasks:
- Greet visitors and direct them to appropriate persons
- Manage front desk phone lines and inquiries
- Coordinate incoming and outgoing mail
- Support administrative staff with various tasks

Skills:
- Professional appearance and demeanor
- Excellent interpersonal and communication skills
- Switchboard operation and data entry
- Organization and customer service focus""",

    'Pharmacist': """Tasks:
- Dispense medications and ensure correct dosages
- Provide advice on drug interactions and side effects
- Manage pharmacy inventory and record keeping
- Consult with healthcare professionals on patient care

Skills:
- Degree in Pharmacy
- Knowledge of pharmacology and clinical pharmacy
- Strong attention to detail and ethics
- Patient counseling and communication""",

    'Nurse': """Tasks:
- Provide direct patient care and administer treatments
- Record patient medical histories and vital signs
- Collaborate with doctors on patient health plans
- Educate patients and families on health management

Skills:
- Degree or Diploma in Nursing
- Clinical assessment and emergency care
- Compassion and interpersonal skills
- Knowledge of medical equipment and procedures""",

    'Chef': """Tasks:
- Plan menus and prepare high-quality dishes
- Oversee kitchen operations and staff
- Ensure food safety and hygiene standards
- Manage kitchen inventory and ordering

Skills:
- Culinary school degree or equivalent experience
- Knowledge of various cooking techniques and cuisines
- Leadership and team management
- Creativity in food presentation""",

    'Barista': """Tasks:
- Prepare and serve hot or cold beverages
- Maintain espresso machines and coffee equipment
- Clean and sanitize work and seating areas
- Provide friendly customer service and handle orders

Skills:
- Knowledge of coffee blends and brewing methods
- Customer service and communication skills
- Ability to work in a fast-paced environment
- Punctuality and attention to detail""",

    'Tutor': """Tasks:
- Provide academic support in specific subjects
- Develop lesson plans and teaching materials
- Monitor student progress and provide feedback
- Prepare students for exams and assessments

Skills:
- Deep knowledge of the subject matter
- Teaching and communication skills
- Patience and motivational ability
- Adaptability to different learning styles""",
    
    'Marketing Manager': """Tasks:
- Develop and implement marketing strategies
- Manage marketing budgets and campaigns
- Conduct market research and competitor analysis
- Lead the marketing team and coordinate activities

Skills:
- Degree in Marketing or related field
- Strategic thinking and analytical skills
- Leadership and communication
- Knowledge of digital and traditional marketing""",
    
    'Social Media Manager': """Tasks:
- Manage and grow social media channels
- Create engaging content and post schedules
- Monitor social media trends and engagement metrics
- Interact with followers and handle inquiries

Skills:
- Knowledge of social media platforms (FB, IG, LinkedIn, etc.)
- Content creation and copywriting
- Social media analytics and tools
- Creativity and trend awareness""",
}

# Alias mapping to handle variations and case-insensitivity
TEMPLATE_ALIASES = {
    'sales person': 'Sales',
    'sales representative': 'Sales',
    'salesperson': 'Sales',
    'sales agents': 'Sales',
    'sales agent': 'Sales',
    'የሽያጭ ሰራተኛ': 'Sales',
    'graphics designer': 'Graphics Designer',
    'graphic designer': 'Graphics Designer',
    'graphic designer': 'Graphics Designer',
    'video editor': 'Video Editor',
    'senior accountant': 'Accountant',
    'junior accountant': 'Accountant',
    'reception': 'Receptionist',
    'receptionist': 'Receptionist',
    'waitress': 'Cashier', # Waitress often similar tasks in basic shops, but better separate if possible. 
    # Let's just use these for now to cover the bulk.
}

def standardize_title(title):
    if not isinstance(title, str):
        return ""
    title = title.strip()
    # Normalize for alias check
    normalized = title.lower()
    if normalized in TEMPLATE_ALIASES:
        return TEMPLATE_ALIASES[normalized]
    # If not in alias, but title starts with or is very similar
    for key in DESCRIPTION_TEMPLATES.keys():
        if key.lower() in normalized:
            return key
    return title # Return original if no match

def process_jobs(file_path, output_path):
    print(f"Reading {file_path}...")
    try:
        df = pd.read_csv(file_path, on_bad_lines='skip', encoding='utf-8')
        print(f"Original row count: {len(df)}")

        # 1. Deduplicate
        # We consider a job duplicate if title and description are identical
        # Also clean up string columns
        for col in ['job_title', 'description', 'category', 'location']:
            if col in df.columns:
                df[col] = df[col].fillna('').astype(str).str.strip()

        df = df.drop_duplicates(subset=['job_title', 'description'], keep='first')
        print(f"Row count after deduplication: {len(df)}")

        # 2. Fill Missing Descriptions
        def enrich_description(row):
            desc = row['description']
            title = row['job_title']
            
            # Check if description is "inadequate"
            # Less than 50 chars OR just "Tasks:" or "Skills:"
            is_poor = (len(desc) < 60) or \
                      (desc.lower().strip() in ['tasks:', 'skills:', 'n/a', 'none', 'unknown', 'nan']) or \
                      ('\n' not in desc)
            
            if is_poor:
                best_match = standardize_title(title)
                if best_match in DESCRIPTION_TEMPLATES:
                    return DESCRIPTION_TEMPLATES[best_match]
            
            return desc

        print("Enriching descriptions...")
        df['description'] = df.apply(enrich_description, axis=1)

        # 3. Organize (Sort)
        # Assuming job_id is numeric, but let's be safe
        df['job_id'] = pd.to_numeric(df['job_id'], errors='coerce')
        df = df.dropna(subset=['job_id'])
        df['job_id'] = df['job_id'].astype(int)
        df = df.sort_values(by='job_id')

        # 4. Save
        print(f"Saving to {output_path}...")
        df.to_csv(output_path, index=False, encoding='utf-8')
        print("Done!")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    jobs_file = r'c:\Users\zuko\Documents\a\AI_JobRecomender\data\jobs.csv'
    # For safety, let's process and then overwrite or save to a temp first.
    # But user asked to organize "the job csv", so I'll overwrite after processing.
    process_jobs(jobs_file, jobs_file)
