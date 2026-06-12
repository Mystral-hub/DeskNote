#!/usr/bin/env python3
"""
Script de test pour les trois fonctionnalités principales :
- creer_facture
- creer_presentation
- recherche_en_ligne
"""

from prompts import SYSTEM_PROMPT
from planner import Planner
import json
import sys
from pathlib import Path

# Ajouter src au path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_feature(planner: Planner, user_input: str, feature_name: str):
    """Teste une fonctionnalité et affiche les résultats."""
    print("\n" + "="*80)
    print(f"TEST: {feature_name}")
    print("="*80)
    print(f"User Input: {user_input}\n")

    try:
        result = planner.extract_action(user_input)

        if result:
            print(f"✅ Action extraite: {result.get('action')}")
            print(f"\nRésultat JSON complet:")
            print(json.dumps(result, indent=2, ensure_ascii=False))

            # Validation spécifique par action
            action = result.get('action')
            params = result.get('parametres', {})

            if action == 'creer_facture':
                print(f"\n📋 Détails de la facture:")
                print(f"  - Numéro: {params.get('numero_facture')}")
                print(f"  - Client: {params.get('client_nom')}")
                print(
                    f"  - Nombre d'articles: {len(params.get('articles', []))}")
                print(f"  - Sauvegarde: {params.get('repertoire_cible')}")

            elif action == 'creer_presentation':
                print(f"\n🎨 Détails de la présentation:")
                print(f"  - Titre: {params.get('titre')}")
                print(f"  - Nombre de slides: {len(params.get('slides', []))}")
                if params.get('slides'):
                    print(
                        f"  - Première slide: {params['slides'][0].get('titre')}")

            elif action == 'recherche_en_ligne':
                print(f"\n🔍 Détails de la recherche:")
                print(f"  - Requête: {params.get('requete')}")
                print(f"  - Sauvegarder: {params.get('sauvegarder_resultat')}")
                if params.get('nom_fichier_resultat'):
                    print(f"  - Fichier: {params.get('nom_fichier_resultat')}")
        else:
            print("❌ Aucune action extraite")

    except Exception as e:
        print(f"❌ Erreur: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Lance les tests."""
    print("\n" + "╔" + "="*78 + "╗")
    print("║" + " "*78 + "║")
    print("║" + "  TEST DES TROIS FONCTIONNALITÉS PRINCIPALES - DeskNote".center(78) + "║")
    print("║" + " "*78 + "║")
    print("╚" + "="*78 + "╝")

    # Initialiser le planner
    try:
        planner = Planner()
        print("\n✅ Planner initialisé avec succès")
    except Exception as e:
        print(f"\n❌ Erreur d'initialisation du planner: {e}")
        sys.exit(1)

    # Test 1: Créer une facture
    test_feature(
        planner,
        "facture numéro 001 pour le client Acme Corp, 3 jours de développement à 350€, "
        "1 consultation à 500€, sauvegarde dans documents",
        "CREER_FACTURE"
    )

    # Test 2: Créer une présentation
    test_feature(
        planner,
        "fais moi une présentation sur l'intelligence artificielle avec un fond bleu "
        "et du texte blanc, environ 4 slides",
        "CREER_PRESENTATION"
    )

    # Test 3: Recherche en ligne
    test_feature(
        planner,
        "cherche des informations sur le machine learning et sauvegarde le résultat "
        "dans un fichier",
        "RECHERCHE_EN_LIGNE"
    )

    print("\n" + "="*80)
    print("✅ Test terminé!")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
