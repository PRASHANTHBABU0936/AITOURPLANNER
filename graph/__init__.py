# # """
# # LangGraph workflow for coordinating travel planning agents
# # """
# # from langgraph.graph import StateGraph
# # from models.schemas import TravelPlanState, FinalTravelPlan
# # from agents import (
# #     intent_agent_node,
# #     research_agent_node,
# #     itinerary_agent_node,
# #     budget_agent_node,
# #     image_agent_node,
# # )
# # from datetime import datetime


# # def create_travel_planner_graph():
# #     """
# #     Create and configure the LangGraph workflow
    
# #     Returns:
# #         Compiled workflow graph
# #     """
    
# #     # Create the StateGraph
# #     graph = StateGraph(TravelPlanState)
    
# #     # Add nodes
# #     graph.add_node("intent_agent", intent_agent_node)
# #     graph.add_node("research_agent", research_agent_node)
# #     graph.add_node("itinerary_agent", itinerary_agent_node)
# #     graph.add_node("budget_agent", budget_agent_node)
# #     graph.add_node("compile_plan", compile_final_plan)
# #     graph.add_node("image_agent", image_agent_node)
    
# #     # Define edges (workflow)
# #     graph.set_entry_point("intent_agent")
# #     graph.add_edge("intent_agent", "research_agent")
# #     graph.add_edge("research_agent", "itinerary_agent")
# #     graph.add_edge("itinerary_agent", "budget_agent")
# #     graph.add_edge("budget_agent", "compile_plan")
# #     graph.add_edge("compile_plan", "image_agent")
# #     graph.set_finish_point("image_agent")
    
# #     # Compile the graph
# #     return graph.compile()


# # def compile_final_plan(state: TravelPlanState) -> TravelPlanState:
# #     """
# #     Compile all agent outputs into final travel plan
    
# #     Args:
# #         state: Current workflow state
        
# #     Returns:
# #         Updated state with final plan
# #     """
    
# #     try:
# #         if (
# #             state.trip_details
# #             and state.research_data
# #             and state.itinerary
# #             and state.budget_breakdown
# #         ):
# #             final_plan = FinalTravelPlan(
# #                 destination=state.trip_details.destination,
# #                 duration=state.trip_details.duration,
# #                 trip_details=state.trip_details,
# #                 destination_info=state.research_data,
# #                 itinerary=state.itinerary,
# #                 budget=state.budget_breakdown,
# #                 generated_at=datetime.now().isoformat(),
# #             )
# #             state.final_plan = final_plan
# #         else:
# #             state.errors.append("Missing required data to compile final plan")

# #     except Exception as e:
# #         state.errors.append(f"Error compiling final plan: {str(e)}")

# #     if state.final_plan:
# #         state.conversation_history.append({
# #             "role": "compile_plan",
# #             "content": (
# #                 f"Plan compiled for {state.final_plan.destination} — "
# #                 f"{state.final_plan.duration} days, "
# #                 f"{state.final_plan.budget.currency} {state.final_plan.budget.total_estimated:,.0f} total. "
# #                 f"Ready for image generation."
# #             ),
# #         })

# #     return state


# # # Create the workflow instance
# # travel_planner_graph = create_travel_planner_graph()



# """
# LangGraph workflow for coordinating travel planning agents
# """
# from langgraph.graph import StateGraph
# from models.schemas import TravelPlanState, FinalTravelPlan
# from agents import (
#     intent_agent_node,
#     research_agent_node,
#     itinerary_agent_node,
#     budget_agent_node,
#     image_agent_node,
# )
# from datetime import datetime


# def create_travel_planner_graph():
#     """
#     Create and configure the LangGraph workflow

#     Returns:
#         Compiled workflow graph
#     """

#     # Create the StateGraph
#     graph = StateGraph(TravelPlanState)

#     # Add nodes
#     graph.add_node("intent_agent", intent_agent_node)
#     graph.add_node("research_agent", research_agent_node)
#     graph.add_node("itinerary_agent", itinerary_agent_node)
#     graph.add_node("budget_agent", budget_agent_node)
#     graph.add_node("compile_plan", compile_final_plan)
#     graph.add_node("image_agent", image_agent_node)

#     # Define edges (workflow)
#     graph.set_entry_point("intent_agent")
#     graph.add_edge("intent_agent", "research_agent")
#     graph.add_edge("research_agent", "itinerary_agent")
#     graph.add_edge("itinerary_agent", "budget_agent")
#     graph.add_edge("budget_agent", "compile_plan")
#     graph.add_edge("compile_plan", "image_agent")
#     graph.set_finish_point("image_agent")

#     # Compile the graph
#     return graph.compile()


# def compile_final_plan(state: TravelPlanState) -> TravelPlanState:
#     """
#     Compile all agent outputs into final travel plan

#     Args:
#         state: Current workflow state

#     Returns:
#         Updated state with final plan
#     """

#     try:
#         # DEBUG: Check whether all required agent outputs exist
#         print(
#             "DEBUG COMPILE:",
#             "trip_details=", bool(state.trip_details),
#             "research_data=", bool(state.research_data),
#             "itinerary=", bool(state.itinerary),
#             "budget_breakdown=", bool(state.budget_breakdown),
#         )

#         if (
#             state.trip_details
#             and state.research_data
#             and state.itinerary
#             and state.budget_breakdown
#         ):
#             final_plan = FinalTravelPlan(
#                 destination=state.trip_details.destination,
#                 duration=state.trip_details.duration,
#                 trip_details=state.trip_details,
#                 destination_info=state.research_data,
#                 itinerary=state.itinerary,
#                 budget=state.budget_breakdown,
#                 generated_at=datetime.now().isoformat(),
#             )

#             state.final_plan = final_plan

#         else:
#             state.errors.append("Missing required data to compile final plan")

#     except Exception as e:
#         state.errors.append(f"Error compiling plan: {str(e)}")

#     if state.final_plan:
#         state.conversation_history.append({
#             "role": "compile_plan",
#             "content": (
#                 f"Plan compiled for {state.final_plan.destination} — "
#                 f"{state.final_plan.duration} days, "
#                 f"{state.final_plan.budget.currency} "
#                 f"{state.final_plan.budget.total_estimated:,.0f} total. "
#                 f"Ready for image generation."
#             ),
#         })

#     return state


# # Create the workflow instance
# travel_planner_graph = create_travel_planner_graph()










"""
LangGraph workflow for coordinating travel planning agents.

Workflow:

Valid request:
Intent → Research → Itinerary → Budget → Compile → Images → END

Invalid request:
Intent → END

The conditional routing after the Intent Agent prevents invalid
user input from reaching the downstream agents.
"""

from datetime import datetime

from langgraph.graph import StateGraph, END

from models.schemas import TravelPlanState, FinalTravelPlan

from agents import (
    intent_agent_node,
    research_agent_node,
    itinerary_agent_node,
    budget_agent_node,
    image_agent_node,
)


# ============================================================
# ROUTING AFTER INTENT AGENT
# ============================================================

def route_after_intent(state: TravelPlanState):
    """
    Decide whether the workflow should continue after the
    Intent Agent.

    If the user's input is invalid or required trip details
    are missing, stop the workflow immediately.

    Otherwise continue to the Research Agent.
    """

    # Invalid request
    if state.errors or not state.trip_details:
        return END

    # Valid request
    return "research_agent"


# ============================================================
# CREATE TRAVEL PLANNER GRAPH
# ============================================================

def create_travel_planner_graph():
    """
    Create and compile the LangGraph travel planner workflow.

    Returns:
        Compiled LangGraph workflow.
    """

    # --------------------------------------------------------
    # Create StateGraph
    # --------------------------------------------------------

    graph = StateGraph(TravelPlanState)

    # --------------------------------------------------------
    # Add agents/nodes
    # --------------------------------------------------------

    graph.add_node(
        "intent_agent",
        intent_agent_node,
    )

    graph.add_node(
        "research_agent",
        research_agent_node,
    )

    graph.add_node(
        "itinerary_agent",
        itinerary_agent_node,
    )

    graph.add_node(
        "budget_agent",
        budget_agent_node,
    )

    graph.add_node(
        "compile_plan",
        compile_final_plan,
    )

    graph.add_node(
        "image_agent",
        image_agent_node,
    )

    # --------------------------------------------------------
    # Entry point
    # --------------------------------------------------------

    graph.set_entry_point(
        "intent_agent"
    )

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # Intent Agent is now conditional.
    #
    # Valid:
    # Intent → Research
    #
    # Invalid:
    # Intent → END
    #
    # DO NOT replace this with:
    #
    # graph.add_edge("intent_agent", "research_agent")
    #
    # --------------------------------------------------------

    graph.add_conditional_edges(
        "intent_agent",
        route_after_intent,
        {
            "research_agent": "research_agent",
            END: END,
        },
    )

    # --------------------------------------------------------
    # Normal successful workflow
    # --------------------------------------------------------

    graph.add_edge(
        "research_agent",
        "itinerary_agent",
    )

    graph.add_edge(
        "itinerary_agent",
        "budget_agent",
    )

    graph.add_edge(
        "budget_agent",
        "compile_plan",
    )

    graph.add_edge(
        "compile_plan",
        "image_agent",
    )

    graph.add_edge(
        "image_agent",
        END,
    )

    # --------------------------------------------------------
    # Compile graph
    # --------------------------------------------------------

    return graph.compile()


# ============================================================
# COMPILE FINAL PLAN
# ============================================================

def compile_final_plan(
    state: TravelPlanState,
) -> TravelPlanState:
    """
    Compile all successful agent outputs into the final
    travel plan.
    """

    try:

        # ----------------------------------------------------
        # Debug information
        # ----------------------------------------------------

        print(
            "DEBUG COMPILE:",
            "trip_details=",
            bool(state.trip_details),
            "research_data=",
            bool(state.research_data),
            "itinerary=",
            bool(state.itinerary),
            "budget_breakdown=",
            bool(state.budget_breakdown),
        )

        # ----------------------------------------------------
        # Verify all required data exists
        # ----------------------------------------------------

        if (
            state.trip_details
            and state.research_data
            and state.itinerary
            and state.budget_breakdown
        ):

            # ------------------------------------------------
            # Build final plan
            # ------------------------------------------------

            final_plan = FinalTravelPlan(
                destination=(
                    state.trip_details.destination
                ),
                duration=(
                    state.trip_details.duration
                ),
                trip_details=(
                    state.trip_details
                ),
                destination_info=(
                    state.research_data
                ),
                itinerary=(
                    state.itinerary
                ),
                budget=(
                    state.budget_breakdown
                ),
                generated_at=(
                    datetime.now().isoformat()
                ),
            )

            state.final_plan = final_plan

        else:

            state.errors.append(
                "Missing required data to compile final plan"
            )

    except Exception as e:

        state.errors.append(
            f"Error compiling plan: {str(e)}"
        )

    # --------------------------------------------------------
    # Conversation history
    # --------------------------------------------------------

    if state.final_plan:

        state.conversation_history.append(
            {
                "role": "compile_plan",
                "content": (
                    f"Plan compiled for "
                    f"{state.final_plan.destination} — "
                    f"{state.final_plan.duration} days, "
                    f"{state.final_plan.budget.currency} "
                    f"{state.final_plan.budget.total_estimated:,.0f} "
                    f"total. "
                    f"Ready for image generation."
                ),
            }
        )

    return state


# ============================================================
# CREATE WORKFLOW INSTANCE
# ============================================================

travel_planner_graph = create_travel_planner_graph()