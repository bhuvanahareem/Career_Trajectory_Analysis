"""
Core AI logic for predicting career paths, analyzing skill gaps, 
and extracting skills from text using a trained BERT model.
"""

import os # OS utilities for environment and paths
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE" # Prevent duplicate library execution errors
import re # regex for skill extraction
import json # metadata parsing
import difflib # Built-in fuzzy string similarity — no extra install needed
import torch # Main deep learning framework
from transformers import BertTokenizer, BertForSequenceClassification # BERT model and tokenizer



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

# ---------------------------------------------------------------------------
# INPUT VALIDATION LAYER
# ---------------------------------------------------------------------------

# Minimum confidence required to accept a user-supplied domain string.
# Below this threshold the pipeline aborts and returns INVALID_DOMAIN.
DOMAIN_SIMILARITY_THRESHOLD = 0.45

# Common shorthand aliases — resolved before fuzzy matching
_ALIAS_MAP = {
    "data scientist": "AI and Data Scientist",
    "data science": "AI and Data Scientist",
    "web developer": "Full Stack Developer",
    "ml engineer": "AI Engineer",
    "devops": "DevOps Engineer",
    "cybersec": "Cyber Security",
    "cyber security": "Cyber Security",
    "cybersecurity": "Cyber Security",
    "qa": "QA (Quality Assurance)",
    "quality assurance": "QA (Quality Assurance)",
    "machine learning": "Machine Learning",
    "ml": "Machine Learning",
    "bi": "BI Analyst",
    "business intelligence": "BI Analyst",
    "product manager": "Product Manager",
    "pm": "Product Manager",
    "android": "Android Developer",
    "ios": "iOS Developer",
    "blockchain": "Blockchain Developer",
    "game dev": "Game Developer",
    "game developer": "Game Developer",
    "mlops": "MLOps Engineer",
    "devsecops": "DevSecOps Engineer",
    "software architect": "Software Architect",
    "ux": "UX Designer",
    "ux designer": "UX Designer",
    "technical writer": "Technical Writer",
    "tech writer": "Technical Writer",
    "data engineer": "Data Engineer",
    "data analyst": "Data Analyst",
    "ai engineer": "AI Engineer",
    "frontend": "Frontend Developer",
    "frontend developer": "Frontend Developer",
    "backend": "Backend Developer",
    "backend developer": "Backend Developer",
    "full stack": "Full Stack Developer",
    "fullstack": "Full Stack Developer",
    "engineering manager": "Engineering Manager",
}


def validate_domain_input(target_domain: str) -> dict:
    """
    Validates whether a user-supplied career domain string is recognisable.

    Three-stage pipeline (short-circuits on first match):
      1. Alias map — exact pre-defined shorthands (e.g. 'devops', 'qa').
      2. Substring check — input is contained in any known domain key.
      3. Fuzzy ratio — difflib.SequenceMatcher against all domain keys;
         accepts if best ratio >= DOMAIN_SIMILARITY_THRESHOLD (0.45).

    Returns:
        dict with keys:
          - valid (bool)
          - matched_domain (str | None)  — canonical domain name when valid
          - score (float)                — best similarity score (0.0–1.0)
          - error (str | None)           — 'INVALID_DOMAIN' when invalid
    """
    if not target_domain or not target_domain.strip():
        return {"valid": False, "matched_domain": None, "score": 0.0, "error": "INVALID_DOMAIN"}

    normalised = target_domain.lower().strip()
    known_domains = list(CAREER_METADATA.keys())

    # ── Stage 1: Alias map (exact) ────────────────────────────────────────────
    if normalised in _ALIAS_MAP:
        return {
            "valid": True,
            "matched_domain": _ALIAS_MAP[normalised],
            "score": 1.0,
            "error": None,
        }

    # ── Stage 2: Substring containment ───────────────────────────────────────
    for domain in known_domains:
        if normalised in domain.lower():
            return {
                "valid": True,
                "matched_domain": domain,
                "score": 1.0,
                "error": None,
            }

    # ── Stage 3: Fuzzy similarity ratio ──────────────────────────────────────
    best_score = 0.0
    best_domain = None
    for domain in known_domains:
        ratio = difflib.SequenceMatcher(
            None, normalised, domain.lower()
        ).ratio()
        if ratio > best_score:
            best_score = ratio
            best_domain = domain

    if best_score >= DOMAIN_SIMILARITY_THRESHOLD:
        return {
            "valid": True,
            "matched_domain": best_domain,
            "score": round(best_score, 4),
            "error": None,
        }

    # ── Below threshold — reject ──────────────────────────────────────────────
    return {
        "valid": False,
        "matched_domain": None,
        "score": round(best_score, 4),
        "error": "INVALID_DOMAIN",
    }


class CareerPredictor:
    """Class to handle career prediction and skill gap analysis using a BERT model."""
    def __init__(self):
        """Initializes the BERT model, tokenizer, and skill metadata."""
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

    def get_best_category(self, target_domain, pre_validated_domain=None):
        """
        Maps user input to a canonical domain name from the trained knowledge.

        If pre_validated_domain is provided (from validate_domain_input), it is
        used directly — skipping the lookup entirely for consistency.
        """
        if pre_validated_domain:
            return pre_validated_domain

        # Fallback path (should not normally be reached after validation)
        target = target_domain.lower().strip()
        if target in _ALIAS_MAP:
            return _ALIAS_MAP[target]

        available_domains = self.structured_data.keys()
        for domain in available_domains:
            if target in domain.lower():
                return domain

        return "Full Stack Developer"  # Last-resort default (post-validation this path is rare)

    def analyze(self, resume_skills, target_domain, pre_validated_domain=None):
        """
        Compares user skills against target requirements to calculate match scores.

        Args:
            resume_skills: List of skills extracted from the user's resume.
            target_domain: Raw domain string supplied by the user.
            pre_validated_domain: Canonical domain name from validate_domain_input().
                                  When provided, skips the internal lookup.

        Raises:
            ValueError("INVALID_DOMAIN") if validation has not been performed
            upstream and the raw input fails the similarity check.
        """
        # Guard: if no pre-validated domain was passed, run validation now.
        # This provides a safety net even if called directly (e.g. from tests).
        if not pre_validated_domain:
            validation = validate_domain_input(target_domain)
            if not validation["valid"]:
                raise ValueError("INVALID_DOMAIN")
            pre_validated_domain = validation["matched_domain"]

        category_key = self.get_best_category(target_domain, pre_validated_domain)
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

# ---------------------------------------------------------------------------
# Module-level bridge functions for app.py
# ---------------------------------------------------------------------------
predictor_instance = CareerPredictor()

def extract_skills_from_text(text):
    """Scans input text for matches against the global skill vocabulary using regex."""
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

def analyze_skill_gap(resume_skills, target_domain, pre_validated_domain=None):
    """
    Wrapper: performs skill-gap analysis for a specific target domain.
    Pass pre_validated_domain from validate_domain_input() to avoid double-validation.
    """
    return predictor_instance.analyze(resume_skills, target_domain, pre_validated_domain)

def analyze_confused_paths(resume_skills):
    """Wrapper function to find alternative career paths for the user's skills."""
    return predictor_instance.analyze_confused(resume_skills)
