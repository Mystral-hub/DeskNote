import os
from pathlib import Path

from utils import (
    resoudre_chemin,
    nettoyer_nom_fichier,
    nettoyer_valeur,
    rechercher_fichier,
    formater_resultats_recherche,
)


def supprimer_fichier(parametres: dict, resolve_executable_func) -> dict:
    nom_fichier = nettoyer_nom_fichier(parametres.get("nom_fichier"))
    repertoire_cible = nettoyer_valeur(parametres.get("repertoire_cible"))

    if nom_fichier is None:
        return {"statut": "echec", "message": "Aucun fichier spécifié.", "donnees": None}

    # résoudre le chemin complet
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
        os.remove(chemin_fichier)
        return {"statut": "succes", "message": f"Fichier supprimé : {nom_fichier}", "donnees": None}
    except Exception as e:
        return {"statut": "echec", "message": f"Erreur lors de la suppression : {e}", "donnees": None}
