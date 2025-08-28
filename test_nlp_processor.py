import unittest
from features.nlp_processor import get_nlp_processor

class TestNLPProcessor(unittest.TestCase):
    def setUp(self):
        self.processor = get_nlp_processor()

    def test_intent_detection(self):
        test_cases = [
            ("xin chào", "greeting"),
            ("tôi muốn xem nhắc nhở", "list_reminder"),
            ("xóa nhắc nhở", "delete_reminder"),
            ("trí tuệ nhân tạo", "ai_enhancement"),
            ("là gì", "question"),
        ]
        
        for command, expected_intent in test_cases:
            with self.subTest(command=command):
                analysis = self.processor.analyze_text_with_context(command)
                intents = analysis.get("intent", {})
                intent_names = [intent for intent, score in sorted(intents.items(), key=lambda x: x[1], reverse=True)]
                self.assertIn(expected_intent, intent_names)

    def test_entity_extraction(self):
        command = "hẹn gặp vào ngày mai lúc 3 giờ"
        analysis = self.processor.analyze_text_with_context(command)
        entities = analysis.get("entities", {})
        self.assertIn("date", entities)
        self.assertIn("time", entities)

    def test_sentiment_analysis(self):
        command = "Tôi rất vui với kết quả này!"
        analysis = self.processor.analyze_text_with_context(command)
        sentiment = analysis.get("sentiment", {})
        self.assertEqual(sentiment['label'], "positive")

    def test_learning_capabilities(self):
        # Test that the processor can learn from interactions
        command = "tôi muốn học cách sử dụng trí tuệ nhân tạo"
        analysis1 = self.processor.analyze_text_with_context(command)
        
        # Check that the interaction was recorded
        self.assertGreater(len(self.processor.user_history), 0)
        
        # Check that patterns were learned
        self.assertIn("ai_enhancement", self.processor.learned_patterns)
        
        # Test with a similar command to see if learning improves detection
        similar_command = "học cách dùng ai"
        analysis2 = self.processor.analyze_text_with_context(similar_command)
        
        # The second analysis should have some learned patterns applied
        intents = analysis2.get("intent", {})
        self.assertGreater(len(intents), 0)

if __name__ == "__main__":
    unittest.main()
