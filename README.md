# VoyagePlus

VoyagePlus est un projet de fin d’études qui aide à préparer un séjour à partir d’une ville de départ, d’une destination, de dates et d’un budget. Il rassemble des offres de vols et d’hébergements, des lieux à visiter et la météo, puis permet de télécharger un carnet de voyage en PDF.

Le projet utilise **Streamlit**, **FastAPI**, **Google ADK**, **LiteLLM** et le protocole **A2A**. Il prépare le voyage sans effectuer de réservation ni de paiement.

## Fonctionnalités

- Recherche de vols aller et retour avec horaires, escales, prix et liens Google Flights.
- Recherche de tarifs d’hébergements pour les dates demandées.
- Découverte de lieux d’activités avec adresses et horaires lorsqu’ils sont disponibles.
- Météo actuelle et prévisions datées pour les jours du séjour disponibles.
- Calcul d’un sous-total vols + hébergement et gestion des résultats manquants.
- Export PDF du voyage affiché, conservé pendant la session Streamlit.

## Architecture

```text
Streamlit → FastAPI POST /run → Coordinateur Google ADK
                                  ├── Agent vols → Google Flights / SerpApi
                                  ├── Agent hôtels → Google Hotels / SerpApi
                                  ├── Agent activités → Geoapify / OpenStreetMap
                                  └── Agent météo → OpenWeather / Open-Meteo
                                              ↓
                               Budget Python + synthèse Gemini / LiteLLM
```

Les quatre spécialistes sont des agents ADK `BaseAgent` qui exécutent des outils `FunctionTool`. Le coordinateur lance leurs recherches en parallèle et conserve les réponses disponibles si un fournisseur échoue. Chaque demande utilise une session ADK distincte.

Un `LlmAgent`, connecté au modèle par LiteLLM, produit une synthèse dans la réponse de l’API. L’interface affiche les cartes de résultats et le PDF ; elle n’affiche pas cette synthèse.

Deux modes sont disponibles :

- **Local**, par défaut : les agents tournent dans le même backend.
- **A2A** : le coordinateur appelle quatre services séparés avec `RemoteA2aAgent`. Chaque spécialiste expose une carte et des messages A2A ; seul le coordinateur expose `POST /run`.

## Installation

Prérequis : **Python 3.11** et une connexion Internet. Depuis la racine du dépôt, sous Windows PowerShell :

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Sous Linux ou macOS :

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
[ -f .env ] || cp .env.example .env
```

## Configuration

Compléter `.env` avec vos clés. Ce fichier est ignoré par Git ; `.env.example` contient uniquement le modèle de configuration.

| Variable | Utilisation | Obtenir une clé |
|---|---|---|
| `SERPAPI_API_KEY` | Vols et hôtels | [SerpApi](https://serpapi.com/manage-api-key) |
| `GEOAPIFY_API_KEY` | Lieux d’activités | [Geoapify](https://myprojects.geoapify.com/) |
| `OPENWEATHER_API_KEY` | Météo actuelle | [OpenWeather](https://home.openweathermap.org/api_keys) |
| `GEMINI_API_KEY` | Synthèse via LiteLLM | [Google AI Studio](https://aistudio.google.com/apikey) |

Open-Meteo ne nécessite pas de clé pour son endpoint public. Les conditions et quotas de chaque fournisseur s’appliquent ; consultez leur tarification avant utilisation.

```dotenv
VOYAGEPLUS_TRANSPORT=local
VOYAGEPLUS_ENABLE_LLM=true
VOYAGEPLUS_MODEL=gemini/gemini-3.1-flash-lite
```

La synthèse peut être désactivée avec `VOYAGEPLUS_ENABLE_LLM=false`. Les recherches restent disponibles si la clé du modèle manque ou si le modèle échoue. Pour changer de fournisseur, renseigner un identifiant compatible LiteLLM et sa clé dans `.env`.

## Lancement

Sous Windows :

```powershell
.\.venv\Scripts\python.exe launch.py
```

Sous Linux ou macOS :

```bash
.venv/bin/python launch.py
```

Le lanceur démarre les services et les arrête avec **Ctrl+C**.

- Interface : [localhost:8501](http://localhost:8501)
- Documentation de l’API : [localhost:8000/docs](http://localhost:8000/docs)
- État du backend : `GET /health`

Pour utiliser A2A, ajouter `--a2a` au lancement. Les services spécialisés utilisent les ports 8001 à 8004. Exemple de carte : `http://localhost:8001/a2a/.well-known/agent-card.json`.

Le premier chargement d’ADK peut être lent. Le lanceur attend jusqu’à 300 secondes ; `--startup-timeout 600` permet de prolonger ce délai. Si un port est occupé, arrêter le lancement précédent. Après une modification de `.env`, redémarrer l’application.

## Données et budget

| Agent | Données utilisées | Limites |
|---|---|---|
| Vols | Prix observés sur Google Flights via SerpApi | Un adulte, classe économique, deux billets simples, EUR ; tarifs à confirmer chez le vendeur |
| Hôtels | Prix Google Hotels pour les dates du séjour | Un adulte, EUR ; aucune réservation ni garantie de disponibilité |
| Activités | Lieux réels Geoapify, avec Nominatim et Overpass en secours | Les prix des billets et créneaux ne sont pas vérifiés ; horaires parfois absents |
| Météo | Observations OpenWeather et prévisions Open-Meteo | Les prévisions couvrent au plus les prochains 16 jours ; dates manquantes signalées |

Les vols aléatoires et les prix hôteliers calculés localement ont été supprimés. Une erreur de fournisseur donne un message explicite ; aucun prix inconnu n’est remplacé par zéro.

L’enveloppe hébergement représente 50 % du budget, divisée par le nombre de nuits. Le calcul retient les vols aller et retour et l’hébergement les moins chers parmi les résultats retournés. Le sous-total exclut les repas, billets d’activités, transports locaux, bagages et autres frais inconnus. Les enveloppes vols (35 %) et autres frais (15 %) sont indicatives.

Une recherche sans cache utilise deux appels SerpApi pour les vols et un pour les hôtels. Les résultats sont conservés dix minutes en mémoire ; les lieux Geoapify, cinq minutes. Les caches sont propres à chaque processus et partagent les quotas du compte fournisseur.

Pour les villes non répertoriées dans l’agent vols, utiliser un code IATA en majuscules, par exemple `CDG` ou `FCO`. Les autres agents utilisent la destination saisie comme nom de lieu ; un code d’aéroport peut donc limiter leurs résultats.

## API

`POST /run` accepte les champs suivants :

```json
{
  "origin": "Paris",
  "destination": "Rome",
  "start_date": "2027-05-10",
  "end_date": "2027-05-13",
  "budget": 1500,
  "priority": "best_location"
}
```

Choisir des dates à venir. `priority` accepte `best_location` ou `cheapest`. Pydantic valide les villes, dates et budget ; le retour doit suivre le départ. Les entrées invalides renvoient HTTP 422.

La réponse contient `flights`, `stay`, `activities`, `weather`, `budget`, `errors`, `summary`, `ai`, `sources` et `architecture`. Les erreurs partielles ne suppriment pas les résultats des autres agents.

## Vérification

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe -m pip check
```

Les tests couvrent ADK/A2A, les réponses des fournisseurs, les caches, le budget, les erreurs et l’interface. Les réponses externes sont remplacées par des fixtures pour éviter la consommation des quotas.

Les scripts suivants effectuent des **appels réseau réels** :

```powershell
.\.venv\Scripts\python.exe scripts/check_free_apis.py
.\.venv\Scripts\python.exe scripts/check_live.py
```

Le premier vérifie Geoapify et le modèle Gemini configuré. Le second vérifie les quatre agents en mode local, sans synthèse LLM, pour un séjour proche. Ils peuvent consommer des crédits ou quotas ; les clés ne sont pas affichées.

## Organisation du dépôt

```text
agents/          Agents ADK et intégrations des fournisseurs
common/          Runtime, API, contrats, outils partagés, budget et PDF
docs/            Note d’intégration ADK
scripts/         Vérifications réseau explicites
tests/           Tests automatisés
image/           Visuel de l’interface
travel_ui.py     Interface Streamlit
launch.py        Lancement et arrêt des services
.env.example     Modèle de configuration sans secrets
requirements.txt Dépendances épinglées
```

La note [docs/integration_adk.md](docs/integration_adk.md) détaille l’intégration. Le mémoire PDF présent localement sert de référence et n’est pas nécessaire pour exécuter l’application.

## Auteurs

Wissam AMEKRANE et Safae CHOUAI.
