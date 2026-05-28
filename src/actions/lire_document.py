import os
from pathlib import Path

from utils import (
    nettoyer_nom_fichier,
    resoudre_chemin,
    nettoyer_valeur,
    rechercher_fichier,
    formater_resultats_recherche,
)


def lire_document(parametres: dict, resolve_executable_func) -> dict:
    nom_fichier = nettoyer_nom_fichier(parametres.get("nom_fichier"))
    repertoire_cible = nettoyer_valeur(parametres.get("repertoire_cible"))

    if nom_fichier is None:
        return {"statut": "echec", "message": "Aucun fichier spécifié.", "donnees": None}

    if repertoire_cible:
        chemin_dossier = resoudre_chemin(repertoire_cible)
        chemin_fichier = chemin_dossier / nom_fichier if chemin_dossier else None
    else:
        resultats = rechercher_fichier(nom_fichier)
        if not resultats:
            return {"statut": "echec", "message": f"Fichier introuvable : {nom_fichier}", "donnees": None}
        if len(resultats) > 1:
            return {"statut": "choix_requis", "message": formater_resultats_recherche(resultats), "donnees": {"resultats": [str(r) for r in resultats]}}
        chemin_fichier = resultats[0]

    if chemin_fichier is None or not chemin_fichier.exists():
        return {"statut": "echec", "message": f"Fichier introuvable : {nom_fichier}", "donnees": None}

    try:
        os.startfile(str(chemin_fichier))
        return {"statut": "succes", "message": f"Document ouvert : {nom_fichier}", "donnees": {"path": str(chemin_fichier)}}
    except Exception as e:
        return {"statut": "echec", "message": f"Impossible d'ouvrir le document : {e}", "donnees": None}
