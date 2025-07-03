import streamlit as st
import PyPDF2
import docx
import os
from openai import OpenAI
from dotenv import load_dotenv

# Konfiguracja API (wprowadź swój klucz w .env lub w interfejsie Streamlit)
load_dotenv()  # załaduj zmienne środowiskowe z .env (działa lokalnie)

# Próbuj najpierw odczytać klucz z Streamlit secrets (działa na Streamlit Cloud)
try:
    API_KEY = st.secrets["OPENAI_API_KEY"]
except:
    API_KEY = os.getenv("OPENAI_API_KEY")

# Weryfikacja klucza API
if not API_KEY:
    st.error("Nie znaleziono klucza API OpenAI. Dodaj go w ustawieniach aplikacji lub pliku .env")
    st.stop()

# Nagłówek i UI
st.image("assets/images.png")
st.title("📄 Generator Spisu Treści")

st.info("Uwaga: Dla efektywności aplikacja przetwarza maksymalnie pierwsze 30 i ostatnie 25 stron PDF. "
        "Jeśli spis treści znajduje się głębiej, może nie zostać wykryty. Pliki DOCX przetwarzane są w całości.")

uploaded_file = st.file_uploader("📂 Prześlij plik PDF lub DOCX", type=["pdf", "docx"])

# Funkcja: PDF – przetwarza pierwsze i ostatnie 25 stron
def extract_text_from_pdf(file):
    reader = PyPDF2.PdfReader(file)
    total_pages = len(reader.pages)
    text = ""

    # Pierwsze 25 stron
    for i in range(min(25, total_pages)):
        text += f"--- STRONA {i+1} ---\n{reader.pages[i].extract_text()}\n\n"

    # Ostatnie 25 stron (bez powtórzeń)
    if total_pages > 25:
        for i in range(max(total_pages - 25, 25), total_pages):
            text += f"--- STRONA {i+1} ---\n{reader.pages[i].extract_text()}\n\n"

    return text

# Funkcja: DOCX – przetwarza cały dokument Worda
def extract_text_from_docx(file):
    doc = docx.Document(file)
    text = ""
    for para in doc.paragraphs:
        text += para.text + "\n"
    return text

# Funkcja: generowanie spisu treści przez GPT-4o
def generate_toc_with_gpt4o(pdf_text):
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
        messages=[{"role": "system", "content": prompt}, {"role": "user", "content": pdf_text}],
        temperature=0.1,
        max_tokens=16000
    )

    return response.choices[0].message.content

# Główna logika przetwarzania pliku
if uploaded_file:
    with st.spinner("📖 Przetwarzanie pliku..."):
        if uploaded_file.type == "application/pdf":
            extracted_text = extract_text_from_pdf(uploaded_file)
        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            extracted_text = extract_text_from_docx(uploaded_file)
        else:
            st.error("❌ Obsługiwany jest tylko PDF lub DOCX.")
            st.stop()

        if extracted_text.strip():
            toc = generate_toc_with_gpt4o(extracted_text)
            st.subheader("📑 Wygenerowany Spis Treści")
            st.markdown(toc, unsafe_allow_html=True)
        else:
            st.error("⚠️ Nie udało się odczytać tekstu z pliku.")
