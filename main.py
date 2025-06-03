import streamlit as st
import PyPDF2
import io
import os
from openai import OpenAI
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
import re

load_dotenv()

st.set_page_config(page_title="AI Resume Critiquer", page_icon="📃", layout="centered")

st.title("AI Resume Critiquer")
st.markdown("Upload your resume and get AI-powered feedback tailored to your needs!")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

uploaded_file = st.file_uploader("Upload your resume (PDF of TXT)", type=["pdf", "txt"])
job_role = st.text_input("Enter the job role you're targetting ")
job_description = st.text_area("Paste the job description here (optional)")
job_url = st.text_input("Paste the job listing URL (optional)")



analyze = st.button("Analyze Resume")

def extract_text_from_url(url):
    try:
        response = requests.get(url, timeout=5)
        soup = BeautifulSoup(response.text, "html.parser")
        # Get visible text from the page
        return soup.get_text(separator="\n", strip=True)
    except Exception as e:
        return f"Could not extract job description from the URL: {e}"

#this extract the text from pdf and but it in text string 

def extract_text_from_pdf(pdf_file):
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() + "\n"
    return text

#
def extract_text_from_file(uploaded_file):
    if uploaded_file.type == "application/pdf":
        return extract_text_from_pdf(io.BytesIO(uploaded_file.read()))
    return uploaded_file.read().decode("ut-8")


if analyze and uploaded_file:
    try:
        file_content = extract_text_from_file(uploaded_file)

        if not file_content.strip():
            st.error("File does not have any content ...")
            st.stop()

        # Use existing job_description or fetch from URL if given
        if job_url:
            job_description = extract_text_from_url(job_url)


        prompt = f"""
        You are an expert resume reviewer.

        Please analyze the resume below and do the following:

        1. Rate each of these categories from 1 to 10:
            - Clarity of content
            - Relevance to the job role '{job_role if job_role else "general job applications"}'
            - Presentation of skills and accomplishments
            - Formatting and readability

        2. Provide specific, constructive feedback for improvement in each category.

        3. Suggest stronger action verbs or industry keywords that could improve the impact.

        4. Compare the resume to this job posting and give a final Match Score from 1 to 10.  
        Clearly write it as: Match Score: X/10 at the end.

        Job Posting:
        {job_description}

        Resume:
        {file_content}
        """

        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert resume reviewer with years of experience in HR and recruitment."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )

        ai_feedback = response.choices[0].message.content
        st.markdown("Analysis Results")
        st.markdown(ai_feedback)

        match = re.search(r"(\d+)/10", ai_feedback)
        match_score = int(match.group(1)) if match else None

        if match_score is not None:
            st.markdown(f"Resume Match Score: {match_score}/10")
            st.progress(match_score / 10)

        st.download_button(
            label="Download Feedback",
            data=ai_feedback,
            file_name="resume_feedback.txt",
            mime="text/plain"
        )

        # Improvement suggestions + rewriting section 
        if match_score is not None and match_score < 10:
            improve_prompt = f"""
            Based on this resume feedback:

            {ai_feedback}

            Please provide 3–5 specific improvements to raise the resume's Match Score from {match_score}/10 to 10/10.

            Focus on aligning better with the job description, filling skill gaps, or improving presentation.
            """

            improve_response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a resume optimization expert."},
                    {"role": "user", "content": improve_prompt}
                ],
                temperature=0.7,
                max_tokens=700
            )

            st.markdown("How to Improve Your Resume to Score 10/10")
            st.markdown(improve_response.choices[0].message.content)

            # Ask AI to rewrite the resume
            rewrite_prompt = f"""
            Here's the original resume content:

            {file_content}

            Based on this feedback:

            {ai_feedback}

            And your improvement suggestions:

            {improve_response.choices[0].message.content}

            Rewrite the resume to score 10/10, keeping the tone professional.
            Use strong action verbs, align with the job description, and structure it clearly.
            Only return the improved resume — no explanation needed.
            """

            rewrite_response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a resume writing expert."},
                    {"role": "user", "content": rewrite_prompt}
                ],
                temperature=0.7,
                max_tokens=1500
            )

            improved_resume = rewrite_response.choices[0].message.content

            st.markdown("Improved Resume (Draft)")
            st.text(improved_resume)

            st.download_button(
                label="Download Improved Resume",
                data=improved_resume,
                file_name="improved_resume.txt",
                mime="text/plain"
            )

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")


       
