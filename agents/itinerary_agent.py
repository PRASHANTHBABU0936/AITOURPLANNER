# """
# Itinerary Agent: Generates day-wise travel plan
# """
# import json
# from langchain_openai import ChatOpenAI
# from pydantic import ValidationError
# from models.schemas import TravelPlanState, ItineraryPlan, DayPlan
# from config import MODEL, AGENT_CONFIG


# def itinerary_agent_node(state: TravelPlanState) -> TravelPlanState:
#     """
#     Generate detailed day-wise itinerary
    
#     Args:
#         state: Current workflow state
        
#     Returns:
#         Updated state with itinerary
#     """
    
#     if not state.trip_details or not state.research_data:
#         state.errors.append("Trip details and research data required for itinerary generation")
#         return state
    
#     try:
#         # Initialize Claude model
#         max_tokens = max(2000, state.trip_details.duration * 800)
#         # llm = ChatOpenAI(
#         #     model=MODEL,
#         #     temperature=AGENT_CONFIG["itinerary_agent"]["temperature"],
#         #     max_tokens=max_tokens,
#         # )

#         llm = ChatOpenAI(
#     model=MODEL,
#     temperature=AGENT_CONFIG["itinerary_agent"]["temperature"],
#     max_tokens=max_tokens,
#     timeout=60,
#     max_retries=1,
# )
        
#         # Prepare context
#         trip_details = state.trip_details.model_dump()
#         research_data = state.research_data.model_dump()
#         currency = state.trip_details.currency
#         travel_style = state.trip_details.travel_style

#         system_prompt = f"""You are an expert travel itinerary planner. Create a detailed day-wise travel plan
# based on the provided trip details and destination research.

# IMPORTANT: All cost estimates in the "estimates" field must be realistic amounts in {currency}.
# Use actual local market prices for {state.trip_details.destination}.
# Travel style is {travel_style} — scale costs accordingly.

# For each day include:
# - day: Day number
# - title: Catchy theme title
# - activities: 6-8 specific activities with exact timing in format "HH:MM AM/PM - Activity name and description (duration)".
#   Cover morning, afternoon, and evening slots.
# - meals: Restaurant name + cuisine type + approx cost in {currency} (breakfast, lunch, dinner)
# - accommodation: Hotel/hostel name with area/neighborhood
# - estimates: Realistic per-day costs in {currency} (food, activities, transport)

# Respond ONLY with valid JSON:
# {{
#     "destination": "destination_name",
#     "duration": 5,
#     "days": [
#         {{
#             "day": 1,
#             "title": "Arrival & City Orientation",
#             "activities": [
#                 "09:00 AM - Visit XYZ temple, explore the main shrine and gardens (1.5 hrs)",
#                 "11:00 AM - Walk through ABC market, try local street food (1 hr)",
#                 "02:00 PM - Tour DEF museum, focus on historical exhibits (2 hrs)",
#                 "05:00 PM - Sunset at GHI viewpoint, great photo opportunity (45 mins)",
#                 "07:30 PM - Evening stroll at JKL promenade (1 hr)"
#             ],
#             "meals": {{
#                 "breakfast": "Hotel restaurant - South Indian buffet - INR 200",
#                 "lunch": "Cafe XYZ - Local thali cuisine - INR 300",
#                 "dinner": "Restaurant ABC - Seafood specialties - INR 600"
#             }},
#             "accommodation": "Hotel Name, Neighborhood Area",
#             "estimates": {{"food": 800, "activities": 200, "transport": 300}}
#         }}
#     ],
#     "special_notes": ["Tip 1", "Tip 2"]
# }}"""
        
#         messages = [
#             {
#                 "role": "user",
#                 "content": system_prompt + f"\n\nTrip Details:\n{json.dumps(trip_details, indent=2)}\n\nDestination Info:\n{json.dumps(research_data, indent=2)}"
#             }
#         ]
        
#         # Call Claude API
#         response = llm.invoke(messages)
#         response_text = response.content
        
#         # Parse JSON response
#         json_str = response_text.strip()
#         if json_str.startswith("```json"):
#             json_str = json_str[7:]
#         if json_str.endswith("```"):
#             json_str = json_str[:-3]
#         json_str = json_str.strip()
        
#         itinerary_dict = json.loads(json_str)
        
#         # Convert to ItinerayPlan
#         days = [DayPlan(**day) for day in itinerary_dict.get("days", [])]
        
#         itinerary = ItineraryPlan(
#             destination=itinerary_dict.get("destination", state.trip_details.destination),
#             duration=itinerary_dict.get("duration", state.trip_details.duration),
#             days=days,
#             special_notes=itinerary_dict.get("special_notes", [])
#         )
        
#         state.itinerary = itinerary
#         day_titles = ", ".join(f"Day {d.day}: {d.title}" for d in days[:3])
#         state.conversation_history.append({
#             "role": "itinerary_agent",
#             "content": (
#                 f"Created a {itinerary.duration}-day itinerary for {itinerary.destination}. "
#                 f"{day_titles}{'...' if len(days) > 3 else ''}. "
#                 f"Special notes: {'; '.join(itinerary.special_notes[:2]) or 'None'}."
#             ),
#         })

#     except ValidationError as e:
#         state.errors.append(f"Validation error in itinerary agent: {str(e)}")
#     except json.JSONDecodeError as e:
#         state.errors.append(f"JSON parsing error in itinerary agent: {str(e)}")
#     except Exception as e:
#         state.errors.append(f"Error in itinerary agent: {str(e)}")
    
#     return state








# """
# Itinerary Agent: Generates day-wise travel plan
# using OpenAI structured output.
# """

# from langchain_openai import ChatOpenAI
# from pydantic import ValidationError

# from models.schemas import TravelPlanState, ItineraryPlan
# from config import MODEL, AGENT_CONFIG


# def itinerary_agent_node(state: TravelPlanState) -> TravelPlanState:
#     """
#     Generate detailed day-wise itinerary.

#     Args:
#         state: Current workflow state

#     Returns:
#         Updated state with itinerary
#     """

#     # ---------------------------------------------------------
#     # Validate required data
#     # ---------------------------------------------------------

#     if not state.trip_details:
#         state.errors.append(
#             "Trip details required for itinerary generation"
#         )
#         return state

#     if not state.research_data:
#         state.errors.append(
#             "Research data required for itinerary generation"
#         )
#         return state

#     try:
#         trip = state.trip_details
#         research = state.research_data

#         destination = trip.destination
#         duration = trip.duration
#         currency = trip.currency
#         travel_style = trip.travel_style

#         # -----------------------------------------------------
#         # Initialize OpenAI
#         # -----------------------------------------------------

#         # GPT-5-mini can use reasoning tokens before producing
#         # structured output, so give it enough room.
#         max_tokens = max(
#             4000,
#             duration * 1200,
#         )

#         llm = ChatOpenAI(
#             model=MODEL,
#             temperature=AGENT_CONFIG[
#                 "itinerary_agent"
#             ]["temperature"],
#             max_tokens=max_tokens,
#             timeout=60,
#             max_retries=1,
#         )

#         # -----------------------------------------------------
#         # Structured output
#         # -----------------------------------------------------

#         structured_llm = llm.with_structured_output(
#             ItineraryPlan
#         )

#         # -----------------------------------------------------
#         # Prepare research context
#         # -----------------------------------------------------

#         attractions = ", ".join(
#             research.attractions
#         )

#         travel_tips = ", ".join(
#             research.travel_tips
#         )

#         research_context = f"""
# Destination:
# {research.destination}

# Overview:
# {research.overview}

# Best time to visit:
# {research.best_time_to_visit}

# Weather:
# {research.weather}

# Top attractions:
# {attractions}

# Cuisine:
# {research.cuisine}

# Transportation:
# {research.transportation}

# Entry requirements:
# {research.entry_requirements}

# Travel tips:
# {travel_tips}
# """

#         # -----------------------------------------------------
#         # User preferences
#         # -----------------------------------------------------

#         preferences = (
#             ", ".join(trip.preferences)
#             if trip.preferences
#             else "None"
#         )

#         interests = (
#             ", ".join(trip.interests)
#             if trip.interests
#             else "None"
#         )

#         accommodation = (
#             trip.accommodation_type
#             if trip.accommodation_type
#             else "Not specified"
#         )

#         # -----------------------------------------------------
#         # Prompt
#         # -----------------------------------------------------

#         prompt = f"""
# You are an expert travel itinerary planner.

# Create a realistic {duration}-day travel itinerary.

# TRIP DETAILS
# ------------
# Destination: {destination}
# Duration: {duration} days
# Budget: {currency} {trip.budget:,.0f}
# Currency: {currency}
# Travel style: {travel_style}
# Preferences: {preferences}
# Interests: {interests}
# Accommodation preference: {accommodation}

# DESTINATION RESEARCH
# --------------------
# {research_context}

# ITINERARY REQUIREMENTS
# ----------------------

# Create exactly {duration} days.

# For every day provide:

# 1. day
#    - Day number starting from 1.

# 2. title
#    - Short and useful theme for the day.

# 3. activities
#    - 5-7 realistic activities.
#    - Cover morning, afternoon and evening.
#    - Include exact times.
#    - Use this format:
#      "09:00 AM - Activity description (1.5 hrs)"
#    - Avoid unrealistic scheduling.
#    - Consider travel time between locations.
#    - Use real attractions from the destination research.

# 4. meals
#    - breakfast
#    - lunch
#    - dinner
#    - Include a realistic food/restaurant recommendation.
#    - Include approximate cost in {currency}.

# 5. accommodation
#    - Give a realistic accommodation type/name and area.
#    - Match the {travel_style} travel style.

# 6. estimates
#    - food
#    - activities
#    - transport
#    - These are estimated costs for that day.
#    - All amounts must be in {currency}.

# 7. special_notes
#    - Give useful practical notes for the trip.

# IMPORTANT RULES
# ---------------

# - Create exactly {duration} days.
# - Use real attractions.
# - Keep the itinerary geographically sensible.
# - Do not overload each day.
# - Keep costs realistic for {destination}.
# - Respect the user's {travel_style} travel style.
# - Do not assume luxury accommodation for a budget trip.
# - Do not include international flights unless explicitly requested.
# - Do not convert the user's budget to USD.
# - All monetary amounts must use {currency}.
# - Use the supplied weather information when useful.
# - Do not invent live weather values.
# - Keep the itinerary practical and achievable.
# - Return ONLY the structured ItineraryPlan.
# """

#         # -----------------------------------------------------
#         # Call OpenAI
#         # -----------------------------------------------------

#         itinerary = structured_llm.invoke(
#             prompt
#         )

#         # -----------------------------------------------------
#         # Validate response
#         # -----------------------------------------------------

#         if itinerary is None:
#             state.errors.append(
#                 "OpenAI returned empty itinerary"
#             )
#             return state

#         if not isinstance(
#             itinerary,
#             ItineraryPlan,
#         ):
#             itinerary = ItineraryPlan.model_validate(
#                 itinerary
#             )

#         # -----------------------------------------------------
#         # Validate number of days
#         # -----------------------------------------------------

#         if len(itinerary.days) != duration:
#             state.errors.append(
#                 f"Itinerary returned "
#                 f"{len(itinerary.days)} days instead of "
#                 f"{duration} days"
#             )
#             return state

#         # -----------------------------------------------------
#         # Validate destination
#         # -----------------------------------------------------

#         itinerary.destination = destination
#         itinerary.duration = duration

#         # -----------------------------------------------------
#         # Store itinerary
#         # -----------------------------------------------------

#         state.itinerary = itinerary

#         # -----------------------------------------------------
#         # Conversation history
#         # -----------------------------------------------------

#         day_titles = ", ".join(
#             f"Day {day.day}: {day.title}"
#             for day in itinerary.days[:3]
#         )

#         state.conversation_history.append(
#             {
#                 "role": "itinerary_agent",
#                 "content": (
#                     f"Created a "
#                     f"{itinerary.duration}-day itinerary "
#                     f"for {itinerary.destination}. "
#                     f"{day_titles}"
#                     f"{'...' if len(itinerary.days) > 3 else ''}. "
#                     f"Special notes: "
#                     f"{'; '.join(itinerary.special_notes[:2]) or 'None'}."
#                 ),
#             }
#         )

#     # ---------------------------------------------------------
#     # Error handling
#     # ---------------------------------------------------------

#     except ValidationError as e:

#         state.errors.append(
#             "Validation error in itinerary agent: "
#             f"{str(e)}"
#         )

#     except Exception as e:

#         state.errors.append(
#             "Error in itinerary agent: "
#             f"{type(e).__name__}: {str(e)}"
#         )

#     return state




# """
# Itinerary Agent: Generates day-wise travel plan
# using OpenAI structured output with function calling.
# """

# from langchain_openai import ChatOpenAI
# from pydantic import ValidationError

# from models.schemas import TravelPlanState, ItineraryPlan
# from config import MODEL, AGENT_CONFIG


# def itinerary_agent_node(state: TravelPlanState) -> TravelPlanState:
#     """
#     Generate detailed day-wise itinerary.

#     Args:
#         state: Current workflow state

#     Returns:
#         Updated state with itinerary
#     """

#     # ---------------------------------------------------------
#     # Validate required data
#     # ---------------------------------------------------------

#     if not state.trip_details:
#         state.errors.append(
#             "Trip details required for itinerary generation"
#         )
#         return state

#     if not state.research_data:
#         state.errors.append(
#             "Research data required for itinerary generation"
#         )
#         return state

#     try:
#         trip = state.trip_details
#         research = state.research_data

#         destination = trip.destination
#         duration = trip.duration
#         currency = trip.currency
#         travel_style = trip.travel_style

#         # -----------------------------------------------------
#         # Initialize OpenAI
#         # -----------------------------------------------------

#         max_tokens = max(
#             4000,
#             duration * 1200,
#         )

#         llm = ChatOpenAI(
#             model=MODEL,
#             temperature=AGENT_CONFIG[
#                 "itinerary_agent"
#             ]["temperature"],
#             max_tokens=max_tokens,
#             timeout=60,
#             max_retries=1,
#         )

#         # -----------------------------------------------------
#         # IMPORTANT:
#         # Use function_calling instead of json_schema.
#         #
#         # Your DayPlan schema contains Dict[str, str] for
#         # "meals", which OpenAI's strict JSON schema mode
#         # is rejecting.
#         # -----------------------------------------------------

#         structured_llm = llm.with_structured_output(
#             ItineraryPlan,
#             method="function_calling",
#         )

#         # -----------------------------------------------------
#         # Prepare research context
#         # -----------------------------------------------------

#         attractions = ", ".join(
#             research.attractions
#         )

#         travel_tips = ", ".join(
#             research.travel_tips
#         )

#         research_context = f"""
# Destination:
# {research.destination}

# Overview:
# {research.overview}

# Best time to visit:
# {research.best_time_to_visit}

# Weather:
# {research.weather}

# Top attractions:
# {attractions}

# Cuisine:
# {research.cuisine}

# Transportation:
# {research.transportation}

# Entry requirements:
# {research.entry_requirements}

# Travel tips:
# {travel_tips}
# """

#         preferences = (
#             ", ".join(trip.preferences)
#             if trip.preferences
#             else "None"
#         )

#         interests = (
#             ", ".join(trip.interests)
#             if trip.interests
#             else "None"
#         )

#         accommodation = (
#             trip.accommodation_type
#             if trip.accommodation_type
#             else "Not specified"
#         )

#         # -----------------------------------------------------
#         # Prompt
#         # -----------------------------------------------------

#         prompt = f"""
# You are an expert travel itinerary planner.

# Create a realistic {duration}-day travel itinerary.

# TRIP DETAILS
# ------------
# Destination: {destination}
# Duration: {duration} days
# Budget: {currency} {trip.budget:,.0f}
# Currency: {currency}
# Travel style: {travel_style}
# Preferences: {preferences}
# Interests: {interests}
# Accommodation preference: {accommodation}

# DESTINATION RESEARCH
# --------------------
# {research_context}

# REQUIREMENTS
# ------------

# Create exactly {duration} days.

# For every day:

# - day:
#   Correct day number starting from 1.

# - title:
#   Short theme for the day.

# - activities:
#   5-7 realistic activities.
#   Cover morning, afternoon and evening.
#   Include exact times.
#   Example:
#   "09:00 AM - Visit Fort Aguada and explore the fort (1.5 hrs)"

# - meals:
#   Include breakfast, lunch and dinner.
#   Each value should contain:
#   restaurant/food location,
#   cuisine or food type,
#   approximate cost in {currency}.

# - accommodation:
#   Give a realistic accommodation type/name and area.
#   Match the {travel_style} travel style.

# - estimates:
#   Include:
#   food
#   activities
#   transport

#   All amounts must be in {currency}.

# - special_notes:
#   Give useful practical travel notes.

# IMPORTANT:

# - Create exactly {duration} days.
# - Use real attractions from the research.
# - Keep locations geographically sensible.
# - Do not overload each day.
# - Allow realistic travel time.
# - Respect the {travel_style} travel style.
# - Keep costs realistic for {destination}.
# - Do not assume luxury accommodation for a budget trip.
# - Do not include international flights unless explicitly requested.
# - Do not convert the budget to USD.
# - All monetary amounts must use {currency}.
# - Do not invent live weather values.
# - Return the itinerary using the requested structured format.
# """

#         # -----------------------------------------------------
#         # Call OpenAI
#         # -----------------------------------------------------

#         itinerary = structured_llm.invoke(
#             prompt
#         )

#         # -----------------------------------------------------
#         # Validate response
#         # -----------------------------------------------------

#         if itinerary is None:
#             state.errors.append(
#                 "OpenAI returned empty itinerary"
#             )
#             return state

#         if not isinstance(
#             itinerary,
#             ItineraryPlan,
#         ):
#             itinerary = ItineraryPlan.model_validate(
#                 itinerary
#             )

#         # -----------------------------------------------------
#         # Validate number of days
#         # -----------------------------------------------------

#         if len(itinerary.days) != duration:
#             state.errors.append(
#                 f"Itinerary returned "
#                 f"{len(itinerary.days)} days instead of "
#                 f"{duration} days"
#             )
#             return state

#         # -----------------------------------------------------
#         # Enforce requested destination/duration
#         # -----------------------------------------------------

#         itinerary.destination = destination
#         itinerary.duration = duration

#         # -----------------------------------------------------
#         # Store itinerary
#         # -----------------------------------------------------

#         state.itinerary = itinerary

#         # -----------------------------------------------------
#         # Conversation history
#         # -----------------------------------------------------

#         day_titles = ", ".join(
#             f"Day {day.day}: {day.title}"
#             for day in itinerary.days[:3]
#         )

#         state.conversation_history.append(
#             {
#                 "role": "itinerary_agent",
#                 "content": (
#                     f"Created a "
#                     f"{itinerary.duration}-day itinerary "
#                     f"for {itinerary.destination}. "
#                     f"{day_titles}"
#                     f"{'...' if len(itinerary.days) > 3 else ''}. "
#                     f"Special notes: "
#                     f"{'; '.join(itinerary.special_notes[:2]) or 'None'}."
#                 ),
#             }
#         )

#     # ---------------------------------------------------------
#     # Error handling
#     # ---------------------------------------------------------

#     except ValidationError as e:

#         state.errors.append(
#             "Validation error in itinerary agent: "
#             f"{str(e)}"
#         )

#     except Exception as e:

#         state.errors.append(
#             "Error in itinerary agent: "
#             f"{type(e).__name__}: {str(e)}"
#         )

#     return state


"""
Itinerary Agent: Generates a day-wise travel plan.

Uses OpenAI function calling with an OpenAI-friendly schema,
then converts the result into the application's ItineraryPlan.
"""

from typing import List


from pydantic import BaseModel, Field, ValidationError

from models.schemas import (
    TravelPlanState,
    ItineraryPlan,
    DayPlan,
)
from config import MODEL, AGENT_CONFIG

from langchain_google_genai import ChatGoogleGenerativeAI
# ============================================================
# OPENAI-FRIENDLY INTERNAL SCHEMAS
# ============================================================

class OpenAIDayPlan(BaseModel):
    """Internal schema used only for OpenAI generation."""

    day: int = Field(
        description="Day number starting from 1"
    )

    title: str = Field(
        description="Short theme/title for the day"
    )

    activities: List[str] = Field(
        description=(
            "5 to 7 realistic activities with exact times. "
            "Example: 09:00 AM - Visit Fort Aguada (1.5 hrs)"
        )
    )

    breakfast: str = Field(
        description=(
            "Breakfast recommendation with approximate "
            "cost in the user's currency"
        )
    )

    lunch: str = Field(
        description=(
            "Lunch recommendation with approximate "
            "cost in the user's currency"
        )
    )

    dinner: str = Field(
        description=(
            "Dinner recommendation with approximate "
            "cost in the user's currency"
        )
    )

    accommodation: str = Field(
        description=(
            "Realistic accommodation and area matching "
            "the user's travel style"
        )
    )

    food_estimate: float = Field(
        description="Estimated food cost for this day"
    )

    activities_estimate: float = Field(
        description="Estimated activity cost for this day"
    )

    transport_estimate: float = Field(
        description="Estimated transport cost for this day"
    )


class OpenAIItinerary(BaseModel):
    """Internal structured response from OpenAI."""

    destination: str = Field(
        description="Travel destination"
    )

    duration: int = Field(
        description="Number of travel days"
    )

    days: List[OpenAIDayPlan] = Field(
        description="Day-by-day itinerary"
    )

    special_notes: List[str] = Field(
        description="Useful practical travel notes"
    )


# ============================================================
# ITINERARY AGENT
# ============================================================

def itinerary_agent_node(
    state: TravelPlanState,
) -> TravelPlanState:
    """
    Generate detailed day-wise itinerary.
    """

    # --------------------------------------------------------
    # Validate required state
    # --------------------------------------------------------

    if not state.trip_details:
        state.errors.append(
            "Trip details required for itinerary generation"
        )
        return state

    if not state.research_data:
        state.errors.append(
            "Research data required for itinerary generation"
        )
        return state

    try:

        trip = state.trip_details
        research = state.research_data

        destination = trip.destination
        duration = trip.duration
        currency = trip.currency
        travel_style = trip.travel_style

        # ----------------------------------------------------
        # Initialize OpenAI
        # ----------------------------------------------------

        max_tokens = max(
            5000,
            duration * 1400,
        )

        llm = ChatGoogleGenerativeAI(
            model=MODEL,
            temperature=AGENT_CONFIG["itinerary_agent"]["temperature"],
            max_output_tokens=max_tokens,
            timeout=90,
            max_retries=1,
        )

        # ----------------------------------------------------
        # Function calling
        # ----------------------------------------------------

        structured_llm = llm.with_structured_output(
            OpenAIItinerary,
            method="function_calling",
        )

        # ----------------------------------------------------
        # Research context
        # ----------------------------------------------------

        attractions = ", ".join(
            research.attractions
        )

        travel_tips = ", ".join(
            research.travel_tips
        )

        preferences = (
            ", ".join(trip.preferences)
            if trip.preferences
            else "None"
        )

        interests = (
            ", ".join(trip.interests)
            if trip.interests
            else "None"
        )

        accommodation_preference = (
            trip.accommodation_type
            if trip.accommodation_type
            else "Not specified"
        )

        research_context = f"""
Destination:
{research.destination}

Overview:
{research.overview}

Best time:
{research.best_time_to_visit}

Weather:
{research.weather}

Attractions:
{attractions}

Cuisine:
{research.cuisine}

Transportation:
{research.transportation}

Travel tips:
{travel_tips}
"""

        # ----------------------------------------------------
        # Prompt
        # ----------------------------------------------------

        prompt = f"""
Create a realistic travel itinerary.

TRIP
----
Destination: {destination}
Duration: {duration} days
Budget: {currency} {trip.budget:,.0f}
Travel style: {travel_style}
Preferences: {preferences}
Interests: {interests}
Accommodation preference: {accommodation_preference}

RESEARCH
--------
{research_context}

RULES
-----

Create EXACTLY {duration} days.

For every day:

- Provide 5-7 activities.
- Cover morning, afternoon and evening.
- Every activity must have a realistic time.
- Use real attractions from the research.
- Keep nearby locations together.
- Allow realistic travel time.
- Do not overload the day.

Meals:

- breakfast
- lunch
- dinner

Each meal should include the food/restaurant and
approximate cost in {currency}.

Accommodation:

Choose realistic accommodation matching the
{travel_style} travel style.

Costs:

food_estimate = daily food cost in {currency}
activities_estimate = daily activities cost in {currency}
transport_estimate = daily transport cost in {currency}

IMPORTANT:

- All costs are in {currency}.
- Never convert to USD.
- Do not include flights unless explicitly requested.
- Keep costs realistic for {destination}.
- Do not invent live weather values.
- Return exactly {duration} days.
"""

        # ----------------------------------------------------
        # Call OpenAI
        # ----------------------------------------------------

        result = structured_llm.invoke(
            prompt
        )

        # ----------------------------------------------------
        # Check result
        # ----------------------------------------------------

        if result is None:

            state.errors.append(
                "OpenAI returned empty itinerary"
            )

            return state

        # ----------------------------------------------------
        # Convert OpenAI response into application schema
        # ----------------------------------------------------

        days = []

        for generated_day in result.days:

            day = DayPlan(
                day=generated_day.day,

                title=generated_day.title,

                activities=generated_day.activities,

                meals={
                    "breakfast": generated_day.breakfast,
                    "lunch": generated_day.lunch,
                    "dinner": generated_day.dinner,
                },

                accommodation=(
                    generated_day.accommodation
                ),

                estimates={
                    "food": generated_day.food_estimate,
                    "activities": (
                        generated_day.activities_estimate
                    ),
                    "transport": (
                        generated_day.transport_estimate
                    ),
                },
            )

            days.append(day)

        # ----------------------------------------------------
        # Validate number of days
        # ----------------------------------------------------

        if len(days) != duration:

            state.errors.append(
                f"Itinerary returned {len(days)} "
                f"days instead of {duration} days"
            )

            return state

        # ----------------------------------------------------
        # Create application's ItineraryPlan
        # ----------------------------------------------------

        itinerary = ItineraryPlan(
            destination=destination,
            duration=duration,
            days=days,
            special_notes=result.special_notes,
        )

        # ----------------------------------------------------
        # Store result
        # ----------------------------------------------------

        state.itinerary = itinerary

        # ----------------------------------------------------
        # Conversation history
        # ----------------------------------------------------

        day_titles = ", ".join(
            f"Day {day.day}: {day.title}"
            for day in days[:3]
        )

        state.conversation_history.append(
            {
                "role": "itinerary_agent",
                "content": (
                    f"Created a {duration}-day itinerary "
                    f"for {destination}. "
                    f"{day_titles}"
                    f"{'...' if len(days) > 3 else ''}. "
                    f"Special notes: "
                    f"{'; '.join(result.special_notes[:2]) or 'None'}."
                ),
            }
        )

    # --------------------------------------------------------
    # Error handling
    # --------------------------------------------------------

    except ValidationError as e:

        state.errors.append(
            "Validation error in itinerary agent: "
            f"{str(e)}"
        )

    except Exception as e:

        state.errors.append(
            "Error in itinerary agent: "
            f"{type(e).__name__}: {str(e)}"
        )

    return state