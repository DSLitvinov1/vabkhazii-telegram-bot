import re
import unittest
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

import bot


class AbkhaziaContentTests(unittest.TestCase):
    def test_each_fact_has_at_least_seven_sentences(self):
        self.assertGreaterEqual(len(bot.FACTS), 10)
        for index, fact in enumerate(bot.FACTS):
            with self.subTest(fact=index):
                self.assertGreaterEqual(
                    len(re.findall(r"[.!?](?=\s|$)", fact.strip())), 7
                )
                self.assertEqual(bot.verified_fact_text(fact), fact)
                self.assertLess(bot.telegram_visible_length(fact), 4096)

    def test_short_fact_is_rejected(self):
        with self.assertRaises(ValueError):
            bot.verified_fact_text("Первый факт. Второй факт.")

    def test_fact_fallback_is_expanded_and_within_telegram_limit(self):
        mock_date = datetime(2026, 10, 2, 9, 0, tzinfo=ZoneInfo("Europe/Moscow"))
        with patch.object(bot, "collect_news_candidates", return_value=[]):
            with patch.object(bot, "now_local", return_value=mock_date):
                post, item_hash = bot.build_positive_news_post({"used_news": []})
                self.assertTrue(item_hash.startswith("fact-"))
                self.assertGreaterEqual(
                    len(re.findall(r"[.!?](?=\s|$)", re.sub(r"<[^>]+>", "", post))),
                    7,
                )
                self.assertLessEqual(bot.telegram_visible_length(post), 4096)

    def test_fact_rotation_avoids_immediate_repeat(self):
        mock_date = datetime(2026, 10, 2, 9, 0, tzinfo=ZoneInfo("Europe/Moscow"))
        with patch.object(bot, "collect_news_candidates", return_value=[]):
            with patch.object(bot, "now_local", return_value=mock_date):
                _, first = bot.build_positive_news_post({"used_news": []})
                _, second = bot.build_positive_news_post({"used_news": [first]})
        self.assertNotEqual(first, second)


if __name__ == "__main__":
    unittest.main()
