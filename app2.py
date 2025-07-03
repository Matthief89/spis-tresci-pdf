import streamlit as st
import PyPDF2
import docx
import os
from openai import OpenAI
from dotenv import load_dotenv

# === Inicjalizacja ===
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    st.error("Brak klucza OpenAI – dodaj do .env jako OPENAI_API_KEY.")
    st.stop()

# === Konfiguracja klienta OpenAI ===
client = OpenAI(api_key=API_KEY)

# === UI ===
st.title("📄 Generator Spisu Treści")
st.markdown("📝 Wczytaj PDF lub DOCX. W przypadku długich spisów treści, klikaj przycisk poniżej, by przetworzyć je fragmentami.")

uploaded_file = st.file_uploader("Prześlij plik", type=["pdf", "docx"])

# === Funkcje pomocnicze ===

def extract_text_from_pdf(file):
    reader = PyPDF2.PdfReader(file)
    pages = len(reader.pages)
    text = ""
    for i in range(min(30, pages)):
        text += reader.pages[i].extract_text() or ""
    if pages > 30:
        for i in range(max(pages - 25, 30), pages):
            text += reader.pages[i].extract_text() or ""
    return text

def extract_text_from_docx(file):
    doc = docx.Document(file)
    return "\n".join(p.text for p in doc.paragraphs)

def split_text(text, chunk_size=6000):
    words = text.split()
    chunks = []
    chunk = []
    current_size = 0

    for word in words:
        current_size += len(word) + 1
        chunk.append(word)
        if current_size >= chunk_size:
            chunks.append(" ".join(chunk))
            chunk = []
            current_size = 0
    if chunk:
        chunks.append(" ".join(chunk))
    return chunks

def get_prompt():
    return """
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

def generate_toc(chunk_text):
    messages = [
        {"role": "system", "content": get_prompt()},
        {"role": "user", "content": chunk_text}
    ]
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.1,
            max_tokens=4000
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ Błąd podczas generowania: {e}"

# === Stan aplikacji ===
if "chunks" not in st.session_state:
    st.session_state.chunks = []
if "current_index" not in st.session_state:
    st.session_state.current_index = 0
if "toc_html" not in st.session_state:
    st.session_state.toc_html = ""

# === Po wczytaniu pliku ===
if uploaded_file:
    if st.button("📤 Rozpocznij przetwarzanie"):
        if uploaded_file.type == "application/pdf":
            text = extract_text_from_pdf(uploaded_file)
        else:
            text = extract_text_from_docx(uploaded_file)

        chunks = split_text(text, chunk_size=6000)
        st.session_state.chunks = chunks
        st.session_state.current_index = 0
        st.session_state.toc_html = ""
        st.success(f"✅ Załadowano {len(chunks)} fragmentów do przetworzenia.")

# === Generuj kolejną część TOC ===
if st.session_state.chunks:
    if st.button("🚀 Wygeneruj kolejną część TOC"):
        idx = st.session_state.current_index
        if idx < len(st.session_state.chunks):
            chunk_text = st.session_state.chunks[idx]
            toc_part = generate_toc(chunk_text)
            st.session_state.toc_html += "\n" + toc_part
            st.session_state.current_index += 1
            st.success(f"✅ Przetworzono fragment {idx+1}/{len(st.session_state.chunks)}")
        else:
            st.info("🎉 Wszystkie fragmenty zostały przetworzone.")

# === Wyświetl wynik ===
if st.session_state.toc_html:
    st.subheader("📑 Spis Treści")
    st.markdown(st.session_state.toc_html, unsafe_allow_html=True)
