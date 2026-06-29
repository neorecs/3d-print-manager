from support import *


class AiProductAssistantTestCase(BackendTestCase):
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
