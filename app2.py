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
except KeyError: # Zmieniono Exception na KeyError, bo to najbardziej typowy błąd gdy secret nie istnieje
    # Jeśli nie znajdziesz w st.secrets, spróbuj z zmiennych środowiskowych
    API_KEY = os.getenv("OPENAI_API_KEY")

# Dodaj weryfikację, czy klucz API został znaleziony
if not API_KEY:
    st.error("Nie znaleziono klucza API OpenAI. Dodaj go w ustawieniach aplikacji Streamlit (Secrets) lub pliku .env.")
    st.stop()
    
st.image("assets/images.png")
st.title("📄 Generator Spisu Treści z PDF")

st.info("Uwaga: Dla efektywności aplikacja przetwarza maksymalnie pierwsze 25 stron PDF. Jeśli Twój spis treści jest głębiej w dokumencie, może nie zostać wykryty.")

uploaded_file = st.file_uploader("📂 Prześlij plik PDF", type="pdf")

def extract_text_from_pdf(file):
    """Ekstrahuje tekst z pliku PDF"""
    try:
        reader = PyPDF2.PdfReader(file)
        text = ""
        # Przetwarzaj maksymalnie 25 stron, dodając oznaczenia stron
        for i, page in enumerate(reader.pages[:25]): 
            # Sprawdź, czy strona nie jest pusta, zanim spróbujesz ekstrahować tekst
            page_text = page.extract_text()
            if page_text:
                text += f"--- STRONA {i+1} ---\n{page_text}\n\n"
            else:
                text += f"--- STRONA {i+1} --- (brak tekstu)\n\n"
        return text
    except PyPDF2.errors.PdfReadError:
        st.error("Wystąpił błąd podczas odczytu pliku PDF. Upewnij się, że plik nie jest uszkodzony ani zaszyfrowany.")
        return None
    except Exception as e:
        st.error(f"Wystąpił nieoczekiwany błąd podczas przetwarzania PDF: {e}")
        return None

def generate_toc_with_gpt4o(pdf_text):
    """Generuje spis treści za pomocą GPT-4o"""
    client = OpenAI(api_key=API_KEY)

    prompt = """
    Instrukcja:
Jesteś asystentem AI, który pomaga użytkownikom generować kod HTML dla spisu treści na podstawie przesłanych plików PDF. Twoim zadaniem jest przetworzenie *dostarczonego tekstu z dokumentu*, wykrycie struktury spisu treści i wygenerowanie odpowiednio sformatowanej tabeli HTML. Przeanalizuj tekst pod kątem wielopoziomowej struktury i dokładnie rozpoznaj wszystkie poziomy hierarchii. Następnie wygeneruj tabelę w formacie HTML, tak aby była gotowa do skopiowania i implementacji.

Nigdy nie dodawaj żadnych dodatkowych komentarzy ani tekstu poza żądanym kodem HTML lub komunikatem o braku spisu treści. Nie zajmuj się frontendem. Pamiętaj żeby wygenerować cały spis treści a nie tylko kawałek. 

Nie dodawaj nic od siebie, korzystaj tylko z danych zawartych w pliku. Opieraj się tylko na spisie treści dostępnym w dostarczonym tekście. Zawsze generuj kompletną tabelę HTML w jednym bloku kodu.

Zachowaj pełną strukturę spisu treści, w tym wszystkie poziomy (rozdziały, podrozdziały). Upewnij się, że żaden element nie zostanie pominięty.

Poszczególne kroki:
1.Przyjmij tekst z pliku PDF i zlokalizuj zawarty w nim spis treści.

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

7. Jeśli spis treści nie jest dostępny w dostarczonym tekście – poinformuj użytkownika, zwracając jedynie ten komunikat: "Nie udało się wykryć spisu treści w przesłanym pliku PDF. Upewnij się, że spis treści jest czytelny i znajduje się w pierwszych 25 stronach dokumentu."

8. W miejscu "Nazwa Publikacji" umieść pełną nazwę książki. Dodaj również podtytuł jeśli istnieje.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": prompt}, {"role": "user", "content": pdf_text}],
            temperature=0.1,
            max_tokens=15000
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Wystąpił błąd podczas generowania spisu treści przez AI: {e}")
        st.info("Spróbuj ponownie lub upewnij się, że Twój klucz API jest prawidłowy.")
        return "Nie udało się wygenerować spisu treści z powodu błędu AI."


if uploaded_file:
    with st.spinner("📖 Przetwarzanie pliku..."):
        pdf_text = extract_text_from_pdf(uploaded_file)

        if pdf_text: # Sprawdź, czy w ogóle udało się wyodrębnić tekst
            # Opcja dla użytkownika, aby zobaczyć surowy tekst
            if st.checkbox("Pokaż wyodrębniony tekst (do debugowania)"):
                st.subheader("Wyodrębniony tekst z PDF")
                st.text_area("Tekst", pdf_text, height=300, help="To jest tekst, który został przekazany do modelu AI. Sprawdź, czy zawiera spis treści.")

            if pdf_text.strip(): # Sprawdź, czy tekst nie jest pusty po usunięciu białych znaków
                toc = generate_toc_with_gpt4o(pdf_text)
                st.subheader("📑 Wynik")
                
                # Sprawdź, czy model zwrócił komunikat o braku spisu treści
                if "nie udało się wykryć spisu treści w przesłanym pliku pdf" in toc.lower():
                    st.warning(toc) # Wyświetl komunikat od modelu
                else:
                    st.markdown(toc, unsafe_allow_html=True)
            else:
                st.error("⚠️ Nie udało się odczytać żadnego sensownego tekstu z przesłanego pliku PDF. Plik może być pusty, składać się wyłącznie z obrazów lub być uszkodzony.")
        else:
            st.error("⚠️ Przetwarzanie pliku PDF nie powiodło się. Sprawdź konsolę pod kątem szczegółów błędu.")
