import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import re
import json
import torch
from transformers import BertTokenizer, BertForSequenceClassification



class CareerPredictor:
    def __init__(self):
        # Using your exact folder name
        self.model_path = os.path.abspath('final_skill_model')
        
        # Load your SOURCE OF TRUTH (The JSON)
        with open('skills_knowledge.json', 'r') as f:
            self.skills_db = json.load(f)
        
        # Load the AI
        self.tokenizer = BertTokenizer.from_pretrained(self.model_path, local_files_only=True)
        self.model = BertForSequenceClassification.from_pretrained(self.model_path, local_files_only=True)
        self.model.eval()

    def get_best_category(self, target_domain):
        """Maps user input to the correct key in your JSON"""
        target = target_domain.lower().strip()
        
        # Mapping common names to your specific JSON keys
        mapping = {
            "data scientist": "AI and Data Scientist",
            "data science": "AI and Data Scientist",
            "web developer": "Full Stack Developer",
            "ml engineer": "AI Engineer",
            "devops": "DevOps Engineer"
        }
        
        if target in mapping:
            return mapping[target]
        
        # Search for partial match in your JSON keys
        for key in self.skills_db.keys():
            if target in key.lower():
                return key
        return "Full Stack Developer"

    def analyze(self, resume_skills, target_domain):
        # 1. Get the right skills from YOUR JSON
        category_key = self.get_best_category(target_domain)
        target_data = self.skills_db[category_key]
        
        # 2. Combine all tiers for a total skill list
        all_required = (target_data.get("beginner", []) + 
                        target_data.get("compulsory", []) + 
                        target_data.get("intermediate", []) + 
                        target_data.get("advanced", []))
        
        # 3. Match against what was found in the resume
        resume_skills_lower = [s.lower() for s in resume_skills]
        found = [s for s in all_required if s.lower() in resume_skills_lower]
        missing = [s for s in all_required if s.lower() not in resume_skills_lower]
        
        # 4. Calculate proper score (No more fake 100%)
        score = (len(found) / len(all_required) * 100) if all_required else 0
        
        # 5. Build Mermaid Roadmap (Matches your UI Container)
        roadmap = "graph TD\n"
        roadmap += f'  Start((You)) --> B["Beginner: {", ".join(target_data["beginner"][:2])}"]\n'
        roadmap += f'  B --> I["Intermediate: {", ".join(target_data["intermediate"][:2])}"]\n'
        roadmap += f'  I --> A["Advanced: {target_data["advanced"][0]}"]\n'
        roadmap += f'  A --> Goal(({category_key}))\n'
        
        # Styling for your Sage Green UI
        roadmap += '  style Start fill:#ACC8A2,stroke:#1A2517\n'
        roadmap += '  style Goal fill:#1A2517,stroke:#ACC8A2,color:#fff\n'

        return {
            "score": score,
            "status_text": f"Match Level: {round(score, 1)}%",
            "found_skills": found,
            "missing_skills": missing,
            "roadmap": roadmap,
            "alt_domain": target_data.get("next_steps", ["Specialist"])[0]
        }

# Bridge for your existing app.py/server
predictor_instance = CareerPredictor()

def extract_skills_from_text(text):
    found_skills = set()
    text_lower = text.lower()
    
    for category in predictor_instance.skills_db.values():
        for tier in ["beginner", "compulsory", "intermediate", "advanced"]:
            for skill_entry in category.get(tier, []):
                # --- NEW LOGIC: Split grouped skills by '/' ---
                # This turns "Python/Scala" into ["Python", "Scala"]
                individual_skills = [s.strip() for s in skill_entry.split('/')]
                
                for skill in individual_skills:
                    # Look for the skill as a standalone word (using regex for accuracy)
                    # This ensures "Java" doesn't match inside "JavaScript"
                    pattern = r'\b' + re.escape(skill.lower()) + r'\b'
                    if re.search(pattern, text_lower):
                        # We add the original group name (e.g., "Python/Scala") 
                        # so the roadmap stays consistent with your JSON
                        found_skills.add(skill_entry)
                        break # Move to next skill_entry once a match is found
                        
    return list(found_skills)

def analyze_skill_gap(resume_skills, target_domain):
    return predictor_instance.analyze(resume_skills, target_domain)