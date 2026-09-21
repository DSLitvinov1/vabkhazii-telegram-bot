import os
import unittest
from types import SimpleNamespace

os.environ["LEADS_UNIT_TEST"] = "1"

import lead_bot


class LeadClassificationTests(unittest.TestCase):
    SOURCE = "Абхазия чат туристов"

    def classify(self, text):
        return lead_bot.classify_lead_detailed(text, self.SOURCE)

    def test_hot_transfer_request_is_kept(self):
        result, reason = self.classify(
            "Добрый день. Кто может забрать с аэропорта Сочи до Лдзаа сегодня "
            "около 1 часа ночи, 4 человека. Пишите с ценой в личку."
        )
        self.assertIsNone(reason)
        self.assertIsNotNone(result)
        self.assertEqual(result["bucket"], "direct")
        self.assertEqual(result["lead_type"], "transfer")

    def test_direct_excursion_request_is_kept(self):
        result, reason = self.classify(
            "Ищем индивидуальную экскурсию на Рицу завтра, нас 3 человека."
        )
        self.assertIsNone(reason)
        self.assertIsNotNone(result)
        self.assertEqual(result["bucket"], "direct")
        self.assertEqual(result["lead_type"], "excursion")

    def test_real_planning_question_is_kept(self):
        result, reason = self.classify(
            "В начале октября собираемся в Абхазию с детьми. "
            "Подскажите, куда лучше съездить и что посмотреть?"
        )
        self.assertIsNone(reason)
        self.assertIsNotNone(result)
        self.assertEqual(result["bucket"], "planning")

    def test_past_trip_story_is_filtered(self):
        result, reason = self.classify(
            "Мы должны были прилететь в Сочи 12.09, а прилетели 13.09. "
            "Врагу не пожелаешь таких приключений."
        )
        self.assertIsNone(result)
        self.assertIsNotNone(reason)

    def test_weather_chatter_is_filtered(self):
        result, reason = self.classify(
            "Неделю была прекрасная летняя погода, штиль, потом шторм, "
            "сейчас разная, меняется постоянно."
        )
        self.assertIsNone(result)
        self.assertIsNotNone(reason)

    def test_transport_news_is_filtered(self):
        result, reason = self.classify(
            "Аэропорт Домодедово ввёл ограничения на использование воздушного "
            "пространства, рейсы принимают по согласованию."
        )
        self.assertIsNone(result)
        self.assertIsNotNone(reason)

    def test_real_estate_ad_is_filtered(self):
        result, reason = self.classify(
            "Участок мечты в Сухуме — 3,5 сотки, до моря 5 минут, "
            "вся инфраструктура рядом. Продажа."
        )
        self.assertIsNone(result)
        self.assertIsNotNone(reason)

    def test_driver_offer_with_free_seats_is_filtered(self):
        result, reason = self.classify(
            "Кто желает завтра в Каманский монастырь? 4 места, выезжаю утром."
        )
        self.assertIsNone(result)
        self.assertIsNotNone(reason)

    def test_route_discussion_is_filtered(self):
        result, reason = self.classify(
            "150 км — это из Сухума до Сочи, а обратно самолёты не летают."
        )
        self.assertIsNone(result)
        self.assertIsNotNone(reason)

    def test_joined_real_estate_chat_is_rejected(self):
        chat = SimpleNamespace(
            title="Аренда недвижимости | Абхазия-Сочи",
            username="hotels_Abhazia",
            broadcast=False,
        )
        self.assertFalse(lead_bot.is_joined_tourist_chat(chat))

    def test_joined_irrelevant_mushroom_chat_is_rejected(self):
        chat = SimpleNamespace(
            title="КультУРа Мухомора Чат Краснодар",
            username="kultura_muhomora",
            broadcast=False,
        )
        self.assertFalse(lead_bot.is_joined_tourist_chat(chat))

    def test_joined_sochi_chat_is_allowed(self):
        chat = SimpleNamespace(
            title="Сочи чат",
            username="sochy_chat",
            broadcast=False,
        )
        self.assertTrue(lead_bot.is_joined_tourist_chat(chat))

    def test_hotel_reviews_abkhazia_chat_is_allowed(self):
        chat = SimpleNamespace(
            title="Отзывы об отелях Абхазии",
            username="abhazia_hotels_travelask",
            broadcast=False,
        )
        self.assertTrue(lead_bot.is_joined_tourist_chat(chat))


if __name__ == "__main__":
    unittest.main()
