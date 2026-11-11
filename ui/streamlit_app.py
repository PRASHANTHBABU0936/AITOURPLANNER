"""
Streamlit UI for Travel Planning Assistant.

Features:
- Live agent progress cards
- Session history
- Destination image display
- Itinerary and budget presentation
- PDF and JSON downloads
- Detailed workflow debugging
"""

import sys
from pathlib import Path

# Ensure the project root is available for imports.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import json
from datetime import datetime

import streamlit as st

from models.schemas import TravelPlanState
from graph import travel_planner_graph
from config import STREAMLIT_CONFIG
from tools.pdf_generator import generate_travel_plan_pdf


# ============================================================
# AGENT CONFIGURATION
# ============================================================

AGENTS = [
    ("intent_agent", "🎯", "Intent Agent"),
    ("research_agent", "🔍", "Research Agent"),
    ("itinerary_agent", "🗓️", "Itinerary Agent"),
    ("budget_agent", "💰", "Budget Agent"),
    ("compile_plan", "📋", "Compiling Plan"),
    ("image_agent", "📸", "Image Agent"),
]


# ============================================================
# SAFE VALUE HELPERS
# ============================================================

def safe_get(obj, attribute, default=None):
    """Safely retrieve an attribute from an object."""
    if obj is None:
        return default

    return getattr(obj, attribute, default)


def safe_string(value, default="Not available"):
    """Convert a value into a displayable string."""
    if value is None:
        return default

    if isinstance(value, list):
        return ", ".join(str(item) for item in value)

    return str(value)


# ============================================================
# FORMAT THE FINAL TRAVEL PLAN
# ============================================================

def format_travel_plan(state: TravelPlanState) -> str:
    """Format the generated travel plan as Markdown."""

    plan = safe_get(state, "final_plan")

    if plan is None:
        return "No final travel plan was generated."

    destination = safe_string(
        safe_get(plan, "destination"),
        "Unknown destination",
    )

    duration = safe_get(plan, "duration", 0)

    budget = safe_get(plan, "budget")
    destination_info = safe_get(plan, "destination_info")
    itinerary = safe_get(plan, "itinerary")

    if budget is None:
        return (
            "# ⚠️ Incomplete Travel Plan\n\n"
            "The final plan does not contain budget information."
        )

    currency = (
        safe_get(budget, "currency")
        or safe_get(
            safe_get(plan, "trip_details"),
            "currency",
        )
        or "USD"
    )

    total_estimated = safe_get(
        budget,
        "total_estimated",
        0,
    ) or 0

    per_day_average = safe_get(
        budget,
        "per_day_average",
        0,
    ) or 0

    budget_status = safe_string(
        safe_get(budget, "budget_status"),
        "Not available",
    )

    output = f"""
# ✈️ Your Travel Plan to {destination}

## Trip Overview

- **Duration:** {duration} days
- **Estimated Cost:** {currency} {total_estimated:,.2f}
- **Daily Average:** {currency} {per_day_average:,.2f}
- **Budget Status:** {budget_status}
"""

    # --------------------------------------------------------
    # Destination information
    # --------------------------------------------------------

    if destination_info is not None:
        output += f"""
## Destination Highlights

**{safe_string(safe_get(destination_info, "overview"))}**

### Best Time to Visit

{safe_string(safe_get(destination_info, "best_time_to_visit"))}

### Weather

{safe_string(safe_get(destination_info, "weather"))}

### Top Attractions
"""

        attractions = safe_get(
            destination_info,
            "attractions",
            [],
        ) or []

        for attraction in attractions:
            output += f"- {attraction}\n"

        output += f"""
### Local Cuisine

{safe_string(safe_get(destination_info, "cuisine"))}

### Transportation

{safe_string(safe_get(destination_info, "transportation"))}
"""

    else:
        output += (
            "\n## Destination Highlights\n\n"
            "Destination information was not included in the final plan.\n"
        )

    # --------------------------------------------------------
    # Day-by-day itinerary
    # --------------------------------------------------------

    output += "\n---\n\n## Day-by-Day Itinerary\n\n"

    if itinerary is None:
        output += (
            "⚠️ The itinerary was not included in the final plan.\n"
        )

    else:
        days = safe_get(itinerary, "days", []) or []

        if not days:
            output += "No itinerary days were returned.\n"

        for day in days:
            day_number = safe_get(day, "day", "?")
            title = safe_string(
                safe_get(day, "title"),
                "Activities",
            )

            output += f"### Day {day_number}: {title}\n\n"

            output += "**Activities:**\n"

            activities = safe_get(
                day,
                "activities",
                [],
            ) or []

            if activities:
                for activity in activities:
                    output += f"- {activity}\n"
            else:
                output += "- No activities provided.\n"

            output += "\n**Meals:**\n"

            meals = safe_get(day, "meals", {}) or {}

            if isinstance(meals, dict) and meals:
                for meal_type, restaurant in meals.items():
                    output += (
                        f"- {str(meal_type).capitalize()}: "
                        f"{restaurant}\n"
                    )
            else:
                output += "- No meal recommendations provided.\n"

            accommodation = safe_string(
                safe_get(day, "accommodation"),
                "Not specified",
            )

            output += (
                f"\n**Accommodation:** {accommodation}\n\n"
                "**Estimated Costs:**\n"
            )

            estimates = safe_get(
                day,
                "estimates",
                {},
            ) or {}

            if isinstance(estimates, dict) and estimates:
                for cost_type, amount in estimates.items():
                    try:
                        formatted_amount = float(amount)
                        output += (
                            f"- {str(cost_type).capitalize()}: "
                            f"{currency} {formatted_amount:,.2f}\n"
                        )
                    except (TypeError, ValueError):
                        output += (
                            f"- {str(cost_type).capitalize()}: "
                            f"{amount}\n"
                        )
            else:
                output += "- No cost estimates provided.\n"

            output += "\n---\n"

    # --------------------------------------------------------
    # Budget breakdown
    # --------------------------------------------------------

    output += "\n## Budget Breakdown\n\n"

    categories = safe_get(
        budget,
        "categories",
        {},
    ) or {}

    if isinstance(categories, dict) and categories:
        for category, amount in categories.items():
            try:
                formatted_amount = float(amount)
                output += (
                    f"- **{str(category).capitalize()}:** "
                    f"{currency} {formatted_amount:,.2f}\n"
                )
            except (TypeError, ValueError):
                output += (
                    f"- **{str(category).capitalize()}:** "
                    f"{amount}\n"
                )
    else:
        output += "No category-level budget breakdown provided.\n"

    output += f"""
### Total Estimated Cost

{currency} {total_estimated:,.2f}

**Budget Status:** {budget_status}

### Money-Saving Tips
"""

    recommendations = safe_get(
        budget,
        "recommendations",
        [],
    ) or []

    for recommendation in recommendations:
        output += f"- {recommendation}\n"

    if not recommendations:
        output += "- No money-saving recommendations provided.\n"

    # --------------------------------------------------------
    # Travel tips
    # --------------------------------------------------------

    output += "\n## Travel Tips\n"

    if destination_info is not None:
        travel_tips = safe_get(
            destination_info,
            "travel_tips",
            [],
        ) or []

        for tip in travel_tips:
            output += f"- {tip}\n"

        if not travel_tips:
            output += "- No additional travel tips provided.\n"
    else:
        output += "- Destination-specific tips are unavailable.\n"

    # --------------------------------------------------------
    # Special notes
    # --------------------------------------------------------

    special_notes = safe_get(
        itinerary,
        "special_notes",
        [],
    ) or []

    if special_notes:
        output += "\n## Special Notes\n"

        for note in special_notes:
            output += f"- {note}\n"

    return output


# ============================================================
# DISPLAY GENERATED IMAGES
# ============================================================

def display_images(images: list) -> None:
    """Display generated images in a responsive grid."""

    if not images:
        return

    valid_images = []

    for img in images:
        if not isinstance(img, dict):
            continue

        image_path = img.get("path")

        if not image_path:
            continue

        path = Path(image_path)

        if path.exists():
            valid_images.append(
                {
                    "path": path,
                    "caption": img.get(
                        "caption",
                        "Travel destination",
                    ),
                }
            )

    if not valid_images:
        return

    st.markdown("## 📸 Destination Gallery")

    columns = st.columns(
        min(len(valid_images), 3)
    )

    for index, img in enumerate(valid_images):
        with columns[index % len(columns)]:
            st.image(
                str(img["path"]),
                caption=img["caption"],
                use_container_width=True,
            )


# ============================================================
# WORKFLOW DEBUG INFORMATION
# ============================================================

def display_debug_information(state: TravelPlanState) -> None:
    """
    Display the actual workflow state when a final plan
    was not generated.
    """

    st.error(
        "❌ The workflow finished without producing "
        "a final travel plan."
    )

    with st.expander(
        "🔍 Debug Information — Click to inspect",
        expanded=True,
    ):
        st.write(
            "**Final plan created:**",
            safe_get(state, "final_plan") is not None,
        )

        st.write(
            "**Trip details created:**",
            safe_get(state, "trip_details") is not None,
        )

        st.write(
            "**Research data created:**",
            safe_get(state, "research_data") is not None,
        )

        st.write(
            "**Itinerary created:**",
            safe_get(state, "itinerary") is not None,
        )

        st.write(
            "**Budget breakdown created:**",
            safe_get(state, "budget_breakdown") is not None,
        )

        st.write(
            "**Generated images:**",
            len(safe_get(state, "generated_images", []) or []),
        )

        errors = safe_get(state, "errors", []) or []

        st.markdown("### Workflow Errors")

        if errors:
            for index, error in enumerate(errors, start=1):
                st.error(f"{index}. {str(error)}")
        else:
            st.info(
                "No errors were recorded in state.errors. "
                "The compiler or graph may have failed to "
                "populate final_plan."
            )

        st.markdown("### Conversation History")

        history = safe_get(
            state,
            "conversation_history",
            [],
        ) or []

        if history:
            for item in history:
                if isinstance(item, dict):
                    role = item.get("role", "unknown")
                    content = item.get("content", "")

                    st.write(f"**{role}:** {content}")
                else:
                    st.write(str(item))
        else:
            st.info("No conversation history was recorded.")


# ============================================================
# RUN PIPELINE WITH LIVE AGENT PROGRESS
# ============================================================

def run_with_streaming(user_input: str) -> TravelPlanState:
    """
    Run the LangGraph workflow and update progress cards.

    This function preserves the graph's returned state so
    downstream errors can be inspected by the UI.
    """

    state = TravelPlanState(
        user_input=user_input,
    )

    st.markdown("#### 🤖 Agent Progress")

    placeholders = {}

    # Create progress cards before the graph begins.
    for key, icon, label in AGENTS:
        placeholders[key] = st.empty()

        placeholders[key].info(
            f"{icon} **{label}:** ⏳ Waiting..."
        )

    # Execute the graph.
    for step in travel_planner_graph.stream(
        state.model_dump()
    ):
        if not isinstance(step, dict) or not step:
            continue

        node_name = next(iter(step.keys()))
        node_output = step[node_name]

        if not isinstance(node_output, dict):
            continue

        # Graph node outputs can be partial state updates.
        # Merge each update into the previous state instead
        # of assuming every node returns the entire state.
        current_state = state.model_dump()

        for key, value in node_output.items():
            current_state[key] = value

        state = TravelPlanState(**current_state)

        if node_name not in placeholders:
            continue

        icon, label = next(
            (icon, label)
            for key, icon, label in AGENTS
            if key == node_name
        )

        conversation_history = (
            state.conversation_history or []
        )

        message = next(
            (
                item.get("content", "")
                for item in reversed(conversation_history)
                if isinstance(item, dict)
                and item.get("role") == node_name
            ),
            "Completed.",
        )

        errors = state.errors or []

        if errors:
            placeholders[node_name].warning(
                f"{icon} **{label}:** ⚠️ {message}"
            )
        else:
            placeholders[node_name].success(
                f"{icon} **{label}:** ✅ {message}"
            )

    return state


# ============================================================
# SIDEBAR — SESSION HISTORY
# ============================================================

def render_sidebar() -> None:
    """Render the sidebar and previously generated plans."""

    with st.sidebar:
        st.header("✈️ Travel Planner")

        st.markdown("*AI-powered trip planning*")

        st.divider()

        history = st.session_state.history

        if history:
            st.subheader("📋 Previous Plans")

            for index, entry in enumerate(reversed(history)):
                original_index = len(history) - 1 - index

                destination = entry.get(
                    "destination",
                    "Unknown",
                )

                currency = entry.get("currency", "USD")

                total = entry.get("total", 0)

                duration = entry.get("duration", 0)

                timestamp = entry.get(
                    "timestamp",
                    "",
                )

                if st.button(
                    (
                        f"🗺️ {destination} — "
                        f"{currency} {total:,.0f} "
                        f"({duration}d)\n_{timestamp}_"
                    ),
                    key=f"history_{original_index}",
                    use_container_width=True,
                ):
                    st.session_state.viewing_history = (
                        original_index
                    )

                    st.rerun()

            st.divider()

        st.info(
            """
**Features:**

- Destination research
- Personalized itineraries
- Budget estimation
- AI-generated images
- Travel tips
"""
        )


# ============================================================
# MAIN STREAMLIT APP
# ============================================================

def main() -> None:
    """Main entry point for the Streamlit application."""

    st.set_page_config(
        page_title=STREAMLIT_CONFIG["page_title"],
        page_icon=STREAMLIT_CONFIG["page_icon"],
        layout=STREAMLIT_CONFIG["layout"],
    )

    # --------------------------------------------------------
    # Initialize session state
    # --------------------------------------------------------

    if "history" not in st.session_state:
        st.session_state.history = []

    if "current_state" not in st.session_state:
        st.session_state.current_state = None

    if "viewing_history" not in st.session_state:
        st.session_state.viewing_history = None

    render_sidebar()

    # --------------------------------------------------------
    # Previous plan view
    # --------------------------------------------------------

    if st.session_state.viewing_history is not None:
        index = st.session_state.viewing_history

        if index >= len(st.session_state.history):
            st.session_state.viewing_history = None
            st.rerun()

        entry = st.session_state.history[index]

        st.title(
            f"✈️ Saved Plan: {entry['destination']}"
        )

        st.caption(
            f"Generated at {entry['timestamp']}"
        )

        if st.button("⬅️ Back to Planner"):
            st.session_state.viewing_history = None
            st.rerun()

        saved_state = entry["state"]

        display_images(
            safe_get(saved_state, "generated_images", []) or []
        )

        st.markdown(
            format_travel_plan(saved_state)
        )

        col1, col2 = st.columns(2)

        with col1:
            saved_plan = safe_get(
                saved_state,
                "final_plan",
            )

            if saved_plan is not None:
                plan_json = json.dumps(
                    saved_plan.model_dump(),
                    indent=2,
                    default=str,
                )

                st.download_button(
                    "📥 Download (JSON)",
                    plan_json,
                    file_name=(
                        f"travel_plan_{entry['destination']}.json"
                    ),
                    mime="application/json",
                    use_container_width=True,
                )

        with col2:
            try:
                saved_plan = safe_get(
                    saved_state,
                    "final_plan",
                )

                if saved_plan is not None:
                    pdf_data = generate_travel_plan_pdf(
                        saved_plan,
                        safe_get(
                            saved_state,
                            "generated_images",
                            [],
                        ) or [],
                    )

                    st.download_button(
                        "📄 Download (PDF)",
                        pdf_data,
                        file_name=(
                            f"travel_plan_{entry['destination']}.pdf"
                        ),
                        mime="application/pdf",
                        use_container_width=True,
                    )

            except Exception as error:
                st.error(
                    f"PDF generation error: {error}"
                )

        return

    # --------------------------------------------------------
    # Main planner interface
    # --------------------------------------------------------

    st.title("✈️ Travel Planning Assistant")

    st.markdown(
        "*Plan your perfect trip with AI-powered personalized recommendations*"
    )

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("🏖️ Tell us about your trip")

        user_input = st.text_area(
            "Describe your travel plans",
            placeholder=(
                "E.g., 'Plan a 5-day budget trip to Goa "
                "under ₹25k with beach activities'"
            ),
            height=120,
            key="user_input",
        )

    with col2:
        st.subheader("💡 Tips")

        st.markdown(
            """
- Be specific about:
  - Destination
  - Budget (₹/$/€)
  - Duration
  - Interests
- Mention travel style:
  - Budget / Moderate / Luxury
"""
        )

    # --------------------------------------------------------
    # Generate travel plan
    # --------------------------------------------------------

    if st.button(
        "🚀 Generate Travel Plan",
        use_container_width=True,
    ):
        if not user_input.strip():
            st.error(
                "❌ Please describe your travel plans."
            )

        else:
            st.divider()

            try:
                result = run_with_streaming(user_input)

                # Preserve the result for debugging, even
                # when final_plan is missing.
                st.session_state.current_state = result

                final_plan = safe_get(
                    result,
                    "final_plan",
                )

                errors = safe_get(
                    result,
                    "errors",
                    [],
                ) or []

                # ------------------------------------------------
                # No final plan: show actual diagnostic details
                # ------------------------------------------------

                if final_plan is None:
                    display_debug_information(result)

                else:
                    # --------------------------------------------
                    # Successful result
                    # --------------------------------------------

                    plan_budget = safe_get(
                        final_plan,
                        "budget",
                    )

                    currency = (
                        safe_get(plan_budget, "currency")
                        or safe_get(
                            safe_get(final_plan, "trip_details"),
                            "currency",
                        )
                        or "USD"
                    )

                    total = safe_get(
                        plan_budget,
                        "total_estimated",
                        0,
                    ) or 0

                    destination = safe_get(
                        final_plan,
                        "destination",
                        "Unknown",
                    )

                    duration = safe_get(
                        final_plan,
                        "duration",
                        0,
                    )

                    # Avoid duplicate history entries.
                    st.session_state.history.append(
                        {
                            "destination": destination,
                            "duration": duration,
                            "currency": currency,
                            "total": total,
                            "timestamp": datetime.now().strftime(
                                "%d %b %Y, %H:%M"
                            ),
                            "state": result,
                        }
                    )

                    st.success(
                        "✅ Travel plan generated successfully!"
                    )

                    if errors:
                        with st.expander(
                            "⚠️ Workflow warnings",
                            expanded=False,
                        ):
                            for error in errors:
                                st.warning(str(error))

            except Exception as error:
                st.error(
                    f"❌ Application error: "
                    f"{type(error).__name__}: {error}"
                )

                with st.expander(
                    "🔍 Full error details",
                    expanded=True,
                ):
                    import traceback

                    st.code(
                        traceback.format_exc(),
                        language="text",
                    )

    # --------------------------------------------------------
    # Display generated plan
    # --------------------------------------------------------

    current_state = st.session_state.current_state

    if current_state is not None:
        final_plan = safe_get(
            current_state,
            "final_plan",
        )

        if final_plan is not None:
            st.divider()

            state = current_state

            if state.errors:
                with st.expander(
                    "⚠️ Warnings",
                    expanded=False,
                ):
                    for error in state.errors:
                        st.warning(str(error))

            display_images(
                safe_get(state, "generated_images", []) or []
            )

            st.markdown(
                format_travel_plan(state)
            )

            col1, col2 = st.columns(2)

            # --------------------------------------------
            # JSON download
            # --------------------------------------------

            with col1:
                try:
                    plan_json = json.dumps(
                        final_plan.model_dump(),
                        indent=2,
                        default=str,
                    )

                    st.download_button(
                        "📥 Download (JSON)",
                        plan_json,
                        file_name=(
                            f"travel_plan_{final_plan.destination}_"
                            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                        ),
                        mime="application/json",
                        use_container_width=True,
                    )

                except Exception as error:
                    st.error(
                        f"JSON export error: {error}"
                    )

            # --------------------------------------------
            # PDF download
            # --------------------------------------------

            with col2:
                try:
                    pdf_data = generate_travel_plan_pdf(
                        final_plan,
                        safe_get(
                            state,
                            "generated_images",
                            [],
                        ) or [],
                    )

                    st.download_button(
                        "📄 Download (PDF)",
                        pdf_data,
                        file_name=(
                            f"travel_plan_{final_plan.destination}_"
                            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                        ),
                        mime="application/pdf",
                        use_container_width=True,
                    )

                except Exception as error:
                    st.error(
                        f"PDF generation error: {error}"
                    )

    # --------------------------------------------------------
    # Footer
    # --------------------------------------------------------

    st.divider()

    st.markdown(
        "<div style='text-align:center'>"
        "<p style='color:gray;'>"
        "Made with ❤️ using LangGraph, Gemini, and Streamlit"
        "</p></div>",
        unsafe_allow_html=True,
    )


# ============================================================
# APPLICATION ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()