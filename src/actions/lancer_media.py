import os
from pathlib import Path

from utils import (
    nettoyer_nom_fichier,
    nettoyer_valeur,
    resoudre_chemin,
    rechercher_fichier,
    formater_resultats_recherche,
)


def lancer_media(parametres: dict, resolve_executable_func) -> dict:
    nom_fichier = nettoyer_nom_fichier(parametres.get("nom_fichier"))
    artiste = nettoyer_valeur(parametres.get("artiste"))
    titre = nettoyer_valeur(parametres.get("titre"))
    repertoire_cible = nettoyer_valeur(parametres.get("repertoire_cible"))
    type_media = nettoyer_valeur(parametres.get("type_media")) or "audio"

    # cas 1 — fichier explicitement nommé
    if nom_fichier:
        dossier = resoudre_chemin(repertoire_cible) if repertoire_cible else (
            Path.home() / "Music" if type_media == "audio" else Path.home() / "Videos"
        )
        chemin_fichier = dossier / nom_fichier if dossier else None

        if chemin_fichier and chemin_fichier.exists():
            os.startfile(str(chemin_fichier))
            return {"statut": "succes", "message": f"Lecture lancée : {nom_fichier}", "donnees": {"path": str(chemin_fichier)}}

    # cas 2 — recherche par artiste ou titre
    terme_recherche = titre or artiste
    if terme_recherche:
        dossier_recherche = Path.home(
        ) / "Music" if type_media == "audio" else Path.home() / "Videos"
        resultats = []

        for fichier in dossier_recherche.rglob("*"):
            if fichier.is_file() and terme_recherche.lower() in fichier.name.lower():
                resultats.append(fichier)

        if not resultats:
            return {"statut": "echec", "message": f"Aucun fichier trouvé pour : {terme_recherche} dans {dossier_recherche}", "donnees": None}

        if len(resultats) > 1:
            return {"statut": "choix_requis", "message": formater_resultats_recherche(resultats), "donnees": {"resultats": [str(r) for r in resultats]}}

        os.startfile(str(resultats[0]))
        return {"statut": "succes", "message": f"Lecture lancée : {resultats[0].name}", "donnees": {"path": str(resultats[0])}}

    return {"statut": "echec", "message": "Aucun fichier, artiste ou titre spécifié.", "donnees": None}
