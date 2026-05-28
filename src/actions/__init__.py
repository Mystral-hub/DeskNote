"""Actions module for DeskNote — bureau automation tasks."""

from .live_typing import live_typing
from .creer_facture import creer_facture
from .ouvrir_app import ouvrir_app
from .supprimer_fichier import supprimer_fichier
from .creer_fichier_texte import creer_fichier_texte
from .lire_document import lire_document
from .recherche_en_ligne import recherche_en_ligne
from .organiser_fichiers import organiser_fichiers
from .changer_fond_ecran import changer_fond_ecran
from .lancer_media import lancer_media
from .rechercher_fichier import rechercher_fichier_action

__all__ = [
    "live_typing",
    "creer_facture",
    "ouvrir_app",
    "supprimer_fichier",
    "creer_fichier_texte",
    "lire_document",
    "recherche_en_ligne",
    "organiser_fichiers",
    "changer_fond_ecran",
    "lancer_media",
    "rechercher_fichier_action",
]
