# VoyagePlus

Prototype de planification de voyages avec une interface Streamlit et cinq
services Python/FastAPI : un orchestrateur et quatre agents specialises.

## Fonctionnement

L'interface envoie la demande a l'orchestrateur, qui interroge les agents en
parallele via HTTP, puis rassemble leurs resultats.

| Service | Port | Source des donnees |
| --- | --- | --- |
| Orchestrateur | 8000 | Agregation des quatre agents |
| Vols | 8001 | Simulation locale |
| Hebergements | 8002 | OpenStreetMap, Nominatim et Overpass |
| Activites | 8003 | OpenStreetMap, Nominatim et Overpass |
| Meteo | 8004 | OpenWeather, meteo actuelle |
| Interface Streamlit | 8501 | Resultats de l'orchestrateur |

## Installation

Python 3.11 est utilise pour le developpement et les tests.
Depuis la racine du projet :

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Sous Linux/macOS, activer l'environnement avec `source .venv/bin/activate`.

Creer la configuration locale si elle n'existe pas encore :

```powershell
Copy-Item .env.example .env
```

Renseigner `OPENWEATHER_API_KEY` dans `.env` pour activer la meteo.
Sans cle, les autres agents restent utilisables et la meteo affiche un message.
Ne jamais publier `.env` ; seul `.env.example` doit etre versionne.

## Lancement

Ouvrir six terminaux a la racine du projet, activer l'environnement dans chacun,
puis lancer une commande par terminal :

```powershell
python -m agents.flight_agent
python -m agents.stay_agent
python -m agents.activities_agent
python -m agents.weather_agent
python -m agents.orchestrateur_agent
python -m streamlit run travel_ui.py
```

Interface : http://localhost:8501. Documentation de l'orchestrateur :
http://127.0.0.1:8000/docs. Chaque agent expose egalement `/docs` et `POST /run`.
Les ports 8000 a 8004 doivent etre disponibles.

### Erreur Windows : Fatal error in launcher

Cette erreur peut apparaitre lorsque le dossier du projet a ete deplace : les
lanceurs `.exe` de l'ancien environnement referencent encore son ancien chemin.
Depuis la racine du projet, utiliser directement le Python de l'environnement :

```powershell
.\.venv\Scripts\python.exe -m uvicorn agents.flight_agent.__main__:app --port 8001
```

Cette commande ne depend ni du lanceur `uvicorn.exe` ni de l'activation du
terminal. Pour un nouveau clone ou une autre machine, creer un environnement
avec les commandes d'installation ; ne pas copier le dossier `.venv`.

### Exemple de requete

Exemple de corps JSON pour `POST /run` de l'orchestrateur :

```json
{
  "origin": "Paris",
  "destination": "Rome",
  "start_date": "2027-05-10",
  "end_date": "2027-05-13",
  "budget": 1500
}
```

## Structure

```text
agents/
  activities_agent/     Recherche de lieux et classement par interet/distance
  flight_agent/         Generation de vols de demonstration
  orchestrateur_agent/  Appels HTTP concurrents aux agents
  stay_agent/           Recherche d'hebergements et estimation des prix
  weather_agent/        Meteo actuelle de la destination
common/                 Client HTTP et fabrique d'applications FastAPI
image/                  Image utilisee par l'interface
tests/                  Tests locaux sans appels aux fournisseurs externes
travel_ui.py            Interface Streamlit
```

Les modules `task_manager.py` relient les points d'entree des services a leur
logique metier. Les echanges sont des appels HTTP JSON simples, sans
implementation complete du protocole A2A ni modele de langage actif.

## Verification

```powershell
python -m unittest discover -s tests -v
```

Les tests couvrent les routes des services, l'agregation des resultats, une panne
partielle et les etats d'erreur de l'interface. GitHub Actions les execute aussi.
Les appels reels a OpenWeather, Nominatim et Overpass necessitent Internet et ne
sont pas effectues par ces tests.

## Limites du prototype

- Les vols sont simules, avec des prix aleatoires, pour Paris/Rome, Paris/Rabat
  et Paris/Madrid dans les deux sens. Aucune reservation n'est effectuee.
- Les prix des hebergements sont des estimations locales, pas des tarifs ni des
  disponibilites verifies. Le budget total est actuellement transmis comme
  plafond par nuit : il n'existe pas encore de repartition globale du budget.
- La meteo correspond au moment de la recherche, pas aux dates du sejour.
- La recherche d'activites utilise actuellement un rayon fixe de 7 km et la
  categorie `top`, meme si d'autres valeurs sont envoyees a l'orchestrateur.
- Les services cartographiques publics peuvent etre lents ou indisponibles.
  Verifier leurs conditions d'utilisation avant un deploiement public.
- Les entrees ne beneficient pas encore d'une validation metier complete.
  L'agent vols decale le retour de trois jours si sa date precede ou egale le
  depart. Utiliser des dates coherentes pour comparer les resultats des agents.
- Les services sont destines a une demonstration locale, sans authentification.

## Publication GitHub

Verifier que `git rev-parse --show-toplevel` designe bien ce dossier avant
d'ajouter les fichiers. `.gitignore` exclut les secrets, environnements, caches
et journaux. Les dependances directes sont epinglees dans `requirements.txt`.

```powershell
git status --short
git add .
git diff --cached --stat
git commit -m "Prepare VoyagePlus for GitHub"
```

Creer ensuite un depot GitHub vide et suivre ses commandes pour ajouter le
remote et pousser la branche. Aucun depot distant n'est configure par le code.
Choisir une licence et verifier les droits sur l'image avant toute diffusion
publique ; aucune licence de redistribution n'est accordee par ce README.
