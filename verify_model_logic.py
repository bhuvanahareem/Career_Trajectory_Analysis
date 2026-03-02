import os
import json
from predictor import CareerPredictor, extract_skills_from_text

def verify_3tier():
    predictor = CareerPredictor()
    
    # 1. Test Skill Extraction
    resume_text = "Experienced with Linux, Networking, and Jenkins. Also familiar with Docker and Kubernetes."
    extracted = extract_skills_from_text(resume_text)
    print(f"Extracted Skills: {extracted}")
    
    # 2. Test DevOps Engineer Match (should trigger mid-tier 30-80%)
    # Expected required: ['Linux', 'Networking ', 'Git/GitHub/GitLab', 'Shell Scripting', 'Jenkins', 'Docker', 'Kubernetes', 'Terraform', 'Prometheus/Grafana', 'AWS/GCP/Azure', 'SRE']
    # Found: Linux, Networking , Jenkins, Docker, Kubernetes (5 out of ~11)
    analysis_devops = predictor.analyze(extracted, "DevOps Engineer")
    print(f"\n--- Analysis for DevOps Engineer ---")
    print(f"Score: {analysis_devops['score']:.1f}%")
    print(f"Warning: '{analysis_devops['warning']}'")
    print(f"Master Msg: '{analysis_devops['master_msg']}'")
    print(f"Missing (Beginner): {analysis_devops['missing_by_tier']['beginner']}")

    # 3. Test High Match (> 80%)
    high_match_skills = ["Linux", "Networking ", "Git/GitHub/GitLab", "Shell Scripting", "Jenkins", "Docker", "Kubernetes", "Terraform", "Prometheus/Grafana"]
    analysis_high = predictor.analyze(high_match_skills, "DevOps Engineer")
    print(f"\n--- High Match Analysis ---")
    print(f"Score: {analysis_high['score']:.1f}%")
    print(f"Master Msg: '{analysis_high['master_msg']}'")

    # 4. Test Low Match (< 30%)
    low_match_skills = ["Linux"]
    analysis_low = predictor.analyze(low_match_skills, "DevOps Engineer")
    print(f"\n--- Low Match Analysis ---")
    print(f"Score: {analysis_low['score']:.1f}%")
    print(f"Warning: '{analysis_low['warning']}'")
    print(f"Alt Domain Found: {analysis_low['alt_domain']}")

if __name__ == "__main__":
    verify_3tier()
