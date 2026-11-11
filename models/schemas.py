"""
Data models and schemas for the Travel Planning Assistant
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class TripDetails(BaseModel):
    """Extracted trip details from user input"""
    destination: str = Field(..., description="Travel destination")
    budget: float = Field(default=0.0, description="Total budget in user's currency, 0 if not specified")
    currency: str = Field("USD", description="User's budget currency code e.g. INR, USD, EUR")
    duration: int = Field(..., description="Trip duration in days")
    start_date: Optional[str] = Field(None, description="Travel start date")
    travel_style: str = Field("moderate", description="Travel style: budget, moderate, luxury")
    preferences: List[str] = Field(default_factory=list, description="Travel preferences")
    accommodation_type: Optional[str] = Field(None, description="Preferred accommodation type")
    interests: List[str] = Field(default_factory=list, description="Activities and interests")


class ResearchData(BaseModel):
    """Researched destination information"""
    destination: str = Field(..., description="Destination name")
    overview: str = Field(..., description="Destination overview")
    best_time_to_visit: str = Field(..., description="Best season/months to visit")
    weather: str = Field(..., description="Weather information")
    attractions: List[str] = Field(default_factory=list, description="Top attractions")
    cuisine: str = Field(..., description="Local cuisine highlights")
    transportation: str = Field(..., description="Local transportation options")
    entry_requirements: str = Field(..., description="Visa/entry requirements")
    travel_tips: List[str] = Field(default_factory=list, description="General travel tips")


class DayPlan(BaseModel):
    """Single day's itinerary"""
    day: int = Field(..., description="Day number")
    title: str = Field(..., description="Day title/theme")
    activities: List[str] = Field(..., description="Activities for the day")
    meals: Dict[str, str] = Field(default_factory=dict, description="Meal recommendations")
    accommodation: str = Field(..., description="Accommodation for the night")
    estimates: Dict[str, float] = Field(default_factory=dict, description="Estimated costs")


class ItineraryPlan(BaseModel):
    """Complete itinerary for the trip"""
    destination: str = Field(..., description="Destination name")
    duration: int = Field(..., description="Total duration in days")
    days: List[DayPlan] = Field(..., description="Day-wise plans")
    special_notes: List[str] = Field(default_factory=list, description="Special notes and tips")


class BudgetBreakdown(BaseModel):
    """Detailed budget breakdown"""
    destination: str = Field(..., description="Destination name")
    duration: int = Field(..., description="Trip duration")
    currency: str = Field("USD", description="Currency code for all amounts")
    categories: Dict[str, float] = Field(..., description="Budget by category in user's currency")
    total_estimated: float = Field(..., description="Total estimated cost in user's currency")
    per_day_average: float = Field(..., description="Average daily cost in user's currency")
    budget_status: str = Field(..., description="Within budget or not")
    recommendations: List[str] = Field(default_factory=list, description="Cost-saving tips")


class FinalTravelPlan(BaseModel):
    """Complete final travel plan"""
    destination: str
    duration: int
    trip_details: TripDetails
    destination_info: ResearchData
    itinerary: ItineraryPlan
    budget: BudgetBreakdown
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class TravelPlanState(BaseModel):
    """Shared state for the LangGraph workflow"""
    user_input: str = Field(default="", description="User's initial query")
    trip_details: Optional[TripDetails] = Field(default=None, description="Extracted trip details")
    research_data: Optional[ResearchData] = Field(default=None, description="Destination research data")
    itinerary: Optional[ItineraryPlan] = Field(default=None, description="Generated itinerary")
    budget_breakdown: Optional[BudgetBreakdown] = Field(default=None, description="Budget calculations")
    final_plan: Optional[FinalTravelPlan] = Field(default=None, description="Final compiled plan")
    generated_images: List[Dict[str, Any]] = Field(default_factory=list, description="Generated images metadata")
    conversation_history: List[Dict[str, str]] = Field(default_factory=list, description="Chat history")
    errors: List[str] = Field(default_factory=list, description="Error messages")
