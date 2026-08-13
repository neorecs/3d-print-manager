from support import *
from services.ai_usage_service import ai_usage_status, complete_ai_request, reserve_ai_request


class AiProductAssistantTestCase(BackendTestCase):
    def test_ai_daily_limit_blocks_extra_paid_request(self) -> None:
        usage = reserve_ai_request(self.db, "product_draft", "test-model", 1)
        complete_ai_request(self.db, usage, {"input_tokens": 10, "output_tokens": 20})

        with self.assertRaises(HTTPException) as blocked:
            reserve_ai_request(self.db, "product_draft", "test-model", 1)

        self.assertEqual(blocked.exception.status_code, 429)
        status = ai_usage_status(self.db, 1)
        self.assertEqual(status["used_today"], 1)
        self.assertEqual(status["output_tokens_today"], 20)

    def test_mock_product_translation_generates_without_openai_call(self) -> None:
        class Settings:
            ai_openai_enabled = False
            openai_api_key = None

        result = generate_product_translation(
            {
                "name": "Dumpling Rood",
                "title": "Dumpling Rood",
                "short_description": "Kleine decoratie voor op bureau.",
                "tags": ["decoratie", "bureau"],
            },
            "de",
            Settings(),
        )

        self.assertEqual(result["source"], "mock_translation")
        self.assertTrue(result["title"].startswith("[DE concept]"))
