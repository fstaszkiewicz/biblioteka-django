# System Zarządzania Biblioteką w Django

![Django](https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white) ![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white) ![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)

## 📖 Opis Projektu
Aplikacja webowa napisana w frameworku Django, symulująca system informatyczny dla biblioteki. Umożliwia zarządzanie katalogiem książek i egzemplarzy, rejestrację czytelników, obsługę wypożyczeń oraz rezerwacji. Projekt zawiera również panel administracyjny z rozszerzonymi funkcjonalnościami oraz zestaw skryptów do automatyzacji zadań i analizy danych.

---

## ✨ Główne Funkcjonalności

Poniżej znajduje się szczegółowy opis kluczowych modułów i mechanizmów zaimplementowanych w aplikacji.

### 📚 Katalog Książek i Egzemplarzy
System rozróżnia abstrakcyjny byt **Książki** (tytuł, autor, ISBN) od jej fizycznych **Egzemplarzy** (konkretna kopia na półce).
- **Zarządzanie Książkami:** Pełne dane bibliograficzne, w tym kategoria, wydawnictwo, rok wydania i lokalizacja na półce.
- **Zarządzanie Egzemplarzami:** Każdy egzemplarz ma unikalny numer inwentarzowy i dynamicznie zarządzany status, który automatycznie zmienia się w zależności od akcji w systemie.

### 👤 System Użytkowników i Czytelników
Aplikacja bazuje na wbudowanym systemie uwierzytelniania Django, rozszerzonym o profil Czytelnika.
- **Rejestracja i Logowanie:** Użytkownicy mogą samodzielnie tworzyć konta. Proces rejestracji automatycznie tworzy powiązany profil czytelnika. E-mail służy jako nazwa użytkownika.
- **Profil Czytelnika:** Każdy użytkownik ma przypisany profil `Czytelnik`, który przechowuje unikalny numer karty bibliotecznej oraz indywidualny limit wypożyczeń (domyślnie 5).

### 🔄 Wypożyczenia i Zwroty (Logika Biznesowa)
Moduł wypożyczeń to serce aplikacji
- **Automatyzacja Procesu:** Przy tworzeniu wypożyczenia system automatycznie:
    - Ustawia datę planowanego zwrotu (domyślnie na 14 dni).
    - Waliduje, czy czytelnik nie przekroczył limitu aktywnych wypożyczeń.
    - Zmienia status egzemplarza na `Wypożyczony`.
- **Obsługa Zwrotów:** Przy rejestracji zwrotu:
    - System automatycznie oblicza i zapisuje opłatę za przetrzymanie, jeśli zwrot nastąpił po terminie (stawka 0.50 PLN/dzień).
    - Status egzemplarza jest aktualizowany. Jeśli na książkę czeka rezerwacja, egzemplarz otrzymuje status `Oczekuje na odbiór`. W przeciwnym razie staje się `Dostępny`.

### ⏳ System Rezerwacji i Kolejka
Użytkownicy mogą rezerwować książki, na które aktualnie nie ma dostępnych egzemplarzy.
- **Kolejka:** Rezerwacje działają w systemie "pierwszy w kolejce, pierwszy obsłużony".
- **Cykl życia rezerwacji:**
    1.  Użytkownik tworzy rezerwację (status `Oczekująca`).
    2.  Gdy ktoś zwróci egzemplarz danej książki, najstarsza rezerwacja automatycznie zmienia status na `Gotowa do odbioru`, a czytelnik ma 3 dni na odbiór książki.
    3.  Jeśli książka nie zostanie odebrana w terminie, komenda zarządzania `anuluj_przeterminowane` zmienia jej status na `Przeterminowana` i przekazuje egzemplarz następnej osobie w kolejce.

### 🛠️ Rozbudowany Panel Administratora
Domyślny panel admina Django został znacznie rozszerzony w celu ułatwienia pracy bibliotekarzowi.
- **Niestandardowe Widoki:** Wyświetlanie kluczowych, powiązanych danych bezpośrednio w listach (np. dla kogo zarezerwowany jest dany egzemplarz).
- **Zaawansowane Filtrowanie:** Możliwość filtrowania danych po statusach, datach i kategoriach.
- **Niestandardowe Akcje:** Dostępne akcje masowe, np. "Oznacz wybrane jako zwrócone dzisiaj" lub "Utwórz wypożyczenie z zaznaczonej rezerwacji".
- **Panel Statystyk:** Dedykowana strona `/statystyki/` prezentująca podstawowe dane o zasobach biblioteki oraz ranking TOP 5 najpopularniejszych książek.

### ⚙️ Automatyzacja Zadań (Komendy Zarządzania)
Projekt zawiera zestaw skryptów do uruchamiania z wiersza poleceń, przeznaczonych do okresowej konserwacji systemu (np. za pomocą crona).
- `sprawdz_przetrzymane`: Generuje raport o książkach przetrzymywanych po terminie.
- `wyslij_przypomnienia`: Informuje o zbliżających się terminach zwrotu.
- `anuluj_przeterminowane`: Automatycznie zarządza kolejką rezerwacji.

### 📊 Analiza i Wizualizacja Danych
Aplikacja posiada moduł do generowania analitycznych raportów wizualnych.
- **Raport Trendów:** Komenda `generuj_raport_trendow` przetwarza całą historię wypożyczeń za pomocą biblioteki `pandas`, a następnie, używając `matplotlib`, generuje wykres słupkowy.
- **Wynik:** Wykres przedstawia miesięczną liczbę wypożyczeń z podziałem na kategorie książek, co pozwala na identyfikację trendów czytelniczych w czasie. Plik graficzny jest zapisywany w folderze `raporty/`.

## 🚀 Instalacja i Uruchomienie
Aby uruchomić projekt lokalnie, postępuj zgodnie z poniższymi krokami:

1.  **Sklonuj repozytorium:**
    ```bash
    git clone https://github.com/fstaszkiewicz/django-biblioteka.git
    ```
    ```bash
    cd django-biblioteka
    ```

2.  **Stwórz i aktywuj wirtualne środowisko:**
    ```bash
    # Stworzenie środowiska
    python -m venv venv

    # Aktywacja (Windows)
    .\venv\Scripts\activate
    ```

3.  **Zainstaluj wymagane pakiety:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Zastosuj migracje**, aby stworzyć strukturę bazy danych:
    ```bash
    python manage.py migrate
    ```

5.  **Załaduj dane demonstracyjne z pliku `initial_data.json`:**
    > **Ważne:** Ten krok stworzy administratora, dwóch użytkowników, książki i aktywne wypożyczenia.
    ```bash
    python manage.py loaddata initial_data.json
    ```

6.  **Uruchom serwer deweloperski:**
    ```bash
    python manage.py runserver
    ```
    Aplikacja będzie dostępna pod adresem `http://127.0.0.1:8000/` i `http://127.0.0.1:8000/admin`.

---

## 🧪 Użytkowanie i Testowanie Systemu

Dzięki załadowaniu danych z pliku `initial_data.json`, system jest od razu gotowy do testowania z predefiniowanymi kontami i danymi.

### Dane do Logowania (Użytkownicy Demonstracyjni)

| Rola | Nazwa użytkownika / E-mail | Hasło |
| :--- | :--- | :--- |
| **Administrator** | `admin` | `admin` |
| **Czytelnik 1** | `anna@gmail.com` | `password123` |
| **Czytelnik 2** | `piotr@gmail.com` | `password123` |

> **Uwaga:** Hasła w pliku `initial_data.json` są zahashowane. Powyższe hasła zostały ustawione w pliku dla uproszczenia testów. Jeśli wystąpi problem z logowaniem, możesz zresetować hasło dla danego użytkownika za pomocą komendy `python manage.py changepassword <nazwa_uzytkownika>`.

### Panel Administratora
- **Adres:** `http://127.0.0.1:8000/admin/`
- **Logowanie:** Użyj danych konta **Administratora**.
- **Możliwości:**
    - Przeglądanie i zarządzanie wszystkimi danymi (książki, wypożyczenia, rezerwacje).
    - Dostęp do strony ze statystykami (`/statystyki/`).
    - Korzystanie z niestandardowych akcji (np. w panelu "Wypożyczenia").

### Strona dla Czytelników

Aby przetestować aplikację z perspektywy zwykłego użytkownika, masz dwie możliwości:

* **Logowanie na konto testowe:** Użyj danych jednego z czytelników, aby zobaczyć panel z historią wypożyczeń i rezerwacji.
    * **Użytkownik:** `anna@gmail.com` (hasło: `password123`)
    * **Użytkownik:** `piotr@gmail.com` (hasło: `password123`)

* **Rejestracja nowego konta:** Wejdź na stronę `/rejestracja/`, aby samodzielnie założyć konto i przetestować system od zera.

---

## 🛠️ Dostępne Komendy Zarządzania
Wszystkie komendy należy uruchamiać z głównego folderu projektu, przy aktywnym środowisku wirtualnym.

#### `sprawdz_przetrzymane`
Wyświetla w konsoli listę wszystkich aktywnych wypożyczeń po terminie zwrotu.
```bash
python manage.py sprawdz_przetrzymane
```

#### `anuluj_przeterminowane`
Anuluje rezerwacje "gotowe do odbioru", których termin ważności minął, i zwalnia egzemplarze.
```bash
python manage.py anuluj_przeterminowane
```

#### `wyslij_przypomnienia`
Symuluje w konsoli wysyłkę przypomnień o zbliżającym się terminie zwrotu.
```bash
# Użycie domyślne (sprawdza 3 dni w przód)
python manage.py wyslij_przypomnienia

# Użycie z własnym parametrem (sprawdza 7 dni w przód)
python manage.py wyslij_przypomnienia --dni 7
```

#### `generuj_raport_trendow`
Generuje raport graficzny (`.png`) i zapisuje go w folderze `raporty/`.
```bash
python manage.py generuj_raport_trendow
```
---

## Fabian Staszkiewicz 300142
