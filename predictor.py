import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import re
import json
import torch
from transformers import BertTokenizer, BertForSequenceClassification



CAREER_METADATA = {
    "Frontend Developer": "Crafts the visual and interactive elements of websites and applications using modern web technologies.",
    "Backend Developer": "Builds and maintains the server-side logic, databases, and APIs that power application functionality.",
    "Full Stack Developer": "Versatile engineer capable of handling both client-side and server-side development seamlessly.",
    "DevOps Engineer": "Bridges the gap between development and operations to automate deployment and ensure system reliability.",
    "DevSecOps Engineer": "Integrates security practices directly into the DevOps pipeline for continuous protection.",
    "Data Analyst": "Interprets complex data sets to provide actionable insights and support business decision-making.",
    "AI Engineer": "Designs and builds intelligent systems using machine learning, neural networks, and NLP.",
    "AI and Data Scientist": "Combines statistical expertise with AI modeling to solve complex predictive problems.",
    "Data Engineer": "Architects and maintains the data pipelines and infrastructure required for large-scale analysis.",
    "Android Developer": "Specializes in building high-performance, native applications for the Android ecosystem.",
    "iOS Developer": "Crafts elegant and performant native mobile experiences for Apple's iOS platform.",
    "Machine Learning": "Focuses on developing algorithms that allow computers to learn and improve from data.",
    "Blockchain Developer": "Builds decentralized applications and smart contracts using distributed ledger technology.",
    "QA (Quality Assurance)": "Ensures software excellence through rigorous testing, automation, and quality standards.",
    "Software Architect": "Designs high-level software structures and defines technical standards for scalable systems.",
    "Cyber Security": "Defends organizational networks and data from sophisticated digital threats and breaches.",
    "UX Designer": "Creates user-centric designs that are intuitive, accessible, and delightful to interact with.",
    "Technical Writer": "Simplifies complex technical concepts into clear, concise, and helpful documentation.",
    "Game Developer": "Engineers immersive digital worlds and interactive gameplay experiences for various platforms.",
    "MLOps Engineer": "Streamlines the lifecycle of machine learning models from development to production.",
    "Product Manager": "Defines the product vision and roadmap, aligning technical execution with business goals.",
    "Engineering Manager": "Leads and mentors technical teams to deliver high-quality software while fostering growth.",
    "BI Analyst": "Transforms data into strategic business intelligence through dashboards and reporting."
}

class CareerPredictor:
    def __init__(self):
        self.model_path = os.path.abspath('final_skill_model')
        
        # Load the Skill Metadata (The AI's "Vocabulary" AND Structure)
        meta_path = os.path.join(self.model_path, 'skill_meta.json')
        with open(meta_path, 'r') as f:
            meta = json.load(f)
            self.all_skills = meta['all_skills']
            self.structured_data = meta.get('structured_data', {})
        
        # Load the AI Brain
        self.tokenizer = BertTokenizer.from_pretrained(self.model_path, local_files_only=True)
        self.model = BertForSequenceClassification.from_pretrained(self.model_path, local_files_only=True)
        self.model.eval()

    def get_model_required_skills(self, domain_name):
        """Asks the model what skills are needed for a specific job title."""
        inputs = self.tokenizer(domain_name, return_tensors="pt", padding=True, truncation=True, max_length=32)
        with torch.no_grad():
            logits = self.model(**inputs).logits
            # Sigmoid for multi-label classification
            probs = torch.sigmoid(logits).squeeze().numpy()
        
        # We pick skills the model thinks are relevant (> 0.5 confidence for strict matching)
        required = [self.all_skills[i] for i, p in enumerate(probs) if p > 0.5]
        
        # Fallback to structured data if model is under-confident (for safety)
        if not required and domain_name in self.structured_data:
            job_data = self.structured_data[domain_name]
            for tier in ["beginner", "compulsory", "intermediate", "advanced"]:
                required.extend(job_data.get(tier, []))
        
        return list(set(required)) # Remove duplicates

    def get_best_category(self, target_domain):
        """Maps user input to a canonical domain name from the trained knowledge."""
        target = target_domain.lower().strip()
        
        # Common alias mapping
        mapping = {
            "data scientist": "AI and Data Scientist",
            "data science": "AI and Data Scientist",
            "web developer": "Full Stack Developer",
            "ml engineer": "AI Engineer",
            "devops": "DevOps Engineer",
            "cybersec": "Cyber Security",
            "qa": "QA (Quality Assurance)"
        }
        if target in mapping: return mapping[target]
        
        # Check against available domains in metadata
        available_domains = self.structured_data.keys()
        for domain in available_domains:
            if target in domain.lower():
                return domain
                
        return "Full Stack Developer" # Default fallback

    def analyze(self, resume_skills, target_domain):
        category_key = self.get_best_category(target_domain)
        all_required = self.get_model_required_skills(category_key)
        
        resume_skills_lower = [s.lower() for s in resume_skills]
        found = [s for s in all_required if s.lower() in resume_skills_lower]
        missing = [s for s in all_required if s.lower() not in resume_skills_lower]
        
        score = (len(found) / len(all_required) * 100) if all_required else 0
        status_text = f"Match Level: {round(score, 1)}%"
        
        warning = ""
        master_msg = ""
        
        if score < 30:
            warning = "you should work on yours skills"
        elif score >= 80:
            next_step = self.structured_data.get(category_key, {}).get('next_steps', ["Industry Leadership"])[0]
            master_msg = f"You are a master in this field. Plan on taking the next step to the \"{next_step}\" mentioned for the input job title."

        # Fetch tiered data for roadmap from structured_data
        job_info = self.structured_data.get(category_key, {})
        missing_by_tier = {
            "beginner": [s for s in job_info.get("beginner", []) if s.lower() not in resume_skills_lower],
            "compulsory": [s for s in job_info.get("compulsory", []) if s.lower() not in resume_skills_lower],
            "intermediate": [s for s in job_info.get("intermediate", []) if s.lower() not in resume_skills_lower],
            "advanced": [s for s in job_info.get("advanced", []) if s.lower() not in resume_skills_lower],
            "next_steps": [s for s in job_info.get("next_steps", []) if s.lower() not in resume_skills_lower]
        }
        
        all_by_tier = {
            "beginner": job_info.get("beginner", []),
            "compulsory": job_info.get("compulsory", []),
            "intermediate": job_info.get("intermediate", []),
            "advanced": job_info.get("advanced", []),
            "next_steps": job_info.get("next_steps", [])
        }

        # Analyze alternative paths (> 30% match)
        all_alt_matches = self.analyze_confused(resume_skills)
        alt_domain = None
        alt_missing_by_tier = {}
        
        # Find best alt that isn't the current target
        for match in all_alt_matches:
            if match['domain'] != category_key:
                alt_domain = match['domain']
                alt_missing_by_tier = match['missing_by_tier']
                break

        return {
            "score": score,
            "status_text": status_text,
            "warning": warning,
            "master_msg": master_msg,
            "found_skills": found,
            "missing_skills": missing,
            "roadmap": "", # Clean up mermaid syntax
            "missing_count": len(missing),
            "missing_by_tier": missing_by_tier,
            "all_skills_by_tier": all_by_tier,
            "alt_domain": alt_domain,
            "alt_missing_by_tier": alt_missing_by_tier,
            "description": CAREER_METADATA.get(category_key, "")
        }

    def analyze_confused(self, resume_skills):
        """Analyzes all career paths to find those with >= 30% match."""
        results = []
        resume_skills_lower = [s.lower() for s in resume_skills]
        
        for domain in self.structured_data.keys():
            required = self.get_model_required_skills(domain)
            if not required: continue
            
            found = [s for s in required if s.lower() in resume_skills_lower]
            score = (len(found) / len(required)) * 100
            
            if score >= 30:
                job_info = self.structured_data.get(domain, {})
                m_by_tier = {
                    "beginner": [s for s in job_info.get("beginner", []) if s.lower() not in resume_skills_lower],
                    "compulsory": [s for s in job_info.get("compulsory", []) if s.lower() not in resume_skills_lower],
                    "intermediate": [s for s in job_info.get("intermediate", []) if s.lower() not in resume_skills_lower],
                    "advanced": [s for s in job_info.get("advanced", []) if s.lower() not in resume_skills_lower],
                    "next_steps": [s for s in job_info.get("next_steps", []) if s.lower() not in resume_skills_lower]
                }
                
                # Also provide ALL skills per tier for the roadmap
                all_by_tier = {
                    "beginner": job_info.get("beginner", []),
                    "compulsory": job_info.get("compulsory", []),
                    "intermediate": job_info.get("intermediate", []),
                    "advanced": job_info.get("advanced", []),
                    "next_steps": job_info.get("next_steps", [])
                }
                
                missing_skills = []
                for tier_list in m_by_tier.values():
                    missing_skills.extend(tier_list)
                
                results.append({
                    "domain": domain,
                    "description": CAREER_METADATA.get(domain, ""),
                    "score": round(score, 1),
                    "missing_count": len(missing_skills),
                    "missing_skills": missing_skills,
                    "missing_by_tier": m_by_tier,
                    "all_skills_by_tier": all_by_tier
                })
        
        return sorted(results, key=lambda x: x['score'], reverse=True)

# Bridge for app.py
predictor_instance = CareerPredictor()

def extract_skills_from_text(text):
    found_skills = set()
    text_lower = text.lower()
    
    # We look for matches in the AI's vocabulary (ALL_SKILLS)
    # Using regex with word boundaries for precision
    for skill_entry in predictor_instance.all_skills:
        # Some entries might be "Skill1/Skill2", handle them
        variants = [v.strip().lower() for v in skill_entry.split('/')]
        for v in variants:
            if not v: continue
            # Handle skills with special characters (like C++) carefully
            escaped_v = re.escape(v)
            # Match if skill is a standalone word
            pattern = rf'\b{escaped_v}\b'
            if re.search(pattern, text_lower):
                found_skills.add(skill_entry)
                break
    return list(found_skills)

def analyze_skill_gap(resume_skills, target_domain):
    return predictor_instance.analyze(resume_skills, target_domain)

def analyze_confused_paths(resume_skills):
    return predictor_instance.analyze_confused(resume_skills)
