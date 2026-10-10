import os
import unittest
from types import SimpleNamespace

os.environ["LEADS_UNIT_TEST"] = "1"

import lead_bot


class LeadClassificationTests(unittest.TestCase):
    SOURCE = "Абхазия чат туристов"

    def classify(self, text):
        return lead_bot.classify_lead_detailed(text, self.SOURCE)

    def test_additional_public_discussion_sources_are_configured(self):
        sources = {item["key"]: item for item in lead_bot.EXTERNAL_SOURCES}
        for key in ("vk_tourist_discussions", "pikabu_travel_discussions"):
            source = sources[key]
            self.assertEqual(source["access"], "search_index")
            self.assertTrue(source["search_queries"])
            self.assertTrue(source["path_regex"])

    def test_planning_notifications_remain_disabled_with_new_sources(self):
        self.assertFalse(lead_bot.PLANNING_NOTIFICATIONS_ENABLED)
        self.assertIsNone(lead_bot.make_planning_digest([{"text": "Планируем поездку"}]))

    def test_hot_transfer_request_is_kept(self):
        result, reason = self.classify(
            "Добрый день. Кто может забрать с аэропорта Сочи до Лдзаа сегодня "
            "около 1 часа ночи, 4 человека. Пишите с ценой в личку."
        )
        self.assertIsNone(reason)
        self.assertIsNotNone(result)
        self.assertEqual(result["bucket"], "direct")
        self.assertEqual(result["lead_type"], "transfer")

    def test_public_transport_question_with_route_and_time_is_kept_as_warm_transfer(self):
        result, reason = self.classify(
            "Добрый день. Подскажите, как добраться из Сухума до Гагры на маршрутке? "
            "Прилет в Сухум запланирован в 15:15. В это время еще ходят маршрутки и откуда?"
        )
        self.assertIsNone(reason)
        self.assertIsNotNone(result)
        self.assertEqual(result["bucket"], "direct")
        self.assertEqual(result["lead_type"], "transfer")
        self.assertEqual(result["temperature"], "warm")

    def test_bus_question_without_explicit_transfer_word_is_kept_warm(self):
        result, reason = self.classify(
            "Подскажите, ходят ли маршрутки из Сухума в Гагру вечером?"
        )
        self.assertIsNone(reason)
        self.assertIsNotNone(result)
        self.assertEqual(result["lead_type"], "transfer")
        self.assertEqual(result["temperature"], "warm")

    def test_airport_local_transport_question_is_kept_warm(self):
        result, reason = self.classify(
            "Прилетаю в Сухум в 15:15. Как добраться от аэропорта до автовокзала?"
        )
        self.assertIsNone(reason)
        self.assertIsNotNone(result)
        self.assertEqual(result["lead_type"], "transfer")
        self.assertEqual(result["temperature"], "warm")

    def test_specific_route_interest_is_kept_as_warm_excursion(self):
        result, reason = self.classify(
            "Подскажите, как попасть на Рицу завтра? Нас двое."
        )
        self.assertIsNone(reason)
        self.assertIsNotNone(result)
        self.assertEqual(result["lead_type"], "excursion")
        self.assertEqual(result["temperature"], "warm")

    def test_natural_bus_question_is_kept_warm(self):
        result, reason = self.classify(
            "Маршрутки Сухум — Гагра вечером еще ходят?"
        )
        self.assertIsNone(reason)
        self.assertIsNotNone(result)
        self.assertEqual(result["lead_type"], "transfer")
        self.assertEqual(result["temperature"], "warm")

    def test_taxi_availability_question_is_kept_warm(self):
        result, reason = self.classify(
            "Есть ли такси из Гагры до аэропорта вечером?"
        )
        self.assertIsNone(reason)
        self.assertIsNotNone(result)
        self.assertEqual(result["lead_type"], "transfer")
        self.assertEqual(result["temperature"], "warm")

    def test_plain_route_chatter_stays_filtered(self):
        result, reason = self.classify(
            "Маршрутка Сухум Гагра идет по этой дороге, около 30 км."
        )
        self.assertIsNone(result)
        self.assertIsNotNone(reason)

    def test_oli_taxi_request_with_tsandripsh_spelling_is_kept(self):
        result, reason = self.classify(
            "Добрый день народ. Подскажите пожалуйста такси Сухума Цандрипш"
        )
        self.assertIsNone(reason)
        self.assertIsNotNone(result)
        self.assertEqual(result["lead_type"], "transfer")

    def test_oli_followup_chain_is_recognized_as_strong_transfer(self):
        text = (
            "Добрый день народ. Подскажите пожалуйста такси Сухума Цандрипш\n"
            "Сколько это будет стоить?\n"
            "Надо забрать двух человек с вещами и привезти в Цандрипш"
        )
        result, reason = self.classify(text)
        self.assertIsNone(reason)
        self.assertIsNotNone(result)
        self.assertEqual(result["lead_type"], "transfer")
        self.assertEqual(lead_bot.detect_people(text), 2)
        self.assertTrue(lead_bot.detect_baggage(text))
        self.assertIn("Цандрыпш", lead_bot.detect_all_places(text))
        self.assertIn("Сухум", lead_bot.detect_all_places(text))

    def test_contextual_transfer_price_question_is_kept(self):
        result, reason = self.classify(
            "Сколько будет стоить из Сухума в Гагру завтра? Нас трое."
        )
        self.assertIsNone(reason)
        self.assertIsNotNone(result)
        self.assertEqual(result["lead_type"], "transfer")
        self.assertEqual(result["temperature"], "warm")

    def test_contextual_transfer_without_word_transfer_is_kept(self):
        result, reason = self.classify(
            "Нужно завтра из Пицунды в Сухум, 2 человека. Подскажите по машине."
        )
        self.assertIsNone(reason)
        self.assertIsNotNone(result)
        self.assertEqual(result["lead_type"], "transfer")

    def test_one_city_taxi_question_is_kept(self):
        result, reason = self.classify(
            "Подскажите такси в Сухуме вечером, нас двое с чемоданами."
        )
        self.assertIsNone(reason)
        self.assertIsNotNone(result)
        self.assertEqual(result["lead_type"], "transfer")

    def test_route_price_question_is_kept_as_excursion(self):
        result, reason = self.classify(
            "Подскажите, сколько будет стоить съездить на Рицу завтра, нас двое?"
        )
        self.assertIsNone(reason)
        self.assertIsNotNone(result)
        self.assertEqual(result["lead_type"], "excursion")
        self.assertEqual(result["temperature"], "warm")

    def test_buyer_cost_question_is_not_mistaken_for_seller(self):
        result, reason = self.classify(
            "Подскажите стоимость экскурсии на Мзы завтра для двух человек?"
        )
        self.assertIsNone(reason)
        self.assertIsNotNone(result)
        self.assertEqual(result["lead_type"], "excursion")

    def test_excursion_ad_with_price_is_still_filtered(self):
        result, reason = self.classify(
            "Стоимость экскурсии на Рицу 2500 руб. Есть свободные места, бронируйте."
        )
        self.assertIsNone(result)
        self.assertEqual(reason, "seller_or_ad")

    def test_plain_transport_statement_is_not_a_lead(self):
        result, reason = self.classify(
            "Маршрутки из Сухума в Гагру ходят весь день."
        )
        self.assertIsNone(result)
        self.assertIsNotNone(reason)

    def test_price_followup_is_kept_as_chain_context_in_amra(self):
        self.assertTrue(
            lead_bot.is_chain_context_message(
                "Сколько это будет стоить?",
                "MY:AMRA Абхазия",
            )
        )

    def test_alt_tsandripsh_source_context_is_recognized(self):
        self.assertTrue(
            lead_bot.has_abkhazia_source_context("Цандрипш поездки")
        )

    def test_priority_queries_cover_colloquial_demand(self):
        joined = " ".join(lead_bot.PRIORITY_SEARCH_QUERIES).lower()
        for marker in ("подскажите такси", "такси сухум", "кто заберет", "нужна экскурсия"):
            self.assertIn(marker, joined)
        self.assertLessEqual(
            len(lead_bot.PRIORITY_SEARCH_QUERIES),
            lead_bot.GLOBAL_QUERY_BATCH_SIZE,
        )

    def test_direct_excursion_request_is_kept(self):
        result, reason = self.classify(
            "Ищем индивидуальную экскурсию на Рицу завтра, нас 3 человека."
        )
        self.assertIsNone(reason)
        self.assertIsNotNone(result)
        self.assertEqual(result["bucket"], "direct")
        self.assertEqual(result["lead_type"], "excursion")

    def test_real_planning_question_is_suppressed(self):
        result, reason = self.classify(
            "В начале октября собираемся в Абхазию с детьми. "
            "Подскажите, куда лучше съездить и что посмотреть?"
        )
        self.assertIsNone(result)
        self.assertIsNotNone(reason)

    def test_planning_digest_is_disabled_even_with_existing_items(self):
        self.assertIsNone(lead_bot.make_planning_digest([{"text": "Планируем поездку"}]))
        self.assertFalse(lead_bot.PLANNING_NOTIFICATIONS_ENABLED)

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
