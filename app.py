"""
AI Email Generator
-------------------
A Streamlit web app that uses the Groq API to generate polished,
professional emails based on user input.

Run locally with:
    streamlit run app.py

Deploy on Streamlit Community Cloud with app.py + requirements.txt.
"""

import os
import streamlit as st
from groq import Groq

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# The Groq chat model used for generation. Change this single variable
# if you want to switch to a different currently-supported Groq model.
GROQ_MODEL = "llama-3.3-70b-versatile"

st.set_page_config(
    page_title="AI Email Generator",
    page_icon="📧",
    layout="centered",
)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def get_api_key() -> str | None:
    """
    Retrieve the Groq API key from environment variables first,
    then fall back to Streamlit secrets. Returns None if not found.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        try:
            api_key = st.secrets.get("GROQ_API_KEY")
        except Exception:
            # st.secrets raises if no secrets.toml exists at all;
            # that's fine, we just treat it as "not found".
            api_key = None
    return api_key


def build_prompt(
    purpose: str,
    email_type: str,
    tone: str,
    recipient_name: str,
    recipient_role: str,
    additional_details: str,
    language: str,
) -> str:
    """Construct the instruction prompt sent to the AI model."""

    recipient_info = ""
    if recipient_name or recipient_role:
        recipient_info = "Recipient details:\n"
        if recipient_name:
            recipient_info += f"- Name: {recipient_name}\n"
        if recipient_role:
            recipient_info += f"- Role/Company: {recipient_role}\n"

    details_section = ""
    if additional_details.strip():
        details_section = f"Additional details to include:\n{additional_details.strip()}\n"

    prompt = f"""
You are a professional email-writing assistant. Write a complete, ready-to-send email
based on the information below.

Purpose of the email:
{purpose.strip()}

Email type: {email_type}
Tone: {tone}
Language: {language}

{recipient_info}
{details_section}

Instructions:
- Write the email in the specified language ({language}). If the language is
  "Roman Urdu", write Urdu using English/Latin script (not Urdu script, not English).
- Follow the selected email type and tone throughout.
- Include all the additional details provided, but do not invent facts, names,
  dates, or information that was not given.
- Keep the email concise and natural, unless the user's details suggest more
  length/detail is needed.
- Include a proper greeting and closing appropriate for the tone and type.
- Address the recipient by name if a recipient name was given; otherwise use a
  suitable generic greeting.
- Sign off generically (e.g. "Best regards,") unless a sender name was provided
  in the details.
- Return ONLY the email itself, formatted EXACTLY like this, with no extra
  commentary, explanations, or markdown formatting:

Subject: <subject line here>

<email body here>
""".strip()

    return prompt


def parse_email_response(raw_text: str) -> tuple[str, str]:
    """
    Split the AI's raw response into (subject, body).
    Falls back gracefully if the expected "Subject:" prefix is missing.
    """
    raw_text = raw_text.strip()

    if raw_text.lower().startswith("subject:"):
        first_line, _, rest = raw_text.partition("\n")
        subject = first_line.split(":", 1)[1].strip()
        body = rest.strip()
        return subject, body

    # Fallback: no clear subject line found, treat everything as the body.
    return "(No subject generated)", raw_text


def generate_email(client: Groq, prompt: str) -> str:
    """Call the Groq API and return the raw generated text."""
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant that writes polished, "
                            "human-like professional emails.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        max_tokens=800,
    )

    if not response.choices or not response.choices[0].message.content:
        raise ValueError("The AI returned an empty response.")

    return response.choices[0].message.content.strip()


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

st.title("📧 AI Email Generator")
st.markdown("**Write professional emails in seconds with AI**")
st.divider()

api_key = get_api_key()
if not api_key:
    st.error(
        "⚠️ Groq API key not found. Please set the `GROQ_API_KEY` environment "
        "variable, or add it to your Streamlit secrets, before using this app."
    )

# --- Input section ---------------------------------------------------------
st.subheader("1. What is your email about?")
purpose = st.text_area(
    "Describe the purpose of your email",
    placeholder="e.g. I want to request an extension for my university assignment.",
    height=120,
)

st.subheader("2. Email details")
col1, col2 = st.columns(2)

with col1:
    email_type = st.selectbox(
        "Email type",
        [
            "Professional",
            "Formal",
            "Friendly",
            "Academic",
            "Job Application",
            "Leave Request",
            "Complaint",
            "Follow-up",
            "Thank You",
            "Custom",
        ],
    )

with col2:
    tone = st.selectbox(
        "Tone",
        ["Professional", "Polite", "Friendly", "Confident", "Apologetic", "Persuasive"],
    )

language = st.selectbox("Language", ["English", "Urdu", "Roman Urdu"])

st.subheader("3. Recipient (optional)")
col3, col4 = st.columns(2)
with col3:
    recipient_name = st.text_input("Recipient name", placeholder="e.g. Dr. Sarah Khan")
with col4:
    recipient_role = st.text_input("Recipient role/company", placeholder="e.g. Course Instructor, ABC University")

st.subheader("4. Additional details (optional)")
additional_details = st.text_area(
    "Any specific information you want included",
    placeholder="e.g. My assignment deadline is Friday, and I need 3 extra days due to illness.",
    height=100,
)

st.divider()
generate_clicked = st.button("✨ Generate Email", type="primary", use_container_width=True)

# --- Generation + output section -------------------------------------------
if generate_clicked:
    if not api_key:
        st.error("Cannot generate email: Groq API key is missing.")
    elif not purpose.strip():
        st.warning("Please describe the purpose of your email before generating.")
    else:
        with st.spinner("Generating your email..."):
            try:
                client = Groq(api_key=api_key)
                prompt = build_prompt(
                    purpose=purpose,
                    email_type=email_type,
                    tone=tone,
                    recipient_name=recipient_name,
                    recipient_role=recipient_role,
                    additional_details=additional_details,
                    language=language,
                )
                raw_output = generate_email(client, prompt)
                subject, body = parse_email_response(raw_output)

                # Store in session state so the result persists across reruns
                # (e.g. when the user clicks the copy button).
                st.session_state["subject"] = subject
                st.session_state["body"] = body

            except ValueError as ve:
                st.error(f"The AI response was invalid: {ve}")
            except Exception as e:
                st.error(f"Something went wrong while generating the email: {e}")

# --- Display generated email -------------------------------------------
if "body" in st.session_state and st.session_state["body"]:
    st.divider()
    st.subheader("📨 Generated Email")

    st.text_input("Subject", value=st.session_state["subject"], key="subject_display")

    full_email = f"Subject: {st.session_state['subject']}\n\n{st.session_state['body']}"

    st.text_area(
        "Email body",
        value=st.session_state["body"],
        height=300,
    )

    st.code(full_email, language=None)
    st.caption("👆 Use the copy icon in the top-right corner of the box above to copy the full email.")
