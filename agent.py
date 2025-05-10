from langchain_google_genai import ChatGoogleGenerativeAI
import os
from dotenv import load_dotenv  
load_dotenv()                    


os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")
llm = ChatGoogleGenerativeAI(
    model="gemini-pro",   # Oppure "models/gemini-pro"
    temperature=0.7
)

response = llm.invoke("Spiegami la relatività in parole semplici.")
print(response.content)