"""
Modele danych dla aplikacji biblioteka.

Ten moduł definiuje strukturę bazy danych dla systemu bibliotecznego,
w tym modele dla książek, egzemplarzy, czytelników, wypożyczeń i rezerwacji.
"""

import logging
from datetime import timedelta, date, datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)


class CzasZnacznikModel(models.Model):
    """
    Abstrakcyjny model bazowy dostarczający pola znaczników czasu.

    Model ten dodaje do każdego dziedziczącego modelu dwa pola:
    - `data_utworzenia`: automatycznie ustawiana przy tworzeniu obiektu.
    - `data_modyfikacji`: automatycznie aktualizowana przy każdym zapisie obiektu.
    """
    data_utworzenia = models.DateTimeField(auto_now_add=True, verbose_name="Data utworzenia")
    data_modyfikacji = models.DateTimeField(auto_now=True, verbose_name="Data modyfikacji")

    class Meta:
        abstract = True
        ordering = ['-data_utworzenia']


class Ksiazka(CzasZnacznikModel):
    """
    Reprezentuje tytuł książki w katalogu bibliotecznym, a nie fizyczny egzemplarz.
    """
    tytul = models.CharField(max_length=255, verbose_name="Tytuł książki")
    autor = models.CharField(max_length=255, verbose_name="Autor")
    wydawnictwo = models.CharField(max_length=200, verbose_name="Wydawnictwo", blank=True, null=True)
    rok_wydania = models.IntegerField(verbose_name="Rok wydania", blank=True, null=True)
    kategoria = models.CharField(max_length=100, verbose_name="Kategoria", blank=True, null=True)
    liczba_stron = models.IntegerField(verbose_name="Liczba stron", blank=True, null=True)
    lokalizacja_na_polce = models.CharField(max_length=100, verbose_name="Lokalizacja na półce", blank=True, null=True)

    # Walidator dla formatu numeru ISBN-13.
    isbn_validator = RegexValidator(
        regex=r'^(?:ISBN(?:-13)?:? )?(?=[0-9]{13}$|(?=(?:[0-9]+[- ]){4})[- 0-9]{17}$)97[89][- ]?[0-9]{1,5}[- ]?[0-9]+[- ]?[0-9]+[- ]?[0-9]$',
        message="Wprowadź poprawny 13-cyfrowy numer ISBN."
    )
    isbn = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="Numer ISBN",
        help_text="Podaj 13-cyfrowy numer ISBN (może zawierać myślniki lub spacje)",
        validators=[isbn_validator]
    )

    class Meta:
        verbose_name = "Książka"
        verbose_name_plural = "Książki"
        ordering = ['tytul', 'autor']

    def __str__(self):
        """Zwraca czytelną dla człowieka reprezentację obiektu książki."""
        return f"{self.tytul} - {self.autor}"

    @classmethod
    def ile_jest_ksiazek(cls):
        """Zwraca całkowitą liczbę tytułów książek w katalogu."""
        return cls.objects.count()


class Egzemplarz(CzasZnacznikModel):
    """
    Reprezentuje pojedynczy, fizyczny egzemplarz książki w bibliotece.
    Każdy egzemplarz jest powiązany z konkretnym tytułem (Ksiazka).
    """
    ksiazka = models.ForeignKey(Ksiazka, on_delete=models.CASCADE, related_name="egzemplarze", verbose_name="Książka")
    numer_inwentarzowy = models.CharField(max_length=50, unique=True, verbose_name="Numer inwentarzowy")

    STATUS_EGZEMPLARZA = [
        ('dostepny', 'Dostępny'),
        ('wypozyczony', 'Wypożyczony'),
        ('oczekuje_na_odbior', 'Oczekuje na odbiór'),
        ('w_naprawie', 'W naprawie'),
        ('zagubiony', 'Zagubiony'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_EGZEMPLARZA,
        default='dostepny',
        verbose_name="Status"
    )

    class Meta:
        verbose_name = "Egzemplarz"
        verbose_name_plural = "Egzemplarze"
        ordering = ['ksiazka', 'numer_inwentarzowy']

    def __str__(self):
        """Zwraca czytelną reprezentację egzemplarza, uwzględniając jego status."""
        return f"{self.ksiazka.tytul} (Egz. {self.numer_inwentarzowy}) - {self.get_status_display()}"


class Czytelnik(CzasZnacznikModel):
    """
    Profil czytelnika, rozszerzający wbudowany model User o dane biblioteczne.
    Każdy Czytelnik jest połączony relacją jeden-do-jednego z obiektem User.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="Użytkownik", related_name='czytelnik')
    numer_karty_bibliotecznej = models.CharField(max_length=50, unique=True, verbose_name="Numer karty bibliotecznej")
    limit_wypozyczen = models.IntegerField(default=5, verbose_name="Limit wypożyczeń")

    class Meta:
        verbose_name = "Czytelnik (Profil)"
        verbose_name_plural = "Czytelnicy (Profile)"
        ordering = ['user__last_name', 'user__first_name']

    def __str__(self):
        """Zwraca reprezentację czytelnika, używając danych z powiązanego modelu User."""
        return f"{self.user.first_name} {self.user.last_name} ({self.numer_karty_bibliotecznej})"

    def aktywne_wypozyczenia_count(self):
        """Zlicza aktywne wypożyczenia dla danego czytelnika."""
        return self.wypozyczenia.filter(data_rzeczywistego_zwrotu__isnull=True).count()


class Wypozyczenie(CzasZnacznikModel):
    """
    Reprezentuje transakcję wypożyczenia jednego egzemplarza przez jednego czytelnika.
    """
    egzemplarz = models.ForeignKey(Egzemplarz, on_delete=models.PROTECT, related_name="wypozyczenia",
                                   verbose_name="Egzemplarz")
    czytelnik = models.ForeignKey(Czytelnik, on_delete=models.PROTECT, related_name="wypozyczenia",
                                  verbose_name="Czytelnik")
    data_wypozyczenia = models.DateField(default=timezone.now, verbose_name="Data wypożyczenia")
    data_planowanego_zwrotu = models.DateField(verbose_name="Data planowanego zwrotu", blank=True, null=True)
    data_rzeczywistego_zwrotu = models.DateField(null=True, blank=True, verbose_name="Data rzeczywistego zwrotu")
    oplata_za_przetrzymanie = models.DecimalField(
        max_digits=7, decimal_places=2, default=0,
        verbose_name="Opłata za przetrzymanie [PLN]"
    )
    uwagi = models.TextField(blank=True, null=True, verbose_name="Uwagi")

    class Meta:
        verbose_name = "Wypożyczenie"
        verbose_name_plural = "Wypożyczenia"
        ordering = ['-data_wypozyczenia']

    def __str__(self):
        """Zwraca czytelną reprezentację wypożyczenia."""
        return f"'{self.egzemplarz}' wypożyczone przez {self.czytelnik} ({self.data_wypozyczenia})"

    def save(self, *args, **kwargs):
        """
        Nadpisana metoda save, implementująca kluczowe logiki biznesowe.

        Automatycznie obsługuje:
        1. Dla nowych wypożyczeń:
           - Ustawia datę planowanego zwrotu (+14 dni).
           - Waliduje, czy egzemplarz jest dostępny lub czeka na odbiór przez właściwą osobę.
           - Waliduje, czy czytelnik nie przekroczył limitu wypożyczeń.
        2. Przy zwrocie (ustawieniu daty rzeczywistego zwrotu):
           - Oblicza i zapisuje opłatę za przetrzymanie.
        3. Po zapisie:
           - Aktualizuje statusy powiązanych obiektów (Egzemplarz, Rezerwacja).
        """
        is_new = self.pk is None
        old_instance = None if is_new else Wypozyczenie.objects.get(pk=self.pk)

        # --- Logika wykonywana PRZED zapisem do bazy ---
        if is_new:
            if not self.data_planowanego_zwrotu:
                self.data_planowanego_zwrotu = self.data_wypozyczenia + timedelta(days=14)

            # Rozbudowana walidacja statusu egzemplarza (obsługuje rezerwacje)
            egzemplarz_status = self.egzemplarz.status
            if egzemplarz_status == 'dostepny':
                pass  # OK
            elif egzemplarz_status == 'oczekuje_na_odbior':
                try:
                    rezerwacja = Rezerwacja.objects.get(
                        ksiazka=self.egzemplarz.ksiazka,
                        czytelnik=self.czytelnik,
                        status='gotowa_do_odbioru'
                    )
                    self.aktywna_rezerwacja_do_zamkniecia = rezerwacja
                except Rezerwacja.DoesNotExist:
                    raise ValidationError("Ten egzemplarz oczekuje na odbiór przez innego czytelnika.")
            else:
                raise ValidationError(f"Egzemplarz '{self.egzemplarz}' nie jest dostępny (status: {self.egzemplarz.get_status_display()}).")

            # Walidacja limitu wypożyczeń
            if self.czytelnik.aktywne_wypozyczenia_count() >= self.czytelnik.limit_wypozyczen:
                raise ValidationError(f"Czytelnik {self.czytelnik} osiągnął już swój limit wypożyczeń.")

        # Oblicz opłatę, jeśli książka jest właśnie zwracana
        if self.data_rzeczywistego_zwrotu and (is_new or not old_instance.data_rzeczywistego_zwrotu):
            # Upewnij się, że porównujemy obiekty typu 'date'
            data_zwrotu_date = self.data_rzeczywistego_zwrotu
            if isinstance(data_zwrotu_date, datetime):
                data_zwrotu_date = data_zwrotu_date.date()

            data_planowana_date = self.data_planowanego_zwrotu
            if isinstance(data_planowana_date, datetime):
                data_planowana_date = data_planowana_date.date()

            if data_zwrotu_date > data_planowana_date:
                dni_zwloki = (data_zwrotu_date - data_planowana_date).days
                stawka_dzienna = Decimal('0.50')
                self.oplata_za_przetrzymanie = dni_zwloki * stawka_dzienna

        # --- Zapis głównego obiektu ---
        super(Wypozyczenie, self).save(*args, **kwargs)

        # --- Logika wykonywana PO zapisie ---
        if is_new:
            self.egzemplarz.status = 'wypozyczony'
            self.egzemplarz.save()
            if hasattr(self, 'aktywna_rezerwacja_do_zamkniecia'):
                rezerwacja = self.aktywna_rezerwacja_do_zamkniecia
                rezerwacja.status = 'zrealizowana'
                rezerwacja.save()
        elif self.data_rzeczywistego_zwrotu and not old_instance.data_rzeczywistego_zwrotu:
            # Logika zwrotu (obsługa kolejki rezerwacji)
            zwrocony_egzemplarz = self.egzemplarz
            ksiazka = zwrocony_egzemplarz.ksiazka
            najstarsza_rezerwacja = Rezerwacja.objects.filter(ksiazka=ksiazka, status='oczekujaca').order_by('data_utworzenia').first()
            if najstarsza_rezerwacja:
                najstarsza_rezerwacja.status = 'gotowa_do_odbioru'
                najstarsza_rezerwacja.data_waznosci = timezone.now().date() + timedelta(days=3)
                najstarsza_rezerwacja.save()
                zwrocony_egzemplarz.status = 'oczekuje_na_odbior'
                logger.info(
                    f"Książka '{ksiazka.tytul}' gotowa do odbioru dla czytelnika: {najstarsza_rezerwacja.czytelnik}. "
                    f"Rezerwacja ważna do: {najstarsza_rezerwacja.data_waznosci}."
                )
            else:
                zwrocony_egzemplarz.status = 'dostepny'
            zwrocony_egzemplarz.save()
        elif not self.data_rzeczywistego_zwrotu and old_instance and old_instance.data_rzeczywistego_zwrotu:
            # Logika anulowania zwrotu
            if self.egzemplarz.status != 'wypozyczony':
                self.egzemplarz.status = 'wypozyczony'
                self.egzemplarz.save()


class Rezerwacja(CzasZnacznikModel):
    """
    Reprezentuje rezerwację konkretnej książki przez czytelnika.
    Tworzy kolejkę oczekujących na dany tytuł.
    """
    ksiazka = models.ForeignKey(Ksiazka, on_delete=models.CASCADE, related_name="rezerwacje", verbose_name="Książka")
    czytelnik = models.ForeignKey(Czytelnik, on_delete=models.CASCADE, related_name="rezerwacje", verbose_name="Czytelnik")

    STATUS_REZERWACJI = [
        ('oczekujaca', 'Oczekująca'),
        ('gotowa_do_odbioru', 'Gotowa do odbioru'),
        ('zrealizowana', 'Zrealizowana'),
        ('anulowana', 'Anulowana'),
        ('przeterminowana', 'Przeterminowana'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_REZERWACJI,
        default='oczekujaca',
        verbose_name="Status rezerwacji"
    )
    data_waznosci = models.DateField(
        null=True, blank=True,
        verbose_name="Rezerwacja ważna do",
        help_text="Data, do której czytelnik powinien odebrać zarezerwowaną książkę."
    )

    class Meta:
        verbose_name = "Rezerwacja"
        verbose_name_plural = "Rezerwacje"
        ordering = ['data_utworzenia']

    def save(self, *args, **kwargs):
        """
        Waliduje, czy można utworzyć rezerwację na daną książkę.

        Rezerwacja jest możliwa tylko wtedy, gdy żaden egzemplarz
        danej książki nie jest aktualnie dostępny.
        """
        if self.pk is None:
            if self.ksiazka.egzemplarze.filter(status='dostepny').exists():
                raise ValidationError(
                    f"Nie można zarezerwować książki '{self.ksiazka.tytul}', "
                    f"ponieważ jest ona aktualnie dostępna na półce."
                )
        super(Rezerwacja, self).save(*args, **kwargs)

    def __str__(self):
        """Zwraca czytelną reprezentację rezerwacji."""
        return f"Rezerwacja na '{self.ksiazka.tytul}' przez {self.czytelnik}"