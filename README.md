# VoyagePlus

VoyagePlus est un projet qui aide à préparer un séjour à partir d’une ville de départ, d’une destination, des dates et d’un budget. Il rassemble des offres de vols et d’hébergements, des lieux à visiter et la météo, puis permet de télécharger un carnet de voyage en PDF.

Le projet utilise **Streamlit**, **FastAPI**, **Google ADK**, **LiteLLM** et le protocole **A2A**.

## Fonctionnalités

- Recherche de vols aller et retour avec horaires, escales et prix.
- Recherche de tarifs d’hébergements pour les dates demandées.
- Découverte de lieux d’activités avec adresses et horaires lorsqu’ils sont disponibles.
- Météo actuelle et prévisions datées pour les jours du séjour disponibles.
- Calcul d’un sous-total vols + hébergement et gestion des résultats manquants.
- Export PDF du voyage affiché, conservé pendant la session Streamlit.

## Architecture

```text
Streamlit → FastAPI POST /run → Coordinateur Google ADK
                                  ├── Agent vols → Google Flights via SerpApi
                                  ├── Agent hôtels → Google Hotels 
                                  ├── Agent activités → Geoapify 
                                  └── Agent météo → OpenWeather 
                                              ↓
                               Budget Python + synthèse Gemini / LiteLLM
```

Les quatre spécialistes sont des agents ADK `BaseAgent` qui exécutent des outils `FunctionTool`. Le coordinateur lance leurs recherches en parallèle et conserve les réponses disponibles si un fournisseur échoue. Chaque demande utilise une session ADK distincte.

Un `LlmAgent`, connecté au modèle par LiteLLM. L’interface affiche les cartes de résultats et le PDF.

Deux modes sont disponibles :

- **Local**, par défaut : les agents tournent dans le même backend.
- **A2A** : le coordinateur appelle quatre services séparés avec `RemoteA2aAgent`. Chaque spécialiste expose une carte et des messages A2A ; seul le coordinateur expose `POST /run`.

## Installation

Prérequis : **Python 3.11**:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Sous Linux ou macOS :

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## Configuration

Compléter `.env` avec vos clés.
Pour changer de fournisseur, renseigner un identifiant compatible LiteLLM et sa clé dans `.env`.

## Lancement

Sous Windows :

```powershell
.\.venv\Scripts\python.exe launch.py
```

Sous Linux ou macOS :

```bash
.venv/bin/python launch.py
```

- Interface : [localhost:8501](http://localhost:8501)
- Documentation de l’API : [localhost:8000/docs](http://localhost:8000/docs)
- État du backend : `GET /health`

Pour utiliser A2A, ajouter `--a2a` au lancement. Les services spécialisés utilisent les ports 8001 à 8004. Exemple de carte : `http://localhost:8001/a2a/.well-known/agent-card.json`.


## Données et budget

| Agent | Données utilisées | Limites |
|---|---|---|
| Vols | Prix observés sur Google Flights via SerpApi | Un adulte, classe économique, deux billets simples, EUR |
| Hôtels | Prix Google Hotels pour les dates du séjour | Un adulte, EUR ; aucune réservation ni garantie de disponibilité |
| Activités | Lieux réels Geoapify | Les horaires parfois absents |
| Météo | Observations OpenWeather et prévisions Open-Meteo | Les prévisions couvrent au plus les prochains 16 jours |


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
