"""
Widoki aplikacji 'biblioteka'.

Ten moduł zawiera funkcje (widoki), które obsługują logikę żądań HTTP.
Każda funkcja odpowiada za pobranie danych z modeli, przetworzenie ich
i przekazanie do szablonu HTML, który jest następnie renderowany
i odsyłany do przeglądarki użytkownika.
"""

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import render, redirect, get_object_or_404

from .forms import RejestracjaCzytelnikaForm
from .models import Ksiazka, Egzemplarz, Czytelnik, Wypozyczenie, Rezerwacja


@login_required
def strona_glowna(request):
    """
    Wyświetla stronę główną dla zalogowanego użytkownika.

    Strona ta działa jako pulpit, pokazując powiadomienia o książkach
    gotowych do odbioru, listę aktywnych wypożyczeń oraz rezerwacji
    w kolejce.
    """
    try:
        # Pobranie profilu czytelnika powiązanego z zalogowanym użytkownikiem.
        czytelnik = request.user.czytelnik
    except Czytelnik.DoesNotExist:
        # Jeśli użytkownik nie ma profilu (np. jest to konto admina bez profilu),
        # ustawiamy czytelnika na None, aby uniknąć błędów w szablonie.
        czytelnik = None

    powiadomienia, aktywne_wypozyczenia, oczekujace_rezerwacje = [], [], []

    if czytelnik:
        # Pobieranie danych specyficznych dla czytelnika.
        powiadomienia = Rezerwacja.objects.filter(czytelnik=czytelnik, status='gotowa_do_odbioru')
        aktywne_wypozyczenia = Wypozyczenie.objects.filter(
            czytelnik=czytelnik, data_rzeczywistego_zwrotu__isnull=True
        ).order_by('data_planowanego_zwrotu')
        oczekujace_rezerwacje = Rezerwacja.objects.filter(
            czytelnik=czytelnik, status='oczekujaca'
        ).order_by('data_utworzenia')

    context = {
        'title': 'Strona Główna',
        'powiadomienia': powiadomienia,
        'aktywne_wypozyczenia': aktywne_wypozyczenia,
        'oczekujace_rezerwacje': oczekujace_rezerwacje,
    }
    return render(request, 'biblioteka/strona_glowna.html', context)


@staff_member_required
def statystyki_view(request):
    """
    Wyświetla stronę ze statystykami biblioteki.

    Dostępna tylko dla personelu (staff). Pokazuje ogólne liczby
    oraz ranking 5 najczęściej wypożyczanych książek.
    """
    liczba_ksiazek = Ksiazka.objects.count()
    liczba_egzemplarzy = Egzemplarz.objects.count()
    liczba_czytelnikow = Czytelnik.objects.count()

    # Agregacja danych: grupowanie wypożyczeń po tytule książki,
    # zliczanie wystąpień i sortowanie, aby uzyskać najpopularniejsze.
    najpopularniejsze_ksiazki = Wypozyczenie.objects.values('egzemplarz__ksiazka__tytul') \
        .annotate(liczba_wypozyczen=Count('egzemplarz__ksiazka')) \
        .order_by('-liczba_wypozyczen')[:5]

    context = {
        'title': 'Statystyki Biblioteki',
        'liczba_ksiazek': liczba_ksiazek,
        'liczba_egzemplarzy': liczba_egzemplarzy,
        'liczba_czytelnikow': liczba_czytelnikow,
        'najpopularniejsze_ksiazki': najpopularniejsze_ksiazki,
    }
    return render(request, 'admin/statystyki.html', context)


def rejestracja_view(request):
    """
    Obsługuje proces rejestracji nowego czytelnika.

    Używa formularza RejestracjaCzytelnikaForm, który po pomyślnej
    walidacji tworzy jednocześnie obiekt User i powiązany z nim
    profil Czytelnika. Nowo zarejestrowany użytkownik jest
    automatycznie logowany.
    """
    if request.method == 'POST':
        form = RejestracjaCzytelnikaForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Rejestracja przebiegła pomyślnie. Witaj w bibliotece!")
            return redirect('strona-glowna')
    else:
        form = RejestracjaCzytelnikaForm()

    context = {
        'form': form,
        'title': 'Rejestracja nowego czytelnika'
    }
    return render(request, 'registration/rejestracja.html', context)


@login_required
def wyszukaj_view(request):
    """
    Obsługuje wyszukiwanie książek i wyświetla wyniki.

    Wyszukuje po tytule, autorze lub numerze ISBN. Dla każdego wyniku
    dodaje do kontekstu dodatkowe informacje, takie jak liczba dostępnych
    egzemplarzy czy najwcześniejsza data zwrotu, co jest wykorzystywane
    do budowania dynamicznego interfejsu w szablonie.
    """
    query = request.GET.get('q')
    wyniki = []

    if query:
        # Wyszukiwanie wielopolowe za pomocą obiektu Q.
        wyniki = Ksiazka.objects.filter(
            Q(tytul__icontains=query) |
            Q(autor__icontains=query) |
            Q(isbn__icontains=query)
        ).distinct()

        # Adnotacja wyników dodatkowymi danymi na potrzeby szablonu.
        for ksiazka in wyniki:
            ksiazka.dostepne_egzemplarze_count = ksiazka.egzemplarze.filter(status='dostepny').count()
            ksiazka.ma_juz_rezerwacje = ksiazka.rezerwacje.filter(
                czytelnik__user=request.user,
                status__in=['oczekujaca', 'gotowa_do_odbioru']
            ).exists()

            # Jeśli książka jest niedostępna, znajdź datę planowanego zwrotu
            # najbliższego egzemplarza.
            ksiazka.najwczesniejszy_zwrot = None
            if ksiazka.dostepne_egzemplarze_count == 0:
                najwczesniejsze_wypozyczenie = Wypozyczenie.objects.filter(
                    egzemplarz__ksiazka=ksiazka,
                    data_rzeczywistego_zwrotu__isnull=True
                ).order_by('data_planowanego_zwrotu').first()
                if najwczesniejsze_wypozyczenie:
                    ksiazka.najwczesniejszy_zwrot = najwczesniejsze_wypozyczenie.data_planowanego_zwrotu

    context = {
        'title': f'Wyniki wyszukiwania dla: "{query}"',
        'wyniki': wyniki,
        'query': query,
    }
    return render(request, 'biblioteka/wyniki_wyszukiwania.html', context)


@login_required
def rezerwuj_ksiazke_view(request, ksiazka_id):
    """
    Tworzy rezerwację na książkę dla zalogowanego użytkownika.

    Przed utworzeniem rezerwacji sprawdza warunki (np. czy książka nie jest
    dostępna, czy użytkownik już jej nie zarezerwował), aby zapobiec
    nieprawidłowym operacjom. Wykorzystuje system wiadomości Django
    do informowania użytkownika o wyniku operacji.
    """
    ksiazka = get_object_or_404(Ksiazka, id=ksiazka_id)
    czytelnik = request.user.czytelnik

    # Walidacja logiki biznesowej przed wykonaniem akcji.
    ma_juz_rezerwacje = Rezerwacja.objects.filter(
        ksiazka=ksiazka, czytelnik=czytelnik, status__in=['oczekujaca', 'gotowa_do_odbioru']
    ).exists()
    czy_dostepna = ksiazka.egzemplarze.filter(status='dostepny').exists()

    if ma_juz_rezerwacje:
        messages.warning(request, f"Masz już aktywną rezerwację na książkę '{ksiazka.tytul}'.")
    elif czy_dostepna:
        # Ten warunek jest również sprawdzany w Rezerwacja.save(), ale
        # dodanie go tutaj pozwala na wyświetlenie bardziej przyjaznego komunikatu.
        messages.warning(request, f"Nie można zarezerwować książki '{ksiazka.tytul}', ponieważ jest już dostępna.")
    else:
        Rezerwacja.objects.create(ksiazka=ksiazka, czytelnik=czytelnik)
        messages.success(request, f"Pomyślnie zarezerwowano książkę '{ksiazka.tytul}'.")

    return redirect('strona-glowna')


def wyloguj_view(request):
    """Wylogowuje użytkownika i przekierowuje go na stronę główną."""
    logout(request)
    messages.success(request, "Zostałeś pomyślnie wylogowany.")
    return redirect('strona-glowna')