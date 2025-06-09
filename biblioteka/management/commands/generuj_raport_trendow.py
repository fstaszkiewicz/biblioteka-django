import os
import pandas as pd
import matplotlib.pyplot as plt
from django.core.management.base import BaseCommand
from django.conf import settings
from biblioteka.models import Wypozyczenie

# python manage.py generuj_raport_trendow

class Command(BaseCommand):
    """
    Niestandardowa komenda do generowania raportu trendów czytelniczych.

    Analizuje historię wypożyczeń i tworzy wykres słupkowy pokazujący
    liczbę wypożyczeń w poszczególnych miesiącach z podziałem na kategorie książek.
    """
    help = 'Generuje raport trendów czytelniczych w postaci wykresu i zapisuje go do pliku.'

    def handle(self, *args, **options):
        """Główna logika komendy."""
        self.stdout.write(self.style.NOTICE("Rozpoczynanie generowania raportu trendów czytelniczych..."))

        # Krok 1: Pobranie danych z bazy za pomocą Django ORM.
        # Wybieramy tylko te pola, które są nam potrzebne.
        wypozyczenia_qs = Wypozyczenie.objects.select_related('egzemplarz__ksiazka').values(
            'data_wypozyczenia',
            'egzemplarz__ksiazka__kategoria'
        )

        if not wypozyczenia_qs.exists():
            self.stdout.write(self.style.WARNING("Brak danych o wypożyczeniach do analizy."))
            return

        # Krok 2: Przetwarzanie danych przy użyciu biblioteki Pandas.
        df = pd.DataFrame(list(wypozyczenia_qs))

        # Konwersja kolumny z datą na typ daty i wyodrębnienie miesiąca w formacie ROK-MIESIĄC.
        df['data_wypozyczenia'] = pd.to_datetime(df['data_wypozyczenia'])
        df['miesiac_wypozyczenia'] = df['data_wypozyczenia'].dt.to_period('M').astype(str)

        # Zmiana nazwy kolumny dla czytelności.
        df.rename(columns={'egzemplarz__ksiazka__kategoria': 'kategoria'}, inplace=True)

        # Krok 3: Agregacja danych.
        # Grupujemy dane po miesiącu i kategorii, a następnie liczymy liczbę wypożyczeń.
        # unstack() przekształca dane w tabelę przestawną idealną do wykresu.
        dane_aggr = df.groupby(['miesiac_wypozyczenia', 'kategoria']).size().unstack(fill_value=0)

        if dane_aggr.empty:
            self.stdout.write(self.style.WARNING("Nie udało się zagregować danych do wygenerowania wykresu."))
            return

        self.stdout.write("Dane przetworzone. Rozpoczynanie generowania wykresu...")

        # Krok 4: Generowanie wykresu za pomocą Matplotlib.
        plt.style.use('seaborn-v0_8-whitegrid') # Ustawienie stylu wykresu
        fig, ax = plt.subplots(figsize=(15, 8)) # Stworzenie figury i osi wykresu

        dane_aggr.plot(
            kind='bar',
            stacked=False,
            ax=ax,
            colormap='viridis' # Wybór palety kolorów
        )

        # Ustawienie tytułów i etykiet
        ax.set_title('Miesięczna liczba wypożyczeń z podziałem na kategorie', fontsize=16)
        ax.set_xlabel('Miesiąc', fontsize=12)
        ax.set_ylabel('Liczba wypożyczeń', fontsize=12)
        plt.xticks(rotation=45, ha='right') # Obrót etykiet osi X dla lepszej czytelności
        ax.legend(title='Kategorie')
        plt.tight_layout() # Dopasowanie wykresu, aby nic nie było ucięte

        # Krok 5: Zapis wykresu do pliku.
        # Stworzymy folder 'raporty', jeśli nie istnieje.
        raporty_dir = os.path.join(settings.BASE_DIR, 'raporty')
        os.makedirs(raporty_dir, exist_ok=True)

        nazwa_pliku = os.path.join(raporty_dir, 'raport_trendy_kategorie.png')
        plt.savefig(nazwa_pliku)

        self.stdout.write(self.style.SUCCESS(
            f"Pomyślnie wygenerowano raport! Wykres został zapisany w pliku: {nazwa_pliku}"
        ))