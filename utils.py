import PyPDF2
import streamlit as st

def read_uploaded_file(uploaded_file):
    """Lit le contenu d'un fichier uploadé (PDF ou TXT)."""
    document_text = ""
    if uploaded_file is None:
        return ""
    try:
        if uploaded_file.type == "application/pdf":
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            document_text = "".join(page.extract_text() for page in pdf_reader.pages)
        elif uploaded_file.type == "text/plain":
            document_text = uploaded_file.getvalue().decode("utf-8")
    except Exception as e:
        st.error(f"Erreur lors de la lecture du fichier : {e}")
        return None
    return document_text