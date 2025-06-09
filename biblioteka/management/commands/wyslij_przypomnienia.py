"""
Niestandardowa komenda zarządzania Django do wysyłania przypomnień o terminie zwrotu.

Skrypt wyszukuje wypożyczenia, których termin zwrotu zbliża się
w ciągu określonej liczby dni, a następnie symuluje wysyłkę
powiadomień poprzez logowanie informacji w konsoli i do loggera.
"""
# python manage.py wyslij_przypomnienia (Domyślnie mniej niż 3 dni do minięcia terminu wypożyczenia)
# python manage.py wyslij_przypomnienia --dni 7 (powiadamia gdy termin wypożyczenia mija za mniej niż 7 dni)


import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from biblioteka.models import Wypozyczenie

# Użycie loggera pozwala na zapisywanie informacji do pliku lub innego strumienia,
# co jest lepszą praktyką niż samo drukowanie do konsoli.
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Wysyła przypomnienia o wypożyczeniach, których termin zwrotu wkrótce upływa."""
    help = 'Wysyła przypomnienia o wypożyczeniach, których termin zwrotu upływa w ciągu najbliższych N dni.'

    def add_arguments(self, parser):
        """Dodaje niestandardowy argument do komendy."""
        parser.add_argument(
            '--dni',
            type=int,
            default=3,
            help='Liczba dni do terminu zwrotu, dla których wysłać przypomnienia (domyślnie: 3).'
        )

    def handle(self, *args, **options):
        """Główna logika komendy."""
        dni_do_terminu = options['dni']
        self.stdout.write(self.style.NOTICE(f'Sprawdzanie wypożyczeń z terminem zwrotu w ciągu {dni_do_terminu} dni...'))

        dzisiaj = timezone.now().date()
        termin_graniczny = dzisiaj + timedelta(days=dni_do_terminu)

        # Znajdź aktywne wypożyczenia, których termin zwrotu mieści się w naszym oknie czasowym.
        # Warunek `__gte=dzisiaj` zapobiega wysyłaniu przypomnień dla książek już przetrzymanych.
        wypozyczenia_do_przypomnienia = Wypozyczenie.objects.filter(
            data_rzeczywistego_zwrotu__isnull=True,
            data_planowanego_zwrotu__gte=dzisiaj,
            data_planowanego_zwrotu__lte=termin_graniczny
        )

        if not wypozyczenia_do_przypomnienia.exists():
            self.stdout.write(self.style.SUCCESS('Brak wypożyczeń wymagających przypomnienia.'))
            return

        self.stdout.write(self.style.WARNING(f'Znaleziono {wypozyczenia_do_przypomnienia.count()} wypożyczeń do przypomnienia:'))

        # W pętli symulujemy wysyłkę powiadomień.
        for wypozyczenie in wypozyczenia_do_przypomnienia:
            wiadomosc = (
                f"PRZYPOMNIENIE DLA: {wypozyczenie.czytelnik}. "
                f"Termin zwrotu '{wypozyczenie.egzemplarz.ksiazka.tytul}' "
                f"upływa {wypozyczenie.data_planowanego_zwrotu}."
            )
            logger.info(wiadomosc)  # Zapis do logów
            self.stdout.write(f" -> Wysłano przypomnienie dla: {wypozyczenie.czytelnik} (termin: {wypozyczenie.data_planowanego_zwrotu})")

        self.stdout.write(self.style.SUCCESS('Zakończono wysyłanie przypomnień.'))