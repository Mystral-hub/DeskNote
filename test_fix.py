#!/usr/bin/env python
"""
Script de test pour vérifier que les corrections fonctionnent.
"""
import os
from planner import Planner
import sys
import json
from pathlib import Path

# Ajouter src au path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Changer au répertoire src
os.chdir(Path(__file__).parent / "src")


# Initialiser le planner
NOM_MODELE = "qwen2.5-1.5b-instruct-q4_k_m.gguf"
print("Chargement du modèle LLM...")
planner = Planner(NOM_MODELE)
print("Modèle chargé!\n")

# Tester les requêtes
test_requetes = [
    "ouvre vlc",
    "ouvre notepad",
    "lance la musique de niska",
]

for requete in test_requetes:
    print(f"Requête: '{requete}'")
    resultat = planner.planifier(requete)
    print(f"Action détectée: {resultat.get('action')}")
    print(
        f"Paramètres: {json.dumps(resultat.get('parametres'), indent=2, ensure_ascii=False)}")
    print("-" * 50)
