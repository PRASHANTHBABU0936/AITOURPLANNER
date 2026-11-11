# """
# Research tools using Open-Meteo (Geocoding & Weather) + Country APIs
# """
# import requests
# from typing import Dict, Any, List, Optional

# _HEADERS = {"User-Agent": "TravelPlannerAssistant/1.0"}

# # WMO Weather Interpretation Codes
# WMO_WEATHER_CODES = {
#     0: "Clear sky",
#     1: "Mainly clear",
#     2: "Partly cloudy",
#     3: "Overcast",
#     45: "Fog",
#     48: "Depositing rime fog",
#     51: "Light drizzle",
#     53: "Moderate drizzle",
#     55: "Dense drizzle",
#     61: "Slight rain",
#     63: "Moderate rain",
#     65: "Heavy rain",
#     71: "Slight snow fall",
#     73: "Moderate snow fall",
#     75: "Heavy snow fall",
#     80: "Slight rain showers",
#     81: "Moderate rain showers",
#     82: "Violent rain showers",
#     95: "Thunderstorm",
#     96: "Thunderstorm with slight hail",
#     99: "Thunderstorm with heavy hail",
# }


# def _get_location_and_weather(destination: str) -> Dict[str, Any]:
#     """
#     Fetch location coordinates and weather using Open-Meteo APIs.
#     No API key required.
#     """
#     result: Dict[str, Any] = {
#         "location": {},
#         "weather": {}
#     }
    
#     try:
#         # 1. Open-Meteo Geocoding
#         geo_url = "https://geocoding-api.open-meteo.com/v1/search"
#         resp = requests.get(
#             geo_url,
#             params={"name": destination, "count": 10, "language": "en", "format": "json"},
#             headers=_HEADERS,
#             timeout=10,
#         )
#         if resp.status_code == 200:
#             data = resp.json()
#             results = data.get("results", [])
            
#             if results:
#                 # Find best matching result
#                 matched = None
#                 dest_clean = destination.strip().lower()
                
#                 # Check for exact name match
#                 exact_matches = [
#                     r for r in results if r.get("name", "").strip().lower() == dest_clean
#                 ]
#                 if exact_matches:
#                     # Prefer exact match with highest population or first
#                     exact_matches.sort(key=lambda x: x.get("population") or 0, reverse=True)
#                     matched = exact_matches[0]
#                 else:
#                     # Fallback to result with highest population
#                     sorted_by_pop = sorted(results, key=lambda x: x.get("population") or 0, reverse=True)
#                     matched = sorted_by_pop[0]
                
#                 lat = matched.get("latitude")
#                 lon = matched.get("longitude")
#                 country = matched.get("country", "")
#                 country_code = matched.get("country_code", "")
#                 admin1 = matched.get("admin1", "")
#                 pop = matched.get("population")
#                 timezone = matched.get("timezone", "UTC")
                
#                 result["location"] = {
#                     "name": matched.get("name", destination),
#                     "country": country,
#                     "country_code": country_code,
#                     "region": admin1,
#                     "latitude": lat,
#                     "longitude": lon,
#                     "population": pop,
#                     "timezone": timezone,
#                 }
                
#                 # 2. Open-Meteo Weather Forecast
#                 if lat is not None and lon is not None:
#                     weather_url = "https://api.open-meteo.com/v1/forecast"
#                     w_resp = requests.get(
#                         weather_url,
#                         params={
#                             "latitude": lat,
#                             "longitude": lon,
#                             "current_weather": "true",
#                             "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
#                             "timezone": timezone or "auto",
#                         },
#                         headers=_HEADERS,
#                         timeout=10,
#                     )
#                     if w_resp.status_code == 200:
#                         w_data = w_resp.json()
#                         cw = w_data.get("current_weather", {})
#                         daily = w_data.get("daily", {})
                        
#                         code = cw.get("weathercode", 0)
#                         condition = WMO_WEATHER_CODES.get(code, "Clear/Mild")
                        
#                         max_temps = daily.get("temperature_2m_max", [])
#                         min_temps = daily.get("temperature_2m_min", [])
#                         avg_max = round(sum(max_temps) / len(max_temps), 1) if max_temps else cw.get("temperature")
#                         avg_min = round(sum(min_temps) / len(min_temps), 1) if min_temps else cw.get("temperature")
                        
#                         result["weather"] = {
#                             "current_temp_c": cw.get("temperature"),
#                             "wind_speed_kmh": cw.get("windspeed"),
#                             "condition": condition,
#                             "avg_max_temp_c": avg_max,
#                             "avg_min_temp_c": avg_min,
#                         }
#     except Exception:
#         pass
        
#     return result


# def _get_country_info(country_name: str, country_code: str = "") -> Dict[str, Any]:
#     """
#     Fetch country and currency details using CountriesNow API.
#     No API key required.
#     """
#     country_data: Dict[str, Any] = {}
#     if not country_name and not country_code:
#         return country_data

#     try:
#         url = "https://countriesnow.space/api/v0.1/countries/currency"
#         resp = requests.get(url, headers=_HEADERS, timeout=10)
#         if resp.status_code == 200:
#             all_countries = resp.json().get("data", [])
#             match = None
#             q_name = country_name.strip().lower()
#             q_code = country_code.strip().upper()

#             for c in all_countries:
#                 if q_code and c.get("iso2", "").upper() == q_code:
#                     match = c
#                     break
#                 if q_name and (c.get("name", "").lower() == q_name or q_name in c.get("name", "").lower()):
#                     match = c
#                     break

#             if match:
#                 country_data = {
#                     "country": match.get("name"),
#                     "currency_code": match.get("currency"),
#                     "iso2": match.get("iso2"),
#                     "iso3": match.get("iso3"),
#                 }
#     except Exception:
#         pass

#     return country_data


# def get_destination_info(destination: str) -> str:
#     """
#     Fetch real destination data using Open-Meteo & Country APIs.
#     Returns a formatted string consumed by the research agent.
#     """
#     loc_weather = _get_location_and_weather(destination)
#     location = loc_weather.get("location", {})
#     weather = loc_weather.get("weather", {})
    
#     country_name = location.get("country", destination)
#     country_code = location.get("country_code", "")
#     country_info = _get_country_info(country_name, country_code)

#     sections: List[str] = [f"Destination: {destination}"]

#     if location:
#         pop = location.get("population")
#         pop_str = f"{pop:,}" if isinstance(pop, int) and pop > 0 else "N/A"
#         region_str = f", Region: {location.get('region')}" if location.get("region") else ""
#         sections.append(
#             f"\nLocation Facts:"
#             f"\n- Matched Place: {location.get('name', destination)}"
#             f"\n- Country: {country_name} ({country_code}){region_str}"
#             f"\n- Population: {pop_str}"
#             f"\n- Coordinates: Lat {location.get('latitude')}, Lon {location.get('longitude')}"
#             f"\n- Timezone: {location.get('timezone', 'UTC')}"
#         )

#     if weather:
#         sections.append(
#             f"\nLive Weather (Open-Meteo):"
#             f"\n- Condition: {weather.get('condition', 'N/A')}"
#             f"\n- Current Temp: {weather.get('current_temp_c', 'N/A')}°C"
#             f"\n- Forecast Range: {weather.get('avg_min_temp_c', 'N/A')}°C to {weather.get('avg_max_temp_c', 'N/A')}°C"
#             f"\n- Wind Speed: {weather.get('wind_speed_kmh', 'N/A')} km/h"
#         )

#     if country_info:
#         sections.append(
#             f"\nCountry & Currency Information:"
#             f"\n- Country Name: {country_info.get('country', country_name)}"
#             f"\n- Official Currency: {country_info.get('currency_code', 'N/A')}"
#             f"\n- Country Code: {country_info.get('iso2', country_code)}"
#         )

#     return "\n".join(sections)


# def search_attractions(destination: str, category: str = "all") -> List[str]:
#     """
#     Returns search query description for attractions.
#     """
#     loc_weather = _get_location_and_weather(destination)
#     location = loc_weather.get("location", {})
#     matched_name = location.get("name", destination)
#     country = location.get("country", "")
#     return [f"Top attractions in {matched_name}, {country} ({category})"]


# def estimate_costs(destination: str, travel_style: str) -> Dict[str, float]:
#     """
#     Estimate daily base costs depending on travel style.
#     """
#     base = {
#         "budget":   {"accommodation": 25, "food": 15, "activities": 10, "transport": 8},
#         "moderate": {"accommodation": 70, "food": 40, "activities": 30, "transport": 18},
#         "luxury":   {"accommodation": 200, "food": 120, "activities": 80, "transport": 45},
#     }.get(travel_style.lower(), {"accommodation": 70, "food": 40, "activities": 30, "transport": 18})

#     return base


# def convert_currency(amount: float, from_currency: str, to_currency: str) -> float:
#     """
#     Convert amount between currencies (returns same amount if equal or simple fallback).
#     """
#     if from_currency.upper() == to_currency.upper():
#         return round(amount, 2)
#     return round(amount, 2)


# __all__ = ["get_destination_info", "search_attractions", "estimate_costs", "convert_currency"]


# """
# Research tools using Open-Meteo + CountriesNow.
# No API keys required.
# """

# import requests
# from typing import Dict, Any, List


# HEADERS = {
#     "User-Agent": "TravelPlannerAssistant/1.0"
# }

# OPEN_METEO_GEOCODING = "https://geocoding-api.open-meteo.com/v1/search"
# OPEN_METEO_WEATHER = "https://api.open-meteo.com/v1/forecast"
# COUNTRIES_NOW = "https://countriesnow.space/api/v0.1/countries/currency"


# # WMO weather codes
# WMO_WEATHER_CODES = {
#     0: "Clear sky",
#     1: "Mainly clear",
#     2: "Partly cloudy",
#     3: "Overcast",
#     45: "Fog",
#     48: "Depositing rime fog",
#     51: "Light drizzle",
#     53: "Moderate drizzle",
#     55: "Dense drizzle",
#     61: "Slight rain",
#     63: "Moderate rain",
#     65: "Heavy rain",
#     71: "Slight snow",
#     73: "Moderate snow",
#     75: "Heavy snow",
#     80: "Slight rain showers",
#     81: "Moderate rain showers",
#     82: "Violent rain showers",
#     95: "Thunderstorm",
#     96: "Thunderstorm with slight hail",
#     99: "Thunderstorm with heavy hail",
# }


# # Important for ambiguous destinations.
# # Open-Meteo may return Genoa when searching "Goa".
# # DESTINATION_HINTS = {
# #     "goa": {
# #         "country_code": "IN",
# #         "country": "India",
# #     },
# #     "bali": {
# #         "country_code": "ID",
# #         "country": "Indonesia",
# #     },
# # }

# DESTINATION_HINTS = {
#     "goa": {
#         "country_code": "IN",
#         "country": "India",
#         "latitude": 15.2993,
#         "longitude": 74.1240,
#     },
#     "bali": {
#         "country_code": "ID",
#         "country": "Indonesia",
#         "latitude": -8.4095,
#         "longitude": 115.1889,
#     },
# }

# def _get_location_and_weather(destination: str) -> Dict[str, Any]:
#     """
#     Get destination coordinates and weather using Open-Meteo.
#     No API key required.
#     """

#     result = {
#         "location": {},
#         "weather": {},
#     }

#     try:
#         # ---------------------------------------------------------
#         # 1. GEOCODING
#         # ---------------------------------------------------------
#         response = requests.get(
#             OPEN_METEO_GEOCODING,
#             params={
#                 "name": destination,
#                 "count": 10,
#                 "language": "en",
#                 "format": "json",
#             },
#             headers=HEADERS,
#             timeout=10,
#         )

#         if response.status_code != 200:
#             print(
#                 f"Open-Meteo geocoding failed: "
#                 f"HTTP {response.status_code}"
#             )
#             return result

#         results = response.json().get("results", [])

#         if not results:
#             print(f"No location found for: {destination}")
#             return result

#         destination_clean = destination.strip().lower()

#         # ---------------------------------------------------------
#         # 2. SMART DESTINATION MATCHING
#         # ---------------------------------------------------------
#         matched = None

#         hint = DESTINATION_HINTS.get(destination_clean)

#         # First: use known country hint.
#         if hint:
#             country_matches = [
#                 item
#                 for item in results
#                 if item.get("country_code", "").upper()
#                 == hint["country_code"]
#             ]

#             exact_country_matches = [
#                 item
#                 for item in country_matches
#                 if item.get("name", "").strip().lower()
#                 == destination_clean
#             ]

#             if exact_country_matches:
#                 matched = max(
#                     exact_country_matches,
#                     key=lambda x: x.get("population") or 0,
#                 )

#             elif country_matches:
#                 matched = max(
#                     country_matches,
#                     key=lambda x: x.get("population") or 0,
#                 )

#         # Second: exact name match.
#         if matched is None:
#             exact_matches = [
#                 item
#                 for item in results
#                 if item.get("name", "").strip().lower()
#                 == destination_clean
#             ]

#             if exact_matches:
#                 matched = max(
#                     exact_matches,
#                     key=lambda x: x.get("population") or 0,
#                 )

#         # Third: first Open-Meteo result.
#         if matched is None:
#             matched = results[0]

#         latitude = matched.get("latitude")
#         longitude = matched.get("longitude")

#         country = matched.get("country", "")
#         country_code = matched.get("country_code", "")
#         region = matched.get("admin1", "")
#         timezone = matched.get("timezone", "UTC")

#         result["location"] = {
#             "name": matched.get("name", destination),
#             "country": country,
#             "country_code": country_code,
#             "region": region,
#             "latitude": latitude,
#             "longitude": longitude,
#             "population": matched.get("population"),
#             "timezone": timezone,
#         }

#         # ---------------------------------------------------------
#         # 3. WEATHER
#         # ---------------------------------------------------------
#         if latitude is None or longitude is None:
#             return result

#         weather_response = requests.get(
#             OPEN_METEO_WEATHER,
#             params={
#                 "latitude": latitude,
#                 "longitude": longitude,
#                 "current": (
#                     "temperature_2m,"
#                     "wind_speed_10m,"
#                     "weather_code"
#                 ),
#                 "daily": (
#                     "temperature_2m_max,"
#                     "temperature_2m_min,"
#                     "precipitation_sum"
#                 ),
#                 "forecast_days": 3,
#                 "timezone": timezone or "auto",
#             },
#             headers=HEADERS,
#             timeout=10,
#         )

#         if weather_response.status_code != 200:
#             print(
#                 f"Open-Meteo weather failed: "
#                 f"HTTP {weather_response.status_code}"
#             )
#             return result

#         weather_data = weather_response.json()

#         current = weather_data.get("current", {})
#         daily = weather_data.get("daily", {})

#         max_temperatures = daily.get(
#             "temperature_2m_max",
#             [],
#         )

#         min_temperatures = daily.get(
#             "temperature_2m_min",
#             [],
#         )

#         average_max = (
#             round(
#                 sum(max_temperatures)
#                 / len(max_temperatures),
#                 1,
#             )
#             if max_temperatures
#             else None
#         )

#         average_min = (
#             round(
#                 sum(min_temperatures)
#                 / len(min_temperatures),
#                 1,
#             )
#             if min_temperatures
#             else None
#         )

#         weather_code = current.get("weather_code")

#         result["weather"] = {
#             "current_temp_c": current.get(
#                 "temperature_2m"
#             ),
#             "wind_speed_kmh": current.get(
#                 "wind_speed_10m"
#             ),
#             "condition": WMO_WEATHER_CODES.get(
#                 weather_code,
#                 "Unknown",
#             ),
#             "avg_max_temp_c": average_max,
#             "avg_min_temp_c": average_min,
#         }

#     except requests.RequestException as e:
#         print(f"Network error in location/weather: {e}")

#     except Exception as e:
#         print(f"Location/weather error: {e}")

#     return result


# def _get_country_info(
#     country_name: str,
#     country_code: str = "",
# ) -> Dict[str, Any]:
#     """
#     Get country and currency information using CountriesNow.
#     No API key required.
#     """

#     if not country_name and not country_code:
#         return {}

#     try:
#         response = requests.get(
#             COUNTRIES_NOW,
#             headers=HEADERS,
#             timeout=10,
#         )

#         if response.status_code != 200:
#             print(
#                 f"CountriesNow failed: "
#                 f"HTTP {response.status_code}"
#             )
#             return {}

#         countries = response.json().get(
#             "data",
#             [],
#         )

#         requested_code = country_code.upper()
#         requested_name = country_name.strip().lower()

#         # Prefer ISO country code.
#         if requested_code:
#             for country in countries:
#                 if (
#                     country.get("iso2", "").upper()
#                     == requested_code
#                 ):
#                     return {
#                         "country": country.get("name"),
#                         "currency_code": country.get(
#                             "currency"
#                         ),
#                         "iso2": country.get("iso2"),
#                         "iso3": country.get("iso3"),
#                     }

#         # Fallback to country name.
#         for country in countries:
#             name = country.get(
#                 "name",
#                 "",
#             ).strip().lower()

#             if name == requested_name:
#                 return {
#                     "country": country.get("name"),
#                     "currency_code": country.get(
#                         "currency"
#                     ),
#                     "iso2": country.get("iso2"),
#                     "iso3": country.get("iso3"),
#                 }

#     except requests.RequestException as e:
#         print(f"Network error in country lookup: {e}")

#     except Exception as e:
#         print(f"Country lookup error: {e}")

#     return {}


# def get_destination_info(destination: str) -> str:
#     """
#     Get destination information from Open-Meteo
#     and CountriesNow.

#     The returned text is consumed by the
#     Research Agent / OpenAI.
#     """

#     location_weather = _get_location_and_weather(
#         destination
#     )

#     location = location_weather.get(
#         "location",
#         {},
#     )

#     weather = location_weather.get(
#         "weather",
#         {},
#     )

#     country_name = location.get(
#         "country",
#         "",
#     )

#     country_code = location.get(
#         "country_code",
#         "",
#     )

#     country_info = _get_country_info(
#         country_name,
#         country_code,
#     )

#     sections = [
#         f"Destination: {destination}"
#     ]

#     # ---------------------------------------------------------
#     # LOCATION
#     # ---------------------------------------------------------
#     if location:
#         population = location.get(
#             "population"
#         )

#         population_text = (
#             f"{population:,}"
#             if isinstance(population, int)
#             else "N/A"
#         )

#         sections.append(
#             "\nLocation Facts:"
#             f"\n- Matched Place: "
#             f"{location.get('name', destination)}"
#             f"\n- Country: "
#             f"{country_name} ({country_code})"
#             f"\n- Region: "
#             f"{location.get('region', 'N/A')}"
#             f"\n- Population: "
#             f"{population_text}"
#             f"\n- Latitude: "
#             f"{location.get('latitude', 'N/A')}"
#             f"\n- Longitude: "
#             f"{location.get('longitude', 'N/A')}"
#             f"\n- Timezone: "
#             f"{location.get('timezone', 'UTC')}"
#         )

#     # ---------------------------------------------------------
#     # WEATHER
#     # ---------------------------------------------------------
#     if weather:
#         sections.append(
#             "\nLive Weather (Open-Meteo):"
#             f"\n- Condition: "
#             f"{weather.get('condition', 'N/A')}"
#             f"\n- Current Temperature: "
#             f"{weather.get('current_temp_c', 'N/A')}°C"
#             f"\n- 3-Day Minimum Temperature Average: "
#             f"{weather.get('avg_min_temp_c', 'N/A')}°C"
#             f"\n- 3-Day Maximum Temperature Average: "
#             f"{weather.get('avg_max_temp_c', 'N/A')}°C"
#             f"\n- Wind Speed: "
#             f"{weather.get('wind_speed_kmh', 'N/A')} km/h"
#         )

#     # ---------------------------------------------------------
#     # COUNTRY / CURRENCY
#     # ---------------------------------------------------------
#     if country_info:
#         sections.append(
#             "\nCountry & Currency Information:"
#             f"\n- Country: "
#             f"{country_info.get('country', country_name)}"
#             f"\n- Currency Code: "
#             f"{country_info.get('currency_code', 'N/A')}"
#             f"\n- ISO2: "
#             f"{country_info.get('iso2', country_code)}"
#             f"\n- ISO3: "
#             f"{country_info.get('iso3', 'N/A')}"
#         )

#     # ---------------------------------------------------------
#     # OPENAI RESEARCH INSTRUCTION
#     # ---------------------------------------------------------
#     sections.append(
#         "\nResearch Instructions:"
#         "\n- Use the supplied live location and weather "
#         "data when available."
#         "\n- Use your travel knowledge for attractions, "
#         "cuisine, best time to visit, entry requirements, "
#         "and practical travel tips."
#         "\n- Do not invent live weather values."
#         "\n- If some external data is unavailable, "
#         "continue using reliable general knowledge."
#     )

#     return "\n".join(sections)


# def search_attractions(
#     destination: str,
#     category: str = "all",
# ) -> List[str]:
#     """
#     Provide an attraction research hint.
#     The Research Agent uses OpenAI for detailed attractions.
#     """

#     location_weather = _get_location_and_weather(
#         destination
#     )

#     location = location_weather.get(
#         "location",
#         {},
#     )

#     matched_name = location.get(
#         "name",
#         destination,
#     )

#     country = location.get(
#         "country",
#         "",
#     )

#     return [
#         f"Top {category} attractions in "
#         f"{matched_name}, {country}. "
#         "Use travel knowledge to identify specific attractions."
#     ]


# def estimate_costs(
#     destination: str,
#     travel_style: str,
# ) -> Dict[str, float]:
#     """
#     Provide approximate daily baseline costs.

#     The main Budget Agent performs the final
#     destination-specific calculation.
#     """

#     base_costs = {
#         "budget": {
#             "accommodation": 25,
#             "food": 15,
#             "activities": 10,
#             "transport": 8,
#         },
#         "moderate": {
#             "accommodation": 70,
#             "food": 40,
#             "activities": 30,
#             "transport": 18,
#         },
#         "luxury": {
#             "accommodation": 200,
#             "food": 120,
#             "activities": 80,
#             "transport": 45,
#         },
#     }

#     return base_costs.get(
#         travel_style.lower(),
#         base_costs["moderate"],
#     )


# def convert_currency(
#     amount: float,
#     from_currency: str,
#     to_currency: str,
# ) -> float:
#     """
#     Currency conversion fallback.

#     The current Budget Agent already works in the
#     user's selected currency, so external conversion
#     is not required for the main workflow.
#     """

#     if (
#         from_currency.upper()
#         == to_currency.upper()
#     ):
#         return round(amount, 2)

#     # No external conversion required.
#     return round(amount, 2)


# __all__ = [
#     "get_destination_info",
#     "search_attractions",
#     "estimate_costs",
#     "convert_currency",
# ]




"""
Research tools using Open-Meteo + CountriesNow.

No API keys required for research tools.
"""

import requests
from typing import Dict, Any, List


# ============================================================
# API ENDPOINTS
# ============================================================

HEADERS = {
    "User-Agent": "TravelPlannerAssistant/1.0"
}

OPEN_METEO_GEOCODING = (
    "https://geocoding-api.open-meteo.com/v1/search"
)

OPEN_METEO_WEATHER = (
    "https://api.open-meteo.com/v1/forecast"
)

COUNTRIES_NOW = (
    "https://countriesnow.space/api/v0.1/countries/currency"
)


# ============================================================
# WEATHER CODE MAPPING
# ============================================================

WMO_WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


# ============================================================
# KNOWN DESTINATIONS
# ============================================================
#
# Open-Meteo can return ambiguous places.
#
# Example:
# "Goa" can return:
#   - Goa, Philippines
#   - Genoa, Italy
#   - Goa, India
#
# For these known destinations, we use reliable coordinates
# directly instead of trusting ambiguous geocoding results.
#

DESTINATION_HINTS = {
    "goa": {
        "name": "Goa",
        "country": "India",
        "country_code": "IN",
        "latitude": 15.2993,
        "longitude": 74.1240,
        "region": "Goa",
    },

    "bali": {
        "name": "Bali",
        "country": "Indonesia",
        "country_code": "ID",
        "latitude": -8.4095,
        "longitude": 115.1889,
        "region": "Bali",
    },
}


# ============================================================
# LOCATION + WEATHER
# ============================================================

def _get_location_and_weather(
    destination: str,
) -> Dict[str, Any]:
    """
    Get destination coordinates and weather.

    Uses known coordinates for ambiguous destinations.
    Otherwise uses Open-Meteo Geocoding.
    """

    result = {
        "location": {},
        "weather": {},
    }

    destination_clean = destination.strip().lower()

    try:

        # --------------------------------------------------------
        # 1. KNOWN DESTINATION
        # --------------------------------------------------------
        #
        # This completely avoids the Goa/Genoa/Philippines
        # problem.
        #

        hint = DESTINATION_HINTS.get(destination_clean)

        if hint:

            latitude = hint["latitude"]
            longitude = hint["longitude"]
            timezone = "auto"

            result["location"] = {
                "name": hint["name"],
                "country": hint["country"],
                "country_code": hint["country_code"],
                "region": hint["region"],
                "latitude": latitude,
                "longitude": longitude,
                "population": None,
                "timezone": timezone,
            }

        else:

            # ----------------------------------------------------
            # 2. OPEN-METEO GEOCODING
            # ----------------------------------------------------

            response = requests.get(
                OPEN_METEO_GEOCODING,
                params={
                    "name": destination,
                    "count": 10,
                    "language": "en",
                    "format": "json",
                },
                headers=HEADERS,
                timeout=10,
            )

            if response.status_code != 200:
                print(
                    "Open-Meteo geocoding failed: "
                    f"HTTP {response.status_code}"
                )
                return result

            results = response.json().get(
                "results",
                [],
            )

            if not results:
                print(
                    f"No Open-Meteo location found "
                    f"for: {destination}"
                )
                return result

            # ----------------------------------------------------
            # 3. SMART GENERAL MATCHING
            # ----------------------------------------------------

            matched = None

            # Exact name match first
            exact_matches = [
                item
                for item in results
                if item.get("name", "")
                .strip()
                .lower()
                == destination_clean
            ]

            if exact_matches:
                matched = max(
                    exact_matches,
                    key=lambda x: (
                        x.get("population") or 0
                    ),
                )

            # Otherwise use first result
            if matched is None:
                matched = results[0]

            latitude = matched.get(
                "latitude"
            )

            longitude = matched.get(
                "longitude"
            )

            timezone = matched.get(
                "timezone",
                "UTC",
            )

            result["location"] = {
                "name": matched.get(
                    "name",
                    destination,
                ),
                "country": matched.get(
                    "country",
                    "",
                ),
                "country_code": matched.get(
                    "country_code",
                    "",
                ),
                "region": matched.get(
                    "admin1",
                    "",
                ),
                "latitude": latitude,
                "longitude": longitude,
                "population": matched.get(
                    "population"
                ),
                "timezone": timezone,
            }

        # --------------------------------------------------------
        # 4. WEATHER FROM OPEN-METEO
        # --------------------------------------------------------

        location = result["location"]

        latitude = location.get(
            "latitude"
        )

        longitude = location.get(
            "longitude"
        )

        timezone = location.get(
            "timezone",
            "auto",
        )

        if latitude is None or longitude is None:
            print(
                "No valid coordinates available "
                f"for {destination}"
            )
            return result

        weather_response = requests.get(
            OPEN_METEO_WEATHER,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": (
                    "temperature_2m,"
                    "wind_speed_10m,"
                    "weather_code"
                ),
                "daily": (
                    "temperature_2m_max,"
                    "temperature_2m_min,"
                    "precipitation_sum"
                ),
                "forecast_days": 3,
                "timezone": timezone,
            },
            headers=HEADERS,
            timeout=10,
        )

        if weather_response.status_code != 200:
            print(
                "Open-Meteo weather failed: "
                f"HTTP {weather_response.status_code}"
            )
            return result

        weather_data = weather_response.json()

        current = weather_data.get(
            "current",
            {},
        )

        daily = weather_data.get(
            "daily",
            {},
        )

        max_temperatures = daily.get(
            "temperature_2m_max",
            [],
        )

        min_temperatures = daily.get(
            "temperature_2m_min",
            [],
        )

        # --------------------------------------------------------
        # Average forecast temperatures
        # --------------------------------------------------------

        if max_temperatures:
            average_max = round(
                sum(max_temperatures)
                / len(max_temperatures),
                1,
            )
        else:
            average_max = None

        if min_temperatures:
            average_min = round(
                sum(min_temperatures)
                / len(min_temperatures),
                1,
            )
        else:
            average_min = None

        weather_code = current.get(
            "weather_code"
        )

        result["weather"] = {
            "current_temp_c": current.get(
                "temperature_2m"
            ),
            "wind_speed_kmh": current.get(
                "wind_speed_10m"
            ),
            "condition": WMO_WEATHER_CODES.get(
                weather_code,
                "Unknown",
            ),
            "avg_max_temp_c": average_max,
            "avg_min_temp_c": average_min,
        }

    except requests.RequestException as e:

        print(
            "Network error while fetching "
            f"location/weather: {e}"
        )

    except Exception as e:

        print(
            "Location/weather error: "
            f"{e}"
        )

    return result


# ============================================================
# COUNTRY INFORMATION
# ============================================================

def _get_country_info(
    country_name: str,
    country_code: str = "",
) -> Dict[str, Any]:
    """
    Get country and currency information.

    Uses CountriesNow.
    No API key required.
    """

    if not country_name and not country_code:
        return {}

    try:

        response = requests.get(
            COUNTRIES_NOW,
            headers=HEADERS,
            timeout=10,
        )

        if response.status_code != 200:
            print(
                "CountriesNow failed: "
                f"HTTP {response.status_code}"
            )
            return {}

        countries = response.json().get(
            "data",
            [],
        )

        requested_code = (
            country_code.upper()
        )

        requested_name = (
            country_name
            .strip()
            .lower()
        )

        # --------------------------------------------------------
        # Match by ISO2
        # --------------------------------------------------------

        if requested_code:

            for country in countries:

                if (
                    country.get(
                        "iso2",
                        "",
                    ).upper()
                    == requested_code
                ):

                    return {
                        "country": country.get(
                            "name"
                        ),
                        "currency_code": country.get(
                            "currency"
                        ),
                        "iso2": country.get(
                            "iso2"
                        ),
                        "iso3": country.get(
                            "iso3"
                        ),
                    }

        # --------------------------------------------------------
        # Match by country name
        # --------------------------------------------------------

        for country in countries:

            name = (
                country.get(
                    "name",
                    "",
                )
                .strip()
                .lower()
            )

            if name == requested_name:

                return {
                    "country": country.get(
                        "name"
                    ),
                    "currency_code": country.get(
                        "currency"
                    ),
                    "iso2": country.get(
                        "iso2"
                    ),
                    "iso3": country.get(
                        "iso3"
                    ),
                }

    except requests.RequestException as e:

        print(
            "Network error in country lookup: "
            f"{e}"
        )

    except Exception as e:

        print(
            "Country lookup error: "
            f"{e}"
        )

    return {}


# ============================================================
# PUBLIC HELPERS (reused by the research MCP server)
# ============================================================

def get_location_and_weather(
    destination: str,
) -> Dict[str, Any]:
    """Public alias of the Open-Meteo location/weather lookup."""
    return _get_location_and_weather(destination)


def get_country_currency(
    country_name: str = "",
    country_code: str = "",
) -> Dict[str, Any]:
    """Public alias of the CountriesNow country/currency lookup."""
    return _get_country_info(country_name, country_code)


# ============================================================
# MAIN RESEARCH FUNCTION
# ============================================================

def get_destination_info(
    destination: str,
) -> str:
    """
    Get destination information from:

    1. Open-Meteo
       - Coordinates
       - Location
       - Current weather
       - Forecast temperatures

    2. CountriesNow
       - Country
       - Currency
       - ISO codes

    The returned text is consumed by the
    Research Agent / OpenAI.
    """

    location_weather = (
        _get_location_and_weather(
            destination
        )
    )

    location = location_weather.get(
        "location",
        {},
    )

    weather = location_weather.get(
        "weather",
        {},
    )

    country_name = location.get(
        "country",
        "",
    )

    country_code = location.get(
        "country_code",
        "",
    )

    country_info = _get_country_info(
        country_name,
        country_code,
    )

    sections = [
        f"Destination: {destination}"
    ]

    # ========================================================
    # LOCATION INFORMATION
    # ========================================================

    if location:

        population = location.get(
            "population"
        )

        if isinstance(
            population,
            int,
        ):
            population_text = (
                f"{population:,}"
            )
        else:
            population_text = "N/A"

        sections.append(
            "\nLocation Facts:"
            f"\n- Matched Place: "
            f"{location.get('name', destination)}"
            f"\n- Country: "
            f"{country_name} ({country_code})"
            f"\n- Region: "
            f"{location.get('region', 'N/A')}"
            f"\n- Population: "
            f"{population_text}"
            f"\n- Latitude: "
            f"{location.get('latitude', 'N/A')}"
            f"\n- Longitude: "
            f"{location.get('longitude', 'N/A')}"
            f"\n- Timezone: "
            f"{location.get('timezone', 'UTC')}"
        )

    # ========================================================
    # WEATHER INFORMATION
    # ========================================================

    if weather:

        sections.append(
            "\nLive Weather (Open-Meteo):"
            f"\n- Condition: "
            f"{weather.get('condition', 'N/A')}"
            f"\n- Current Temperature: "
            f"{weather.get('current_temp_c', 'N/A')}°C"
            f"\n- 3-Day Minimum Temperature Average: "
            f"{weather.get('avg_min_temp_c', 'N/A')}°C"
            f"\n- 3-Day Maximum Temperature Average: "
            f"{weather.get('avg_max_temp_c', 'N/A')}°C"
            f"\n- Wind Speed: "
            f"{weather.get('wind_speed_kmh', 'N/A')} km/h"
        )

    # ========================================================
    # COUNTRY / CURRENCY INFORMATION
    # ========================================================

    if country_info:

        sections.append(
            "\nCountry & Currency Information:"
            f"\n- Country: "
            f"{country_info.get('country', country_name)}"
            f"\n- Currency Code: "
            f"{country_info.get('currency_code', 'N/A')}"
            f"\n- ISO2: "
            f"{country_info.get('iso2', country_code)}"
            f"\n- ISO3: "
            f"{country_info.get('iso3', 'N/A')}"
        )

    # ========================================================
    # INSTRUCTIONS FOR OPENAI RESEARCH AGENT
    # ========================================================

    sections.append(
        "\nResearch Instructions:"
        "\n- Use the supplied live location and weather "
        "data when available."
        "\n- Use reliable travel knowledge for attractions, "
        "cuisine, best time to visit, entry requirements, "
        "and practical travel tips."
        "\n- Do not invent live weather values."
        "\n- If some external information is unavailable, "
        "continue using reliable general travel knowledge."
    )

    return "\n".join(sections)


# ============================================================
# ATTRACTIONS
# ============================================================

def search_attractions(
    destination: str,
    category: str = "all",
) -> List[str]:
    """
    Provide an attraction research hint.

    The Research Agent / OpenAI generates the
    actual detailed attraction list.
    """

    location_weather = (
        _get_location_and_weather(
            destination
        )
    )

    location = location_weather.get(
        "location",
        {},
    )

    matched_name = location.get(
        "name",
        destination,
    )

    country = location.get(
        "country",
        "",
    )

    return [
        (
            f"Find the best {category} attractions "
            f"in {matched_name}, {country}. "
            "Use reliable travel knowledge."
        )
    ]


# ============================================================
# COST ESTIMATION
# ============================================================

def estimate_costs(
    destination: str,
    travel_style: str,
) -> Dict[str, float]:
    """
    Provide approximate daily baseline costs.

    The Budget Agent performs the final
    destination-specific calculation.
    """

    base_costs = {

        "budget": {
            "accommodation": 25,
            "food": 15,
            "activities": 10,
            "transport": 8,
        },

        "moderate": {
            "accommodation": 70,
            "food": 40,
            "activities": 30,
            "transport": 18,
        },

        "luxury": {
            "accommodation": 200,
            "food": 120,
            "activities": 80,
            "transport": 45,
        },
    }

    return base_costs.get(
        travel_style.lower(),
        base_costs["moderate"],
    )


# ============================================================
# CURRENCY CONVERSION
# ============================================================

def convert_currency(
    amount: float,
    from_currency: str,
    to_currency: str,
) -> float:
    """
    Currency conversion fallback.

    The current Budget Agent already reasons
    directly in the user's currency, so the main
    workflow does not require external conversion.
    """

    if (
        from_currency.upper()
        == to_currency.upper()
    ):
        return round(
            amount,
            2,
        )

    # Main Budget Agent handles currency directly.
    return round(
        amount,
        2,
    )


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "get_destination_info",
    "get_location_and_weather",
    "get_country_currency",
    "search_attractions",
    "estimate_costs",
    "convert_currency",
]