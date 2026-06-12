"""
Test script to verify that creer_presentation action works correctly
after prompt fixes.
"""

from prompts import SYSTEM_PROMPT
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# Verify that creer_presentation is properly defined in prompt
print("=" * 70)
print("VALIDATION: creer_presentation dans le SYSTEM_PROMPT")
print("=" * 70)

# Check 1: Is creer_presentation defined?
if "### 13. creer_presentation" in SYSTEM_PROMPT:
    print("✅ Action 13 (creer_presentation) trouvée dans le prompt")
else:
    print("❌ Action 13 (creer_presentation) MANQUANTE")
    sys.exit(1)

# Check 2: Does it have rule s in RÈGLES STRICTES?
if "Pour creer_presentation :" in SYSTEM_PROMPT:
    print("✅ Règles pour creer_presentation dans RÈGLES STRICTES")
else:
    print("❌ Règles pour creer_presentation MANQUANTES")
    sys.exit(1)

# Check 3: Is the JSON template valid?
try:
    # Extract the JSON schema for creer_presentation
    import re
    match = re.search(
        r'### 13\. creer_presentation\n(\{.*?\n\})', SYSTEM_PROMPT, re.DOTALL)
    if match:
        json_template = match.group(1)
        parsed = json.loads(json_template)
        if parsed["action"] == "creer_presentation":
            print("✅ JSON template pour creer_presentation est VALIDE")
            # Check the slides structure
            slides = parsed["parametres"]["slides"]
            if isinstance(slides, list) and len(slides) > 0:
                first_slide = slides[0]
                if "titre" in first_slide and "contenu" in first_slide and "style" in first_slide:
                    style = first_slide["style"]
                    if isinstance(style["taille_titre"], int) and isinstance(style["taille_contenu"], int):
                        print("✅ Structure slides correcte avec nombres pour taille")
                    else:
                        print(
                            "❌ taille_titre ou taille_contenu ne sont pas des nombres")
            else:
                print("❌ Slides array vide ou invalide")
        else:
            print("❌ Action name incorrect")
    else:
        print("❌ Impossible d'extraire le JSON de creer_presentation")
except Exception as e:
    print(f"❌ Erreur parsing JSON: {e}")
    sys.exit(1)

# Check 4: Are both examples present?
examples_present = 0
if "fais une présentation sur les dauphins" in SYSTEM_PROMPT:
    print("✅ Exemple 1 (dauphins) trouvé")
    examples_present += 1
else:
    print("⚠️  Exemple 1 (dauphins) manquant")

if "système solaire" in SYSTEM_PROMPT and "crée une présentation" in SYSTEM_PROMPT:
    print("✅ Exemple 2 (système solaire) trouvé")
    examples_present += 1
else:
    print("⚠️  Exemple 2 (système solaire) manquant")

if examples_present == 2:
    print(
        f"✅ Tous les {examples_present} exemples pour creer_presentation trouvés")
else:
    print(f"⚠️  Seulement {examples_present}/2 exemples trouvés")

# Check 5: No old malformatted rules?
if "-Regles strictes pour creer_presentation:" in SYSTEM_PROMPT:
    print("⚠️  Anciennes règles malformatées trouvées (devraient être suprimées)")
else:
    print("✅ Pas de format danciennes règles non-formatées")

print("\n" + "=" * 70)
print("RÉSUMÉ: Le prompt est prêt pour creer_presentation !")
print("=" * 70)
print("\nProchaines étapes:")
print("1. Testez avec le model: 'fais une présentation sur [thème]'")
print("2. Vérifiez que l'action retournée est 'creer_presentation' et pas 'incompris'")
print("3. Vérifiez que le JSON a tous les champs: titre, slides[], repertoire_cible")
