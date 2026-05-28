from pathlib import Path
import subprocess
import shutil
import os

from utils import resoudre_chemin, nettoyer_valeur


def ouvrir_app(parametres: dict, resolve_executable_func) -> dict:
    nom_app = nettoyer_valeur(parametres.get("nom_app"))
    chemin_app = nettoyer_valeur(parametres.get("chemin_app"))

    if nom_app is None and chemin_app is None:
        return {"statut": "echec", "message": "Aucune application spécifiée.", "donnees": None}

    # si un chemin explicite est fourni, l'utiliser directement
    if chemin_app:
        try:
            p = None
            ppath = None
            if Path(chemin_app).exists():
                ppath = Path(chemin_app)
                p = subprocess.Popen(
                    [str(ppath)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
            else:
                found = shutil.which(chemin_app) or shutil.which(
                    f"{chemin_app}.exe")
                if found:
                    ppath = Path(found)
                    p = subprocess.Popen(
                        [str(ppath)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
                else:
                    p = subprocess.Popen(
                        chemin_app, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)

            pid = p.pid if p is not None else None
            donnees = {"pid": pid, "exe": str(
                ppath) if ppath is not None else None}
            return {"statut": "succes", "message": f"Application lancée : {chemin_app}", "donnees": donnees}
        except Exception as e:
            return {"statut": "echec", "message": f"Impossible d'ouvrir {chemin_app} : {e}", "donnees": None}

    # 1) essayer via PATH (shutil.which)
    try:
        found = shutil.which(nom_app) or shutil.which(f"{nom_app}.exe")
        if found:
            p = subprocess.Popen(
                [found], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
            return {"statut": "succes", "message": f"Application lancée : {found}", "donnees": {"pid": p.pid, "exe": str(found)}}
    except Exception:
        pass

    # 2) tentative générale via helper non bloquant
    if resolve_executable_func:
        exec_path = resolve_executable_func(nom_app)
        if exec_path:
            try:
                p = subprocess.Popen(
                    [str(exec_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
                return {"statut": "succes", "message": f"Application lancée : {exec_path}", "donnees": {"pid": p.pid, "exe": str(exec_path)}}
            except Exception as e:
                return {"statut": "echec", "message": f"Impossible d'ouvrir {exec_path} : {e}", "donnees": None}

    return {"statut": "echec", "message": f"Application '{nom_app}' non trouvée automatiquement. Spécifiez 'chemin_app' avec le chemin complet de l'exécutable.", "donnees": None}
