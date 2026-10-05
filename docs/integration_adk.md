# Intégration VoyagePlus

Mise à jour : 5 octobre 2026. Le mémoire PDF reste inchangé.

Google ADK exécute quatre agents spécialisés et un coordinateur. Les recherches restent des outils Python ; le modèle via LiteLLM synthétise uniquement les résultats disponibles. Les échanges utilisent le Runner ADK local ou RemoteA2aAgent avec VOYAGEPLUS_TRANSPORT=a2a.

| Agent | Source réelle | Limite |
|---|---|---|
| Vols | Google Flights via SerpApi, horaires, escales, prix EUR | Deux billets simples pour un adulte ; prix observé à confirmer |
| Hébergements | Google Hotels via SerpApi, tarifs aux dates demandées | Total retourné par la source ; réservation non garantie |
| Activités | Geoapify / OpenStreetMap, lieux, adresses, coordonnées | Horaires et sites lorsqu'ils existent ; billets et créneaux non vérifiés |
| Météo | OpenWeather actuel + Open-Meteo pour les jours du séjour | Prévisions limitées aux prochains 16 jours ; dates manquantes explicites |

Les prix hôteliers calculés localement et les vols aléatoires ont été supprimés. Une erreur ou un quota épuisé donne un résultat vide et un message explicite. Aucun montant inconnu n'est remplacé par zéro. Le sous-total vols + hôtel reste partiel : repas, activités, transports locaux et frais supplémentaires ne sont pas inclus.

Clés dans .env : SERPAPI_API_KEY, GEOAPIFY_API_KEY, OPENWEATHER_API_KEY, GEMINI_API_KEY. Elles ne sont jamais affichées dans les tests ni ajoutées au PDF. Les recherches SerpApi sont conservées dix minutes en mémoire et partagent le quota du compte ; les lieux Geoapify sont conservés cinq minutes.

L'interface affiche les cartes, les liens de consultation et les prévisions datées. Le bouton final exporte le même voyage dans un PDF paginé. Les mentions de sources, les dates de consultation et les liens techniques ont été retirés du PDF à la demande de l’utilisateur. La synthèse et les paragraphes répétitifs ne sont plus affichés en tête de page.

Les tests couvrent le Runner ADK, les cartes et échanges A2A, les tarifs observés, les erreurs et quotas, le respect des dates de prévision, les calculs du budget et l'export dans l'interface. Les tests automatisés simulent les réponses des fournisseurs pour ne pas consommer les quotas ; les appels réels sont contrôlés séparément.
