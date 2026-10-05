"""Generate a portable travel booklet from the displayed search results."""
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer


def build_trip_pdf(trip, results):
    output = BytesIO()
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle('TripTitle', parent=styles['Title'], textColor=colors.HexColor('#E65100'), spaceAfter=18))
    styles['BodyText'].leading = 15
    story = []

    def text(value, style='BodyText'):
        story.append(Paragraph(escape(str(value)).replace('\n', '<br/>'), styles[style]))
        story.append(Spacer(1, 7))

    def money(value):
        return f'{value:.2f} EUR' if isinstance(value, (int, float)) else 'Non disponible'

    text('VoyagePlus · Carnet de voyage', 'TripTitle')
    text(f"{trip.get('origin', '')} → {trip.get('destination', '')}", 'Heading1')
    text(f"Du {trip.get('start_date', '')} au {trip.get('end_date', '')} · Budget : {money(trip.get('budget'))}")

    budget = results.get('budget') or {}
    text('Budget estimé', 'Heading2')
    text(f"Vols aller-retour : {money(budget.get('flight_cost_eur'))}\nHébergement : {money(budget.get('stay_cost_eur'))}\nSous-total vols + hébergement : {money(budget.get('estimated_subtotal_eur'))}\nReste sur le budget : {money(budget.get('remaining_eur'))}")
    text('Sous-total partiel : repas, activités, transports locaux, bagages et frais supplémentaires non inclus.')

    flights = results.get('flights') or {}
    for direction, label in [('aller', 'Vols aller'), ('retour', 'Vols retour')]:
        text(label + ' · prix observés', 'Heading2')
        offers = flights.get(direction, []) if isinstance(flights, dict) else []
        for offer in offers:
            text(f"{offer.get('airline', 'Compagnie')} · {offer.get('departure_time', '')} → {offer.get('arrival_time', '')}\nDurée : {offer.get('duration', '')} · Prix observé : {money(offer.get('price'))}")
        if not offers:
            text('Aucun vol disponible.')

    text('Hébergements', 'Heading2')
    stays = results.get('stay', [])
    if isinstance(stays, dict):
        stays = stays.get('stays', [])
    for stay in stays if isinstance(stays, list) else []:
        text(stay.get('name', 'Hébergement'), 'Heading3')
        text(f"{stay.get('address', 'Adresse non disponible')}\nType : {str(stay.get('type', '')).replace('_', ' ')}\nPrix observé par nuit : {money(stay.get('price_per_night_eur'))} · Total observé : {money(stay.get('total_price_eur'))}")
    if not stays or isinstance(stays, str):
        text(stays if isinstance(stays, str) else 'Aucun hébergement disponible.')

    text('Activités et lieux à découvrir', 'Heading2')
    activities = results.get('activities') or []
    for activity in activities:
        text(activity.get('name', 'Activité'), 'Heading3')
        text(f"{activity.get('category', '')} · {activity.get('address', 'Adresse non disponible')}\nDistance du centre : {activity.get('distance_km', 'Non disponible')} km")
    if not activities:
        text('Aucune activité disponible.')

    text('Météo actuelle', 'Heading2')
    weather = results.get('weather') or {}
    weather = weather.get('weather', weather)
    if weather and not weather.get('error'):
        text(f"Température : {weather.get('temperature', 'Non disponible')}\nHumidité : {weather.get('humidity', 'Non disponible')}\nConditions : {weather.get('condition', 'Non disponible')}\nConseil : {weather.get('tip', '')}")
    else:
        text(weather.get('error', 'Météo indisponible.'))
    if weather.get('daily'):
        text('Prévisions datées pour le séjour', 'Heading2')
        for day in weather['daily']:
            text(f"{day['date']} · {day['min_c']} à {day['max_c']} °C · Risque de pluie : {day['rain_probability_pct']} %")
    for warning in weather.get('warnings', []):
        text(warning)
    if results.get('errors'):
        text('Résultats manquants', 'Heading2')
        for name, message in results['errors'].items():
            text(f'{name} : {message}')

    def footer(canvas, doc):
        canvas.setFont('Helvetica', 9)
        canvas.setFillColor(colors.grey)
        canvas.drawString(42, 25, 'VoyagePlus · Document de préparation du voyage')
        canvas.drawRightString(A4[0] - 42, 25, str(doc.page))

    SimpleDocTemplate(output, pagesize=A4, rightMargin=42, leftMargin=42, topMargin=42, bottomMargin=42,
                      title=f"VoyagePlus - {trip.get('destination', 'Voyage')}").build(story, onFirstPage=footer, onLaterPages=footer)
    return output.getvalue()
