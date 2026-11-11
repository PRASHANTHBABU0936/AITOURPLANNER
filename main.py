"""
Main entry point for Travel Planning Assistant
"""
from models.schemas import TravelPlanState
from graph import travel_planner_graph
import json


def main():
    """Interactive CLI for testing the travel planner"""
    
    print("=" * 60)
    print("✈️  AI-Powered Travel Planning Assistant")
    print("=" * 60)
    print()
    
    # Get user input
    user_input = input("📝 Describe your travel plans: ").strip()
    
    if not user_input:
        print("❌ No input provided. Exiting.")
        return
    
    # Create initial state
    initial_state = TravelPlanState(user_input=user_input)
    
    print("\n🤔 Processing your request...\n")
    
    try:
        # Run the workflow
        result = travel_planner_graph.invoke(initial_state.model_dump())
        
        # Convert dict result back to TravelPlanState
        if isinstance(result, dict):
            result = TravelPlanState(**result)
        
        # Display results
        if result.errors:
            print("\n⚠️  Errors encountered:")
            for error in result.errors:
                print(f"  - {error}")
        
        if result.trip_details:
            cur = result.trip_details.currency
            print("\n✅ Trip Details Extracted:")
            print(f"  Destination: {result.trip_details.destination}")
            print(f"  Budget: {cur} {result.trip_details.budget:,.2f}")
            print(f"  Duration: {result.trip_details.duration} days")
            print(f"  Travel Style: {result.trip_details.travel_style}")
            print(f"  Interests: {', '.join(result.trip_details.interests)}")

        if result.final_plan:
            cur = result.final_plan.budget.currency
            print("\n✅ Travel Plan Generated Successfully!")
            print(f"\nFinal Plan Summary:")
            print(f"  Destination: {result.final_plan.destination}")
            print(f"  Total Duration: {result.final_plan.duration} days")
            print(f"  Total Budget: {cur} {result.final_plan.budget.total_estimated:,.2f}")
            print(f"  Daily Average: {cur} {result.final_plan.budget.per_day_average:,.2f}")
            print(f"  Budget Status: {result.final_plan.budget.budget_status}")
            
            # Save to file
            output_filename = f"travel_plan_{result.final_plan.destination}.json"
            with open(output_filename, "w") as f:
                json.dump(result.final_plan.model_dump(), f, indent=2, default=str)
            print(f"\n💾 Plan saved to: {output_filename}")
        else:
            print("\n❌ Could not generate travel plan.")
    
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
