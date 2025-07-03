import streamlit as st
import PyPDF2
import docx
import os
from openai import OpenAI
from dotenv import load_dotenv

# Załaduj zmienne środowiskowe
load_dotenv()

# Pobierz klucz API z secrets lub .env
try:
    API_KEY = st.secrets["OPENAI_API_KEY"]
except:
    API_KEY = os.getenv("OPENAI_API_KEY")

if not API_KEY:
    st.error("❌ Nie znaleziono klucza API OpenAI. Dodaj go w ustawieniach aplikacji lub pliku .env.")
    st.stop()

# Konfiguracja klienta OpenAI
client = OpenAI(api_key=API_KEY)

# --- INTERFEJS ---
st.image("assets/images.png")
st.title("📄 Generator Spisu Treści")

st.info("⚠️ Dla efektywności aplikacja przetwarza maksymalnie pierwsze 30 i ostatnie 25 stron PDF. "
        "Pliki DOCX przetwarzane są w całości.")

uploaded_file = st.file_uploader("📂 Prześlij plik PDF lub DOCX", type=["pdf", "docx"])

# --- FUNKCJE ---
def extract_text_from_pdf(file):
    reader = PyPDF2.PdfReader(file)
    total_pages = len(reader.pages)
    text = ""

    for i in range(min(25, total_pages)):
        page = reader.pages[i].extract_text()
        if page:
            text += f"--- STRONA {i+1} ---\n{page}\n\n"

    if total_pages > 25:
        for i in range(max(total_pages - 25, 25), total_pages):
            page = reader.pages[i].extract_text()
            if page:
                text += f"--- STRONA {i+1} ---\n{page}\n\n"

    return text

def extract_text_from_docx(file):
    doc = docx.Document(file)
    return "\n".join(para.text for para in doc.paragraphs)

# Główny prompt
prompt = """
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

# --- GENEROWANIE ---
def generate_toc_with_memory():
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=st.session_state.chat_history,
        temperature=0.1,
        max_tokens=4096
    )
    message = response.choices[0].message.content
    st.session_state.chat_history.append({"role": "assistant", "content": message})
    return message

# --- LOGIKA ---
if uploaded_file:
    if 'extracted_text' not in st.session_state:
        if uploaded_file.type == "application/pdf":
            extracted_text = extract_text_from_pdf(uploaded_file)
        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            extracted_text = extract_text_from_docx(uploaded_file)
        else:
            st.error("❌ Obsługiwany jest tylko PDF lub DOCX.")
            st.stop()

        if not extracted_text.strip():
            st.error("⚠️ Nie udało się odczytać tekstu z pliku.")
            st.stop()

        st.session_state.extracted_text = extracted_text
        st.session_state.chat_history = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": extracted_text}
        ]
        st.session_state.generated_toc = ""

    st.subheader("📑 Wygenerowany spis treści")

    if st.button("📄 Generuj pierwszy fragment"):
        with st.spinner("🧠 Generuję spis treści..."):
            part = generate_toc_with_memory()
            st.session_state.generated_toc += part
            st.markdown(st.session_state.generated_toc, unsafe_allow_html=True)

    if st.session_state.generated_toc:
        if st.button("➕ Kontynuuj generowanie"):
            with st.spinner("🧠 Kontynuuję..."):
                st.session_state.chat_history.append({
                    "role": "user",
                    "content": "Kontynuuj generowanie spisu treści od miejsca, w którym zakończyłeś. Pamiętaj, żeby zachować ten sam format HTML."
                })
                part = generate_toc_with_memory()
                st.session_state.generated_toc += part
                st.markdown(st.session_state.generated_toc, unsafe_allow_html=True)

        if st.button("🔁 Wyczyść i zacznij od nowa"):
            for key in ['extracted_text', 'chat_history', 'generated_toc']:
                if key in st.session_state:
                    del st.session_state[key]
            st.experimental_rerun()
