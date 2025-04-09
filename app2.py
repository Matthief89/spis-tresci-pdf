import streamlit as st
import PyPDF2
import os
from openai import OpenAI
from dotenv import load_dotenv

# Konfiguracja API (wprowadź swój klucz w .env lub w interfejsie Streamlit)
load_dotenv()  # załaduj zmienne środowiskowe z .env (działa lokalnie)

# Próbuj najpierw odczytać klucz z Streamlit secrets (działa na Streamlit Cloud)
try:
    API_KEY = st.secrets["OPENAI_API_KEY"]
except:
    # Jeśli nie znajdziesz w st.secrets, spróbuj z zmiennych środowiskowych
    API_KEY = os.getenv("OPENAI_API_KEY")

# Dodaj weryfikację, czy klucz API został znaleziony
if not API_KEY:
    st.error("Nie znaleziono klucza API OpenAI. Dodaj go w ustawieniach aplikacji lub pliku .env")
    st.stop()
    
st.image("assets/download.png", width=100)
st.title("📄 Generator Spisu Treści z PDF")

uploaded_file = st.file_uploader("📂 Prześlij plik PDF", type="pdf")

def extract_text_from_pdf(file):
    """Ekstrahuje tekst z pliku PDF"""
    reader = PyPDF2.PdfReader(file)
    text = ""
    for i, page in enumerate(reader.pages[:25]):  # Maksymalnie 25 stron
        text += f"--- STRONA {i+1} ---\n{page.extract_text()}\n\n"
    return text

def generate_toc_with_gpt4o(pdf_text):
    """Generuje spis treści za pomocą GPT-4o"""
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

3. Generuj kod HTML w tabeli <table>, stosując poniższy format. Na podstawie stylu spisu treści, dostosuj wcięcia w kodzie.
<table>
  <caption>Spis treści „NAZWA PUBLIKACJI”</caption>
  <tr>
    <th>Zawartość</th>
    <th>Nr strony</th>
  </tr>
  <tr>
    <td>Wykaz skrótów</td>
    <td>11</td>
  </tr>
  <tr>
    <td>Wprowadzenie</td>
    <td>15</td>
  </tr>
  <tr>
    <td>1. Kontekst badawczy</td>
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
        messages=[{"role": "system", "content": prompt}, {"role": "user", "content": pdf_text}],
        temperature=0.1,
        max_tokens=15000
    )
    
    return response.choices[0].message.content

if uploaded_file:
    with st.spinner("📖 Przetwarzanie pliku..."):
        pdf_text = extract_text_from_pdf(uploaded_file)

        if pdf_text.strip():
            toc = generate_toc_with_gpt4o(pdf_text)
            st.subheader("📑 Wygenerowany Spis Treści")
            st.markdown(toc, unsafe_allow_html=True)
        else:
            st.error("⚠️ Nie udało się odczytać tekstu z PDF.")
