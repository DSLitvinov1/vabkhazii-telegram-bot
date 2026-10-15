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
        self.assertIn(result["temperature"], {"warm", "hot"})

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

    def test_generic_excursion_demand_with_date_and_party_is_kept(self):
        result, reason = self.classify(
            "Подскажите, куда съездить завтра из Гагры? Нас четверо."
        )
        self.assertIsNone(reason)
        self.assertIsNotNone(result)
        self.assertEqual(result["lead_type"], "excursion")
        self.assertEqual(result["temperature"], "warm")

    def test_generic_sightseeing_question_in_local_city_is_warm_excursion(self):
        result, reason = self.classify(
            "Что посмотреть в Сухуме?"
        )
        self.assertIsNone(reason)
        self.assertIsNotNone(result)
        self.assertEqual(result["lead_type"], "excursion")
        self.assertEqual(result["temperature"], "warm")

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

    def test_distance_question_is_not_mistaken_for_transfer_price(self):
        result, reason = self.classify(
            "Подскажите, сколько километров от Сухума до Гагры?"
        )
        self.assertIsNone(result)
        self.assertIsNotNone(reason)

    def test_travel_time_question_is_not_mistaken_for_transfer_lead(self):
        result, reason = self.classify(
            "Подскажите, сколько ехать от Сухума до Гагры?"
        )
        self.assertIsNone(result)
        self.assertIsNotNone(reason)

    def test_plain_transport_statement_is_not_a_lead(self):
        result, reason = self.classify(
            "Маршрутки из Сухума в Гагру ходят весь день."
        )
        self.assertIsNone(result)
        self.assertIsNotNone(reason)

    def test_price_followup_is_kept_in_trusted_generic_tourist_chat(self):
        self.assertTrue(
            lead_bot.is_chain_context_message(
                "Сколько это будет стоить?",
                "MY:Свободное общение",
                trusted_source=True,
            )
        )

    def test_empty_chatter_is_not_kept_even_in_trusted_chat(self):
        self.assertFalse(
            lead_bot.is_chain_context_message(
                "Спасибо большое",
                "MY:Свободное общение",
                trusted_source=True,
            )
        )

    def test_price_followup_is_kept_as_chain_context_in_amra(self):
        self.assertTrue(
            lead_bot.is_chain_context_message(
                "Сколько это будет стоить?",
                "MY:AMRA Абхазия",
            )
        )

    def test_more_abkhazia_localities_are_recognized_for_transfer_context(self):
        samples = {
            "Алахадзы": "Нужно завтра из Алахадзы в Сухум, нас двое.",
            "Гулрыпш": "Подскажите такси из Сухума в Гулрыпш вечером?",
            "Кындыг": "Сколько будет стоить машина из Сухума в Кындыг завтра?",
        }
        for place, text in samples.items():
            with self.subTest(place=place):
                result, reason = self.classify(text)
                self.assertIsNone(reason)
                self.assertIsNotNone(result)
                self.assertEqual(result["lead_type"], "transfer")
                self.assertIn(place, lead_bot.detect_all_places(text))

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

    def test_terse_route_request_without_service_word_is_kept(self):
        result, reason = self.classify(
            "Сухум — Гагра завтра, 2 человека с чемоданами."
        )
        self.assertIsNone(reason)
        self.assertIsNotNone(result)
        self.assertEqual(result["lead_type"], "transfer")
        self.assertEqual(result["temperature"], "warm")

    def test_terse_route_price_question_is_kept(self):
        result, reason = self.classify(
            "Сухум — Цандрипш, сколько будет стоить?"
        )
        self.assertIsNone(reason)
        self.assertIsNotNone(result)
        self.assertEqual(result["lead_type"], "transfer")

    def test_terse_excursion_request_is_kept(self):
        result, reason = self.classify(
            "Рица завтра, нас двое. Подскажите варианты."
        )
        self.assertIsNone(reason)
        self.assertIsNotNone(result)
        self.assertEqual(result["lead_type"], "excursion")

    def test_scenic_destination_how_to_get_there_is_excursion(self):
        result, reason = self.classify(
            "Подскажите, как добраться до Рицы завтра?"
        )
        self.assertIsNone(reason)
        self.assertIsNotNone(result)
        self.assertEqual(result["lead_type"], "excursion")

    def test_explicit_taxi_to_scenic_destination_stays_transfer(self):
        result, reason = self.classify(
            "Нужно такси из Гагры на Рицу завтра."
        )
        self.assertIsNone(reason)
        self.assertIsNotNone(result)
        self.assertEqual(result["lead_type"], "transfer")

    def test_local_sightseeing_question_is_kept_as_warm_excursion(self):
        result, reason = self.classify(
            "Подскажите, что посмотреть в Гагре?"
        )
        self.assertIsNone(reason)
        self.assertIsNotNone(result)
        self.assertEqual(result["lead_type"], "excursion")
        self.assertEqual(result["temperature"], "warm")

    def test_local_where_to_go_question_is_kept_as_excursion(self):
        result, reason = self.classify(
            "Куда съездить из Пицунды? Мы здесь на несколько дней."
        )
        self.assertIsNone(reason)
        self.assertIsNotNone(result)
        self.assertEqual(result["lead_type"], "excursion")

    def test_broad_abkhazia_sightseeing_question_without_local_context_stays_filtered(self):
        result, reason = self.classify(
            "Что посмотреть в Абхазии?"
        )
        self.assertIsNone(result)
        self.assertIsNotNone(reason)

    def test_generic_excursion_opportunity_with_city_and_date_is_kept(self):
        result, reason = self.classify(
            "Мы в Гагре. Куда съездить завтра с ребёнком?"
        )
        self.assertIsNone(reason)
        self.assertIsNotNone(result)
        self.assertEqual(result["lead_type"], "excursion")
        self.assertEqual(result["temperature"], "warm")

    def test_generic_planning_without_local_detail_stays_filtered(self):
        result, reason = self.classify(
            "Планируем поездку в Абхазию когда-нибудь осенью, что посмотреть?"
        )
        self.assertIsNone(result)
        self.assertIsNotNone(reason)

    def test_service_discussion_group_is_not_blocked_only_by_taxi_word(self):
        chat = SimpleNamespace(
            title="Такси и поездки Абхазия — обсуждение",
            username="abhazia_taxi_talk",
            broadcast=False,
            megagroup=True,
        )
        self.assertTrue(lead_bot.is_discovery_candidate_chat(chat))

    def test_clear_commercial_storefront_group_remains_blocked(self):
        chat = SimpleNamespace(
            title="Служба такси Абхазия",
            username="abhazia_taxi_service",
            broadcast=False,
            megagroup=True,
        )
        self.assertFalse(lead_bot.is_discovery_candidate_chat(chat))

    def test_fast_priority_search_runs_more_often_than_full_search(self):
        self.assertLessEqual(
            lead_bot.FAST_PRIORITY_SEARCH_INTERVAL_MINUTES,
            lead_bot.GLOBAL_SEARCH_INTERVAL_MINUTES,
        )
        self.assertGreaterEqual(len(lead_bot.FAST_PRIORITY_SEARCH_QUERIES), 12)
        for query in lead_bot.FAST_PRIORITY_SEARCH_QUERIES:
            self.assertIn(query, lead_bot.PRIORITY_SEARCH_QUERIES)

    def test_natural_transfer_verbs_are_understood(self):
        samples = [
            "Кто может подвезти из Сухума в Гагру завтра? Нас двое.",
            "Надо подбросить 2 человек из Гагры в Сухум вечером.",
            "Можно подобрать нас в Пицунде и довезти до Сухума?",
        ]
        for text in samples:
            with self.subTest(text=text):
                result, reason = self.classify(text)
                self.assertIsNone(reason)
                self.assertIsNotNone(result)
                self.assertEqual(result["lead_type"], "transfer")

    def test_latin_place_spellings_are_recognized(self):
        result, reason = self.classify(
            "Такси Sukhum — Gagra завтра, 2 человека"
        )
        self.assertIsNone(reason)
        self.assertIsNotNone(result)
        self.assertEqual(result["lead_type"], "transfer")

    def test_search_capacity_is_expanded(self):
        self.assertGreaterEqual(lead_bot.SEARCH_LIMIT, 50)
        self.assertGreaterEqual(lead_bot.MAX_DISCOVERED_CHATS, 100)
        self.assertGreaterEqual(lead_bot.MY_CHATS_MAX_GROUPS, 100)
        self.assertGreaterEqual(lead_bot.GLOBAL_QUERY_BATCH_SIZE, 50)

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

    def test_joined_abkhazia_transfer_group_is_scanned(self):
        chat = SimpleNamespace(
            title="Трансфер Абхазия | Сухум Гагра",
            username="abhazia_transfer_chat",
            broadcast=False,
        )
        self.assertTrue(lead_bot.is_joined_tourist_chat(chat))

    def test_seller_ad_inside_service_group_is_filtered(self):
        result, reason = self.classify(
            "Предлагаю трансфер по Абхазии. Есть свободные места, пишите в личку."
        )
        self.assertIsNone(result)
        self.assertEqual(reason, "seller_or_ad")

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

    def test_hidden_night_transport_problem_is_kept(self):
        result, reason = self.classify(
            "Мне нужна ночная цена, опять рейс перенесли. "
            "Как ночью добираться хз. И у аквафона по вай фаю не вызвать."
        )
        self.assertIsNone(reason)
        self.assertIsNotNone(result)
        self.assertEqual(result["lead_type"], "transfer")
        self.assertEqual(result["temperature"], "warm")

    def test_delayed_flight_natural_wording_is_transfer(self):
        result, reason = self.classify(
            "Рейс задержали, прилетаем поздно. Как ночью добираться до Гагры?"
        )
        self.assertIsNone(reason)
        self.assertIsNotNone(result)
        self.assertEqual(result["lead_type"], "transfer")

    def test_no_route_word_needed_for_transport_problem_in_abkhazia_source(self):
        result, reason = self.classify(
            "Маршрутки уже не ходят, как уехать ночью?"
        )
        self.assertIsNone(reason)
        self.assertIsNotNone(result)
        self.assertEqual(result["lead_type"], "transfer")

    def test_historical_taxi_experience_stays_filtered(self):
        result, reason = self.classify(
            "Мы ехали в августе. По приложению такси цена была 2700. "
            "Таксист повез нас за 3 тыс."
        )
        self.assertIsNone(result)
        self.assertIsNotNone(reason)

    def test_advice_about_individual_transfer_is_not_new_lead(self):
        result, reason = self.classify(
            "Может Вам лучше индивидуальный трансфер? "
            "И водитель будет следить за Вашим рейсом."
        )
        self.assertIsNone(result)
        self.assertIsNotNone(reason)

    def test_travelask_hotel_forum_is_priority_source(self):
        self.assertIn("abhazia_hotels_travelask", lead_bot.TARGET_CHATS)

    def test_search_expansion_covers_hidden_transport_and_local_excursions(self):
        all_queries = " ".join(lead_bot.SEARCH_QUERIES).lower()
        for marker in (
            "как ночью добираться",
            "рейс перенесли как добраться",
            "до которого часа такси псоу",
            "мы в гагре куда поехать",
            "экскурсия на завтра гагра",
        ):
            self.assertIn(marker, all_queries)

        self.assertGreaterEqual(lead_bot.SEARCH_LIMIT, 70)
        self.assertGreaterEqual(lead_bot.MAX_DISCOVERED_CHATS, 150)
        self.assertGreaterEqual(lead_bot.MY_CHATS_BOOTSTRAP_PER_RUN, 20)
        self.assertGreaterEqual(lead_bot.DISCOVERY_BOOTSTRAP_PER_RUN, 25)

    def test_deep_survey_priority_sources_are_pinned(self):
        for username in (
            "chatyourabkhazia",
            "Sukhum_Abhazia_chat",
            "poputchiki_abkhazia",
            "sukhumefirchat",
            "forum_abkhazia",
            "GAGRA8",
            "pitsundas",
            "AbkhaziaKPP",
            "abhazia_chat",
            "NewsApsnyChat",
        ):
            self.assertIn(username, lead_bot.TARGET_CHATS)

    def test_deep_search_capacity_is_expanded(self):
        self.assertGreaterEqual(lead_bot.SEARCH_LIMIT, 80)
        self.assertGreaterEqual(lead_bot.MAX_DISCOVERED_CHATS, 200)
        self.assertGreaterEqual(lead_bot.MY_CHATS_MAX_GROUPS, 220)
        self.assertGreaterEqual(lead_bot.GLOBAL_QUERY_BATCH_SIZE, 88)

    def test_natural_excursion_purchase_question_is_kept(self):
        result, reason = self.classify(
            "Подскажите, где взять экскурсию из Гагры на завтра?"
        )
        self.assertIsNone(reason)
        self.assertIsNotNone(result)
        self.assertEqual(result["lead_type"], "excursion")

    def test_excursion_experience_question_is_kept_as_opportunity(self):
        result, reason = self.classify(
            "Кто ездил на экскурсию в Восточную Абхазию? Что посоветуете?"
        )
        self.assertIsNone(reason)
        self.assertIsNotNone(result)
        self.assertEqual(result["lead_type"], "excursion")

    def test_new_priority_searches_fit_batch(self):
        joined = " ".join(lead_bot.PRIORITY_SEARCH_QUERIES).lower()
        for marker in (
            "маршрутки уже не ходят псоу",
            "как добраться от псоу до гагры",
            "какие экскурсии посоветуете абхазия",
            "где взять экскурсию абхазия",
            "акармара как попасть",
        ):
            self.assertIn(marker, joined)
        self.assertLessEqual(
            len(lead_bot.PRIORITY_SEARCH_QUERIES),
            lead_bot.GLOBAL_QUERY_BATCH_SIZE,
        )

    def test_second_wave_global_message_sources_are_pinned(self):
        for username in (
            "blablacar_abh",
            "krasnaya_polyana",
            "gidvsochi",
            "naidisvoihsochi",
        ):
            self.assertIn(username, lead_bot.TARGET_CHATS)

    def test_extended_excursion_geography_is_recognized(self):
        samples = {
            "Гагра и окрестности": "Подскажите, как попасть на Мамзышху завтра?",
            "Рица": "Хотим завтра на Голубое озеро и Юпшарский каньон.",
            "Новый Афон": "Подскажите экскурсию в Новоафонскую пещеру завтра.",
            "Восточная Абхазия": "Хотим съездить в Кындыг и Кодорское ущелье.",
            "Святыни": "Ищем экскурсию в Мокву, Илор и Бедиа.",
        }
        for route, text in samples.items():
            with self.subTest(route=route):
                self.assertEqual(lead_bot.detect_route(text), route)
                result, reason = self.classify(text)
                self.assertIsNone(reason)
                self.assertIsNotNone(result)
                self.assertEqual(result["lead_type"], "excursion")

    def test_new_long_tail_excursion_queries_are_present(self):
        joined = " ".join(lead_bot.SEARCH_QUERIES).lower()
        for marker in (
            "мамзышха",
            "гегский водопад",
            "ауадхара",
            "новоафонская пещера",
            "кодорское ущелье",
            "псху",
            "паломничество",
            "трекинг абхазия",
        ):
            self.assertIn(marker, joined)

    def test_priority_queries_still_fit_expanded_batch(self):
        self.assertLessEqual(
            len(lead_bot.PRIORITY_SEARCH_QUERIES),
            lead_bot.GLOBAL_QUERY_BATCH_SIZE,
        )
        self.assertGreaterEqual(lead_bot.GLOBAL_QUERY_BATCH_SIZE, 96)

    def test_prebooking_excursion_questions_are_kept_warm(self):
        samples = [
            "Кто ездил на Рицу? Что посоветуете на завтра?",
            "Кто ходил на Мзы? Хотим съездить завтра.",
            "Какую экскурсию взять из Гагры на завтра?",
        ]
        for text in samples:
            with self.subTest(text=text):
                result, reason = self.classify(text)
                self.assertIsNone(reason)
                self.assertIsNotNone(result)
                self.assertEqual(result["lead_type"], "excursion")

    def test_rideshare_demand_queries_are_in_search_base(self):
        joined = " ".join(lead_bot.SEARCH_QUERIES).lower()
        for marker in (
            "ищу попутку абхазия",
            "кто едет псоу гагра сегодня",
            "кто заберет с псоу",
            "нужно уехать с псоу",
        ):
            self.assertIn(marker, joined)

    def test_expanded_priority_batch_still_fits(self):
        self.assertLessEqual(
            len(lead_bot.PRIORITY_SEARCH_QUERIES),
            lead_bot.GLOBAL_QUERY_BATCH_SIZE,
        )
        self.assertGreaterEqual(lead_bot.GLOBAL_QUERY_BATCH_SIZE, 104)

    def test_all_excursion_searches_run_every_cycle(self):
        for query in lead_bot.EXCURSION_ALWAYS_SEARCH_QUERIES:
            self.assertIn(query, lead_bot.PRIORITY_SEARCH_QUERIES)
        self.assertLessEqual(
            len(lead_bot.PRIORITY_SEARCH_QUERIES),
            lead_bot.GLOBAL_QUERY_BATCH_SIZE,
        )

    def test_global_search_depth_is_large_enough_for_bot_noise(self):
        self.assertGreaterEqual(lead_bot.SEARCH_LIMIT, 120)

    def test_additional_excursion_discussion_groups_are_pinned(self):
        for username in (
            "abhaziaturchat",
            "chat_sochi_abkhazia_trip",
            "abkhazia_active_rests",
            "pohody_sochi_abkhazia",
        ):
            self.assertIn(username, lead_bot.TARGET_CHATS)

    def test_public_chat_peer_cache_round_trip(self):
        class DummyChat:
            username = "ExampleTouristChat"
            id = 123456
            access_hash = 987654321
            title = "Example Tourist Chat"

        state = {"telegram_peer_cache": {}}
        lead_bot.cache_public_chat_peer(state, DummyChat())
        peer = lead_bot.get_cached_public_chat_peer(state, "exampletouristchat")

        self.assertIsNotNone(peer)
        self.assertEqual(peer.channel_id, 123456)
        self.assertEqual(peer.access_hash, 987654321)
        self.assertEqual(
            lead_bot.chat_cursor_key(peer, "whitelist"),
            "whitelist:123456",
        )


if __name__ == "__main__":
    unittest.main()
