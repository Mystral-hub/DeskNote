from utils import (
    nettoyer_valeur,
    rechercher_fichier,
    formater_resultats_recherche,
)


def rechercher_fichier_action(parametres: dict, resolve_executable_func) -> dict:
    nom_fichier = nettoyer_valeur(parametres.get("nom_fichier"))
    extension = nettoyer_valeur(parametres.get("extension"))
    repertoire_cible = nettoyer_valeur(parametres.get("repertoire_cible"))

    terme = nom_fichier or extension
    if terme is None:
        return {"statut": "echec", "message": "Aucun critère de recherche spécifié.", "donnees": None}

    resultats = rechercher_fichier(terme)

    if not resultats:
        return {"statut": "echec", "message": f"Aucun fichier trouvé pour : {terme}", "donnees": None}

    return {"statut": "succes", "message": formater_resultats_recherche(resultats), "donnees": {"resultats": [str(r) for r in resultats]}}
