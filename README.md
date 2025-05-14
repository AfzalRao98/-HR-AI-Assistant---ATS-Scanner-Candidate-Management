🤖 HR AI Assistant - ATS Scanner & Candidate Management


A powerful Streamlit application that helps HR professionals automate resume screening, generate assessment tests, and manage candidate communications — all powered by Groq LLM through LangChain.



🚀 Features


📝 Automated resume scanning and ATS scoring

🔍 Intelligent qualification matching against job descriptions

📊 Visualization of matching and missing qualifications

📋 Auto-generated skills assessment tests with MCQs

📧 Customizable email templates for qualified and rejected candidates

🔒 Secure handling of credentials with environment variables






🛠️ Tech Stack



Python 3.10+

Streamlit

LangChain & LangChain Groq

Groq LLM 

PyPDF2 for PDF processing and text extraction

SMTP for email communication

dotenv for secure API key management




🧠 How It Works


HR uploads a candidate's resume PDF and enters the job description

The application extracts text from the PDF and analyzes it against the job requirements

Groq's LLM generates an ATS score, matching/missing qualifications, and a recommendation

For qualified candidates, a customized skills assessment test is automatically generated

HR can preview and send personalized emails to candidates with just one click
