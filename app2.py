import streamlit as st
import PyPDF2
import docx
import os
from openai import OpenAI
from dotenv import load_dotenv

# --- Ładowanie zmiennych środowiskowych ---
load_dotenv()

try:
    API_KEY = st.secrets["OPENAI_API_KEY"]
except:
    API_KEY = os.getenv("OPENAI_API_KEY")

if not API_KEY:
    st.error("Nie znaleziono klucza API OpenAI. Dodaj go w ustawieniach aplikacji lub pliku .env")
    st.stop()

# --- UI ---
st.image("assets/images.png")
st.title("📄 Generator Spisu Treści")
st.info("Dla efektywności aplikacja przetwarza tylko część dokumentu. "
        "Jeśli spis treści zajmuje wiele stron, zostanie podzielony i zrekonstruowany.")

uploaded_file = st.file_uploader("📂 Prześlij plik PDF lub DOCX", type=["pdf", "docx"])

# --- Funkcje ---

def extract_text_from_pdf(file):
    reader = PyPDF2.PdfReader(file)
    total_pages = len(reader.pages)
    text = ""

    for i in range(min(30, total_pages)):
        page = reader.pages[i].extract_text()
        text += f"--- STRONA {i+1} ---\n{page if page else ''}\n\n"

    if total_pages > 30:
        for i in range(max(total_pages - 25, 30), total_pages):
            page = reader.pages[i].extract_text()
            text += f"--- STRONA {i+1} ---\n{page if page else ''}\n\n"

    return text

def extract_text_from_docx(file):
    doc = docx.Document(file)
    return "\n".join(para.text for para in doc.paragraphs)

def split_text_into_chunks(text, chunk_size=6000):
    paragraphs = text.split("\n")
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        if len(current_chunk) + len(para) > chunk_size:
            chunks.append(current_chunk)
            current_chunk = ""
        current_chunk += para + "\n"
    if current_chunk:
        chunks.append(current_chunk)
    return chunks

def generate_toc_with_gpt4o(chunk_text):
    client = OpenAI(api_key=API_KEY)

    prompt = """
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

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": prompt}, {"role": "user", "content": chunk_text}],
        temperature=0.1,
        max_tokens=4096  # bezpieczny limit
    )

    return response.choices[0].message.content


# --- Sesja do przechowywania wyników ---
if "toc_output" not in st.session_state:
    st.session_state.toc_output = ""
if "chunks_remaining" not in st.session_state:
    st.session_state.chunks_remaining = []


# --- Przetwarzanie pliku ---
if uploaded_file:
    with st.spinner("📖 Przetwarzanie pliku..."):
        if uploaded_file.type == "application/pdf":
            text = extract_text_from_pdf(uploaded_file)
        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            text = extract_text_from_docx(uploaded_file)
        else:
            st.error("❌ Obsługiwany jest tylko PDF lub DOCX.")
            st.stop()

        if text.strip():
            chunks = split_text_into_chunks(text)
            st.session_state.chunks_remaining = chunks
        else:
            st.error("⚠️ Nie udało się odczytać tekstu z pliku.")

# --- Generowanie spisu treści ---
if st.session_state.chunks_remaining:
    if st.button("🚀 Wygeneruj kolejną część spisu treści"):
        current_chunk = st.session_state.chunks_remaining.pop(0)
        with st.spinner("✍️ Generowanie fragmentu..."):
            toc_part = generate_toc_with_gpt4o(current_chunk)
            st.session_state.toc_output += "\n\n" + toc_part

# --- Wyświetlenie wyniku ---
if st.session_state.toc_output:
    st.subheader("📑 Wygenerowany Spis Treści")
    st.markdown(st.session_state.toc_output, unsafe_allow_html=True)

    if st.session_state.chunks_remaining:
        st.success("Część spisu treści została wygenerowana. Kliknij ponownie, aby kontynuować.")
    else:
        st.success("✅ Wszystkie części spisu treści zostały wygenerowane.")
