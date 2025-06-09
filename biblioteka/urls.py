"""
Definicje adresów URL dla aplikacji 'biblioteka'.

Ten moduł mapuje konkretne ścieżki URL na odpowiednie funkcje widoków
(views), które obsługują żądania przychodzące pod te adresy.
"""

from django.urls import path
from . import views

# Nazwy URL (name='...') są używane w szablonach i widokach do dynamicznego
# generowania linków, co ułatwia zarządzanie i zmiany w przyszłości.
urlpatterns = [
    # Strona główna aplikacji.
    path('', views.strona_glowna, name='strona-glowna'),
    # Strona ze statystykami (dostępna dla personelu).
    path('statystyki/', views.statystyki_view, name='statystyki'),
    # Strona rejestracji nowego użytkownika.
    path('rejestracja/', views.rejestracja_view, name='rejestracja'),
    # Widok obsługujący wyszukiwanie książek.
    path('wyszukaj/', views.wyszukaj_view, name='wyszukaj'),
    # Widok do tworzenia rezerwacji na konkretną książkę.
    path('rezerwuj/<int:ksiazka_id>/', views.rezerwuj_ksiazke_view, name='rezerwuj'),
    # Widok do wylogowywania użytkownika.
    path('wyloguj/', views.wyloguj_view, name='wyloguj'),
]