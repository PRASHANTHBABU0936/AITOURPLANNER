# """
# Research Agent: Fetches destination information using Open-Meteo and Country APIs,
# then synthesizes comprehensive travel research via OpenAI.
# """
# import json
from langchain_google_genai import ChatGoogleGenerativeAI
# from pydantic import ValidationError
# from models.schemas import TravelPlanState, ResearchData
# from config import MODEL, AGENT_CONFIG
# from tools import get_destination_info


# def research_agent_node(state: TravelPlanState) -> TravelPlanState:
#     """
#     Research destination and gather information using Open-Meteo & Country APIs + LLM structured generation.
    
#     Args:
#         state: Current workflow state
        
#     Returns:
#         Updated state with research data
#     """
    
#     if not state.trip_details:
#         state.errors.append("Trip details not available for research agent")
#         return state
    
#     try:
#         destination = state.trip_details.destination
        
#         # 1. Fetch live Open-Meteo weather/location data and country metadata
#         research_content = get_destination_info(destination)
        
#         # 2. Initialize LLM
#         llm = ChatOpenAI(
#             model=MODEL,
#             temperature=AGENT_CONFIG["research_agent"]["temperature"],
#             max_tokens=AGENT_CONFIG["research_agent"]["max_tokens"],
#         )
        
#         system_prompt = """You are an expert travel researcher. Based on the provided destination facts (weather, coordinates, country data) and your deep travel knowledge, create a comprehensive travel research summary.

# Respond ONLY with a valid JSON object matching this schema:
# {
#     "destination": "Destination Name",
#     "overview": "Rich overview of the destination culture, geography, and appeal",
#     "best_time_to_visit": "Best season/months to visit with reasons",
#     "weather": "Current weather conditions & typical climate patterns",
#     "attractions": ["List of 5-8 top real attractions and landmarks"],
#     "cuisine": "Famous local dishes, drinks, street food highlights",
#     "transportation": "Local transport options (metro, buses, cabs, scooters, trains)",
#     "entry_requirements": "Visa, passport, and entry requirements",
#     "travel_tips": ["5-7 practical travel tips (safety, etiquette, bargaining, payments)"]
# }"""
        
#         messages = [
#             {
#                 "role": "user",
#                 "content": f"{system_prompt}\n\nDestination Information:\n{research_content}"
#             }
#         ]
        
#         response = llm.invoke(messages)
#         response_text = response.content.strip()
        
#         # Strip markdown fences
#         for fence in ("```json", "```"):
#             if response_text.startswith(fence):
#                 response_text = response_text[len(fence):]
#         if response_text.endswith("```"):
#             response_text = response_text[:-3]
#         json_str = response_text.strip()
        
#         research_data_dict = json.loads(json_str)
#         research_data = ResearchData(**research_data_dict)
        
#         state.research_data = research_data
#         state.conversation_history.append({
#             "role": "research_agent",
#             "content": (
#                 f"Researched {research_data.destination}. "
#                 f"Best time to visit: {research_data.best_time_to_visit}. "
#                 f"Top attractions: {', '.join(research_data.attractions[:3])}. "
#                 f"Weather: {research_data.weather}."
#             ),
#         })

#     except ValidationError as e:
#         state.errors.append(f"Validation error in research agent: {str(e)}")
#     except json.JSONDecodeError as e:
#         state.errors.append(f"JSON parsing error in research agent: {str(e)}")
#     except Exception as e:
#         state.errors.append(f"Error in research agent: {str(e)}")
    
#     return state





# """
# Research Agent: Fetches destination information using Open-Meteo
# and Country APIs, then synthesizes comprehensive travel research
# via OpenAI structured generation.
# """

# from langchain_openai import ChatOpenAI
# from pydantic import ValidationError

# from models.schemas import TravelPlanState, ResearchData
# from config import MODEL, AGENT_CONFIG
# from tools import get_destination_info


# def research_agent_node(
#     state: TravelPlanState,
# ) -> TravelPlanState:
#     """
#     Research destination and gather information using
#     Open-Meteo + Country APIs + OpenAI structured generation.

#     Args:
#         state: Current workflow state

#     Returns:
#         Updated state with research data
#     """

#     # ---------------------------------------------------------
#     # Validate trip details
#     # ---------------------------------------------------------

#     if not state.trip_details:
#         state.errors.append(
#             "Trip details not available for research agent"
#         )
#         return state

#     try:
#         destination = state.trip_details.destination

#         # -----------------------------------------------------
#         # 1. Fetch live destination information
#         # -----------------------------------------------------

#         research_content = get_destination_info(
#             destination
#         )

#         if not research_content:
#             state.errors.append(
#                 "No destination research data returned"
#             )
#             return state

#         # -----------------------------------------------------
#         # 2. Initialize OpenAI
#         # -----------------------------------------------------

#         llm = ChatOpenAI(
#             model=MODEL,
#             temperature=AGENT_CONFIG[
#                 "research_agent"
#             ]["temperature"],
#             max_tokens=AGENT_CONFIG[
#                 "research_agent"
#             ]["max_tokens"],
#         )

#         # -----------------------------------------------------
#         # 3. Force OpenAI to return ResearchData
#         # -----------------------------------------------------

#         structured_llm = llm.with_structured_output(
#             ResearchData
#         )

#         prompt = f"""
# You are an expert travel researcher.

# Create comprehensive and useful travel research for:

# DESTINATION:
# {destination}

# LIVE DESTINATION INFORMATION:
# {research_content}

# Your job is to transform the supplied destination information
# and your reliable travel knowledge into a complete ResearchData
# object.

# IMPORTANT RULES:

# 1. DESTINATION
#    - Use the requested destination: {destination}
#    - Do not replace it with a similarly named city or country.

# 2. OVERVIEW
#    - Explain the destination's geography, culture,
#      character, and major appeal.

# 3. BEST TIME TO VISIT
#    - Give the best seasons/months and explain why.

# 4. WEATHER
#    - Use the supplied Open-Meteo live weather information
#      when available.
#    - Clearly distinguish current weather from typical climate.
#    - NEVER invent live weather values.

# 5. ATTRACTIONS
#    - Provide at least 5 specific and real attractions.
#    - Use actual landmarks, beaches, monuments, museums,
#      viewpoints, neighborhoods, or experiences.

# 6. CUISINE
#    - Include important local dishes, drinks,
#      street food, and regional specialties.

# 7. TRANSPORTATION
#    - Explain realistic ways travelers can get around,
#      including public transport, taxis, rental vehicles,
#      walking, etc. where appropriate.

# 8. ENTRY REQUIREMENTS
#    - Give general passport/visa/entry guidance.
#    - Mention that requirements depend on nationality
#      and travelers should verify current official rules.

# 9. TRAVEL TIPS
#    - Provide at least 5 practical tips covering things
#      such as safety, payments, local etiquette,
#      transportation, weather, and common tourist issues.

# 10. DATA ACCURACY
#    - Use the supplied API data for location and weather.
#    - Do not invent live API values.
#    - For information not supplied by the APIs, use
#      reliable general travel knowledge.

# Return ONLY the structured ResearchData object.
# """

#         # -----------------------------------------------------
#         # 4. Call OpenAI
#         # -----------------------------------------------------

#         research_data = structured_llm.invoke(
#             prompt
#         )

#         # -----------------------------------------------------
#         # 5. Validate result
#         # -----------------------------------------------------

#         if research_data is None:
#             state.errors.append(
#                 "OpenAI returned empty research data"
#             )
#             return state

#         if not isinstance(
#             research_data,
#             ResearchData,
#         ):
#             research_data = ResearchData.model_validate(
#                 research_data
#             )

#         # -----------------------------------------------------
#         # 6. Store research data
#         # -----------------------------------------------------

#         state.research_data = research_data

#         # -----------------------------------------------------
#         # 7. Conversation history
#         # -----------------------------------------------------

#         attractions_preview = ", ".join(
#             research_data.attractions[:3]
#         )

#         state.conversation_history.append(
#             {
#                 "role": "research_agent",
#                 "content": (
#                     f"Researched "
#                     f"{research_data.destination}. "
#                     f"Best time to visit: "
#                     f"{research_data.best_time_to_visit}. "
#                     f"Top attractions: "
#                     f"{attractions_preview}. "
#                     f"Weather: "
#                     f"{research_data.weather}."
#                 ),
#             }
#         )

#     # ---------------------------------------------------------
#     # Error handling
#     # ---------------------------------------------------------

#     except ValidationError as e:

#         state.errors.append(
#             "Validation error in research agent: "
#             f"{str(e)}"
#         )

#     except Exception as e:

#         state.errors.append(
#             "Error in research agent: "
#             f"{type(e).__name__}: {str(e)}"
#         )

#     return state



"""
Research Agent: Fetches destination information using Open-Meteo
and Country APIs, then synthesizes structured travel research
via OpenAI.
"""

from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import ValidationError
import logging

from models.schemas import TravelPlanState, ResearchData
from config import MODEL, AGENT_CONFIG
from tools import get_destination_info


logger = logging.getLogger(__name__)


def _fetch_research_content(destination: str) -> str:
    """
    Fetch live destination research via the MCP research server.

    Falls back to the direct REST helper when MCP is unavailable so the
    workflow keeps working without the MCP runtime.
    """
    try:
        from mcp_client import call_tool

        content = call_tool(
            "research",
            "destination_info",
            {"destination": destination},
        )

        if isinstance(content, str) and content.strip():
            return content

        raise ValueError("empty MCP research response")

    except Exception as exc:
        logger.warning(
            "MCP research lookup failed (%s); using direct REST fallback",
            exc,
        )
        return get_destination_info(destination)


def research_agent_node(
    state: TravelPlanState,
) -> TravelPlanState:
    """
    Research destination and create structured ResearchData.
    """

    if not state.trip_details:
        state.errors.append(
            "Trip details not available for research agent"
        )
        return state

    try:
        destination = state.trip_details.destination

        # -----------------------------------------------------
        # 1. Get live destination information
        # -----------------------------------------------------

        research_content = _fetch_research_content(
            destination
        )

        if not research_content:
            state.errors.append(
                "No destination research data returned"
            )
            return state

        # -----------------------------------------------------
        # 2. Initialize OpenAI
        # -----------------------------------------------------

        llm = ChatGoogleGenerativeAI(
            model=MODEL,
            temperature=AGENT_CONFIG["research_agent"]["temperature"],
            max_output_tokens=4000,
        )

        # -----------------------------------------------------
        # 3. Structured output
        # -----------------------------------------------------

        structured_llm = llm.with_structured_output(
            ResearchData
        )

        prompt = f"""
Create a complete travel research profile for {destination}.

Use the live API information below for location and weather.
Use your travel knowledge for the remaining information.

LIVE DATA:
{research_content}

Requirements:
- destination: "{destination}"
- overview: concise destination overview
- best_time_to_visit: best months/seasons and reason
- weather: current weather + typical climate
- attractions: 5-8 real attractions
- cuisine: important local foods and specialties
- transportation: practical local transport
- entry_requirements: general visa/passport guidance
- travel_tips: 5 practical tips

Important:
- Keep every field concise.
- Do not invent live weather values.
- Use the supplied API weather data when available.
- Entry requirements vary by nationality.
- Return only the ResearchData structure.
"""

        # -----------------------------------------------------
        # 4. Generate structured research
        # -----------------------------------------------------

        research_data = structured_llm.invoke(
            prompt
        )

        # -----------------------------------------------------
        # 5. Validate
        # -----------------------------------------------------

        if research_data is None:
            state.errors.append(
                "OpenAI returned empty research data"
            )
            return state

        if not isinstance(
            research_data,
            ResearchData,
        ):
            research_data = ResearchData.model_validate(
                research_data
            )

        # -----------------------------------------------------
        # 6. Store result
        # -----------------------------------------------------

        state.research_data = research_data

        attractions_preview = ", ".join(
            research_data.attractions[:3]
        )

        state.conversation_history.append(
            {
                "role": "research_agent",
                "content": (
                    f"Researched "
                    f"{research_data.destination}. "
                    f"Best time: "
                    f"{research_data.best_time_to_visit}. "
                    f"Top attractions: "
                    f"{attractions_preview}. "
                    f"Weather: "
                    f"{research_data.weather}."
                ),
            }
        )

    except ValidationError as e:
        state.errors.append(
            "Validation error in research agent: "
            f"{str(e)}"
        )

    except Exception as e:
        state.errors.append(
            "Error in research agent: "
            f"{type(e).__name__}: {str(e)}"
        )

    return state