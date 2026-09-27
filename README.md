# VoyagePlus

**Un seul espace pour préparer son voyage : vols, hébergements, activités et météo.**

VoyagePlus regroupe les informations utiles à la préparation d'un séjour dans une
seule interface : vols, hébergements, activités touristiques et météo. À partir
d'une ville de départ, d'une destination, de dates et d'un budget, un orchestrateur
coordonne quatre agents spécialisés et rassemble leurs résultats.

L'application associe une interface interactive, des services indépendants et
plusieurs sources de données. Elle accompagne la préparation du voyage, de la
saisie des critères à la consultation de propositions structurées, pour faciliter
les choix de l'utilisateur.

## Pourquoi VoyagePlus ?

Organiser un voyage implique souvent de consulter plusieurs plateformes pour
comparer les transports, rechercher un logement, choisir des visites et vérifier
la météo. Cette dispersion rend la préparation longue et complique la lecture
globale du séjour.

VoyagePlus s'adresse aux voyageurs qui souhaitent préparer leur séjour à partir
d'une vue d'ensemble claire. Le projet poursuit quatre objectifs :

- Centraliser les informations essentielles dans une interface unique.
- Automatiser la collecte et le traitement des données par des agents spécialisés.
- Sélectionner et classer les résultats pour faciliter leur comparaison.
- Proposer une vue d'ensemble du séjour pour accompagner la décision.

## Points forts

- **Une recherche centralisée** : une seule saisie pour retrouver les quatre
  catégories d'informations utiles au séjour.
- **Une architecture modulaire** : chaque agent prend en charge un domaine
  précis, ce qui facilite l'évolution des fonctionnalités et des sources de données.
- **Des traitements concurrents** : l'orchestrateur lance les recherches des
  agents en parallèle et rassemble leurs réponses.
- **Des recommandations classées** : les hébergements et les activités sont
  sélectionnés à partir de critères de prix, de distance ou d'intérêt.
- **Une restitution lisible** : Streamlit présente les résultats par catégorie
  pour faciliter la consultation et la comparaison.
- **Une base testable** : les services disposent d'une documentation API
  interactive et de tests automatisés exécutés avec GitHub Actions.

## Fonctionnalités

| Fonctionnalité | Ce que propose VoyagePlus |
| --- | --- |
| Saisie du voyage | Ville de départ, destination, dates et budget dans Streamlit |
| Vols aller-retour | Génération locale de vols de démonstration pour Paris/Rome, Paris/Rabat et Paris/Madrid, dans les deux sens |
| Hébergements | Recherche de lieux dans OpenStreetMap, estimation des prix et classement selon la distance et le prix |
| Activités | Sélection de cinq lieux au maximum, classés selon leur intérêt et leur distance au centre de la destination |
| Météo | Température, humidité, conditions actuelles et conseil adapté à la température via OpenWeather |
| Orchestration | Appels concurrents aux quatre agents et regroupement des réponses |
| Restitution | Affichage des résultats par catégorie dans une seule interface |

## Architecture

L'interface transmet une requête JSON à l'orchestrateur. Celui-ci distribue les
tâches aux agents via HTTP, attend leurs réponses avec `asyncio.gather`, puis
retourne les résultats agrégés à Streamlit.

```text
Interface Streamlit (8501)
    |
    | POST /run
    v
Agent orchestrateur (8000)
    |
    +-- Vols (8001) ----------> Simulation locale
    |
    +-- Hébergements (8002) --> OpenStreetMap / Nominatim / Overpass
    |
    +-- Activités (8003) -----> OpenStreetMap / Nominatim / Overpass
    |
    +-- Météo (8004) ---------> OpenWeather
```

Chaque service FastAPI expose `POST /run` et une documentation interactive sur
`/docs`. Lorsqu'un appel à un agent échoue, l'orchestrateur peut conserver les
résultats renvoyés par les autres agents.

### Technologies utilisées

| Technologie | Rôle |
| --- | --- |
| Python 3.11 | Logique des agents, traitement des données et orchestration |
| FastAPI et Uvicorn | Exposition et exécution des services HTTP |
| Streamlit | Interface de saisie et présentation des résultats |
| HTTPX et Requests | Appels HTTP entre services, vers les sources externes et depuis l'interface |
| python-dotenv | Chargement de la configuration locale |
| OpenStreetMap, Nominatim et Overpass | Géocodage et recherche de lieux |
| OpenWeather | Informations météorologiques actuelles |
| unittest et Streamlit AppTest | Tests des services et de l'interface |
| GitHub Actions | Exécution automatique des tests lors des envois de commits et des pull requests |

La communication entre agents repose sur des requêtes HTTP et des réponses JSON.
Les composants communs centralisent les appels et la création des services,
tandis que chaque agent conserve sa propre logique de traitement.

## Installation

Prérequis : Python 3.11 et une connexion Internet pour les services externes.
Depuis la racine du projet, dans PowerShell :

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Sous Linux ou macOS, activer l'environnement avec `source .venv/bin/activate`.

Si le fichier `.env` n'existe pas encore, créer la configuration locale :

```powershell
Copy-Item .env.example .env
```

Renseigner ensuite `OPENWEATHER_API_KEY` dans `.env`. Cette clé est nécessaire
uniquement pour la météo. Sans clé, les autres agents restent utilisables et la
météo affiche un message.

Les dépendances directes sont épinglées dans `requirements.txt`. Le fichier
`.env`, l'environnement `.venv`, les caches et les journaux sont exclus de Git ;
seul le modèle de configuration `.env.example` est versionné.

## Lancement

Ouvrir six terminaux à la racine du projet et activer l'environnement dans chacun.
Exécuter une commande par terminal :

| Terminal | Commande | Port |
| --- | --- | --- |
| Vols | `python -m agents.flight_agent` | 8001 |
| Hébergements | `python -m agents.stay_agent` | 8002 |
| Activités | `python -m agents.activities_agent` | 8003 |
| Météo | `python -m agents.weather_agent` | 8004 |
| Orchestrateur | `python -m agents.orchestrateur_agent` | 8000 |
| Interface | `python -m streamlit run travel_ui.py` | 8501 |

Les ports 8000 à 8004 et 8501 doivent être disponibles.

- Interface : http://localhost:8501
- Documentation de l'orchestrateur : http://127.0.0.1:8000/docs

### Erreur Windows : Fatal error in launcher

Cette erreur peut apparaître après un déplacement du projet : les lanceurs
`.exe` de l'ancien environnement référencent encore son ancien chemin.
Depuis la racine du projet, utiliser directement le Python de l'environnement :

```powershell
.\.venv\Scripts\python.exe -m uvicorn agents.flight_agent.__main__:app --port 8001
```

Cette commande fonctionne sans activation du terminal et sans passer par
`uvicorn.exe`. Pour un nouveau clone ou une autre machine, créer un nouvel
environnement avec les commandes d'installation au lieu de copier `.venv`.

## Exemple d'utilisation

1. Saisir une ville de départ et une destination, par exemple Paris et Rome.
2. Choisir des dates de départ et de retour cohérentes, puis indiquer un budget.
3. Lancer la planification.
4. Consulter les vols aller-retour, les hébergements, les activités et la météo.

Exemple de corps JSON pour `POST http://127.0.0.1:8000/run` :

```json
{
  "origin": "Paris",
  "destination": "Rome",
  "start_date": "2027-05-10",
  "end_date": "2027-05-13",
  "budget": 1500
}
```

La réponse regroupe les clés `flights`, `stay`, `activities` et `weather`,
directement exploitées par l'interface pour afficher les différentes propositions.

## Structure du dépôt

```text
agents/
  activities_agent/     Recherche et classement des lieux touristiques
  flight_agent/         Génération des vols de démonstration
  orchestrateur_agent/  Coordination des appels et agrégation des résultats
  stay_agent/           Recherche d'hébergements et estimation des prix
  weather_agent/        Météo actuelle de la destination
common/
  a2a_client.py         Client HTTP pour appeler les agents
  a2a_server.py         Création des applications FastAPI
image/                  Image utilisée par l'interface
tests/                  Tests des services et de l'interface
.github/workflows/      Vérification automatique sur GitHub
.env.example            Modèle de configuration sans secret
requirements.txt        Dépendances Python
travel_ui.py            Interface Streamlit
```

Les modules `__main__.py` démarrent les services. Les `task_manager.py` relient
leurs routes à la logique métier ; celui de l'orchestrateur coordonne les appels
aux quatre agents.

## Tests automatisés

```powershell
python -m unittest discover -s tests -v
```

Les six tests couvrent l'exposition des services, la génération d'un aller-retour,
l'agrégation des réponses, une panne partielle et les messages d'erreur dans
l'interface. Ils utilisent des réponses simulées pour les appels externes et
n'exigent pas de clé API. Le workflow GitHub Actions exécute cette même suite.

Ces tests ne vérifient pas la disponibilité réelle d'OpenWeather, de Nominatim
ou d'Overpass, ni les performances en production.

## Périmètre actuel

VoyagePlus est un outil d'aide à la décision, sans réservation ni paiement.
Il combine des données externes et des données de démonstration :

- Les vols sont simulés et les tarifs des hébergements sont estimés.
- Les lieux proviennent d'OpenStreetMap ; la météo correspond aux conditions
  actuelles fournies par OpenWeather, et non aux dates du séjour.
- Le budget est utilisé comme plafond par nuit pour l'hébergement ; sa répartition
  entre les différentes composantes du voyage reste une perspective d'évolution.
- Les activités sont recherchées dans un rayon fixe de 7 km, pour la catégorie `top`.

L'application s'exécute localement et dépend de la disponibilité des API
externes. Utiliser des dates cohérentes : l'agent vols décale le retour de trois
jours si sa date précède ou égale celle du départ. La version actuelle fonctionne
sans comptes utilisateurs ni historique persistant.

## Perspectives d'évolution

- Mener des tests avec des utilisateurs réels.
- Améliorer la lisibilité et la hiérarchisation des recommandations.
- Enrichir la personnalisation et les sources de données.
- Optimiser les échanges entre agents et les temps de réponse.
- Renforcer la validation des dates et la répartition du budget.
- Étudier la gestion des profils utilisateurs et le passage à plus grande échelle.

## Auteurs

Wissam AMEKRANE et Safae CHOUAI.

## Licence

Aucune licence de redistribution n'est actuellement déclarée dans ce dépôt.
