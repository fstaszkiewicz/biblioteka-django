"""
Niestandardowa komenda zarządzania Django do raportowania o przetrzymanych książkach.

Skrypt ten znajduje wszystkie aktywne wypożyczenia, których termin zwrotu minął,
a następnie generuje i wyświetla w konsoli raport na ich temat, włączając
w to potencjalną opłatę naliczoną na dzień uruchomienia skryptu.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
from biblioteka.models import Wypozyczenie


class Command(BaseCommand):
    """Znajduje wszystkie przetrzymane wypożyczenia i wyświetla raport."""
    help = 'Znajduje wszystkie przetrzymane wypożyczenia i wyświetla raport.'

    def handle(self, *args, **options):
        """Główna logika komendy."""
        self.stdout.write(self.style.NOTICE('Rozpoczynanie sprawdzania przetrzymanych wypożyczeń...'))

        dzisiaj = timezone.now().date()

        # Zapytanie do bazy o aktywne (niezwrócone) wypożyczenia po terminie.
        przetrzymane_wypozyczenia = Wypozyczenie.objects.filter(
            data_rzeczywistego_zwrotu__isnull=True,
            data_planowanego_zwrotu__lt=dzisiaj
        )

        if not przetrzymane_wypozyczenia.exists():
            self.stdout.write(self.style.SUCCESS('Brak przetrzymanych książek.'))
            return

        self.stdout.write(
            self.style.WARNING(f'Znaleziono {przetrzymane_wypozyczenia.count()} przetrzymanych wypożyczeń:'))

        # Przygotowanie danych do raportu.
        # Opłata jest tutaj obliczana tylko na potrzeby raportu, a nie zapisywana w bazie.
        for w in przetrzymane_wypozyczenia:
            dni_po_terminie = (dzisiaj - w.data_planowanego_zwrotu).days
            potencjalna_oplata = dni_po_terminie * Decimal('0.50')

            self.stdout.write(
                f"-> Czytelnik: {w.czytelnik} | "
                f"Książka: {w.egzemplarz} | "
                f"Dni po terminie: {dni_po_terminie} | "
                f"Naliczona opłata na dziś: {potencjalna_oplata:.2f} PLN"
            )

        self.stdout.write(self.style.SUCCESS('Zakończono raportowanie.'))