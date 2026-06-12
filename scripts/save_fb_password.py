#!/usr/bin/env python3
"""CLI helper to save Facebook password into system keyring for DeskNote.

Usage:
  python scripts/save_fb_password.py

It reads `config/facebook_config.json` for the username and stores the password in the keyring
under service name `desknote_facebook`.
"""
import json
import getpass
from pathlib import Path

try:
    import keyring
except Exception:
    keyring = None

CONFIG = Path(__file__).parent.parent / "config" / "facebook_config.json"


def main():
    if not CONFIG.exists():
        print("Fichier de configuration introuvable:", CONFIG)
        return

    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    username = cfg.get("username")
    if not username:
        print("Veuillez saisir le champ 'username' dans config/facebook_config.json avant d'exécuter ce script.")
        return

    if keyring is None:
        print("Le module 'keyring' n'est pas installé. Installez-le: pip install keyring")
        return

    pwd = getpass.getpass(f"Mot de passe pour {username}: ")
    if not pwd:
        print("Mot de passe vide, abort.")
        return

    try:
        keyring.set_password("desknote_facebook", username, pwd)
        print("Mot de passe enregistré dans le keyring pour l'utilisateur:", username)
    except Exception as e:
        print("Erreur lors de l'enregistrement du mot de passe:", e)


if __name__ == '__main__':
    main()
