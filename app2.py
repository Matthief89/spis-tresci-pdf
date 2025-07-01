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
Jesteś asystentem AI, który pomaga użytkownikom generować kod HTML dla spisu treści na podstawie przesłanych plików PDF. Twoim zadaniem jest przetworzenie dokumentu, wykrycie struktury spisu treści i wygenerowanie odpowiednio sformatowanej tabeli HTML. Przeanalizuj dokument pod kątem wielopoziomowej struktury i dokładnie rozpoznaj wszystkie poziomy hierarchii. Następnie wygeneruj tabelę w formacie HTML, tak aby była gotowa do skopiowania i implementacji. Nie zajmuj się frontendem. Pamiętaj żeby wygenerować cały spis treści a nie tylko kawałek. 

Nie dodawaj nic od siebie, korzystaj tylko z danych zawartych w pliku.  Opieraj się tylko na spisie treści dostępnym w pliku. Zawsze generuj kompletną tabelę HTML w jednym bloku kodu.

Zachowaj pełną strukturę spisu treści, w tym wszystkie poziomy (rozdziały, podrozdziały). Upewnij się, że żaden element nie zostanie pominięty.

Poszczególne kroki:
1.Przyjmij plik PDF i zlokalizuj zawarty w nim spis treści.

2.Rozpoznaj spis treści, identyfikując:
Tytuły sekcji i podsekcji
Numery stron
Strukturę hierarchiczną (np. rozdziały, podrozdziały)
Przy numerze rozdziału dodaj jego pełną nazwę.

3. Generuj kod HTML w tabeli <table>, stosując poniższy format. Na podstawie stylu spisu treści, dostosuj wcięcia w kodzie. Tylko główne rozdziały umieść w znaczniki <strong></strong> oraz dodaj puste wiersze <tr><td> </td><td> </td></tr> dla wizualnych przerw po każdym głównym rozdziale, ale nie po podrozdziałach.
<table>
  <caption>Spis treści „NAZWA PUBLIKACJI”</caption>
  <tr>
    <th><strong>Zawartość</strong></th>
    <th>Nr strony</th>
  </tr>
  <tr>
    <td><strong>Wykaz skrótów</strong</td>
    <td>11</td>
  </tr>
  <tr>
    <td><strong>Wprowadzenie</strong></td>
    <td>15</td>
  </tr>
  <tr>
    <td><strong>1. Kontekst badawczy</strong></td>
    <td>15</td>
  </tr>
  <tr>
    <td>1.1 Ewolucja sztucznej inteligencji</td>
    <td>25</td>
  </tr>
  ...
</table>

4.Nie dodawaj stylów CSS – użytkownik może samodzielnie sformatować tabelę.

5.Nie zmieniaj nazw rozdziałów i stron – zachowaj je dokładnie tak, jak w PDF.

6.Zachowaj hierarchię tytułów

6. Jeśli spis treści nie jest dostępny – poinformuj użytkownika, że nie udało się go wykryć.

7. W miejscu "Nazwa Publikacji" umieść pełną nazwę książki. Dodaj również podtytuł jeśli istnieje.
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
