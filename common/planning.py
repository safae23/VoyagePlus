def budget_summary(trip, results):
    flights = results.get("flights", {})
    stays = results.get("stay", [])
    outbound = flights.get("aller", []) if isinstance(flights, dict) else []
    inbound = flights.get("retour", []) if isinstance(flights, dict) else []
    cheapest_out = min(outbound, key=lambda x: x["price"], default=None)
    cheapest_in = min(inbound, key=lambda x: x["price"], default=None)
    cheapest_stay = min(stays, key=lambda x: x["total_price_eur"], default=None) if isinstance(stays, list) else None
    flight_cost = round(cheapest_out["price"] + cheapest_in["price"], 2) if cheapest_out and cheapest_in else None
    stay_cost = cheapest_stay["total_price_eur"] if cheapest_stay else None
    subtotal = round(flight_cost + stay_cost, 2) if flight_cost is not None and stay_cost is not None else None
    return {
        "total_budget_eur": trip.budget, "nights": trip.nights,
        "lodging_envelope_eur": round(trip.budget * .5, 2),
        "flight_envelope_eur": round(trip.budget * .35, 2),
        "other_envelope_eur": round(trip.budget * .15, 2),
        "lodging_per_night_eur": trip.lodging_per_night,
        "selected_flights": {"aller": cheapest_out, "retour": cheapest_in},
        "selected_stay": cheapest_stay,
        "flight_cost_eur": flight_cost, "stay_cost_eur": stay_cost,
        "estimated_subtotal_eur": subtotal,
        "remaining_eur": round(trip.budget - subtotal, 2) if subtotal is not None else None,
        "within_budget": subtotal <= trip.budget if subtotal is not None else None,
        "complete_total": False,
        "excluded_costs": ["activités", "repas", "transports locaux", "bagages et frais supplémentaires"],
    }


def basic_summary(trip, budget):
    subtotal = budget["estimated_subtotal_eur"]
    cost = f"Le sous-total estimé vols + hébergement est de {subtotal:.2f} EUR." if subtotal is not None else "Les données disponibles ne permettent pas de calculer le sous-total vols + hébergement."
    return (f"Séjour à {trip.destination} de {trip.nights} nuits. {cost} "
            "Les prix des vols sont observés sur Google Flights et les tarifs d'hébergement observés sur Google Hotels. "
            "Les repas, activités et transports locaux restent à prévoir. La météo distingue les observations actuelles des prévisions disponibles.")
