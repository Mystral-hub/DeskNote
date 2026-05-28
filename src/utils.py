import os
from pathlib import Path


DOSSIER_BASE = Path.cwd()

DOSSIERS_CONNUS = {
    "documents": Path.home() / "Documents",
    "bureau": Path.home() / "Desktop",
    "images": Path.home() / "Pictures",
    "telechargements": Path.home() / "Downloads",
    "musique": Path.home() / "Music",
    "videos": Path.home() / "Videos",
}


def resoudre_chemin(nom_dossier: str | None) -> Path | None:
    """Traduit un nom de dossier courant en chemin absolu Windows."""
    if nom_dossier is None:
        return None

    nom_normalise = nom_dossier.strip().lower()

    if nom_normalise in DOSSIERS_CONNUS:
        return DOSSIERS_CONNUS[nom_normalise]

    # si c'est déjà un chemin absolu
    chemin = Path(nom_dossier)
    if chemin.is_absolute() and chemin.exists():
        return chemin

    return None


def nettoyer_valeur(valeur: str | None) -> str | None:
    """Nettoie une valeur extraite par le LLM."""
    if valeur is None:
        return None

    valeur = valeur.strip()

    if valeur.lower() == "null" or valeur == "":
        return None

    return valeur


def nettoyer_nom_fichier(nom_fichier: str | None) -> str | None:
    """Nettoie et normalise un nom de fichier."""
    if nom_fichier is None:
        return None

    nom_fichier = nom_fichier.strip()

    caracteres_interdits = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
    for caractere in caracteres_interdits:
        nom_fichier = nom_fichier.replace(caractere, '')

    return nom_fichier if nom_fichier else None


def rechercher_fichier(nom_fichier: str | None) -> list:
    """
    Recherche un fichier dans les dossiers utilisateur.
    Retourne une liste de chemins absolus trouvés.
    """
    resultats = []
    if nom_fichier is None:
        return resultats
    nom_normalise = nom_fichier.strip().lower()

    for nom_dossier, chemin_dossier in DOSSIERS_CONNUS.items():
        if not chemin_dossier.exists():
            continue

        for fichier in chemin_dossier.rglob("*"):
            if fichier.is_file() and nom_normalise in fichier.name.lower():
                resultats.append(fichier)

    return resultats


def formater_resultats_recherche(resultats: list) -> str:
    """
    Formate la liste des résultats pour affichage à l'utilisateur.
    Retourne une chaîne lisible avec numérotation.
    """
    if not resultats:
        return "Aucun fichier trouvé."

    lignes = ["Plusieurs fichiers trouvés, lequel voulez-vous utiliser ?\n"]
    for index, chemin in enumerate(resultats, start=1):
        lignes.append(f"  {index}. {chemin.name}  —  {chemin.parent}")

    return "\n".join(lignes)


def placer_dans_repertoire(repertoire_cible: str | None) -> Path | None:
    """
    Se place dans le répertoire cible.
    Retourne le chemin cible ou None si introuvable.
    """
    chemin_cible = resoudre_chemin(repertoire_cible)

    if chemin_cible is None:
        return None

    os.chdir(chemin_cible)
    return chemin_cible


def revenir_repertoire_base():
    """Revient toujours au répertoire de base fixe défini au démarrage."""
    os.chdir(DOSSIER_BASE)
