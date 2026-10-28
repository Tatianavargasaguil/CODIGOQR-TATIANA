import unittest
from unittest.mock import Mock, patch

from app import cotizador


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
        for reference_price, expected_width in [(50_000_000, 3_000_000), (100_000_000, 5_000_000)]:
            with self.subTest(reference_price=reference_price):
                with patch.object(cotizador, "score_market_references", return_value=[{"price": reference_price}]):
                    result = cotizador.calculate_local_quote("TEST", "TEST", 2020, 10_000, "", {})
                self.assertEqual(result["offer_max"] - result["offer_min"], expected_width)

    def test_ai_range_keeps_midpoint_and_applies_rule(self):
        local_quote = {"director_review": False, "offer_min": 38_500_000, "offer_max": 41_500_000}
        cases = [
            ({"offer_min": 37_500_000, "offer_max": 42_500_000}, (38_500_000, 41_500_000)),
            ({"offer_min": 58_500_000, "offer_max": 61_500_000}, (57_500_000, 62_500_000)),
            ({"offer": 80_000_000}, (77_500_000, 82_500_000)),
            ({}, (38_500_000, 41_500_000)),
        ]
        for ai_quote, expected in cases:
            with self.subTest(ai_quote=ai_quote):
                import json

                response = Mock(status_code=200)
                response.json.return_value = {"choices": [{"message": {"content": json.dumps(ai_quote)}}]}
                with patch.dict("os.environ", {"CARMAX_DEEPSEEK_API_KEY": "test-key"}):
                    with patch.object(cotizador, "calculate_local_quote", return_value=local_quote):
                        with patch.object(cotizador.requests, "post", return_value=response):
                            result = cotizador.calculate_deepseek_quote("TEST", "TEST", 2020, 10_000, "", {})
                self.assertEqual((result["offer_min"], result["offer_max"]), expected)
                self.assertEqual(result["offer_min_formatted"], cotizador.format_cop(expected[0]))
                self.assertEqual(result["offer_max_formatted"], cotizador.format_cop(expected[1]))

    def test_new_cache_version_separates_previous_results(self):
        for features in [{}, {"plate": "ABC123"}]:
            with self.subTest(features=features):
                with patch.object(cotizador, "QUOTE_CACHE_VERSION", 1):
                    previous = cotizador.quote_cache_key("TEST", "TEST", 2020, 10_000, "", features)
                current = cotizador.quote_cache_key("TEST", "TEST", 2020, 10_000, "", features)
                self.assertNotEqual(previous, current)


if __name__ == "__main__":
    unittest.main()
