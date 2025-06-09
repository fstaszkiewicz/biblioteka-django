"""
Testy jednostkowe i integracyjne dla aplikacji 'biblioteka'.

Ten moduł zawiera zestaw testów weryfikujących poprawność działania
kluczowych komponentów aplikacji, w szczególności logiki biznesowej
zawartej w modelach.
"""

from django.test import TestCase
from django.utils import timezone
from .models import Ksiazka, Egzemplarz, Czytelnik, Wypozyczenie, Rezerwacja, User
from decimal import Decimal


class ModelCreationTest(TestCase):
    """Zestaw testów sprawdzających podstawowe tworzenie obiektów i ich reprezentacje."""

    def setUp(self):
        """Przygotowuje podstawowe obiekty potrzebne do testów."""
        self.user = User.objects.create_user(username='testuser@example.com', password='password')
        self.czytelnik = Czytelnik.objects.create(user=self.user, numer_karty_bibliotecznej="TESTCARD123")
        self.ksiazka = Ksiazka.objects.create(tytul="Testowa Książka", autor="Testowy Autor", isbn="9780000000001")

    def test_ksiazka_str_representation(self):
        """Testuje, czy metoda __str__ modelu Ksiazka zwraca poprawny format."""
        self.assertEqual(str(self.ksiazka), "Testowa Książka - Testowy Autor")

    def test_czytelnik_str_representation(self):
        """Testuje, czy metoda __str__ modelu Czytelnik zwraca poprawny format."""
        self.user.first_name = "Jan"
        self.user.last_name = "Kowalski"
        self.user.save()
        self.assertEqual(str(self.czytelnik), "Jan Kowalski (TESTCARD123)")


class WypozyczenieBusinessLogicTest(TestCase):
    """Zestaw testów dla zaawansowanej logiki biznesowej w modelu Wypozyczenie."""

    def setUp(self):
        """Przygotowuje obiekty do symulacji scenariuszy wypożyczeń i rezerwacji."""
        self.ksiazka = Ksiazka.objects.create(tytul="Książka do testów", autor="Autor", isbn="9789999999999")
        self.egzemplarz = Egzemplarz.objects.create(ksiazka=self.ksiazka, numer_inwentarzowy="TEST001")

        user1 = User.objects.create_user(username='czytelnik1@test.com', password='password')
        self.czytelnik1 = Czytelnik.objects.create(user=user1, numer_karty_bibliotecznej="KARTA1")

        user2 = User.objects.create_user(username='czytelnik2@test.com', password='password')
        self.czytelnik2 = Czytelnik.objects.create(user=user2, numer_karty_bibliotecznej="KARTA2")

    def test_zwrot_z_rezerwacja_w_tle(self):
        """
        Testuje scenariusz, w którym zwrot książki aktywuje rezerwację.

        Kroki:
        1. Czytelnik1 wypożycza książkę.
        2. Czytelnik2 rezerwuje tę książkę.
        3. Czytelnik1 zwraca książkę.
        Oczekiwany wynik:
        - Status egzemplarza zmienia się na 'oczekuje_na_odbior'.
        - Status rezerwacji Czytelnika2 zmienia się na 'gotowa_do_odbioru'.
        """
        # Krok 1: Wypożyczenie
        wypozyczenie = Wypozyczenie.objects.create(egzemplarz=self.egzemplarz, czytelnik=self.czytelnik1)
        self.assertEqual(Egzemplarz.objects.get(pk=self.egzemplarz.pk).status, 'wypozyczony')

        # Krok 2: Rezerwacja
        rezerwacja = Rezerwacja.objects.create(ksiazka=self.ksiazka, czytelnik=self.czytelnik2)
        self.assertEqual(rezerwacja.status, 'oczekujaca')

        # Krok 3: Zwrot
        wypozyczenie.data_rzeczywistego_zwrotu = timezone.now().date()
        wypozyczenie.save()

        # Asercje: Sprawdzenie stanu po operacji
        self.egzemplarz.refresh_from_db()
        rezerwacja.refresh_from_db()

        self.assertEqual(self.egzemplarz.status, 'oczekuje_na_odbior')
        self.assertEqual(rezerwacja.status, 'gotowa_do_odbioru')
        self.assertIsNotNone(rezerwacja.data_waznosci)

    def test_naliczanie_oplaty_za_przetrzymanie(self):
        """Testuje, czy opłata za przetrzymanie jest poprawnie naliczana przy zwrocie."""
        # Utwórz wypożyczenie z przeszłą datą planowanego zwrotu.
        data_wypozyczenia = timezone.now().date() - timezone.timedelta(days=20)
        data_plan_zwrotu = data_wypozyczenia + timezone.timedelta(days=14) # minęło 6 dni od terminu

        wypozyczenie = Wypozyczenie.objects.create(
            egzemplarz=self.egzemplarz,
            czytelnik=self.czytelnik1,
            data_wypozyczenia=data_wypozyczenia,
            data_planowanego_zwrotu=data_plan_zwrotu
        )

        # Symuluj zwrot w dniu dzisiejszym.
        wypozyczenie.data_rzeczywistego_zwrotu = timezone.now().date()
        wypozyczenie.save()

        dni_zwloki = (timezone.now().date() - data_plan_zwrotu).days
        oczekiwana_oplata = Decimal(dni_zwloki) * Decimal('0.50')

        self.assertEqual(wypozyczenie.oplata_za_przetrzymanie, oczekiwana_oplata)