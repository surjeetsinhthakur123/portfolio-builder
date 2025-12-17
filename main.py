import streamlit as st
import os
from dotenv import load_dotenv
from io import BytesIO
import pdfplumber
from pypdf import PdfReader
from docx import Document
import zipfile
from langchain_google_genai import ChatGoogleGenerativeAI

# ------------------ ENV SETUP ------------------
load_dotenv()
os.environ["GOOGLE_API_KEY"] = os.getenv("Gemini")

# ------------------ STREAMLIT UI ------------------
st.set_page_config(page_title="Portfolio Builder")
st.title("Welcome to my Portfolio Builder")

file = st.file_uploader(
    "Choose a PDF or DOCX file",
    type=["pdf", "docx"],
    help="Upload your resume here"
)

# ------------------ FILE PARSER ------------------
def parse_file(uploaded_file) -> str:
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    text = ""

    if ext == ".pdf":
        try:
            with pdfplumber.open(uploaded_file) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
        except Exception:
            uploaded_file.seek(0)
            reader = PdfReader(BytesIO(uploaded_file.read()))
            for page in reader.pages:
                text += page.extract_text() or ""
    elif ext in [".doc", ".docx"]:
        uploaded_file.seek(0)
        doc = Document(BytesIO(uploaded_file.read()))
        text = "\n".join(p.text for p in doc.paragraphs)
    else:
        raise ValueError("Unsupported file type")
    return text.strip()

# ------------------ HELPER FUNCTION ------------------
def extract_code_section(content, tag):
    """
    Safely extract code between --tag-- markers.
    """
    try:
        start = content.index(f"--{tag}--") + len(f"--{tag}--")
        end = content.index(f"--{tag}--", start)
        return content[start:end].strip()
    except ValueError:
        # If the second marker does not exist (like JS at the end), take till the end
        return content[start:].strip()

# ------------------ LLM GENERATION ------------------
if file:
    system_prompt = """
You are a senior frontend web developer and UI designer.

Your task is to create a clean, modern, professional portfolio website
based strictly on the user-provided resume content.

Rules:
1. Generate ONLY raw code.
2. Do NOT explain anything.
3. Do NOT use markdown or backticks.
4. Output must follow the EXACT format below.
5. Use semantic HTML, clean CSS, and vanilla JavaScript only.
6. The website must be responsive.

Output format (MANDATORY):

--html--
[complete HTML code]
--html--

--css--
[complete CSS code]
--css--

--js--
[complete JavaScript code]
--js--
"""

    resume_text = parse_file(file)
    messages = [
        ("system", system_prompt),
        ("user", resume_text)
    ]

    model = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        temperature=0.7
    )

    response = model.invoke(messages)

    # Extract clean code sections
    html_code = extract_code_section(response.content, "html")
    css_code  = extract_code_section(response.content, "css")
    js_code   = extract_code_section(response.content, "js")

    # Save files
    with open("index.html","w",encoding="utf-8") as f:
        f.write(html_code)

    with open("style.css","w",encoding="utf-8") as f:
        f.write(css_code)

    with open("script.js","w",encoding="utf-8") as f:
        f.write(js_code)

    # ZIP packaging
    with zipfile.ZipFile("website.zip","w") as z:
        z.write("index.html")
        z.write("style.css")
        z.write("script.js")

    st.download_button(
        "Click to download",
        data=open("website.zip","rb"),
        file_name="website.zip"
    )

    st.success("Portfolio website generated successfully!")
