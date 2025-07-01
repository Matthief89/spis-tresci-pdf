import streamlit as st
import PyPDF2
import os
import docx  # Dodajemy obsługę .docx
from openai import OpenAI
from dotenv import load_dotenv

# Wczytaj zmienne środowiskowe
load_dotenv()

# Pobierz klucz API z sekretnych danych Streamlit lub .env
try:
    API_KEY = st.secrets["OPENAI_API_KEY"]
except:
    API_KEY = os.getenv("OPENAI_API_KEY")

if not API_KEY:
    st.error("Nie znaleziono klucza API OpenAI. Dodaj go w ustawieniach aplikacji lub pliku .env")
    st.stop()

# UI
st.image("assets/images.png")
st.title("📄 Generator Spisu Treści z PDF i DOCX")

st.info("Uwaga: Dla PDF przetwarzane są maksymalnie pierwsze 25 stron. Jeśli spis treści znajduje się dalej, może nie zostać wykryty.")

uploaded_file = st.file_uploader("📂 Prześlij plik PDF lub DOCX", type=["pdf", "docx"])

# Funkcja: PDF
def extract_text_from_pdf(file):
    reader = PyPDF2.PdfReader(file)
    text = ""
    for i, page in enumerate(reader.pages[:25]):
        text += f"--- STRONA {i+1} ---\n{page.extract_text()}\n\n"
    return text

# Funkcja: DOCX
def extract_text_from_docx(file):
    doc = docx.Document(file)
    text = ""
    for i, para in enumerate(doc.paragraphs):
        text += para.text + "\n"
    return text

# Funkcja: GPT-4o do generowania TOC
def generate_toc_with_gpt4o(document_text):
    client = OpenAI(api_key=API_KEY)

    prompt = """
Instrukcja:
Jesteś asystentem AI, który pomaga użytkownikom generować kod HTML dla spisu treści na podstawie przesłanych plików PDF lub Word. Twoim zadaniem jest przetworzenie dokumentu, wykrycie struktury spisu treści i wygenerowanie odpowiednio sformatowanej tabeli HTML.

Zasady:
- Użyj tylko danych ze spisu treści zawartych w pliku.
- Nie dodawaj nic od siebie.
- Zastosuj strukturę HTML jak poniżej.
- Główne rozdziały oznacz <strong> i oddziel <tr><td> </td><td> </td></tr>.
- Jeśli spisu treści nie ma – poinformuj użytkownika, że nie udało się go wykryć.
- W <caption> dodaj nazwę publikacji i ewentualny podtytuł, jeśli istnieje.

Przykład:
<table>
  <caption>Spis treści „NAZWA PUBLIKACJI”</caption>
  <tr><th><strong>Zawartość</strong></th><th>Nr strony</th></tr>
  <tr><td><strong>1. Wprowadzenie</strong></td><td>1</td></tr>
  <tr><td>1.1 Tło problemu</td><td>2</td></tr>
  <tr><td>1.2 Cele badania</td><td>4</td></tr>
  <tr><td> </td><td> </td></tr>
</table>
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": document_text}
        ],
        temperature=0.1,
        max_tokens=15000
    )

    return response.choices[0].message.content

# Logika przetwarzania pliku
if uploaded_file:
    with st.spinner("📖 Przetwarzanie pliku..."):

        file_extension = uploaded_file.name.lower().split(".")[-1]
        if file_extension == "pdf":
            document_text = extract_text_from_pdf(uploaded_file)
        elif file_extension == "docx":
            document_text = extract_text_from_docx(uploaded_file)
        else:
            st.error("Obsługiwane są tylko pliki PDF i DOCX.")
            st.stop()

        if document_text.strip():
            toc = generate_toc_with_gpt4o(document_text)
            st.subheader("📑 Wygenerowany Spis Treści")
            st.markdown(toc, unsafe_allow_html=True)
        else:
            st.error("⚠️ Nie udało się odczytać tekstu z dokumentu.")
