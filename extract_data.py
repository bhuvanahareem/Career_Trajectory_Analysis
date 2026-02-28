import os
import json
from groq import Groq
from pydantic import BaseModel, Field
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()

# =============================================
# PYDANTIC SCHEMAS FOR STRUCTURED EXTRACTION
# =============================================

class Experience(BaseModel):
    title: str = Field(description="The professional job title held")
    company: str = Field(description="The name of the company")
    duration: str = Field(description="The time period worked (e.g., 'Jan 2020 - December 2023')")
    responsibilities: List[str] = Field(description="A list of 3-4 key responsibilities or achievements")

class ResumeData(BaseModel):
    name: str = Field(description="The full name of the candidate")
    email: str = Field(description="The email address of the candidate")
    skills: List[str] = Field(description="A list of 10-15 core technical and core skills")
    experience: List[Experience] = Field(description="A list of all professional experience entries")

class ChatbotResumeData(BaseModel):
    """Schema for extracting career-relevant context from a resume for chatbot use."""
    name: str = Field(description="The full name of the candidate")
    current_status: str = Field(description="Current professional status: 'student', 'working', 'fresher', or 'gap year'")
    years_experience: Optional[float] = Field(description="Total years of professional experience, 0 if student/fresher")
    education: List[str] = Field(description="List of degrees or certifications (e.g., 'B.Tech Computer Science', 'PMP')")
    skills: List[str] = Field(description="A comprehensive list of all technical and soft skills found")
    career_interests: List[str] = Field(description="Inferred career interests based on experience and skills")
    recent_role: Optional[str] = Field(description="Most recent job title, or 'Student' if not applicable")
    industry: Optional[str] = Field(description="Primary industry the candidate has worked in")


# =============================================
# GROQ EXTRACTION FUNCTIONS
# =============================================

def extract_resume_data(resume_text: str, api_key: str) -> str:
    """
    Uses Groq API to extract structured data from resume text.
    """
    if not api_key:
        return json.dumps({"error": "Groq API key is not set."}, indent=2)
    
    try:
        client = Groq(api_key=api_key)

        prompt = (
            "Parse the following resume text. Extract all the information into the "
            "required JSON structure. Focus specifically on extracting a comprehensive "
            "list of 'skills' and a detailed list of 'experience' entries. "
            "Return ONLY valid JSON.\n\n"
            f"Schema:\n{json.dumps(ResumeData.model_json_schema(), indent=2)}\n\n"
            f"Resume Text:\n{resume_text}"
        )

        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a professional resume parser that outputs strictly valid JSON."},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"},
            temperature=0.1
        )

        return response.choices[0].message.content
    
    except Exception as e:
        return json.dumps({"error": f"An API error occurred: {e}"}, indent=2)


def extract_chatbot_context(resume_text: str, api_key: str) -> dict:
    """
    Extracts career-relevant context from a resume to provide personalized
    chatbot conversations. Used by the Career Advisor chatbot.
    """
    if not api_key:
        return {}
    
    try:
        client = Groq(api_key=api_key)

        prompt = (
            "Analyze the following resume text and extract career-relevant details. "
            "Determine the candidate's current professional status (student, working, fresher, or gap year), "
            "their total years of experience, education background, all skills, "
            "and infer likely career interests based on their background. "
            "Return ONLY valid JSON.\n\n"
            f"Schema:\n{json.dumps(ChatbotResumeData.model_json_schema(), indent=2)}\n\n"
            f"Resume Text:\n{resume_text}"
        )

        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a professional career advisor that outputs strictly valid JSON context."},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"},
            temperature=0.1
        )

        return json.loads(response.choices[0].message.content) if response.choices[0].message.content else {}
    
    except Exception as e:
        print(f"[Chatbot Context Extraction Error]: {e}")
        return {}


# =============================================
# STANDALONE USAGE (for testing)
# =============================================
if __name__ == '__main__':
    api_key = os.environ.get('GROQ_API_KEY', '')
    if not api_key:
        print("Set GROQ_API_KEY in your .env file to test.")
    else:
        sample_text = """
        ALEXANDER J. COOPER Austin, TX | (555) 012-3456 | alex.cooper@email.com

        SUMMARY Project Manager & Analyst with 6+ years of experience in SaaS implementation 
        and data-driven operations. Expert in Agile workflows and stakeholder management.

        CORE SKILLS
        Tools: Python, SQL, Tableau, Salesforce, JIRA.
        Ops: Agile/Scrum, Budgeting, Process Optimization.

        EXPERIENCE
        Senior Project Coordinator | NexaStream Solutions 2021 - Present
        Lead 12-person team on SaaS projects, delivering 15% ahead of schedule.

        Data Analyst | BlueGrid Energy Group 2018 - 2020
        Automated dashboards in Tableau, identifying $200k in annual cost savings.

        EDUCATION & CERTS
        B.S. Business Administration | CU Boulder
        Certifications: PMP, Scrum Master (CSM), Google Data Analytics.
        """
        
        print("=== Resume Data Extraction ===")
        result = extract_resume_data(sample_text, api_key)
        print(result)
        
        print("\n=== Chatbot Context Extraction ===")
        context = extract_chatbot_context(sample_text, api_key)
        print(json.dumps(context, indent=2))
