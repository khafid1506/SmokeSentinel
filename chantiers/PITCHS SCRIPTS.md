Voici 3 pitches de scripts qui s'intègrent naturellement dans l'écosystème SmokeSentinel :

---

**① `env_check.py` — Validateur d'environnement pré-lancement**

Avant de lancer l'agent, ce script vérifie que tout est en ordre : variables d'environnement critiques présentes (`ANTHROPIC_API_KEY`, `JIRA_TOKEN`, `SLACK_WEBHOOK_URL`…), format valide (clé Anthropic qui commence bien par `sk-ant-`), services joignables (ping GitHub, Jira, Slack), Docker en cours d'exécution, dépendances Python installées et aux bonnes versions. Un feu vert / rouge clair par item, un score global, et un rapport de ce qui bloque avant même de lancer `sentinel.py`. Fini les crashes au runtime pour une variable oubliée dans `.env`.

---

**② `test_report_cleaner.py` — Archiveur & nettoyeur de rapports de tests**

À chaque run de SmokeSentinel, un rapport HTML/Markdown est généré. Ce script organise automatiquement : déplace les anciens rapports dans `reports/archive/YYYY-MM-DD/`, supprime les runs de plus de N jours (configurable), génère un `index.html` récapitulatif avec historique des runs (pass/fail, date, durée, lien), et envoie un résumé Slack hebdomadaire. Le dossier `reports/` reste propre, l'historique reste consultable, sans intervention manuelle.

---

**③ `jira_story_fetcher.py` — Récupérateur de User Stories Jira en CLI**

SmokeSentinel a besoin d'une User Story en entrée — ce script la lui apporte directement. En une commande (`python jira_story_fetcher.py --ticket PROJ-1234`), il se connecte à l'API Jira, récupère le titre, la description, les critères d'acceptance et les labels, formate tout en Markdown propre dans `stories/PROJ-1234.md`, et lance optionnellement l'agent directement derrière. Zéro copier-coller depuis l'interface Jira, pipeline 100% CLI du ticket au rapport.

---

Les trois suivent la même philosophie que les scripts existants : standalone, zéro dépendance lourde, interactifs, colorés, safe-by-default. Lequel vous intéresse en premier ?