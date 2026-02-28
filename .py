import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

def test_groq():
    api_key = os.getenv('GROQ_API_KEY')
    if not api_key:
        print("FAILED! GROQ_API_KEY not found in .env")
        return

    print(f"Testing Groq with key starting with: {api_key[:10]}...")
    
    try:
        client = Groq(api_key=api_key)
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": "Say 'Groq is working!'",
                }
            ],
            model="llama-3.3-70b-versatile",
        )
        print(f"SUCCESS! Response: {chat_completion.choices[0].message.content}")
    except Exception as e:
        print(f"FAILED! Error: {e}")

if __name__ == "__main__":
    test_groq()
