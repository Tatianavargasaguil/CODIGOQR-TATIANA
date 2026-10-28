import json
import unittest
from unittest.mock import Mock, patch

import requests

from app import cotizador


def web_response(price=100_000_000):
    year = cotizador.datetime.utcnow().year
    refs = {
        "new": [{"brand": "TEST", "model": "MODEL", "year": year, "price": price,
                 "url": "https://example.com/new", "platform": "Marca"}],
        "used": [{"brand": "TEST", "model": "MODEL", "year": year - 2, "price": price,
                  "url": "https://example.com/used", "platform": "Plataforma"}],
    }
    content = [
        {"type": "server_tool_use", "name": "web_search", "id": "search1"},
        {"type": "web_search_tool_result", "content": [
            {"type": "web_search_result", "url": item["url"], "title": "Vehiculo"}
            for items in refs.values() for item in items
        ]},
        {"type": "text", "text": json.dumps(refs)},
    ]
    response = Mock(status_code=200)
    response.json.return_value = {"content": content, "stop_reason": "end_turn"}
    return response


class OfferRangeTests(unittest.TestCase):
    def test_offer_ranges_at_threshold(self):
        cases = [
            (40_000_000, (38_500_000, 41_500_000)),
            (59_999_999, (58_499_999, 61_499_999)),
            (60_000_000, (57_500_000, 62_500_000)),
            (80_000_000, (77_500_000, 82_500_000)),
        ]
        for offer, expected in cases:
            with self.subTest(offer=offer):
                self.assertEqual(cotizador.get_offer_range(offer), expected)

    def test_local_calculation_uses_variable_range(self):
        for price, width in [(50_000_000, 3_000_000), (100_000_000, 5_000_000)]:
            with self.subTest(price=price):
                result = cotizador.calculate_quote_from_references(2020, 10_000, {}, [{"price": price}], [{"price": price}])
                self.assertEqual(result["offer_max"] - result["offer_min"], width)

    def test_director_threshold_keeps_calculated_values(self):
        for price, review in [(159_999_999, False), (160_000_000, True), (200_000_000, True)]:
            with self.subTest(price=price):
                result = cotizador.calculate_quote_from_references(2020, 10_000, {}, [{"price": price}], [])
                self.assertEqual(result["director_review"], review)
                self.assertGreater(result["estimated_sale"], 0)
                self.assertGreater(result["offer_min"], 0)

    def test_claude_search_preserves_electric_rules_and_sources(self):
        year = cotizador.datetime.utcnow().year - 2
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch.object(cotizador.requests, "post", return_value=web_response()) as post:
                result = cotizador.calculate_claude_quote("TEST", "MODEL", year, 10_000, "", {"fuel": "Electrico", "plate": "PRIVATE"})
        self.assertTrue(result["web_search_performed"])
        self.assertEqual(result["ai_provider"], "anthropic")
        self.assertEqual((result["offer_min"], result["offer_max"]), (50_500_000, 53_500_000))
        self.assertEqual(result["market_references"]["used"][0]["url"], "https://example.com/used")
        kwargs = post.call_args.kwargs
        self.assertEqual(post.call_args.args[0], "https://api.anthropic.com/v1/messages")
        self.assertEqual(kwargs["json"]["tools"][0]["name"], "web_search")
        self.assertNotIn("PRIVATE", kwargs["json"]["messages"][0]["content"])

    def test_claude_search_preserves_director_rule(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch.object(cotizador.requests, "post", return_value=web_response(200_000_000)):
                result = cotizador.calculate_claude_quote("TEST", "MODEL", cotizador.datetime.utcnow().year - 2, 10_000, "", {})
        self.assertTrue(result["director_review"])
        self.assertEqual((result["offer_min"], result["offer_max"]), (151_500_000, 156_500_000))

    def test_web_prices_cannot_override_commercial_rules(self):
        response = web_response()
        content = response.json.return_value["content"]
        data = json.loads(content[-1]["text"])
        data.update({"offer": 999_000_000, "director_review": False})
        content[-1]["text"] = json.dumps(data)
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch.object(cotizador.requests, "post", return_value=response):
                result = cotizador.calculate_claude_quote("TEST", "MODEL", cotizador.datetime.utcnow().year - 2, 10_000, "", {})
        self.assertEqual((result["offer_min"], result["offer_max"]), (74_500_000, 79_500_000))

    def test_search_rejects_urls_not_in_search_results(self):
        content = web_response().json()["content"]
        content[1]["content"] = []
        with self.assertRaises(cotizador.CotizadorError):
            cotizador.parse_claude_references(content, "TEST", "MODEL", cotizador.datetime.utcnow().year - 2)

    def test_search_rejects_wrong_brand_and_model_year(self):
        content = web_response().json()["content"]
        data = json.loads(content[-1]["text"])
        data["new"][0]["brand"] = "OTHER"
        data["used"][0]["year"] = 1990
        content[-1]["text"] = json.dumps(data)
        with self.assertRaises(cotizador.CotizadorError):
            cotizador.parse_claude_references(content, "TEST", "MODEL", cotizador.datetime.utcnow().year - 2)

    def test_json_split_across_text_blocks_is_parsed(self):
        content = web_response().json()["content"]
        text = content.pop()["text"]
        split_at = len(text) // 2
        content.extend([{"type": "text", "text": text[:split_at]}, {"type": "text", "text": text[split_at:]}])
        refs = cotizador.parse_claude_references(content, "TEST", "MODEL", cotizador.datetime.utcnow().year - 2)
        self.assertEqual(len(refs["used"]), 1)

    def test_paused_search_continues_with_previous_content(self):
        first = Mock(status_code=200)
        first.json.return_value = {"stop_reason": "pause_turn", "content": [{"type": "text", "text": "Buscando"}]}
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch.object(cotizador.requests, "post", side_effect=[first, web_response()]) as post:
                result = cotizador.calculate_claude_quote("TEST", "MODEL", cotizador.datetime.utcnow().year - 2, 10000, "", {})
        self.assertEqual(post.call_count, 2)
        self.assertTrue(result["web_search_performed"])

    def test_successful_web_search_is_cached_with_sources(self):
        payload = {"brand": "TEST", "line": "MODEL", "year": 2024, "mileage": 10000}
        result = {"web_search_performed": True, "market_references": {"new": [], "used": []}}
        with patch.object(cotizador, "get_cached_quote", return_value=None):
            with patch.object(cotizador, "calculate_claude_quote", return_value=result):
                with patch.object(cotizador, "save_cached_quote") as save:
                    cotizador.quote(payload)
        save.assert_called_once()
        self.assertIn("market_references", save.call_args.args[1])

    def test_claude_failure_is_visible_and_does_not_claim_web_search(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch.object(cotizador.requests, "post", side_effect=requests.Timeout()):
                with patch.object(cotizador, "score_market_references", return_value=[{"price": 200_000_000}]):
                    result = cotizador.calculate_claude_quote("TEST", "MODEL", 2020, 10_000, "", {})
        self.assertFalse(result["web_search_performed"])
        self.assertIsNone(result["ai_provider"])
        self.assertTrue(result["director_review"])
        self.assertIn("catalogos locales", result["notes"][0])

    def test_failed_web_search_is_not_cached(self):
        payload = {"brand": "TEST", "line": "MODEL", "year": 2024, "mileage": 10000}
        with patch.object(cotizador, "get_cached_quote", return_value=None):
            with patch.object(cotizador, "calculate_claude_quote", return_value={"web_search_performed": False}):
                with patch.object(cotizador, "save_cached_quote") as save:
                    cotizador.quote(payload)
        save.assert_not_called()

    def test_cache_includes_vehicle_details_even_with_same_plate(self):
        args = ("TEST", "MODEL", 2024, 10000, "")
        first = cotizador.quote_cache_key(*args, {"plate": "ABC123", "fuel": "Gasolina"})
        second = cotizador.quote_cache_key(*args, {"plate": "ABC123", "fuel": "Electrico"})
        self.assertNotEqual(first, second)

    def test_new_cache_version_separates_previous_results(self):
        with patch.object(cotizador, "QUOTE_CACHE_VERSION", 3):
            previous = cotizador.quote_cache_key("TEST", "MODEL", 2024, 10000, "", {})
        current = cotizador.quote_cache_key("TEST", "MODEL", 2024, 10000, "", {})
        self.assertNotEqual(previous, current)


if __name__ == "__main__":
    unittest.main()
