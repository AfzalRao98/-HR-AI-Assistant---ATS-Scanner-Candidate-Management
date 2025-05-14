import streamlit as st
import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import PyPDF2
import io
from typing import Dict, List, Any, Tuple
from langchain_groq import ChatGroq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set page configuration
st.set_page_config(
    page_title="HR AI Assistant - ATS Scanner",
    page_icon="📝",
    layout="wide"
)

# Main title and description
st.title("HR AI Assistant - ATS Scanner")
st.markdown("""
This application helps HR professionals analyze resumes against job descriptions, 
generate assessment tests, and automate email communication with candidates.
""")

# Initialize session state for storing data between reruns
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None
if 'mcq_test' not in st.session_state:
    st.session_state.mcq_test = None
if 'email_sent' not in st.session_state:
    st.session_state.email_sent = False
if 'candidate_info' not in st.session_state:
    st.session_state.candidate_info = {}

# Load configuration from environment variables
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))


# Function to extract text from PDF
def pdf_to_text(pdf_file) -> str:
    """Convert PDF file to text"""
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        st.error(f"Error extracting text from PDF: {e}")
        return ""


# Function to analyze resume
def analyze_resume(resume_text: str, job_description: str, candidate_email: str) -> Dict:
    """Analyze resume against job description using LLM"""
    try:
        # Check if API key is available
        if not GROQ_API_KEY:
            st.error("Groq API key not found in environment variables. Please check your .env file.")
            return {}

        # Initialize the LLM
        llm = ChatGroq(model="llama3-8b-8192", temperature=0.1, api_key=GROQ_API_KEY)

        # Create prompt template
        prompt = f"""You are an expert HR assistant. Analyze the resume against the job description and provide:
1. An ATS match score as a percentage
2. List of key qualifications matching the job requirements
3. List of missing qualifications
4. Final recommendation (qualified / not qualified) with reasoning

Resume Text:
{resume_text}

Job Description:
{job_description}

Candidate Email: {candidate_email}

Format your response as a valid JSON with the following structure:
{{
    "ats_score": number,
    "matching_qualifications": [string],
    "missing_qualifications": [string],
    "recommendation": string,
    "reasoning": string
}}

Ensure the entire response is ONLY a valid parseable JSON format.
"""

        # Call the LLM
        response = llm.invoke(prompt)

        # Extract and parse JSON response
        try:
            analysis = json.loads(response.content)
            return analysis
        except json.JSONDecodeError:
            # If the response is not valid JSON, attempt to extract JSON portion
            import re
            json_match = re.search(r'({[\s\S]*})', response.content)
            if json_match:
                analysis = json.loads(json_match.group(1))
                return analysis
            else:
                raise ValueError("Could not extract valid JSON from LLM response")

    except Exception as e:
        st.error(f"Error analyzing resume: {e}")
        return {
            "ats_score": 0,
            "matching_qualifications": [],
            "missing_qualifications": ["Error processing resume"],
            "recommendation": "Error",
            "reasoning": f"An error occurred: {str(e)}"
        }


# Function to generate MCQ test
def generate_mcq_test(job_description: str) -> Dict:
    """Generate MCQ test based on job description"""
    try:
        # Check if API key is available
        if not GROQ_API_KEY:
            st.error("Groq API key not found in environment variables. Please check your .env file.")
            return {}

        # Initialize the LLM
        llm = ChatGroq(model="llama3-8b-8192", temperature=0.4, api_key=GROQ_API_KEY)

        # Create prompt template
        prompt = f"""You are an expert HR test creator. Based on the job description below, create 5 multiple-choice questions to assess candidates.
Each question should have 4 options with one correct answer marked.

Job Description:
{job_description}

Format your response as a valid JSON with the following structure:
{{
    "questions": [
        {{
            "question": "Question text",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct_answer_index": 0,
            "explanation": "Explanation of why this is the correct answer"
        }}
    ]
}}

Make sure to include an explanation field for each question that explains why the answer is correct.
Ensure the entire response is ONLY a valid parseable JSON format.
"""

        # Call the LLM
        response = llm.invoke(prompt)

        # Extract and parse JSON response
        try:
            mcq_test = json.loads(response.content)
            return mcq_test
        except json.JSONDecodeError:
            # If the response is not valid JSON, attempt to extract JSON portion
            import re
            json_match = re.search(r'({[\s\S]*})', response.content)
            if json_match:
                mcq_test = json.loads(json_match.group(1))
                return mcq_test
            else:
                raise ValueError("Could not extract valid JSON from LLM response")

    except Exception as e:
        st.error(f"Error generating MCQ test: {e}")
        return {"questions": []}


# Function to send email
def send_email(recipient_email: str, subject: str, html_content: str) -> bool:
    """Send email to candidate"""
    try:
        # Check if email credentials are available
        if not EMAIL_USER or not EMAIL_PASSWORD:
            st.error("Email credentials not found in environment variables. Please check your .env file.")
            return False

        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = EMAIL_USER
        msg['To'] = recipient_email

        # Attach HTML content
        part = MIMEText(html_content, 'html')
        msg.attach(part)

        # Send email
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()

        return True

    except Exception as e:
        st.error(f"Error sending email: {e}")
        return False


# Function to create qualified email with MCQs
def create_qualified_email(candidate_name: str, job_title: str, mcq_test: Dict) -> str:
    """Create HTML email for qualified candidates with MCQ test"""

    # Create MCQ questions HTML
    mcq_html = ""
    for i, q in enumerate(mcq_test.get("questions", [])):
        mcq_html += f"""
        <div style="margin-bottom: 20px; padding: 15px; background-color: #f9f9f9; border-radius: 5px;">
            <p style="font-weight: bold; margin-bottom: 10px;">Question {i + 1}: {q['question']}</p>
            <ul style="list-style-type: none; padding-left: 0;">
        """

        for j, option in enumerate(q.get("options", [])):
            mcq_html += f"""
                <li style="margin-bottom: 5px;">
                    <input type="radio" name="q{i}" value="{j}"> {option}
                </li>
            """

        mcq_html += """
            </ul>
        </div>
        """

    # Create full HTML email
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #4CAF50; color: white; padding: 10px 20px; text-align: center; }}
            .content {{ padding: 20px; }}
            .footer {{ background-color: #f1f1f1; padding: 10px 20px; text-align: center; font-size: 0.8em; }}
            .button {{ background-color: #4CAF50; color: white; padding: 10px 15px; text-decoration: none; border-radius: 4px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>Congratulations, {candidate_name}!</h2>
            </div>
            <div class="content">
                <p>We are pleased to inform you that your resume has been reviewed for the <strong>{job_title}</strong> position, and you have been selected to move forward in our recruitment process.</p>

                <p>As part of the next step, we would like you to complete the following assessment. Please answer these questions to the best of your ability:</p>

                <form>
                    {mcq_html}
                </form>

                <p>Please reply to this email with your answers within the next 48 hours.</p>

                <p>We look forward to reviewing your responses and potentially discussing the opportunity further.</p>

                <p>Best regards,<br>HR Team</p>
            </div>
            <div class="footer">
                <p>This email was sent automatically by our HR AI Assistant.</p>
            </div>
        </div>
    </body>
    </html>
    """

    return html


# Function to create rejection email
def create_rejection_email(candidate_name: str, job_title: str, reason: str) -> str:
    """Create HTML email for rejected candidates"""

    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #e53935; color: white; padding: 10px 20px; text-align: center; }}
            .content {{ padding: 20px; }}
            .footer {{ background-color: #f1f1f1; padding: 10px 20px; text-align: center; font-size: 0.8em; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>Application Status Update</h2>
            </div>
            <div class="content">
                <p>Dear {candidate_name},</p>

                <p>Thank you for your interest in the <strong>{job_title}</strong> position and for taking the time to submit your application.</p>

                <p>After careful consideration of your qualifications and experience in relation to the requirements of this role, we regret to inform you that we have decided not to move forward with your application at this time.</p>

                <p>While your profile has many strengths, {reason}</p>

                <p>We encourage you to apply for future opportunities that align more closely with your skills and experience.</p>

                <p>We wish you the best in your job search and professional endeavors.</p>

                <p>Best regards,<br>HR Team</p>
            </div>
            <div class="footer">
                <p>This email was sent automatically by our HR AI Assistant.</p>
            </div>
        </div>
    </body>
    </html>
    """

    return html


# Function to display analysis results
def display_analysis_results(analysis: Dict):
    """Display analysis results in a visually appealing way"""

    if not analysis:
        st.warning("No analysis results to display.")
        return

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("ATS Match Score")
        score = analysis.get('ats_score', 0)
        st.markdown(
            f"""
            <div style="text-align:center; background-color:{'#66bb6a' if score >= 70 else '#ffb74d' if score >= 50 else '#ef5350'}; 
            padding:20px; border-radius:10px; color:white; font-size:24px; font-weight:bold;">
                {score}%
            </div>
            """,
            unsafe_allow_html=True
        )

        st.subheader("Recommendation")
        recommendation = analysis.get('recommendation', '').lower()
        if 'qualified' in recommendation and 'not' not in recommendation:
            icon = "✅"
            color = "#66bb6a"
            text = "Qualified"
        else:
            icon = "❌"
            color = "#ef5350"
            text = "Not Qualified"

        st.markdown(
            f"""
            <div style="text-align:center; background-color:{color}; 
            padding:15px; border-radius:10px; color:white; font-size:18px; font-weight:bold;">
                {icon} {text}
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:
        st.subheader("Matching Qualifications")
        if matching := analysis.get('matching_qualifications', []):
            for qual in matching:
                st.markdown(f"✅ {qual}")
        else:
            st.write("No matching qualifications found.")

        st.subheader("Missing Qualifications")
        if missing := analysis.get('missing_qualifications', []):
            for qual in missing:
                st.markdown(f"❌ {qual}")
        else:
            st.write("No missing qualifications found.")

    st.subheader("Reasoning")
    st.write(analysis.get('reasoning', 'No reasoning provided.'))


# Function to display MCQ test with answers
def display_mcq_test(mcq_test: Dict):
    """Display MCQ test with answers and explanations"""
    if not mcq_test or not mcq_test.get('questions'):
        st.warning("No MCQ test available.")
        return

    st.subheader("Skills Assessment Test")

    for i, q in enumerate(mcq_test.get('questions', [])):
        with st.expander(f"Question {i + 1}: {q.get('question', 'No question')}"):
            for j, option in enumerate(q.get('options', [])):
                if j == q.get('correct_answer_index', 0):
                    st.markdown(f"✅ **{option}** (Correct Answer)")
                else:
                    st.write(f"○ {option}")

            st.markdown(f"**Explanation:** {q.get('explanation', 'No explanation provided.')}")


# Create tabs for different functionalities
tab1, tab2, tab3 = st.tabs(["Resume Upload", "Analysis Results", "Email Management"])

with tab1:
    st.header("Resume Upload")

    # Form for resume analysis
    with st.form("resume_analysis_form"):
        uploaded_file = st.file_uploader("Upload Resume (PDF)", type="pdf")
        job_description = st.text_area("Job Description", height=200)
        candidate_email = st.text_input("Candidate Email")
        candidate_name = st.text_input("Candidate Name")
        job_title = st.text_input("Job Title")

        submit_button = st.form_submit_button("Analyze Resume")

        if submit_button and uploaded_file and job_description and candidate_email:
            with st.spinner("Processing resume..."):
                # Extract text
                resume_text = pdf_to_text(uploaded_file)

                # Analyze resume
                analysis = analyze_resume(resume_text, job_description, candidate_email)
                st.session_state.analysis_results = analysis

                # Store candidate info
                st.session_state.candidate_info = {
                    'name': candidate_name,
                    'email': candidate_email,
                    'job_title': job_title
                }

                # If qualified, generate MCQ test
                if 'qualified' in analysis.get('recommendation', '').lower() and 'not' not in analysis.get(
                        'recommendation', '').lower():
                    with st.spinner("Generating assessment test..."):
                        mcq_test = generate_mcq_test(job_description)
                        st.session_state.mcq_test = mcq_test

            st.success("Analysis completed! Please go to the Analysis Results tab.")

with tab2:
    st.header("Analysis Results")

    # Check if we have analysis results
    if st.session_state.analysis_results:
        # Display analysis results
        display_analysis_results(st.session_state.analysis_results)

        # If qualified, display MCQ test
        analysis = st.session_state.analysis_results
        recommendation = analysis.get('recommendation', '').lower()
        if 'qualified' in recommendation and 'not' not in recommendation and st.session_state.mcq_test:
            st.markdown("---")
            display_mcq_test(st.session_state.mcq_test)
    else:
        st.info("No analysis results available. Please upload and analyze a resume first.")

with tab3:
    st.header("Email Management")

    # Check if analysis is available
    if not st.session_state.analysis_results or not st.session_state.candidate_info:
        st.warning("Please analyze a resume first before sending emails.")
    else:
        analysis = st.session_state.analysis_results
        candidate_info = st.session_state.candidate_info

        # Determine if qualified
        is_qualified = 'qualified' in analysis.get('recommendation', '').lower() and 'not' not in analysis.get(
            'recommendation', '').lower()

        st.subheader("Email Preview")

        if is_qualified and st.session_state.mcq_test:
            st.info(
                f"📧 Candidate **{candidate_info['name']}** is qualified. A skills assessment test will be included in the email.")

            # Email content
            email_content = create_qualified_email(
                candidate_info['name'],
                candidate_info['job_title'],
                st.session_state.mcq_test
            )
            email_subject = f"Next Steps for {candidate_info['job_title']} Application"

            # Display email preview
            with st.expander("Preview Acceptance Email", expanded=True):
                st.components.v1.html(email_content, height=600, scrolling=True)
        else:
            st.warning(
                f"📧 Candidate **{candidate_info['name']}** is not qualified. A rejection email will be prepared.")

            # Custom rejection reason field
            reason = st.text_area(
                "Customize Rejection Reason (optional)",
                value=analysis.get('reasoning', ''),
                key="rejection_reason"
            )

            # Email content
            email_content = create_rejection_email(
                candidate_info['name'],
                candidate_info['job_title'],
                reason
            )
            email_subject = f"Update on Your {candidate_info['job_title']} Application"

            # Display email preview
            with st.expander("Preview Rejection Email", expanded=True):
                st.components.v1.html(email_content, height=500, scrolling=True)

        # Send email button
        if st.button("Send Email", key="send_email_button", type="primary"):
            with st.spinner("Sending email..."):
                success = send_email(
                    candidate_info['email'],
                    email_subject,
                    email_content
                )

            if success:
                st.session_state.email_sent = True
                st.success(f"Email successfully sent to {candidate_info['email']}!")
            else:
                st.error("Failed to send email. Please check your .env file configuration.")

# Add some spacing at the bottom
st.markdown("<br><br>", unsafe_allow_html=True)
st.caption("HR AI Assistant - ATS Scanner | Powered by Groq & Streamlit")

# Important: Create a .env file with the following variables:
# GROQ_API_KEY=your_groq_api_key_here
# EMAIL_USER=your_email_address_here
# EMAIL_PASSWORD=your_email_password_here
# EMAIL_HOST=smtp.gmail.com
# EMAIL_PORT=587

# Make sure to install the required packages:
# pip install streamlit PyPDF2 langchain-groq python-dotenv


GROQ_API_KEY = GROQ_API_KEY
EMAIL_USER = EMAIL_USER
EMAIL_PASSWORD = EMAIL_PASSWORD
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587