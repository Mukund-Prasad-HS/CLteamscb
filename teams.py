import streamlit as st
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication  # Corrected import
from datetime import datetime
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_google_genai import ChatGoogleGenerativeAI
import os
# Configure page
st.set_page_config(page_title="Support Chatbot", layout="centered")

# Email configuration - Store these in environment variables in production
EMAIL_SETTINGS = {
    "SMTP_SERVER": "smtp.gmail.com",
    "SMTP_PORT": 587,
    "SENDER_EMAIL": "1rn20ai033.mukundprasadhs@gmail.com",
    "SENDER_PASSWORD": "gjarqxihnmmelwhv"
}

# Updated Category and department email mapping
CATEGORIES = {
    "Training": "training@example.com",
    "IT Operations": "demogptmukund@gmail.com",
    "Technology": "mukunddemochatgpt@gmail.com",
    "HR": "hr@example.com",
    "Finance": "finance@example.com",
    "Sales": "sales@example.com"
}

# Gemini API Key configuration (replace with actual API key)
GEMINI_API_KEY = "AIzaSyCwg902HLytTm7bwpxMFv70EluwPdFGuoo"


def create_mime_attachment(uploaded_file):
    """
    Create MIME attachment based on file type
    Supports PDF, DOCX, and image files
    """
    # Allowed file extensions
    allowed_extensions = ['.pdf', '.docx', '.jpg', '.jpeg', '.png', '.gif', '.bmp']

    # Get file extension
    file_ext = os.path.splitext(uploaded_file.name)[1].lower()

    # Check if file type is allowed
    if file_ext not in allowed_extensions:
        st.warning(f"Unsupported file type: {uploaded_file.name}")
        return None

    # Read file content
    file_content = uploaded_file.getvalue()

    try:
        if file_ext in ['.pdf']:
            # PDF attachment
            attachment = MIMEApplication(file_content, _subtype='pdf')
        elif file_ext in ['.docx']:
            # DOCX attachment
            attachment = MIMEApplication(file_content, _subtype='docx')
        else:
            # Image attachment
            attachment = MIMEApplication(file_content, _subtype=file_ext[1:])

        # Set the filename
        attachment.add_header('Content-Disposition', 'attachment', filename=uploaded_file.name)
        return attachment
    except Exception as e:
        st.error(f"Error processing attachment {uploaded_file.name}: {e}")
        return None


def send_notification(subject, body, to_email, attachments=None):
    """Email sending function with multiple attachments"""
    msg = MIMEMultipart()
    msg['From'] = EMAIL_SETTINGS['SENDER_EMAIL']
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    # Attach files if any
    if attachments:
        for attachment in attachments:
            if attachment:  # Only attach valid files
                msg.attach(attachment)

    try:
        with smtplib.SMTP(EMAIL_SETTINGS['SMTP_SERVER'], EMAIL_SETTINGS['SMTP_PORT']) as server:
            server.starttls()
            server.login(EMAIL_SETTINGS['SENDER_EMAIL'], EMAIL_SETTINGS['SENDER_PASSWORD'])
            server.send_message(msg)
        return True
    except Exception as e:
        st.error(f"Email Error: {str(e)}")
        return False


def get_department_from_gemini(description):
    """Use Gemini API to determine the department based on issue description."""
    # Define prompt template for classification
    prompt_template = """
    You are an AI assistant for a support ticket system. Your task is to classify employee issues into specific categories based on the description provided. Here are the categories:

    - Training
    - IT Operations
    - Technology
    - HR
    - Finance
    - Sales

    Instructions:
    1. Analyze the issue description to determine the most appropriate category.
    2. If the description includes words related to multiple categories, choose the one most directly related to the problem.
    3. Return only the category name as your answer.

    Description: {description}

    Category:
    """

    # Create a prompt with LangChain
    prompt = PromptTemplate(template=prompt_template, input_variables=["description"])

    # Initialize the model
    model = ChatGoogleGenerativeAI(model="gemini-pro", api_key=GEMINI_API_KEY, temperature=0.3)

    # Use LLMChain instead of ConversationChain
    chain = LLMChain(llm=model, prompt=prompt)

    # Run the chain and get the category
    category = chain.run({"description": description}).strip()
    return category if category in CATEGORIES else "Training"  # Default to Training if no match


def main():
    st.title("Support Ticket System")

    # Initialize session state if needed
    if 'submitted' not in st.session_state:
        st.session_state.submitted = False
        st.session_state.department = ""  # To store department information

    # Form inputs
    with st.form("ticket_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            category = st.selectbox("Issue Category*", ["Auto-detect Category"] + list(CATEGORIES.keys()))
            emp_id = st.text_input("Employee ID*")
        with col2:
            name = st.text_input("Full Name*")
            email = st.text_input("Email*")
        description = st.text_area("Description*")

        # File uploader with specific file types
        uploaded_files = st.file_uploader(
            "Attach files (PDF, DOCX, Images)*",
            type=['pdf', 'docx', 'jpg', 'jpeg', 'png', 'gif', 'bmp'],
            accept_multiple_files=True
        )

        submitted = st.form_submit_button("Submit Ticket", use_container_width=True)

        if submitted and emp_id and name and email and description:
            # Generate unique ticket ID
            ticket_id = f"TKT-{datetime.now().strftime('%Y%m%d%H%M')}"

            # Use Gemini API to auto-detect department if "Auto-detect Category" is selected
            if category == "Auto-detect Category":
                category = get_department_from_gemini(description)
            dept_email = CATEGORIES.get(category, EMAIL_SETTINGS['SENDER_EMAIL'])

            # Prepare attachments
            attachments = []
            if uploaded_files:
                for uploaded_file in uploaded_files:
                    mime_attachment = create_mime_attachment(uploaded_file)
                    if mime_attachment:
                        attachments.append(mime_attachment)

            # Email to department
            dept_msg = f""" New Ticket: {ticket_id} 
            Category: {category}
            From: {name} ({emp_id})
            Email: {email}
            Description: {description} 
            Attachments: {len(attachments)} file(s) """

            # Email to employee
            confirm_msg = f""" Dear {name},
            Your ticket {ticket_id} has been received.
            Category: {category}
            Attachments: {len(attachments)} file(s)
            We'll process your request soon.
            Best regards,
            Support Team """

            # Send emails
            if send_notification(f"Support Ticket {ticket_id}", dept_msg, dept_email, attachments):
                if send_notification("Ticket Confirmation", confirm_msg, email):
                    st.session_state.submitted = True
                    st.session_state.department = category  # Store the department
                    st.rerun()

    # Show success message after submission
    if st.session_state.submitted:
        department = st.session_state.department  # Retrieve the department
        st.success(
            f"✅ Ticket submitted successfully! Your ticket has been raised to the '{department}' department. Check your email for confirmation.")
        if st.button("Submit Another Ticket"):
            st.session_state.submitted = False
            st.session_state.department = ""  # Reset department
            st.rerun()


if __name__ == "__main__":
    main()