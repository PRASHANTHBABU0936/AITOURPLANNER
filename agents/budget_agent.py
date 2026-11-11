# """
# Budget Agent: Estimates realistic trip costs in the user's own currency.
# No USD round-trip conversion — the LLM reasons in the destination's native
# price context and outputs amounts directly in user_currency.
# """
# import json
# from langchain_openai import ChatOpenAI
# from pydantic import ValidationError
# from models.schemas import TravelPlanState, BudgetBreakdown
# from config import MODEL, AGENT_CONFIG


# def budget_agent_node(state: TravelPlanState) -> TravelPlanState:
#     if not state.trip_details or not state.itinerary:
#         state.errors.append("Trip details and itinerary required for budget calculation")
#         return state

#     try:
#         llm = ChatOpenAI(
#             model=MODEL,
#             temperature=AGENT_CONFIG["budget_agent"]["temperature"],
#             max_tokens=AGENT_CONFIG["budget_agent"]["max_tokens"],
#         )

#         trip = state.trip_details
#         user_currency = trip.currency.upper()
#         destination = trip.destination
#         duration = trip.duration
#         travel_style = trip.travel_style
#         user_budget = trip.budget  # already in user's currency — use as-is

#         research_context = ""
#         if state.research_data:
#             research_context = (
#                 f"\nDestination context:\n"
#                 f"- Overview: {state.research_data.overview[:300]}\n"
#                 f"- Transportation: {state.research_data.transportation}\n"
#                 f"- Tips: {', '.join(state.research_data.travel_tips[:3])}\n"
#             )

#         activities_context = "\n".join(
#             f"Day {d.day}: {', '.join(d.activities[:3])}"
#             for d in state.itinerary.days
#         )

#         system_prompt = f"""You are a travel budget expert. Estimate a REALISTIC cost breakdown for this trip.

# Trip details:
# - Destination: {destination}
# - Duration: {duration} days
# - Travel style: {travel_style}
# - User's total budget: {user_currency} {user_budget:,.0f}
# - Output currency: {user_currency}

# IMPORTANT: All amounts in your response must be in {user_currency}.
# Use your knowledge of actual local prices in {destination} — think in the local economy,
# not in USD. For example, if the destination is in India, think in rupees; if Thailand, in baht, etc.

# Planned activities to cost:
# {activities_context}
# {research_context}
# Estimate totals for the FULL {duration}-day trip (not per day) across these categories:
# - accommodation: total for {duration} nights
# - food: total for {duration} days (mix of local eateries and occasional restaurants)
# - activities: total entry fees, tours, experiences from the itinerary
# - transportation: total local transport (auto, metro, cab, intercity buses/trains)
# - miscellaneous: shopping, tips, buffer for unexpected costs

# Respond ONLY with valid JSON, no markdown:
# {{
#     "destination": "{destination}",
#     "duration": {duration},
#     "currency": "{user_currency}",
#     "categories": {{
#         "accommodation": <number>,
#         "food": <number>,
#         "activities": <number>,
#         "transportation": <number>,
#         "miscellaneous": <number>
#     }},
#     "total_estimated": <sum of all categories>,
#     "per_day_average": <total_estimated / {duration}>,
#     "budget_status": "within budget or over budget placeholder — will be recalculated",
#     "recommendations": [<3-5 specific money-saving tips for {destination}>]
# }}"""

#         response = llm.invoke([{"role": "user", "content": system_prompt}])
#         json_str = response.content.strip()

#         for fence in ("```json", "```"):
#             if json_str.startswith(fence):
#                 json_str = json_str[len(fence):]
#         if json_str.endswith("```"):
#             json_str = json_str[:-3]
#         json_str = json_str.strip()

#         budget_dict = json.loads(json_str)

#         # Enforce currency — LLM must not have overridden it
#         budget_dict["currency"] = user_currency

#         # Recalculate totals from categories to be safe (in case LLM math drifts)
#         categories = budget_dict.get("categories", {})
#         total = round(sum(categories.values()), 2)
#         budget_dict["total_estimated"] = total
#         budget_dict["per_day_average"] = round(total / duration, 2)

#         # Authoritative budget status check — done in code, not by the LLM
#         if user_budget == 0:
#             budget_dict["budget_status"] = "Estimated"
#         elif total <= user_budget:
#             budget_dict["budget_status"] = "Within budget"
#         else:
#             overage = total - user_budget
#             budget_dict["budget_status"] = f"Over budget by {user_currency} {overage:,.0f}"

#         budget_breakdown = BudgetBreakdown(**budget_dict)
#         state.budget_breakdown = budget_breakdown
#         state.conversation_history.append({
#             "role": "budget_agent",
#             "content": (
#                 f"Estimated total cost: {user_currency} {budget_breakdown.total_estimated:,.0f} "
#                 f"({user_currency} {budget_breakdown.per_day_average:,.0f}/day). "
#                 f"Status: {budget_breakdown.budget_status}."
#             ),
#         })

#     except ValidationError as e:
#         state.errors.append(f"Validation error in budget agent: {str(e)}")
#     except json.JSONDecodeError as e:
#         state.errors.append(f"JSON parsing error in budget agent: {str(e)}")
#     except Exception as e:
#         state.errors.append(f"Error in budget agent: {str(e)}")

#     return state


"""
Budget Agent: Estimates realistic trip costs in the user's own currency.

Uses OpenAI function calling with an OpenAI-friendly schema,
then converts the result into the application's BudgetBreakdown.
"""

from typing import List

from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field, ValidationError

from models.schemas import (
    TravelPlanState,
    BudgetBreakdown,
)

from config import MODEL, AGENT_CONFIG


# ============================================================
# OPENAI-FRIENDLY INTERNAL SCHEMAS
# ============================================================

class OpenAIBudgetCategories(BaseModel):
    """Budget categories generated by OpenAI."""

    accommodation: float = Field(
        description="Total accommodation cost for the entire trip"
    )

    food: float = Field(
        description="Total food cost for the entire trip"
    )

    activities: float = Field(
        description="Total activities, attractions and experiences cost"
    )

    transportation: float = Field(
        description="Total local transportation cost for the entire trip"
    )

    miscellaneous: float = Field(
        description="Total miscellaneous, tips and emergency buffer cost"
    )


class OpenAIBudget(BaseModel):
    """Internal structured budget response from OpenAI."""

    destination: str = Field(
        description="Travel destination"
    )

    duration: int = Field(
        description="Trip duration in days"
    )

    categories: OpenAIBudgetCategories = Field(
        description="Full-trip budget categories"
    )

    recommendations: List[str] = Field(
        description="3 to 5 specific money-saving recommendations"
    )


# ============================================================
# BUDGET AGENT
# ============================================================

def budget_agent_node(
    state: TravelPlanState,
) -> TravelPlanState:
    """
    Calculate realistic trip budget.

    Args:
        state: Current workflow state

    Returns:
        Updated state with budget_breakdown
    """

    # --------------------------------------------------------
    # Validate required data
    # --------------------------------------------------------

    if not state.trip_details:
        state.errors.append(
            "Trip details required for budget calculation"
        )
        return state

    if not state.itinerary:
        state.errors.append(
            "Itinerary required for budget calculation"
        )
        return state

    try:

        trip = state.trip_details
        itinerary = state.itinerary

        destination = trip.destination
        duration = trip.duration
        travel_style = trip.travel_style

        user_currency = trip.currency.upper()
        user_budget = trip.budget

        # ----------------------------------------------------
        # Initialize OpenAI
        # ----------------------------------------------------

        llm = ChatGoogleGenerativeAI(
            model=MODEL,
            temperature=AGENT_CONFIG["budget_agent"]["temperature"],
            max_output_tokens=4000,
            timeout=90,
            max_retries=1,
        )

        # ----------------------------------------------------
        # Use function calling instead of strict JSON schema
        # ----------------------------------------------------

        structured_llm = llm.with_structured_output(
            OpenAIBudget,
            method="function_calling",
        )

        # ----------------------------------------------------
        # Research context
        # ----------------------------------------------------

        research_context = ""

        if state.research_data:

            research_context = f"""
Destination:
{state.research_data.destination}

Overview:
{state.research_data.overview}

Transportation:
{state.research_data.transportation}

Travel tips:
{", ".join(state.research_data.travel_tips[:5])}
"""

        # ----------------------------------------------------
        # Itinerary context
        # ----------------------------------------------------

        itinerary_context_parts = []

        for day in itinerary.days:

            activities = "\n".join(
                f"- {activity}"
                for activity in day.activities
            )

            meals = "\n".join(
                f"- {key}: {value}"
                for key, value in day.meals.items()
            )

            estimates = "\n".join(
                f"- {key}: {value}"
                for key, value in day.estimates.items()
            )

            itinerary_context_parts.append(
                f"""
DAY {day.day}: {day.title}

Activities:
{activities}

Meals:
{meals}

Accommodation:
{day.accommodation}

Existing daily estimates:
{estimates}
"""
            )

        itinerary_context = "\n".join(
            itinerary_context_parts
        )

        # ----------------------------------------------------
        # Prompt
        # ----------------------------------------------------

        prompt = f"""
You are an expert travel budget planner.

Calculate a REALISTIC FULL-TRIP budget for the following
travel plan.

TRIP DETAILS
------------

Destination:
{destination}

Duration:
{duration} days

Travel style:
{travel_style}

User's total budget:
{user_currency} {user_budget:,.0f}

Output currency:
{user_currency}

IMPORTANT:

ALL monetary values MUST be in {user_currency}.

The user's budget is already expressed in {user_currency}.

DO NOT convert the budget to USD.

RESEARCH INFORMATION
--------------------

{research_context}

ITINERARY
---------

{itinerary_context}

BUDGET CATEGORIES
-----------------

Calculate the TOTAL cost for the entire {duration}-day trip.

1. Accommodation
   - Total accommodation cost for the trip.
   - Consider the number of nights.
   - Match the {travel_style} travel style.

2. Food
   - Total breakfast, lunch and dinner cost.
   - Include realistic local food and occasional restaurants.
   - Match the travel style.

3. Activities
   - Attraction entry fees.
   - Tours.
   - Experiences.
   - Other planned activity costs.

4. Transportation
   - Auto-rickshaws.
   - Taxis.
   - Buses.
   - Metro where applicable.
   - Scooters where applicable.
   - Other local transportation.

5. Miscellaneous
   - Tips.
   - Small purchases.
   - Unexpected expenses.
   - Reasonable emergency buffer.

IMPORTANT RULES
---------------

- Think in the local economy of {destination}.
- Use realistic local prices.
- Match the {travel_style} travel style.
- Calculate the FULL trip.
- Do NOT calculate only one day.
- Do NOT automatically spend the entire budget.
- Do NOT include international flights unless explicitly requested.
- Do NOT convert anything to USD.
- Every amount must be in {user_currency}.
- Return 3-5 useful money-saving recommendations.
"""

        # ----------------------------------------------------
        # Call OpenAI
        # ----------------------------------------------------

        result = structured_llm.invoke(
            prompt
        )

        # ----------------------------------------------------
        # Check response
        # ----------------------------------------------------

        if result is None:

            state.errors.append(
                "OpenAI returned empty budget"
            )

            return state

        # ----------------------------------------------------
        # Extract categories
        # ----------------------------------------------------

        categories = {
            "accommodation": round(
                float(
                    result.categories.accommodation
                ),
                2,
            ),

            "food": round(
                float(
                    result.categories.food
                ),
                2,
            ),

            "activities": round(
                float(
                    result.categories.activities
                ),
                2,
            ),

            "transportation": round(
                float(
                    result.categories.transportation
                ),
                2,
            ),

            "miscellaneous": round(
                float(
                    result.categories.miscellaneous
                ),
                2,
            ),
        }

        # ----------------------------------------------------
        # Calculate total ourselves
        # ----------------------------------------------------

        total = round(
            sum(categories.values()),
            2,
        )

        per_day_average = round(
            total / duration,
            2,
        )

        # ----------------------------------------------------
        # Calculate authoritative budget status
        # ----------------------------------------------------

        if user_budget == 0:

            budget_status = "Estimated"

        elif total <= user_budget:

            budget_status = "Within budget"

        else:

            overage = round(
                total - user_budget,
                2,
            )

            budget_status = (
                f"Over budget by "
                f"{user_currency} "
                f"{overage:,.0f}"
            )

        # ----------------------------------------------------
        # Create application's BudgetBreakdown
        # ----------------------------------------------------

        budget_breakdown = BudgetBreakdown(
            destination=destination,
            duration=duration,
            currency=user_currency,
            categories=categories,
            total_estimated=total,
            per_day_average=per_day_average,
            budget_status=budget_status,
            recommendations=[
                str(recommendation)
                for recommendation
                in result.recommendations[:5]
            ],
        )

        # ----------------------------------------------------
        # Store budget
        # ----------------------------------------------------

        state.budget_breakdown = (
            budget_breakdown
        )

        # ----------------------------------------------------
        # Conversation history
        # ----------------------------------------------------

        state.conversation_history.append(
            {
                "role": "budget_agent",
                "content": (
                    f"Estimated total cost: "
                    f"{user_currency} "
                    f"{total:,.0f} "
                    f"({user_currency} "
                    f"{per_day_average:,.0f}/day). "
                    f"Status: "
                    f"{budget_status}."
                ),
            }
        )

    # --------------------------------------------------------
    # Error handling
    # --------------------------------------------------------

    except ValidationError as e:

        state.errors.append(
            "Validation error in budget agent: "
            f"{str(e)}"
        )

    except Exception as e:

        state.errors.append(
            "Error in budget agent: "
            f"{type(e).__name__}: {str(e)}"
        )

    return state