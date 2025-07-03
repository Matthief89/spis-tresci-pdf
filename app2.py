import streamlit as st
import PyPDF2
import docx
import os
import io
from openai import OpenAI
from dotenv import load_dotenv

# Wczytaj zmienne środowiskowe
load_dotenv()

# Klucz API
try:
    API_KEY = st.secrets["OPENAI_API_KEY"]
except:
    API_KEY = os.getenv("OPENAI_API_KEY")

if not API_KEY:
    st.error("Nie znaleziono klucza API OpenAI. Dodaj go w ustawieniach aplikacji lub pliku .env")
    st.stop()

# Inicjalizacja klienta OpenAI
client = OpenAI(api_key=API_KEY)

# Nagłówek
st.image("assets/images.png")
st.title("📄 Generator Spisu Treści")

st.info("Dla efektywności aplikacja dzieli dokument PDF na bloki (np. po 10 stron) i pozwala użytkownikowi generować kolejne fragmenty spisu treści krok po kroku.")

uploaded_file = st.file_uploader("📂 Prześlij plik PDF lub DOCX", type=["pdf", "docx"])

# Funkcja: dzielenie PDF na bloki

def extract_text_blocks_from_pdf(file, block_size=10):
    reader = PyPDF2.PdfReader(file)
    total_pages = len(reader.pages)
    blocks = []

    for start in range(0, total_pages, block_size):
        end = min(start + block_size, total_pages)
        text = ""
        for i in range(start, end):
            page_text = reader.pages[i].extract_text()
            if page_text:
                text += f"--- STRONA {i+1} ---\n{page_text}\n\n"
        blocks.append(text)

    return blocks

# Funkcja: DOCX – cały dokument jako jeden blok

def extract_text_from_docx(file):
    doc = docx.Document(file)
    text = ""
    for para in doc.paragraphs:
        text += para.text + "\n"
    return text

# Funkcja: generowanie spisu treści przez GPT-4o

def generate_toc_with_gpt4o(text_block):
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

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": text_block}
        ],
        temperature=0.1,
        max_tokens=16000
    )

    return response.choices[0].message.content

# Stan aplikacji
if uploaded_file:
    if "current_block_index" not in st.session_state:
        st.session_state.current_block_index = 0
    if "text_blocks" not in st.session_state:
        if uploaded_file.type == "application/pdf":
            st.session_state.text_blocks = extract_text_blocks_from_pdf(uploaded_file, block_size=10)
        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            full_text = extract_text_from_docx(uploaded_file)
            st.session_state.text_blocks = [full_text]
        else:
            st.error("❌ Obsługiwany jest tylko PDF lub DOCX.")
            st.stop()
        st.session_state.toc_parts = []

    blocks = st.session_state.text_blocks
    idx = st.session_state.current_block_index

    if idx < len(blocks):
        with st.spinner(f"🔍 Generowanie spisu treści: blok {idx + 1}/{len(blocks)}..."):
            result = generate_toc_with_gpt4o(blocks[idx])
            st.session_state.toc_parts.append(result)
            st.session_state.current_block_index += 1

    st.subheader("📑 Wygenerowany Spis Treści (częściowy)")
    for part in st.session_state.toc_parts:
        st.markdown(part, unsafe_allow_html=True)

    if st.session_state.current_block_index < len(blocks):
        st.button("➡️ Kontynuuj generowanie", type="primary")
    else:
        full_html = "\n".join(st.session_state.toc_parts)
        st.success("✅ Spis treści został w pełni wygenerowany.")
        html_file = io.BytesIO(full_html.encode("utf-8"))
        st.download_button("📥 Pobierz pełny spis treści (HTML)", data=html_file, file_name="spis_tresci.html", mime="text/html")

    if st.button("🔄 Rozpocznij od nowa"):
        for key in ["text_blocks", "toc_parts", "current_block_index"]:
            if key in st.session_state:
                del st.session_state[key]
        st.experimental_rerun()
