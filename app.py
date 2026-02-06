import streamlit as st
import pdfplumber
from docx import Document
import spacy
import re
from langdetect import detect
import json
import os
from datetime import datetime

# Load NLP model
nlp = spacy.load("en_core_web_sm")

st.title("🧠 GenAI Legal Assistant for Indian SMEs")

# ---------------- TEXT EXTRACTION ----------------

def extract_text(file):

    if file.name.endswith(".pdf"):
        text = ""
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                if page.extract_text():
                    text += page.extract_text()
        return text

    elif file.name.endswith(".docx"):
        doc = Document(file)
        return "\n".join([p.text for p in doc.paragraphs])

    elif file.name.endswith(".txt"):
        return file.read().decode("utf-8")

    return ""

# ---------------- CLAUSE EXTRACTION ----------------

def extract_clauses(text):
    pattern = r"(Clause\s+\d+.*?)(?=Clause\s+\d+|$)"
    matches = re.findall(pattern, text, re.S | re.I)

    if not matches:
        matches = text.split("\n\n")

    return [m.strip() for m in matches if len(m.strip()) > 30]

# ---------------- RISK DETECTION ----------------

def detect_risk(clause):

    high = [
        "unlimited liability",
        "sole discretion",
        "irrevocable transfer",
        "automatic renewal",
        "indemnify and hold harmless"
    ]

    medium = [
        "penalty",
        "lock in period",
        "termination without notice"
    ]

    c = clause.lower()

    for h in high:
        if h in c:
            return "HIGH"

    for m in medium:
        if m in c:
            return "MEDIUM"

    return "LOW"

# ---------------- SCORE ----------------

def contract_score(risks):

    mapping = {"LOW":1, "MEDIUM":2, "HIGH":3}

    values = [mapping[r] for r in risks]

    if len(values)==0:
        return 0

    return round(sum(values)/len(values),2)

# ---------------- NER ----------------

def extract_entities(text):
    doc = nlp(text)
    return [(ent.text, ent.label_) for ent in doc.ents]

# ---------------- AUDIT LOG ----------------

def save_audit(score, clauses):

    log = {
        "time": str(datetime.now()),
        "risk_score": score,
        "total_clauses": clauses
    }

    if not os.path.exists("audit.json"):
        with open("audit.json","w") as f:
            json.dump([],f)

    with open("audit.json","r") as f:
        data = json.load(f)

    data.append(log)

    with open("audit.json","w") as f:
        json.dump(data,f,indent=2)

# ---------------- UI ----------------

file = st.file_uploader("Upload Contract", type=["pdf","docx","txt"])

if file:

    text = extract_text(file)

    st.subheader("📄 Contract Preview")
    st.write(text[:1000])

    lang = detect(text)
    st.info(f"Language Detected: {lang}")

    clauses = extract_clauses(text)

    st.subheader(f"✂ Clauses Found: {len(clauses)}")

    risks = []

    for c in clauses:
        r = detect_risk(c)
        risks.append(r)

        if r=="HIGH":
            st.error(c[:200])
        elif r=="MEDIUM":
            st.warning(c[:200])
        else:
            st.success(c[:200])

    score = contract_score(risks)

    st.subheader("📊 Contract Risk Score")
    st.metric("Risk Score", score)

    ents = extract_entities(text)

    st.subheader("🧬 Named Entities")
    st.write(ents[:20])

    save_audit(score, len(clauses))
