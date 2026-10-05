"""Observed one-way fares from Google Flights through SerpApi."""
import asyncio
from datetime import datetime, timezone
import math
import os
import re
import time
import unicodedata
from urllib.parse import urlparse
import httpx
from dotenv import load_dotenv
load_dotenv()
AIRPORTS = {'paris':'CDG,ORY', 'rome':'FCO,CIA', 'rabat':'RBA', 'casablanca':'CMN', 'marrakech':'RAK', 'madrid':'MAD', 'barcelone':'BCN', 'barcelona':'BCN', 'londres':'LHR,LGW,STN,LTN,LCY', 'london':'LHR,LGW,STN,LTN,LCY', 'lisbonne':'LIS', 'lisbon':'LIS', 'istanbul':'IST,SAW', 'tunis':'TUN', 'alger':'ALG', 'berlin':'BER', 'amsterdam':'AMS', 'bruxelles':'BRU', 'brussels':'BRU', 'dubai':'DXB', 'new york':'JFK,EWR,LGA', 'tokyo':'HND,NRT', 'nice':'NCE', 'lyon':'LYS', 'marseille':'MRS', 'bordeaux':'BOD', 'toulouse':'TLS', 'porto':'OPO', 'agadir':'AGA', 'tanger':'TNG', 'fes':'FEZ'}
_cache = {}

class FlightSearchError(Exception):
    """A public diagnostic that cannot contain credentials from request URLs."""

def airport_id(city):
    city = city.strip()
    if re.fullmatch(r'[A-Z]{3}(,[A-Z]{3})*', city): return city
    normalized = ''.join(c for c in unicodedata.normalize('NFKD', city.casefold()) if not unicodedata.combining(c))
    return AIRPORTS.get(normalized)

async def offers(client, departure, arrival, day, key):
    cache_key = (departure, arrival, day, key)
    cached = _cache.get(cache_key)
    if cached and time.monotonic() - cached[0] < 600: return cached[1]
    response = await client.get('https://serpapi.com/search.json', params={'engine':'google_flights', 'departure_id':departure, 'arrival_id':arrival, 'outbound_date':day, 'type':2, 'currency':'EUR', 'hl':'fr', 'gl':'fr', 'adults':1, 'travel_class':1, 'api_key':key}, timeout=40)
    if response.status_code in (401,403): raise FlightSearchError('Clé SerpApi refusée. Vérifiez SERPAPI_API_KEY dans .env.')
    if response.status_code == 429: raise FlightSearchError('Quota SerpApi atteint.')
    response.raise_for_status()
    body = response.json()
    if body.get('error'): raise FlightSearchError('Recherche SerpApi impossible : vérifiez les aéroports, dates et quota.')
    search_url = body.get('search_metadata', {}).get('google_flights_url', '')
    parsed = urlparse(search_url)
    if parsed.scheme != 'https' or parsed.hostname not in {'www.google.com', 'google.com'}:
        search_url = 'https://www.google.com/travel/flights'
    observed = datetime.now(timezone.utc).isoformat()
    items = []
    for offer in body.get('best_flights', []) + body.get('other_flights', []):
        segments = offer.get('flights') or []
        price = offer.get('price')
        if not segments or not isinstance(price,(int,float)) or not math.isfinite(price) or price < 0: continue
        first,last = segments[0],segments[-1]
        duration = offer.get('total_duration',sum(s.get('duration',0) for s in segments))
        items.append({'airline':' / '.join(dict.fromkeys(s.get('airline','Compagnie') for s in segments)), 'departure_time':first.get('departure_airport',{}).get('time',''), 'arrival_time':last.get('arrival_airport',{}).get('time',''), 'departure_airport':first.get('departure_airport',{}).get('id',departure), 'arrival_airport':last.get('arrival_airport',{}).get('id',arrival), 'duration':f'{duration // 60}h {duration % 60}min', 'price':price, 'date':day, 'currency':'EUR', 'stops':len(segments)-1, 'segments':segments, 'source':'Google Flights via SerpApi', 'price_kind':'observed', 'price_scope':'one_way', 'observed_at':observed, 'search_url':search_url})
    items = sorted(items,key=lambda item:item['price'])[:5]
    if len(_cache)>=128: _cache.pop(next(iter(_cache)))
    _cache[cache_key]=(time.monotonic(),items)
    return items

async def execute(request):
    result={'flights':{'aller':[], 'retour':[]}}
    key=os.getenv('SERPAPI_API_KEY','').strip()
    if not key: return {**result,'error':'Clé SerpApi absente : ajoutez SERPAPI_API_KEY dans .env.'}
    origin,destination=airport_id(request.get('origin','')),airport_id(request.get('destination',''))
    if not origin or not destination: return {**result,'error':'Ville non reconnue pour les vols. Saisissez un code IATA en majuscules (ex. CDG, FCO).'}
    try:
        start=datetime.strptime(request['start_date'],'%Y-%m-%d').date()
        end=datetime.strptime(request['end_date'],'%Y-%m-%d').date()
        if start < datetime.now(timezone.utc).date() or end <= start: return {**result,'error':'Choisissez un départ à venir et un retour après le départ.'}
    except (ValueError,KeyError,TypeError): return {**result,'error':'Dates de vol invalides.'}
    async with httpx.AsyncClient() as client:
        answers=await asyncio.gather(offers(client,origin,destination,start.isoformat(),key), offers(client,destination,origin,end.isoformat(),key), return_exceptions=True)
    errors=[]
    for direction,answer in zip(('aller','retour'),answers):
        if isinstance(answer,Exception):
            message=str(answer) if isinstance(answer,FlightSearchError) else 'Service de vols indisponible. Réessayez plus tard.'
            errors.append(f'{direction} : {message}')
        else:
            result['flights'][direction]=answer
            if not answer: errors.append(f'{direction} : aucune offre réelle trouvée pour ces dates.')
    if errors: result['error']=' '.join(errors)
    return result
