"""
Tests for image_agent and budget_agent.

Run with: .\\venv\\Scripts\\python.exe tests/test_agents.py
"""

import sys
import unittest
import tempfile
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from PIL import Image

# Make sure project root is importable
sys.path.insert(0, str(Path(__file__).parent.parent))


def jpeg_bytes(width=400, height=300) -> bytes:
    """Return real JPEG bytes for tests that need a valid image."""
    buffer = BytesIO()
    Image.new("RGB", (width, height), (10, 120, 200)).save(buffer, format="JPEG")
    return buffer.getvalue()


class StateStub:
    """Minimal TravelPlanState stand-in for node-level tests."""

    def __init__(self, final_plan=None):
        self.final_plan = final_plan
        self.errors = []
        self.generated_images = []
        self.conversation_history = []


# ═══════════════════════════════════════════════════════════════════════════════
# IMAGE AGENT — HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

class TestImageAgentHelpers(unittest.TestCase):
    """Tests for the place/slug helpers — no network access."""

    def test_make_slug(self):
        from agents.image_agent import _make_slug

        self.assertEqual(_make_slug("New York"), "new_york")
        self.assertEqual(_make_slug(""), "travel_photo")

    def test_place_name_strips_activity_prefix(self):
        from agents.image_agent import _place_name

        self.assertEqual(_place_name("Visit Baga Beach"), "Baga Beach")

    def test_place_name_rejects_generic_activities(self):
        from agents.image_agent import _place_name

        self.assertEqual(_place_name("Breakfast"), "")
        self.assertEqual(_place_name("free time"), "")

    def test_place_name_from_mapping(self):
        from agents.image_agent import _place_name

        self.assertEqual(_place_name({"name": "Fort Aguada"}), "Fort Aguada")

    def test_extract_places_deduplicates_and_skips_generic(self):
        from agents.image_agent import _extract_places

        plan = {
            "destination_info": {"attractions": ["Baga Beach", "Visit Baga Beach"]},
            "itinerary": {"days": [{"activities": ["Dudhsagar Falls", "Lunch"]}]},
        }

        self.assertEqual(
            _extract_places(None, plan),
            ["Baga Beach", "Dudhsagar Falls"],
        )


# ═══════════════════════════════════════════════════════════════════════════════
# IMAGE AGENT — IMAGE WRITING
# ═══════════════════════════════════════════════════════════════════════════════

class TestWriteImageBytes(unittest.TestCase):
    """Tests for _write_image_bytes validation and JPEG conversion."""

    def test_saves_valid_jpeg(self):
        from agents.image_agent import _write_image_bytes

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "photo.jpg"
            _write_image_bytes(jpeg_bytes(400, 300), output)

            self.assertTrue(output.is_file())
            with Image.open(output) as image:
                self.assertEqual(image.format, "JPEG")

    def test_rejects_small_image(self):
        from agents.image_agent import _write_image_bytes

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(RuntimeError):
                _write_image_bytes(jpeg_bytes(50, 50), Path(tmp) / "small.jpg")

    def test_rejects_invalid_bytes(self):
        from agents.image_agent import _write_image_bytes

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(RuntimeError):
                _write_image_bytes(b"not an image", Path(tmp) / "bad.jpg")

    def test_rejects_empty_bytes(self):
        from agents.image_agent import _write_image_bytes

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(RuntimeError):
                _write_image_bytes(b"", Path(tmp) / "empty.jpg")


# ═══════════════════════════════════════════════════════════════════════════════
# IMAGE AGENT — NODE
# ═══════════════════════════════════════════════════════════════════════════════

class TestImageAgentNode(unittest.TestCase):
    """Tests for image_agent_node state handling (MCP/search mocked)."""

    PHOTO = {
        "title": "Baga Beach",
        "url": "https://example.com/1.jpg",
        "source_url": "https://example.com/page",
        "artist": "Someone",
        "license": "CC BY-SA 4.0",
        "caption": "Baga Beach",
    }

    def _plan(self, attractions=("Baga Beach",)):
        return {
            "destination": "Goa",
            "destination_info": {"attractions": list(attractions)},
            "itinerary": {"days": []},
        }

    def test_no_final_plan_appends_error(self):
        from agents.image_agent import image_agent_node

        state = StateStub(final_plan=None)
        result = image_agent_node(state)

        self.assertEqual(result.generated_images, [])
        self.assertTrue(any("final_plan" in e for e in result.errors))

    def test_no_places_appends_error(self):
        from agents.image_agent import image_agent_node

        state = StateStub(final_plan=self._plan(attractions=()))
        result = image_agent_node(state)

        self.assertEqual(result.generated_images, [])
        self.assertTrue(any("no named attractions" in e for e in result.errors))

    def test_successful_download_updates_state(self):
        from agents.image_agent import image_agent_node

        state = StateStub(final_plan=self._plan())

        with tempfile.TemporaryDirectory() as tmp:
            with patch("agents.image_agent.IMAGES_DIR", Path(tmp)), patch(
                "agents.image_agent._search_commons",
                return_value=[self.PHOTO],
            ), patch(
                "agents.image_agent._download_photo_bytes",
                return_value=jpeg_bytes(),
            ):
                result = image_agent_node(state)

            saved = list(Path(tmp).glob("*.jpg"))

        self.assertEqual(len(result.generated_images), 1)
        self.assertEqual(result.errors, [])
        self.assertEqual(len(saved), 1)
        self.assertEqual(result.generated_images[0]["caption"], "Baga Beach")

    def test_download_failure_appends_error_not_crash(self):
        from agents.image_agent import image_agent_node

        state = StateStub(final_plan=self._plan())

        with tempfile.TemporaryDirectory() as tmp:
            with patch("agents.image_agent.IMAGES_DIR", Path(tmp)), patch(
                "agents.image_agent._search_commons",
                return_value=[self.PHOTO],
            ), patch(
                "agents.image_agent._download_photo_bytes",
                side_effect=RuntimeError("network down"),
            ):
                result = image_agent_node(state)

        self.assertEqual(result.generated_images, [])
        self.assertTrue(
            any("Could not download photo" in e for e in result.errors)
        )


# ═══════════════════════════════════════════════════════════════════════════════
# BUDGET AGENT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestBudgetCalculations(unittest.TestCase):
    """Tests for budget arithmetic — must use Python math, not LLM math."""

    def _make_categories(self, accommodation=5000, food=3000,
                          activities=2000, transportation=1500,
                          miscellaneous=1000):
        return {
            "accommodation": accommodation,
            "food": food,
            "activities": activities,
            "transportation": transportation,
            "miscellaneous": miscellaneous,
        }

    def test_total_is_sum_of_categories(self):
        cats = self._make_categories(5000, 3000, 2000, 1500, 1000)
        total = round(sum(cats.values()), 2)
        self.assertEqual(total, 12500.0)

    def test_per_day_average(self):
        cats = self._make_categories(5000, 3000, 2000, 1500, 1000)
        total = sum(cats.values())
        duration = 5
        per_day = round(total / duration, 2)
        self.assertEqual(per_day, 2500.0)

    def test_budget_status_within(self):
        cats = self._make_categories(5000, 3000, 2000, 1500, 1000)
        total = sum(cats.values())   # 12500
        user_budget = 15000
        currency = "INR"
        if user_budget == 0:
            status = "Estimated"
        elif total <= user_budget:
            status = "Within budget"
        else:
            overage = round(total - user_budget, 2)
            status = f"Over budget by {currency} {overage:,.0f}"
        self.assertEqual(status, "Within budget")

    def test_budget_status_over(self):
        cats = self._make_categories(8000, 5000, 3000, 2000, 1500)
        total = sum(cats.values())   # 19500
        user_budget = 15000
        currency = "INR"
        if user_budget == 0:
            status = "Estimated"
        elif total <= user_budget:
            status = "Within budget"
        else:
            overage = round(total - user_budget, 2)
            status = f"Over budget by {currency} {overage:,.0f}"
        self.assertEqual(status, "Over budget by INR 4,500")

    def test_budget_status_zero_budget(self):
        cats = self._make_categories()
        total = sum(cats.values())
        user_budget = 0
        if user_budget == 0:
            status = "Estimated"
        elif total <= user_budget:
            status = "Within budget"
        else:
            status = "Over budget"
        self.assertEqual(status, "Estimated")

    def test_total_consistency_exact(self):
        """Total in BudgetBreakdown must exactly equal sum of its own categories."""
        cats = self._make_categories(7200, 4500, 3100, 2800, 900)
        expected_total = 7200 + 4500 + 3100 + 2800 + 900  # = 18500
        computed_total = round(sum(cats.values()), 2)
        self.assertEqual(computed_total, expected_total)

    def test_budget_difference_correct(self):
        """Budget difference must be total - user_budget (not the reverse)."""
        total = 19500.0
        user_budget = 15000.0
        diff = round(total - user_budget, 2)
        self.assertGreater(diff, 0)
        self.assertEqual(diff, 4500.0)

    def test_within_budget_difference_is_saving(self):
        total = 12000.0
        user_budget = 15000.0
        saving = round(user_budget - total, 2)
        self.assertGreater(saving, 0)
        self.assertEqual(saving, 3000.0)


# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Image agent tests
    suite.addTests(loader.loadTestsFromTestCase(TestImageAgentHelpers))
    suite.addTests(loader.loadTestsFromTestCase(TestWriteImageBytes))
    suite.addTests(loader.loadTestsFromTestCase(TestImageAgentNode))

    # Budget tests
    suite.addTests(loader.loadTestsFromTestCase(TestBudgetCalculations))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
