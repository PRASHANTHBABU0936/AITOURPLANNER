"""
PDF Generator for Travel Plans — with embedded Gemini-generated images
"""
from fpdf import FPDF
from pathlib import Path
from models.schemas import FinalTravelPlan
from typing import List, Dict, Any
import re


def clean(text: str) -> str:
    return re.sub(r'[^\x00-\xFF]', '', str(text)).strip()


def mc(pdf, h, text, align="L"):
    """Helper: multi_cell that always resets to left margin."""
    pdf.multi_cell(0, h, clean(text), align=align, new_x="LMARGIN", new_y="NEXT")


def _embed_image(pdf: FPDF, img_path: str, caption: str, max_w: int = 170) -> None:
    """
    Embed an image into the PDF centered, with caption below.
    Skips gracefully if file doesn't exist or is unreadable.
    """
    path = Path(img_path)
    if not path.exists():
        return
    try:
        # Calculate height to maintain aspect ratio within max_w
        pdf.ln(3)
        x = pdf.get_x()
        page_w = pdf.w - pdf.l_margin - pdf.r_margin
        img_w = min(max_w, page_w)
        img_x = pdf.l_margin + (page_w - img_w) / 2

        pdf.image(str(path), x=img_x, w=img_w)
        pdf.ln(2)

        # Caption in italics
        pdf.set_font("Helvetica", "I", 9)
        mc(pdf, 5, caption, align="C")
        pdf.set_font("Helvetica", "", 10)
        pdf.ln(4)
    except Exception:
        # Never crash the PDF over a missing image
        pass


def generate_travel_plan_pdf(
    plan: FinalTravelPlan,
    generated_images: List[Dict[str, Any]] = None,
) -> bytes:

    generated_images = generated_images or []
    # Map images by index for easy access
    hero_img = generated_images[0] if len(generated_images) > 0 else None
    landmark_img = generated_images[1] if len(generated_images) > 1 else None
    culture_img = generated_images[2] if len(generated_images) > 2 else None
    extra_img = generated_images[3] if len(generated_images) > 3 else None

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(left=15, top=15, right=15)
    pdf.set_auto_page_break(auto=True, margin=15)

    cur = getattr(plan.budget, "currency", None) or getattr(plan.trip_details, "currency", "USD")

    # ── Page 1: Cover / Overview ──────────────────────────────────────────────
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 22)
    mc(pdf, 12, f"Travel Plan to {plan.destination}", align="C")
    pdf.ln(3)

    # Hero image right at the top
    if hero_img:
        _embed_image(pdf, hero_img["path"], hero_img["caption"])

    pdf.set_font("Helvetica", "B", 14)
    mc(pdf, 10, "Trip Overview")

    pdf.set_font("Helvetica", "", 11)
    mc(pdf, 6, (
        f"Duration: {plan.duration} days\n"
        f"Estimated Cost: {cur} {plan.budget.total_estimated:,.2f}\n"
        f"Daily Average: {cur} {plan.budget.per_day_average:.2f}\n"
        f"Travel Style: {plan.trip_details.travel_style.capitalize()}\n"
        f"Budget Status: {plan.budget.budget_status}"
    ))
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 14)
    mc(pdf, 10, "Destination Highlights")

    pdf.set_font("Helvetica", "", 11)
    mc(pdf, 6, plan.destination_info.overview)

    # Landmark image after overview
    if landmark_img:
        _embed_image(pdf, landmark_img["path"], landmark_img["caption"])

    pdf.set_font("Helvetica", "B", 11)
    mc(pdf, 6, "Best Time to Visit")
    pdf.set_font("Helvetica", "", 10)
    mc(pdf, 5, plan.destination_info.best_time_to_visit)

    pdf.set_font("Helvetica", "B", 11)
    mc(pdf, 6, "Weather")
    pdf.set_font("Helvetica", "", 10)
    mc(pdf, 5, plan.destination_info.weather)

    pdf.set_font("Helvetica", "B", 11)
    mc(pdf, 6, "Top Attractions")
    pdf.set_font("Helvetica", "", 10)
    for attraction in plan.destination_info.attractions:
        mc(pdf, 5, f"- {attraction}")

    # ── Page 2: Itinerary ─────────────────────────────────────────────────────
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    mc(pdf, 10, "Day-by-Day Itinerary")

    # Culture image at top of itinerary page
    if culture_img:
        _embed_image(pdf, culture_img["path"], culture_img["caption"])

    for day in plan.itinerary.days:
        pdf.ln(3)
        pdf.set_font("Helvetica", "B", 13)
        mc(pdf, 7, f"Day {day.day}: {day.title}")

        pdf.set_font("Helvetica", "B", 11)
        mc(pdf, 6, "Activities")
        pdf.set_font("Helvetica", "", 10)
        for activity in day.activities:
            mc(pdf, 5, f"- {activity}")

        pdf.set_font("Helvetica", "B", 11)
        mc(pdf, 6, "Meals")
        pdf.set_font("Helvetica", "", 10)
        for meal_type, restaurant in day.meals.items():
            mc(pdf, 5, f"- {meal_type.capitalize()}: {restaurant}")

        pdf.set_font("Helvetica", "B", 11)
        mc(pdf, 6, "Accommodation")
        pdf.set_font("Helvetica", "", 10)
        mc(pdf, 5, day.accommodation)

        pdf.set_font("Helvetica", "B", 11)
        mc(pdf, 6, "Estimated Costs")
        pdf.set_font("Helvetica", "", 10)
        for cost_type, amount in day.estimates.items():
            mc(pdf, 5, f"- {cost_type.capitalize()}: {cur} {amount:,.0f}")

    # ── Page 3: Budget & Tips ─────────────────────────────────────────────────
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    mc(pdf, 10, "Budget Breakdown")

    pdf.set_font("Helvetica", "", 11)
    for category, amount in plan.budget.categories.items():
        mc(pdf, 6, f"{category.capitalize()}: {cur} {amount:,.2f}")

    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 12)
    mc(pdf, 6, f"Total Estimated Cost: {cur} {plan.budget.total_estimated:,.2f}")

    pdf.set_font("Helvetica", "", 11)
    mc(pdf, 6, f"Budget Status: {plan.budget.budget_status}")

    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 12)
    mc(pdf, 8, "Money-Saving Tips")
    pdf.set_font("Helvetica", "", 10)
    for tip in plan.budget.recommendations:
        mc(pdf, 5, f"- {tip}")

    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 14)
    mc(pdf, 8, "Travel Tips")
    pdf.set_font("Helvetica", "", 10)
    for tip in plan.destination_info.travel_tips:
        mc(pdf, 5, f"- {tip}")

    if plan.itinerary.special_notes:
        pdf.ln(3)
        pdf.set_font("Helvetica", "B", 14)
        mc(pdf, 8, "Special Notes")
        pdf.set_font("Helvetica", "", 10)
        for note in plan.itinerary.special_notes:
            mc(pdf, 5, f"- {note}")

    if extra_img:
        pdf.ln(5)
        _embed_image(pdf, extra_img["path"], extra_img["caption"])

    return bytes(pdf.output())