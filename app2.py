import streamlit as st
import PyPDF2
import docx
import os
from openai import OpenAI
from dotenv import load_dotenv

# Konfiguracja API
load_dotenv()
try:
    API_KEY = st.secrets["OPENAI_API_KEY"]
except:
    API_KEY = os.getenv("OPENAI_API_KEY")

if not API_KEY:
    st.error("Nie znaleziono klucza API OpenAI. Dodaj go w ustawieniach aplikacji lub pliku .env")
    st.stop()

client = OpenAI(api_key=API_KEY)

# Stan aplikacji
if 'toc_partial' not in st.session_state:
    st.session_state['toc_partial'] = ""
if 'previous_text' not in st.session_state:
    st.session_state['previous_text'] = ""
if 'last_page_processed' not in st.session_state:
    st.session_state['last_page_processed'] = 0
if 'uploaded_file' not in st.session_state:
    st.session_state['uploaded_file'] = None

# UI
st.image("assets/images.png")
st.title("📄 Generator Spisu Treści")

st.info("Aplikacja przetwarza maksymalnie pierwsze 50 i ostatnie 50 stron PDF. Pliki DOCX są przetwarzane w całości.")

uploaded_file = st.file_uploader("📂 Prześlij plik PDF lub DOCX", type=["pdf", "docx"])

if uploaded_file:
    st.session_state['uploaded_file'] = uploaded_file

# Ekstrakcja tekstu z PDF

def extract_text_from_pdf(file, start_page=0, end_page=None):
    reader = PyPDF2.PdfReader(file)
    total_pages = len(reader.pages)
    text = ""
    end_page = end_page or total_pages

    for i in range(start_page, min(end_page, total_pages)):
        page = reader.pages[i].extract_text()
        if page:
            text += f"--- STRONA {i+1} ---\n{page}\n\n"
    return text

# Ekstrakcja tekstu z DOCX

def extract_text_from_docx(file):
    doc = docx.Document(file)
    return "\n".join([p.text for p in doc.paragraphs])

# Prompt bazowy
prompt_base = """
Instrukcja:
Jesteś asystentem AI, który pomaga użytkownikom generować kod HTML dla spisu treści na podstawie przesłanych plików PDF lub DOCX. Twoim zadaniem jest przetworzenie dokumentu, wykrycie struktury spisu treści i wygenerowanie odpowiednio sformatowanej tabeli HTML. Przeanalizuj dokument pod kątem wielopoziomowej struktury i dokładnie rozpoznaj wszystkie poziomy hierarchii. Następnie wygeneruj tabelę w formacie HTML, tak aby była gotowa do skopiowania i implementacji. Nie zajmuj się frontendem. Pamiętaj żeby wygenerować cały spis treści a nie tylko kawałek.

Nie dodawaj nic od siebie, korzystaj tylko z danych zawartych w pliku. Opieraj się tylko na spisie treści dostępnym w pliku. Zawsze generuj kompletną tabelę HTML w jednym bloku kodu.

Zachowaj pełną strukturę spisu treści, w tym wszystkie poziomy (rozdziały, podrozdziały). Upewnij się, że żaden element nie zostanie pominięty.

Poszczególne kroki:
1. Przyjmij plik PDF lub DOCX i zlokalizuj zawarty w nim spis treści.
2. Rozpoznaj spis treści, identyfikując:
   - Tytuły sekcji i podsekcji
   - Numery stron
   - Strukturę hierarchiczną (np. rozdziały, podrozdziały)
   - Przy numerze rozdziału dodaj jego pełną nazwę.
3. Generuj kod HTML w tabeli <table>, stosując poniższy format. Na podstawie stylu spisu treści, dostosuj wcięcia w kodzie.
   Tylko główne rozdziały umieść w znaczniki <strong></strong> oraz dodaj puste wiersze <tr><td> </td><td> </td></tr> po każdym z nich.
<table>
  <caption>Spis treści „NAZWA PUBLIKACJI”</caption>
  <tr>
    <th><strong>Zawartość</strong></th>
    <th>Nr strony</th>
  </tr>
  <tr>
    <td><strong>Wykaz skrótów</strong></td>
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

4. Nie dodawaj stylów CSS – użytkownik może samodzielnie sformatować tabelę.
5. Nie zmieniaj nazw rozdziałów i stron – zachowaj je dokładnie tak, jak w PDF lub DOCX.
6. Zachowaj hierarchię tytułów.
7. Jeśli spis treści nie jest dostępny – poinformuj użytkownika, że nie udało się go wykryć.
8. W miejscu "Nazwa Publikacji" umieść pełną nazwę książki. Dodaj również podtytuł jeśli istnieje.
"""

# Generowanie spisu treści

def generate_toc(prompt):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": prompt_base},
                  {"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=16000
    )
    return response.choices[0].message.content

# Pierwsze przetwarzanie pliku
if st.session_state['uploaded_file'] and st.session_state['last_page_processed'] == 0:
    with st.spinner("📖 Przetwarzanie pliku..."):
        file = st.session_state['uploaded_file']

        if file.type == "application/pdf":
            text = extract_text_from_pdf(file, 0, 50)
        elif file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            text = extract_text_from_docx(file)
        else:
            st.error("❌ Obsługiwany jest tylko PDF lub DOCX.")
            st.stop()

        if text.strip():
            toc = generate_toc(text)
            st.session_state['toc_partial'] = toc
            st.session_state['previous_text'] = text
            st.session_state['last_page_processed'] = 50
            st.subheader("📑 Wygenerowany Spis Treści")
            st.markdown(toc, unsafe_allow_html=True)
        else:
            st.error("⚠️ Nie udało się odczytać tekstu z pliku.")

# Kontynuacja
if st.session_state['last_page_processed'] > 0:
    if st.button("📎 Kontynuuj"):
        with st.spinner("🔄 Przetwarzanie kolejnych stron..."):
            file = st.session_state['uploaded_file']
            last = st.session_state['last_page_processed']
            new_text = extract_text_from_pdf(file, last, last + 50)

            if not new_text.strip():
                st.warning("Nie znaleziono więcej tekstu do przetworzenia.")
                st.stop()

            followup_prompt = f"Kontynuuj spis treści na podstawie dodatkowego fragmentu dokumentu. Nie powtarzaj poprzednich pozycji.\n\n{new_text}"

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": prompt_base},
                    {"role": "user", "content": st.session_state['previous_text']},
                    {"role": "assistant", "content": st.session_state['toc_partial']},
                    {"role": "user", "content": followup_prompt},
                ],
                temperature=0.1,
                max_tokens=16000
            )

            new_toc = response.choices[0].message.content
            st.session_state['toc_partial'] += "\n" + new_toc
            st.session_state['previous_text'] += "\n" + new_text
            st.session_state['last_page_processed'] += 50

            st.subheader("📑 Uzupełniony Spis Treści")
            st.markdown(st.session_state['toc_partial'], unsafe_allow_html=True)
