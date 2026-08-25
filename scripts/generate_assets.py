"""Generate sample_data/sample_resume.pdf and assets/architecture.png for the repo."""

import os

# ---------------------------------------------------------------- sample PDF
import pymupdf

RESUME_TEXT = """JANE SMITH
Python Backend Developer
jane.smith@email.com | linkedin.com/in/janesmith | github.com/janesmith

SUMMARY
Backend developer with 4 years of experience building REST APIs and
data-driven web applications with Python, Django, and PostgreSQL.

SKILLS
Python, Django, Django REST Framework, FastAPI (basic), PostgreSQL,
REST APIs, Git, GitHub Actions, Docker (learning), HTML/CSS

EXPERIENCE
Software Engineer — Cloudline Apps (2022 - Present)
- Built and maintained 12+ REST API endpoints in Django REST Framework
  serving 50k daily active users.
- Reduced average API response time by 35% via PostgreSQL query
  optimization and caching.
- Wrote CI pipelines with GitHub Actions running automated test suites.

Junior Developer — BrightSoft (2020 - 2022)
- Developed internal dashboards with Python and Flask.
- Collaborated in an agile team of six engineers.

PROJECTS
Ecommerce Order Service - Django + PostgreSQL service handling order
lifecycle with JWT authentication; deployed with Docker Compose.

Weather Analytics Dashboard - Flask app consuming third-party APIs,
charting trends with Plotly.

EDUCATION
Bachelor degree in Computer Science, State University (2016 - 2020)

CERTIFICATIONS
AWS Certified Cloud Practitioner (2023)
"""

os.makedirs("sample_data", exist_ok=True)
doc = pymupdf.open()
page = doc.new_page()  # A4 default
rect = page.rect
margins = pymupdf.Rect(rect.x0 + 48, rect.y0 + 40, rect.x1 - 48, rect.y1 - 40)
page.insert_textbox(margins, RESUME_TEXT, fontsize=9.5, fontname="helv")
doc.save("sample_data/sample_resume.pdf")
doc.close()
print("sample_data/sample_resume.pdf written")

# ------------------------------------------------------- architecture diagram
from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 780
img = Image.new("RGB", (W, H), "#0e1117")
d = ImageDraw.Draw(img)

try:
    font_b = ImageFont.truetype("arialbd.ttf", 22)
    font_s = ImageFont.truetype("arial.ttf", 15)
    font_t = ImageFont.truetype("arialbd.ttf", 30)
except OSError:
    font_b = font_s = font_t = ImageFont.load_default()


def box(x, y, w, h, title, sub="", fill="#1f2937", outline="#4F8BF9"):
    d.rounded_rectangle([x, y, x + w, y + h], radius=12, fill=fill, outline=outline, width=2)
    tb = d.textbbox((0, 0), title, font=font_b)
    d.text((x + w / 2 - (tb[2] - tb[0]) / 2, y + h / 2 - 18), title, fill="white", font=font_b)
    if sub:
        sb = d.textbbox((0, 0), sub, font=font_s)
        d.text((x + w / 2 - (sb[2] - sb[0]) / 2, y + h / 2 + 8), sub, fill="#8b95a5", font=font_s)


def arrow(x1, y1, x2, y2):
    d.line([x1, y1, x2, y2], fill="#4F8BF9", width=3)
    d.polygon([(x2, y2), (x2 - 8, y2 - 12), (x2 + 8, y2 - 12)], fill="#4F8BF9")


title = "ResumeIQ — Architecture"
tb = d.textbbox((0, 0), title, font=font_t)
d.text((W / 2 - (tb[2] - tb[0]) / 2, 24), title, fill="#4F8BF9", font=font_t)

# Layer 1: inputs
box(90, 100, 300, 70, "📄 Resume Upload", "PDF / TXT")
box(810, 100, 300, 70, "💼 Job Description", "Paste / Upload")

# Layer 2: parsers
box(90, 230, 300, 70, "PyMuPDF Parser", "text extraction")
box(810, 230, 300, 70, "JD Parser", "section detection")

# Layer 3: processing
box(450, 360, 300, 70, "Text Cleaning", "normalize + sections")

# Layer 4: engines
box(150, 490, 380, 80, "Deterministic Engine", "ATS scoring · skill gap · pandas")
box(670, 490, 380, 80, "Gemini AI Engine", "semantic analysis · critic · JSON")

# Layer 5: outputs
box(250, 650, 700, 70, "📊 Interactive Streamlit Dashboard",
    "KPIs · charts · recommendations · interview prep")

arrow(240, 170, 240, 230)
arrow(960, 170, 960, 230)
arrow(240, 300, 520, 360)
arrow(960, 300, 680, 360)
arrow(600, 430, 340, 490)
arrow(600, 430, 860, 490)
arrow(340, 570, 480, 650)
arrow(860, 570, 720, 650)

os.makedirs("assets", exist_ok=True)
img.save("assets/architecture.png")
print("assets/architecture.png written")
