"""
Niestandardowa komenda zarządzania Django do anulowania przeterminowanych rezerwacji.

Skrypt ten jest przeznaczony do okresowego uruchamiania (np. za pomocą crona).
Jego zadaniem jest znalezienie rezerwacji ze statusem 'gotowa_do_odbioru',
których termin ważności minął, a następnie przetworzenie ich.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from biblioteka.models import Rezerwacja, Egzemplarz


class Command(BaseCommand):
    """Anuluje rezerwacje 'gotowe do odbioru', których termin ważności minął."""
    help = 'Anuluje rezerwacje "gotowe do odbioru", których termin ważności minął.'

    def handle(self, *args, **options):
        """Główna logika komendy."""
        self.stdout.write(self.style.NOTICE('Rozpoczynanie procesu anulowania przeterminowanych rezerwacji...'))

        dzisiaj = timezone.now().date()
        # Znajdź wszystkie rezerwacje, które są gotowe do odbioru i których data ważności minęła.
        przeterminowane_rezerwacje = Rezerwacja.objects.filter(
            status='gotowa_do_odbioru',
            data_waznosci__lt=dzisiaj
        )

        if not przeterminowane_rezerwacje.exists():
            self.stdout.write(self.style.SUCCESS('Nie znaleziono przeterminowanych rezerwacji do anulowania.'))
            return

        licznik_anulowanych = 0
        for rezerwacja in przeterminowane_rezerwacje:
            ksiazka = rezerwacja.ksiazka
            self.stdout.write(
                f"Przetwarzanie rezerwacji na '{ksiazka.tytul}' dla czytelnika: {rezerwacja.czytelnik}...")

            # Krok 1: Zmień status bieżącej rezerwacji na 'przeterminowana'.
            rezerwacja.status = 'przeterminowana'
            rezerwacja.save()
            licznik_anulowanych += 1

            # Krok 2: Znajdź egzemplarz, który był "odłożony" dla tej rezerwacji.
            odlozony_egzemplarz = Egzemplarz.objects.filter(
                ksiazka=ksiazka,
                status='oczekuje_na_odbior'
            ).first()

            if not odlozony_egzemplarz:
                # Sytuacja awaryjna - logujemy ostrzeżenie i kontynuujemy.
                self.stdout.write(self.style.WARNING(
                    f"OSTRZEŻENIE: Nie znaleziono egzemplarza 'oczekuje_na_odbior' dla książki '{ksiazka.tytul}'."))
                continue

            # Krok 3: Sprawdź, czy w kolejce czeka kolejna osoba na tę książkę.
            nastepna_rezerwacja = Rezerwacja.objects.filter(
                ksiazka=ksiazka,
                status='oczekujaca'
            ).order_by('data_utworzenia').first()

            if nastepna_rezerwacja:
                # Jeśli jest następna osoba, przypisz jej ten egzemplarz.
                nastepna_rezerwacja.status = 'gotowa_do_odbioru'
                nastepna_rezerwacja.data_waznosci = dzisiaj + timedelta(days=3)
                nastepna_rezerwacja.save()
                # Egzemplarz pozostaje w statusie 'oczekuje_na_odbior', ale teraz dla nowej osoby.
                self.stdout.write(self.style.SUCCESS(
                    f"  -> Rezerwacja anulowana. Egzemplarz przypisany do następnego czytelnika: {nastepna_rezerwacja.czytelnik}."))
            else:
                # Jeśli nikt więcej nie czeka, uwolnij egzemplarz.
                odlozony_egzemplarz.status = 'dostepny'
                odlozony_egzemplarz.save()
                self.stdout.write(self.style.SUCCESS(
                    f"  -> Rezerwacja anulowana. Egzemplarz '{odlozony_egzemplarz}' jest teraz dostępny."))

        self.stdout.write(self.style.SUCCESS(f'Zakończono. Anulowano łącznie {licznik_anulowanych} rezerwacji.'))