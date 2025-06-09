"""
Konfiguracja panelu administracyjnego Django dla aplikacji 'biblioteka'.

Ten moduł dostosowuje domyślny panel admina, aby ułatwić zarządzanie
modelami aplikacji, takimi jak Książka, Czytelnik, Wypożyczenie, itp.
Wprowadza m.in. zagnieżdżone formularze, niestandardowe akcje,
pola wyszukiwania i filtry.
"""

import csv
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.utils import timezone
from .models import Ksiazka, Egzemplarz, Czytelnik, Wypozyczenie, Rezerwacja


class CzytelnikInline(admin.StackedInline):
    """
    Definiuje wbudowany (inline) formularz dla profilu Czytelnika.

    Umożliwia edycję powiązanego profilu Czytelnika bezpośrednio
    na stronie edycji obiektu User.
    """
    model = Czytelnik
    can_delete = False
    verbose_name_plural = 'Profil Czytelnika'
    # Określa pola, które będą widoczne w formularzu inline.
    fields = ('numer_karty_bibliotecznej', 'limit_wypozyczen')


class UserAdmin(BaseUserAdmin):
    """
    Rozszerza domyślną konfigurację panelu admina dla modelu User.

    Dodaje formularz CzytelnikInline do strony edycji użytkownika oraz
    dostosowuje wyświetlaną listę użytkowników.
    """
    inlines = (CzytelnikInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active')


# Wyrejestrowanie domyślnego UserAdmin i zarejestrowanie naszej niestandardowej wersji.
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(Czytelnik)
class CzytelnikAdmin(admin.ModelAdmin):
    """
    Konfiguracja panelu admina dla modelu Czytelnik.

    Została dodana głównie po to, aby umożliwić działanie pola
    'autocomplete_fields' w innych modelach, które mają relację
    do Czytelnika (np. w WypozyczenieAdmin).
    """
    list_display = ('user', 'numer_karty_bibliotecznej', 'limit_wypozyczen')
    # Definiuje pola, po których można wyszukiwać czytelników w panelu admina.
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'numer_karty_bibliotecznej')


@admin.register(Ksiazka)
class KsiazkaAdmin(admin.ModelAdmin):
    """Konfiguracja panelu admina dla modelu Ksiazka."""
    list_display = ('tytul', 'autor', 'kategoria', 'data_utworzenia')
    search_fields = ('tytul', 'autor', 'isbn')
    list_filter = ('kategoria', 'wydawnictwo', 'rok_wydania')


@admin.register(Egzemplarz)
class EgzemplarzAdmin(admin.ModelAdmin):
    """
    Konfiguracja panelu admina dla modelu Egzemplarz.

    Dodaje niestandardową kolumnę 'zarezerwowany_dla', aby pokazać,
    dla kogo oczekuje dany egzemplarz.
    """
    list_display = ('ksiazka', 'numer_inwentarzowy', 'status', 'zarezerwowany_dla', 'data_utworzenia')
    search_fields = ('numer_inwentarzowy', 'ksiazka__tytul', 'ksiazka__isbn')
    list_filter = ('status', 'ksiazka__kategoria')
    # Umożliwia wygodne wyszukiwanie i podpowiadanie książek przy tworzeniu/edycji egzemplarza.
    autocomplete_fields = ['ksiazka']

    def zarezerwowany_dla(self, obj):
        """
        Niestandardowa metoda do wyświetlania w list_display.

        Jeśli egzemplarz ma status 'oczekuje_na_odbior', znajduje powiązaną
        rezerwację i zwraca czytelnika, który na nią czeka.

        Args:
            obj (Egzemplarz): Instancja modelu Egzemplarz.

        Returns:
            str: Nazwa czytelnika lub '---', jeśli brak rezerwacji.
        """
        if obj.status == 'oczekuje_na_odbior':
            rezerwacja = Rezerwacja.objects.filter(
                ksiazka=obj.ksiazka,
                status='gotowa_do_odbioru'
            ).first()
            if rezerwacja:
                return rezerwacja.czytelnik
        return "---"
    zarezerwowany_dla.short_description = 'Zarezerwowany dla'


@admin.register(Wypozyczenie)
class WypozyczenieAdmin(admin.ModelAdmin):
    """
    Konfiguracja panelu admina dla modelu Wypozyczenie.

    Dodaje niestandardowe akcje oraz pole wyliczane 'is_przetrzymane_display'.
    """
    list_display = (
        'egzemplarz',
        'czytelnik',
        'data_wypozyczenia',
        'data_planowanego_zwrotu',
        'data_rzeczywistego_zwrotu',
        'oplata_za_przetrzymanie',
        'is_przetrzymane_display'
    )
    search_fields = ('egzemplarz__numer_inwentarzowy', 'czytelnik__user__last_name',
                     'czytelnik__numer_karty_bibliotecznej')
    list_filter = ('data_wypozyczenia', 'data_planowanego_zwrotu', 'data_rzeczywistego_zwrotu')
    autocomplete_fields = ['egzemplarz', 'czytelnik']
    actions = ['oznacz_jako_zwrocone_dzisiaj', 'eksportuj_do_csv']

    def oznacz_jako_zwrocone_dzisiaj(self, request, queryset):
        """
        Niestandardowa akcja panelu admina do masowego oznaczania zwrotów.

        Ustawia dzisiejszą datę jako datę zwrotu dla zaznaczonych,
        niezwróconych jeszcze wypożyczeń.
        """
        for wypozyczenie in queryset.filter(data_rzeczywistego_zwrotu__isnull=True):
            wypozyczenie.data_rzeczywistego_zwrotu = timezone.now().date()
            # Wywołanie save() uruchomi logikę biznesową z modelu, np. naliczenie opłat.
            wypozyczenie.save()
        self.message_user(request, "Zaznaczone wypożyczenia zostały oznaczone jako zwrócone dzisiaj.")
    oznacz_jako_zwrocone_dzisiaj.short_description = "Oznacz wybrane jako zwrócone dzisiaj"

    def eksportuj_do_csv(self, request, queryset):
        """Niestandardowa akcja panelu admina do eksportu danych do pliku CSV."""
        meta = self.model._meta
        field_names = [field.name for field in meta.fields]
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename={meta}.csv'
        writer = csv.writer(response)
        writer.writerow(field_names)
        for obj in queryset:
            row = writer.writerow([getattr(obj, field) for field in field_names])
        return response
    eksportuj_do_csv.short_description = "Eksportuj zaznaczone do CSV"

    def is_przetrzymane_display(self, obj):
        """
        Niestandardowa metoda do wyświetlania w list_display.

        Sprawdza, czy aktywne wypożyczenie jest po terminie zwrotu.
        """
        if obj.data_rzeczywistego_zwrotu is None and obj.data_planowanego_zwrotu:
            return "Tak" if timezone.now().date() > obj.data_planowanego_zwrotu else "Nie"
        return "Nie"
    is_przetrzymane_display.short_description = 'Przetrzymane?'
    is_przetrzymane_display.admin_order_field = 'data_planowanego_zwrotu'


@admin.register(Rezerwacja)
class RezerwacjaAdmin(admin.ModelAdmin):
    """

    Konfiguracja panelu admina dla modelu Rezerwacja.

    Dodaje niestandardową akcję pozwalającą na szybkie utworzenie
    wypożyczenia na podstawie rezerwacji gotowej do odbioru.
    """
    list_display = ('ksiazka', 'czytelnik', 'status', 'data_utworzenia', 'data_waznosci')
    list_filter = ('status', 'data_utworzenia', 'data_waznosci')
    search_fields = ('ksiazka__tytul', 'czytelnik__user__last_name')
    autocomplete_fields = ['ksiazka', 'czytelnik']
    actions = ['utworz_wypozyczenie_z_rezerwacji']

    def utworz_wypozyczenie_z_rezerwacji(self, request, queryset):
        """
        Niestandardowa akcja do zrealizowania rezerwacji.

        Tworzy obiekt Wypozyczenie na podstawie zaznaczonej rezerwacji,
        o ile spełnia ona odpowiednie warunki (jest jedna i ma status
        'gotowa_do_odbioru').
        """
        if queryset.count() != 1:
            self.message_user(request, "Proszę wybrać dokładnie jedną rezerwację do zrealizowania.", level='error')
            return

        rezerwacja = queryset.first()
        if rezerwacja.status != 'gotowa_do_odbioru':
            self.message_user(request, "Można utworzyć wypożyczenie tylko z rezerwacji 'gotowej do odbioru'.",
                              level='error')
            return

        # Znajdź egzemplarz, który został odłożony dla tej rezerwacji.
        odlozony_egzemplarz = Egzemplarz.objects.filter(
            ksiazka=rezerwacja.ksiazka,
            status='oczekuje_na_odbior'
        ).first()

        if not odlozony_egzemplarz:
            self.message_user(request,
                              f"Błąd: Nie znaleziono egzemplarza książki '{rezerwacja.ksiazka.tytul}' oczekującego na odbiór.",
                              level='error')
            return

        # Utworzenie wypożyczenia. Logika w Wypozyczenie.save() sama zaktualizuje
        # statusy rezerwacji i egzemplarza.
        Wypozyczenie.objects.create(
            czytelnik=rezerwacja.czytelnik,
            egzemplarz=odlozony_egzemplarz
        )
        self.message_user(request,
                          f"Pomyślnie utworzono wypożyczenie dla {rezerwacja.czytelnik}.",
                          level='success')
    utworz_wypozyczenie_z_rezerwacji.short_description = "Utwórz wypożyczenie z zaznaczonej rezerwacji"