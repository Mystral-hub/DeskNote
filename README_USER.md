DeskNote — Manuel d'utilisation
===============================

But
----
DeskNote automatise des tâches sur Windows via des commandes en langage naturel (français). L'interface principale est la zone de saisie : écrivez une phrase simple, l'agent planifie et exécute l'action.

Principes
---------
- Écrivez vos instructions en français, de façon concise.
- Pour un minimum d'efforts, fournissez le chemin ou le nom du fichier dans votre phrase.
- Pour programmer une action, indiquez la date/heure au format `YYYY-MM-DD HH:MM` (ex: `2026-06-09 15:30`) ou `DD/MM/YYYY HH:MM`.

Exemples d'utilisation par fonctionnalité
----------------------------------------

- Poster sur Facebook (message-driven)
  - Immédiat : "poste photo_vacances.jpg sur facebook avec le texte 'Vacances 2024'"
  - Programmé : "programme la publication video_demo.mp4 sur facebook le 2026-06-09 15:30 avec 'Nouvelle démo'"
  - Sans texte : "partage image_event.jpg sur facebook"

- Créer une présentation
  - "crée une presentation 'Synthèse projet' 5 slides thème sombre"
  - "crée une presentation 'Système solaire' 3 slides fond noir texte jaune"

- Ouvrir une application
  - "ouvre notepad"
  - "ouvre vlc"

- Lancer un média
  - "joue demo.mp4"
  - "lance la musique de niska"

- Créer un fichier texte
  - "crée un fichier texte appelé notes.txt sur le bureau avec comme contenu: point1, point2"

- Rechercher en ligne et sauvegarder
  - "cherche informations sur la tour eiffel et sauvegarde le résultat"

- Organiser les fichiers
  - "range les fichiers de mon bureau par type"

- Changer le fond d'écran
  - "mets comme fond d'écran paysage.jpg qui est dans mes images"

- Créer une facture
  - "facture 003 pour le client Tech Solutions 5 jours de développement à 300€, 2 formations à 200€, sauvegarde dans documents"

- Supprimer un fichier (confirmation requise)
  - "supprime rapport.docx dans mes documents"

- Saisie automatique (live typing)
  - "ouvre notepad et tape Bonjour tout le monde"

Conseils et limites
-------------------
- Pour les publications sociales, l'application accepte les chemins Windows (`C:\\Users\\...`), chemins Unix (`/home/...`) ou simplement le nom du fichier si le média se trouve dans un dossier connu.
- Les pièces jointes doivent respecter la limite `max_media_mb` (par défaut 20 MB).
- Les actions destructrices demandent confirmation avant exécution.
- Le composant planner essaie d'extraire automatiquement les paramètres (chemin, nom du fichier, date, confidentialité) depuis votre message ; si quelque chose manque, reformulez en ajoutant la donnée.

Dépannage rapide
----------------
- Si une publication programmée n'est pas postée, vérifiez `data/desknote.db` dans la table `scheduled_posts`.
- Si Playwright ne parvient pas à poster, assurez-vous d'avoir configuré `config/facebook_config.json` et d'avoir enregistré le mot de passe dans le keyring (script `scripts/save_fb_password.py`).

Fichiers utiles
---------------
- `src/prompts.py` — règles et exemples pour le planner.
- `src/planner.py` — logique d'extraction et post-traitement des paramètres.
- `src/social/facebook.py` — implémentation Playwright pour poster.
- `data/desknote.db` — base SQLite (historique, logs, scheduled_posts).

Support
-------
Ouvrez une issue ou demandez de l'aide si un cas réel échoue : fournissez l'exemple de message et le fichier `data/last_llm_response_raw.json` si disponible.
