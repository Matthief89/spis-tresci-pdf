import streamlit as st
import PyPDF2
import docx
import os
from openai import OpenAI
from dotenv import load_dotenv

# Konfiguracja API (wprowadź swój klucz w .env lub w interfejsie Streamlit)
load_dotenv()  # załaduj zmienne środowiskowe z .env (działa lokalnie)

try:
    API_KEY = st.secrets["OPENAI_API_KEY"]
except:
    API_KEY = os.getenv("OPENAI_API_KEY")

if not API_KEY:
    st.error("Nie znaleziono klucza API OpenAI. Dodaj go w ustawieniach aplikacji lub pliku .env")
    st.stop()

st.image("assets/images.png")
st.title("📄 Generator Spisu Treści")

st.info("Uwaga: Dla efektywności aplikacja przetwarza maksymalnie pierwsze 25 i ostatnie 25 stron PDF. "
        "Jeśli spis treści znajduje się głębiej, może nie zostać wykryty. Pliki DOCX przetwarzane są w całości.")

uploaded_file = st.file_uploader("📂 Prześlij plik PDF lub DOCX", type=["pdf", "docx"])

# Funkcje ekstrakcji tekstu
def extract_text_from_pdf(file):
    reader = PyPDF2.PdfReader(file)
    total_pages = len(reader.pages)
    text = ""

    for i in range(min(25, total_pages)):
        text += f"--- STRONA {i+1} ---\n{reader.pages[i].extract_text()}\n\n"

    if total_pages > 25:
        for i in range(max(total_pages - 25, 25), total_pages):
            text += f"--- STRONA {i+1} ---\n{reader.pages[i].extract_text()}\n\n"

    return text

def extract_text_from_docx(file):
    doc = docx.Document(file)
    text = ""
    for para in doc.paragraphs:
        text += para.text + "\n"
    return text

# Prompt do GPT
BASE_PROMPT = """
Instrukcja:
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

Jeśli wygenerujesz część spisu treści, dodaj na końcu tekst: "[KONTYNUUJ]", aby użytkownik mógł zażądać dalszej części.
"""

# Inicjalizacja klienta OpenAI
client = OpenAI(api_key=API_KEY)

# Funkcja generowania spisu treści - z obsługą kontynuacji
def generate_toc(messages):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.1,
        max_tokens=16000
    )
    return response.choices[0].message.content

# Inicjalizacja stanu sesji dla przechowywania wyników
if "toc_parts" not in st.session_state:
    st.session_state["toc_parts"] = []
if "extracted_text" not in st.session_state:
    st.session_state["extracted_text"] = ""
if "is_complete" not in st.session_state:
    st.session_state["is_complete"] = False

if uploaded_file:
    # Jeśli plik się zmienił, wyczyść stan
    if uploaded_file.name != st.session_state.get("last_uploaded", ""):
        st.session_state["toc_parts"] = []
        st.session_state["extracted_text"] = ""
        st.session_state["is_complete"] = False
        st.session_state["last_uploaded"] = uploaded_file.name

    if not st.session_state["extracted_text"]:
        with st.spinner("📖 Przetwarzanie pliku..."):
            if uploaded_file.type == "application/pdf":
                text = extract_text_from_pdf(uploaded_file)
            elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                text = extract_text_from_docx(uploaded_file)
            else:
                st.error("❌ Obsługiwany jest tylko PDF lub DOCX.")
                st.stop()

            if not text.strip():
                st.error("⚠️ Nie udało się odczytać tekstu z pliku.")
                st.stop()

            st.session_state["extracted_text"] = text

    # Jeśli brak jeszcze wygenerowanych części - generuj pierwszą
    if not st.session_state["toc_parts"]:
        with st.spinner("🤖 Generowanie spisu treści..."):
            messages = [
                {"role": "system", "content": BASE_PROMPT},
                {"role": "user", "content": st.session_state["extracted_text"]}
            ]
            part = generate_toc(messages)
            st.session_state["toc_parts"].append(part)
            # Jeśli w odpowiedzi nie ma [KONTYNUUJ], to znaczy, że mamy pełen wynik
            if "[KONTYNUUJ]" not in part.upper():
                st.session_state["is_complete"] = True

    # Wyświetlanie wyniku
    combined_toc = "\n".join(st.session_state["toc_parts"]).replace("[KONTYNUUJ]", "")
    st.subheader("📑 Wygenerowany Spis Treści")
    st.markdown(combined_toc, unsafe_allow_html=True)

    # Przycisk kontynuacji - widoczny tylko jeśli jest więcej do wygenerowania
    if not st.session_state["is_complete"]:
        if st.button("➡️ Kontynuuj generowanie spisu treści"):
            with st.spinner("🤖 Kontynuacja generowania spisu treści..."):
                messages = [
                    {"role": "system", "content": BASE_PROMPT},
                    {"role": "assistant", "content": "\n".join(st.session_state["toc_parts"])},
                    {"role": "user", "content": "Proszę kontynuuj generowanie spisu treści z miejsca, gdzie przerwano."}
                ]
                next_part = generate_toc(messages)
                st.session_state["toc_parts"].append(next_part)
                if "[KONTYNUUJ]" not in next_part.upper():
                    st.session_state["is_complete"] = True
                st.experimental_rerun()
