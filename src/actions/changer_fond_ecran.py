import ctypes
from utils import (
    nettoyer_nom_fichier,
    nettoyer_valeur,
    resoudre_chemin,
    rechercher_fichier,
)

from pathlib import Path


def changer_fond_ecran(parametres: dict, resolve_executable_func) -> dict:
    nom_fichier = nettoyer_nom_fichier(parametres.get("nom_fichier"))
    repertoire_cible = nettoyer_valeur(parametres.get("repertoire_cible"))

    if nom_fichier is None:
        return {"statut": "echec", "message": "Aucun fichier image spécifié.", "donnees": None}

    if repertoire_cible:
        chemin_dossier = resoudre_chemin(repertoire_cible)
        chemin_fichier = chemin_dossier / nom_fichier if chemin_dossier else None
    else:
        resultats = rechercher_fichier(nom_fichier)
        if not resultats:
            return {"statut": "echec", "message": f"Image introuvable : {nom_fichier}", "donnees": None}
        chemin_fichier = resultats[0]

    if chemin_fichier is None or not Path(chemin_fichier).exists():
        return {"statut": "echec", "message": f"Image introuvable : {nom_fichier}", "donnees": None}

    try:
        ctypes.windll.user32.SystemParametersInfoW(
            20, 0, str(chemin_fichier), 3)
        return {"statut": "succes", "message": f"Fond d'écran changé : {nom_fichier}", "donnees": None}
    except Exception as e:
        return {"statut": "echec", "message": f"Erreur : {e}", "donnees": None}
