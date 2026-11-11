"""
Intent Agent: Extracts and validates trip details from user input.

The Intent Agent is the first validation layer of the travel planner.
It extracts trip information, validates the input, and prepares
structured data for the downstream agents.
"""

import json
import re

from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import ValidationError

from models.schemas import TravelPlanState, TripDetails
from config import MODEL, AGENT_CONFIG


# ============================================================
# GEMINI RESPONSE NORMALIZATION
# ============================================================

def _response_to_text(response) -> str:
    """
    Convert a LangChain/Gemini response into a plain string.

    Gemini integrations can return response.content as either:
    - A string
    - A list of content blocks, such as:
      [{"type": "text", "text": "..."}]

    This prevents:
        AttributeError: 'list' object has no attribute 'strip'
    """

    content = getattr(response, "content", response)

    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        text_parts = []

        for block in content:
            if isinstance(block, str):
                text_parts.append(block)

            elif isinstance(block, dict):
                if block.get("type") == "text":
                    text_value = block.get("text", "")

                    if isinstance(text_value, str):
                        text_parts.append(text_value)

                elif isinstance(block.get("text"), str):
                    text_parts.append(block["text"])

            else:
                block_text = getattr(block, "text", None)

                if isinstance(block_text, str):
                    text_parts.append(block_text)

        return "\n".join(text_parts).strip()

    if content is None:
        return ""

    return str(content).strip()


# ============================================================
# EXPLICIT CURRENCY DETECTION
# ============================================================

_EXPLICIT_CURRENCY_RE = [
    (
        re.compile(
            r"(?:₹|(?<!\w)rs\.?(?!\w)|rupees?|(?<!\w)inr(?!\w))",
            re.IGNORECASE,
        ),
        "INR",
    ),
    (
        re.compile(
            r"(?:\$|(?<!\w)usd(?!\w)|dollars?)",
            re.IGNORECASE,
        ),
        "USD",
    ),
    (
        re.compile(
            r"(?:€|(?<!\w)eur(?!\w)|euros?)",
            re.IGNORECASE,
        ),
        "EUR",
    ),
    (
        re.compile(
            r"(?:£|(?<!\w)gbp(?!\w)|pounds?)",
            re.IGNORECASE,
        ),
        "GBP",
    ),
    (
        re.compile(
            r"(?:¥|(?<!\w)jpy(?!\w)|yen)",
            re.IGNORECASE,
        ),
        "JPY",
    ),
    (
        re.compile(
            r"(?<!\w)aed(?!\w)|dirhams?",
            re.IGNORECASE,
        ),
        "AED",
    ),
    (
        re.compile(
            r"(?<!\w)sgd(?!\w)",
            re.IGNORECASE,
        ),
        "SGD",
    ),
]


def _detect_explicit_currency(text: str) -> str | None:
    """
    Detect currency only when the user explicitly mentions it.

    Examples:
        ₹20,000       -> INR
        20,000 rupees -> INR
        20k INR       -> INR
        $500          -> USD

    Bare amounts such as 20000 and 25k do not specify currency.
    """

    for pattern, code in _EXPLICIT_CURRENCY_RE:
        if pattern.search(text):
            return code

    return None


# ============================================================
# NUMBER NORMALIZATION
# ============================================================

def _normalize_numbers(text: str) -> str:
    """
    Convert shorthand numbers into numeric values.

    Examples:
        25k       -> 25000
        1.5lac    -> 150000
        2 lakh    -> 200000
        2.5 lakhs -> 250000
    """

    text = re.sub(
        r"\b(\d+(?:\.\d+)?)\s*[kK]\b",
        lambda match: str(
            int(float(match.group(1)) * 1000)
        ),
        text,
    )

    text = re.sub(
        r"\b(\d+(?:\.\d+)?)\s*[lL](?:ac|akh)?\b",
        lambda match: str(
            int(float(match.group(1)) * 100000)
        ),
        text,
    )

    return text


# ============================================================
# CURRENCY INFERENCE
# ============================================================

def _infer_currency_for_destination(
    destination: str,
    llm: ChatGoogleGenerativeAI,
) -> str:
    """
    Infer the destination's local currency when the user
    has not explicitly specified one.
    """

    if not destination:
        return "USD"

    prompt = f"""
What is the official local currency ISO 4217 code for the
travel destination "{destination}"?

Reply with ONLY the 3-letter ISO code.

Examples:
India -> INR
Thailand -> THB
Japan -> JPY
France -> EUR
USA -> USD
United Kingdom -> GBP
"""

    try:
        response = llm.invoke(
            [
                {
                    "role": "user",
                    "content": prompt,
                }
            ]
        )

        code = _response_to_text(response).upper()

        # Accept only a valid three-letter currency code.
        if re.fullmatch(r"[A-Z]{3}", code):
            return code

    except Exception:
        pass

    # Fallback if currency inference fails.
    return "USD"


# ============================================================
# TRIP INPUT VALIDATION
# ============================================================

def _validate_trip_input(
    trip_data: dict,
) -> list[str]:
    """
    Validate extracted trip information.

    Returns friendly messages instead of allowing invalid
    values to reach downstream agents.
    """

    errors = []

    # Destination
    destination = str(
        trip_data.get("destination") or ""
    ).strip()

    if not destination:
        errors.append(
            "Please tell me your travel destination."
        )

    # Duration
    duration = trip_data.get("duration", 0)

    try:
        duration = int(duration)
    except (TypeError, ValueError):
        duration = 0

    if duration <= 0:
        errors.append(
            "Please specify how many days you want to travel."
        )

    elif duration > 365:
        errors.append(
            "The trip duration seems too long. "
            "Please enter a duration between 1 and 365 days."
        )

    # Budget
    budget = trip_data.get("budget", 0)

    try:
        budget = float(budget)
    except (TypeError, ValueError):
        budget = 0

    if budget < 0:
        errors.append(
            "Your budget cannot be negative."
        )

    return errors


# ============================================================
# FRIENDLY ERROR MESSAGE
# ============================================================

def _set_input_error(
    state: TravelPlanState,
    message: str,
) -> TravelPlanState:
    """
    Store a user-friendly error and clear invalid trip details.
    """

    state.trip_details = None
    state.errors.append(message)

    state.conversation_history.append(
        {
            "role": "intent_agent",
            "content": message,
        }
    )

    return state


# ============================================================
# INTENT AGENT
# ============================================================

def intent_agent_node(
    state: TravelPlanState,
) -> TravelPlanState:
    """
    Extract and validate trip details.

    Valid request:
        Intent -> Research -> Itinerary -> Budget -> Compile

    Invalid request:
        Intent -> STOP
    """

    # --------------------------------------------------------
    # Step 1: Check empty input
    # --------------------------------------------------------

    if (
        not state.user_input
        or not state.user_input.strip()
    ):
        return _set_input_error(
            state,
            (
                "⚠️ I need a little more information "
                "before I can plan your trip.\n\n"
                "Please provide a destination and trip duration.\n\n"
                "Example:\n"
                '"Plan a 3-day trip to Hyderabad '
                'with a budget of ₹20,000."'
            ),
        )

    user_input = state.user_input.strip()

    try:
        # ----------------------------------------------------
        # Step 2: Initialize Gemini
        # ----------------------------------------------------

        llm = ChatGoogleGenerativeAI(
            model=MODEL,
            temperature=AGENT_CONFIG["intent_agent"]["temperature"],
            max_output_tokens=AGENT_CONFIG["intent_agent"]["max_tokens"],
            timeout=60,
            max_retries=1,
        )

        # ----------------------------------------------------
        # Step 3: Detect explicitly specified currency
        # ----------------------------------------------------

        explicit_currency = _detect_explicit_currency(
            user_input
        )

        # ----------------------------------------------------
        # Step 4: Normalize shorthand numbers
        # ----------------------------------------------------

        normalized_input = _normalize_numbers(
            user_input
        )

        # ----------------------------------------------------
        # Step 5: Extract trip information
        # ----------------------------------------------------

        system_prompt = """
You are the intent extraction component of a travel
planning application.

Extract trip information from the user's request.

Return ONLY a valid JSON object.
Do not return markdown.
Do not return explanations.

Required fields:

destination:
- Travel destination.
- Return an empty string if missing.

budget:
- Numeric total budget.
- Return 0 if the user did not mention a budget.

currency:
- 3-letter ISO currency code.
- Best guess based on the request.

duration:
- Number of travel days.
- If the user DOES NOT explicitly specify the trip duration,
  return 0.
- NEVER invent a duration.
- NEVER assume 1, 2, 3, 5 or any other number.

start_date:
- YYYY-MM-DD if specified.
- Otherwise null.

travel_style:
- budget
- moderate
- luxury
- If not specified, use moderate.

accommodation_type:
- hotel
- hostel
- airbnb
- resort
- Default to hotel.

preferences:
- List of user preferences.

interests:
- List of user interests.

IMPORTANT:
Never invent missing information.

Example 1:

User:
Plan a 5-day budget trip to Goa with INR 20,000.

Return:
{
    "destination": "Goa",
    "budget": 20000,
    "currency": "INR",
    "duration": 5,
    "start_date": null,
    "travel_style": "budget",
    "accommodation_type": "hotel",
    "preferences": [],
    "interests": ["beaches"]
}

Example 2:

User:
Travel to Hyderabad around 20000 rupees.

Duration is missing, so return:
{
    "destination": "Hyderabad",
    "budget": 20000,
    "currency": "INR",
    "duration": 0,
    "start_date": null,
    "travel_style": "moderate",
    "accommodation_type": "hotel",
    "preferences": [],
    "interests": []
}
"""

        response = llm.invoke(
            [
                {
                    "role": "user",
                    "content": (
                        system_prompt
                        + "\n\nUSER INPUT:\n"
                        + normalized_input
                    ),
                }
            ]
        )

        # ----------------------------------------------------
        # Step 6: Convert Gemini response to plain text
        # ----------------------------------------------------

        # IMPORTANT:
        # Do not use response.content.strip() directly.
        # Gemini may return response.content as a list.
        response_text = _response_to_text(response)

        # Remove optional Markdown code fences.
        if response_text.startswith("```json"):
            response_text = response_text[7:]

        elif response_text.startswith("```"):
            response_text = response_text[3:]

        if response_text.endswith("```"):
            response_text = response_text[:-3]

        response_text = response_text.strip()

        if not response_text:
            return _set_input_error(
                state,
                (
                    "⚠️ I couldn't understand your trip request.\n\n"
                    "Please provide a destination and duration.\n\n"
                    "Example:\n"
                    '"Plan a 3-day trip to Hyderabad '
                    'with a budget of ₹20,000."'
                ),
            )

        # Parse the JSON response.
        trip_data = json.loads(response_text)

        if not isinstance(trip_data, dict):
            return _set_input_error(
                state,
                (
                    "⚠️ I couldn't extract your trip details "
                    "correctly. Please try describing your "
                    "destination, duration, and budget again."
                ),
            )

        # ----------------------------------------------------
        # Step 7: Validate extracted trip information
        # ----------------------------------------------------

        validation_errors = _validate_trip_input(
            trip_data
        )

        if validation_errors:
            error_lines = "\n".join(
                f"• {error}"
                for error in validation_errors
            )

            friendly_message = (
                "⚠️ I need a little more information "
                "before I can plan your trip.\n\n"
                f"{error_lines}\n\n"
                "Example:\n"
                '"Plan a 3-day trip to Hyderabad '
                'with a budget of ₹20,000."'
            )

            state.conversation_history.append(
                {
                    "role": "user",
                    "content": user_input,
                }
            )

            return _set_input_error(
                state,
                friendly_message,
            )

        # ----------------------------------------------------
        # Step 8: Resolve currency
        # ----------------------------------------------------

        if explicit_currency:
            # Respect an explicitly provided currency.
            final_currency = explicit_currency

        else:
            # Infer the local currency for the destination.
            destination = str(
                trip_data.get("destination", "")
            ).strip()

            final_currency = _infer_currency_for_destination(
                destination,
                llm,
            )

        trip_data["currency"] = final_currency

        # ----------------------------------------------------
        # Step 9: Create validated TripDetails
        # ----------------------------------------------------

        trip_details = TripDetails(
            **trip_data
        )

        state.trip_details = trip_details

        # ----------------------------------------------------
        # Step 10: Update conversation history
        # ----------------------------------------------------

        state.conversation_history.append(
            {
                "role": "user",
                "content": user_input,
            }
        )

        if trip_details.budget > 0:
            budget_text = (
                f"with a budget of "
                f"{trip_details.currency} "
                f"{trip_details.budget:,.0f}"
            )

        else:
            budget_text = "with no specified budget"

        state.conversation_history.append(
            {
                "role": "intent_agent",
                "content": (
                    f"Understood! Planning a "
                    f"{trip_details.duration}-day "
                    f"{trip_details.travel_style} trip "
                    f"to {trip_details.destination} "
                    f"{budget_text}. "
                    f"Interests: "
                    f"{', '.join(trip_details.interests) or 'general'}."
                ),
            }
        )

    # --------------------------------------------------------
    # JSON parsing failure
    # --------------------------------------------------------

    except json.JSONDecodeError:
        return _set_input_error(
            state,
            (
                "⚠️ I couldn't understand that trip request.\n\n"
                "Please provide a destination and number of days.\n\n"
                "Example:\n"
                '"Plan a 3-day trip to Hyderabad '
                'with a budget of ₹20,000."'
            ),
        )

    # --------------------------------------------------------
    # Pydantic validation failure
    # --------------------------------------------------------

    except ValidationError as e:
        return _set_input_error(
            state,
            (
                "⚠️ Some of the trip details are invalid.\n\n"
                "Please provide a valid destination and "
                "trip duration.\n\n"
                f"Details: {str(e)}"
            ),
        )

    # --------------------------------------------------------
    # Unexpected error
    # --------------------------------------------------------

    except Exception as e:
        return _set_input_error(
            state,
            (
                "⚠️ I couldn't process your trip request "
                "right now.\n\n"
                f"Error: {type(e).__name__}: {str(e)}"
            ),
        )

    return state