"""
Formularze dla aplikacji biblioteka.

Ten moduł zawiera niestandardowe formularze używane w części publicznej aplikacji,
takie jak formularz rejestracji nowego czytelnika.
"""

import uuid

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Czytelnik


class RejestracjaCzytelnikaForm(UserCreationForm):
    """
    Niestandardowy formularz rejestracji dla nowych czytelników.

    Dziedziczy z domyślnego UserCreationForm i rozszerza go o dodatkowe pola
    oraz logikę, która automatycznie tworzy profil Czytelnika po utworzeniu
    konta User. Używa adresu e-mail jako loginu (username).
    """
    # Definicja pól, które użytkownik musi wypełnić w formularzu.
    first_name = forms.CharField(max_length=150, required=True, label="Imię")
    last_name = forms.CharField(max_length=150, required=True, label="Nazwisko")
    email = forms.EmailField(max_length=254, required=True, label="Adres e-mail",
                             help_text='Wymagane. Będzie służyć jako login.')

    class Meta(UserCreationForm.Meta):
        """
        Konfiguracja metadanych formularza.
        """
        model = User
        # Jawnie określamy, które pola z modelu User mają być widoczne.
        # Pomijamy pole 'username', ponieważ będzie ono generowane automatycznie.
        fields = ("first_name", "last_name", "email")

    def save(self, commit=True):
        """
        Nadpisuje domyślną metodę save, aby obsłużyć tworzenie Użytkownika i Czytelnika.

        Logika tej metody:
        1. Ustawia adres e-mail jako nazwę użytkownika (username).
        2. Zapisuje obiekt User.
        3. Generuje unikalny, 13-znakowy numer karty bibliotecznej.
        4. Tworzy powiązany profil Czytelnika.
        """
        # Krok 1: Zapisz obiekt User, ale jeszcze nie do bazy (commit=False).
        user = super().save(commit=False)

        # Krok 2: Ustaw dodatkowe atrybuty obiektu User z danych formularza.
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.email = self.cleaned_data["email"]
        user.username = self.cleaned_data["email"]  # Używamy e-maila jako loginu

        if commit:
            user.save()  # Zapisz obiekt User do bazy danych.

            # Krok 3: Wygeneruj unikalny numer karty bibliotecznej.
            # Pętla zapewnia unikalność, na wypadek ekstremalnie rzadkiej kolizji UUID.
            while True:
                numer_karty = uuid.uuid4().hex[:13].upper()
                if not Czytelnik.objects.filter(numer_karty_bibliotecznej=numer_karty).exists():
                    break  # Znaleziono wolny numer, wyjdź z pętli.

            # Krok 4: Stwórz i zapisz powiązany profil Czytelnika.
            Czytelnik.objects.create(
                user=user,
                numer_karty_bibliotecznej=numer_karty
            )
        return user