import shutil
from pathlib import Path

from utils import (
    resoudre_chemin,
)


def _type_fichier_local(extension: str) -> str:
    categories = {
        "Images":     [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp"],
        "Videos":     [".mp4", ".avi", ".mkv", ".mov", ".wmv"],
        "Audio":      [".mp3", ".wav", ".flac", ".aac", ".ogg"],
        "Documents":  [".pdf", ".docx", ".doc", ".txt", ".odt"],
        "Tableurs":   [".xlsx", ".xls", ".csv", ".ods"],
        "Archives":   [".zip", ".rar", ".7z", ".tar", ".gz"],
        "Code":       [".py", ".js", ".html", ".css", ".json"],
    }
    ext = extension.lower()
    for categorie, extensions in categories.items():
        if ext in extensions:
            return categorie
    return "Divers"


def organiser_fichiers(parametres: dict, resolve_executable_func) -> dict:
    repertoire_cible = parametres.get("repertoire_cible")
    critere = parametres.get("critere") or "par_extension"

    chemin_dossier = resoudre_chemin(repertoire_cible)
    if chemin_dossier is None or not chemin_dossier.exists():
        return {"statut": "echec", "message": f"Dossier introuvable : {repertoire_cible}", "donnees": None}

    fichiers = [f for f in chemin_dossier.iterdir() if f.is_file()]
    compteur = 0

    for fichier in fichiers:
        if critere == "par_extension":
            sous_dossier = fichier.suffix.lstrip(
                '.') .upper() or "SANS_EXTENSION"
        elif critere == "par_type":
            sous_dossier = _type_fichier_local(fichier.suffix)
        else:
            sous_dossier = "Divers"

        destination = chemin_dossier / sous_dossier
        destination.mkdir(exist_ok=True)
        shutil.move(str(fichier), str(destination / fichier.name))
        compteur += 1

    return {"statut": "succes", "message": f"{compteur} fichiers organisés dans {repertoire_cible}.", "donnees": None}
