"""
Konfiguracja aplikacji Django 'biblioteka'.

Ten plik zawiera klasę konfiguracyjną dla aplikacji, gdzie można
zdefiniować jej metadane i zachowanie.
"""

from django.apps import AppConfig


class BibliotekaConfig(AppConfig):
    """Klasa konfiguracyjna dla aplikacji 'biblioteka'."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'biblioteka'