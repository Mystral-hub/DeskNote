from pathlib import Path

from utils import (
    resoudre_chemin,
    nettoyer_nom_fichier,
    nettoyer_valeur,
    placer_dans_repertoire,
    revenir_repertoire_base,
)


def creer_fichier_texte(parametres: dict, resolve_executable_func) -> dict:
    nom_fichier = nettoyer_nom_fichier(parametres.get("nom_fichier"))
    contenu = parametres.get("contenu") or ""
    repertoire_cible = nettoyer_valeur(parametres.get("repertoire_cible"))

    if nom_fichier is None:
        return {"statut": "echec", "message": "Aucun nom de fichier spécifié.", "donnees": None}

    chemin_dossier = resoudre_chemin(
        repertoire_cible) if repertoire_cible else Path.home() / "Documents"

    if chemin_dossier is None:
        return {"statut": "echec", "message": f"Dossier introuvable : {repertoire_cible}", "donnees": None}

    chemin_fichier = chemin_dossier / nom_fichier

    try:
        placer_dans_repertoire(repertoire_cible) if repertoire_cible else None
        chemin_fichier.write_text(contenu, encoding="utf-8")
        revenir_repertoire_base()
        return {"statut": "succes", "message": f"Fichier créé : {chemin_fichier}", "donnees": {"path": str(chemin_fichier)}}
    except Exception as e:
        revenir_repertoire_base()
        return {"statut": "echec", "message": f"Erreur lors de la création : {e}", "donnees": None}
