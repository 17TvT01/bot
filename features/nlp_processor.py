import re
import string
import datetime
from typing import Dict, List, Tuple, Optional, Any
from collections import Counter, defaultdict
import json

# Lazy loading for advanced NLP libraries
_spacy_nlp = None
_transformers_pipeline = None
_requests = None

def get_spacy_nlp():
    global _spacy_nlp
    if _spacy_nlp is None:
        try:
            import spacy
            _spacy_nlp = spacy.load("en_core_web_sm")
        except:
            _spacy_nlp = None
    return _spacy_nlp

def get_transformers_pipeline():
    global _transformers_pipeline
    if _transformers_pipeline is None:
        try:
            from transformers import pipeline
            _transformers_pipeline = pipeline("sentiment-analysis")
        except:
            _transformers_pipeline = None
    return _transformers_pipeline

def get_requests():
    global _requests
    if _requests is None:
        try:
            import requests
            _requests = requests
        except:
            _requests = None
    return _requests

# Từ khóa và mẫu cho việc nhận diện tính năng
keywords = ["hiểu", "phân tích", "ngôn ngữ", "nlp", "xử lý", "lời nói", "cảm xúc", "ý định", "trí tuệ nhân tạo", "ai"]

patterns = [
    "hiểu lời nói",
    "phân tích ngôn ngữ",
    "xử lý ngôn ngữ tự nhiên",
    "hiểu ý định",
    "phân tích cảm xúc",
    "xóa ghi chú",
    "xóa nhắc nhở",
    "hủy lịch",
    "trí tuệ nhân tạo",
    "học máy"
]

class EnhancedNLPProcessor:
    """Bộ xử lý ngôn ngữ tự nhiên cải tiến với khả năng hiểu ngữ cảnh"""
    
    def __init__(self):
        self.intent_patterns = self._load_enhanced_intent_patterns()
        self.entity_patterns = self._load_entity_patterns()
        self.sentiment_words = self._load_enhanced_sentiment_words()
        self.synonyms = self._load_synonyms()
        self.context_memory = []  # Lưu trữ ngữ cảnh hội thoại
        self.user_preferences = {}  # Lưu trữ sở thích người dùng
        self.user_history = []  # Lưu trữ lịch sử tương tác người dùng
        self.learned_patterns = {}  # Lưu trữ các mẫu đã học từ người dùng
        self.language_preferences = ["vi", "en"]  # Ngôn ngữ được hỗ trợ
        self.search_history = []  # Lưu trữ lịch sử tìm kiếm
        
    def process_command(self, command: str) -> str:
        """Xử lý lệnh từ người dùng với enhanced processing"""
        if not command:
            return "Tôi có thể giúp phân tích ngôn ngữ, nhận diện ý định, và xử lý các lệnh liên quan đến nhắc nhở với khả năng hiểu ngữ cảnh tốt hơn."
        
        # Enhance command với synonyms và normalization
        enhanced_command = self._enhance_command(command)
        
        # Phân tích văn bản với context
        analysis = self.analyze_text_with_context(enhanced_command)
        
        # Xác định ý định chính
        main_intent = self._get_main_intent(analysis)
        
        # Xử lý lệnh liên quan đến nhắc nhở
        if self._is_reminder_related(enhanced_command, analysis):
            from features.reminder import reminder
            return reminder(enhanced_command)
        
        # Kiểm tra xem có nên tìm kiếm thông tin từ bên ngoài không
        if self._should_search_for_information(analysis):
            # Trích xuất truy vấn từ phân tích
            query = self._extract_search_query(enhanced_command, analysis)
            # Thực hiện tìm kiếm và trả về kết quả
            return self._search_for_information(query)
        
        # Cập nhật context memory
        self._update_context(enhanced_command, analysis)
        
        # Hiển thị kết quả phân tích cải tiến
        return self._format_analysis_result(analysis)
    
    def _enhance_command(self, command: str) -> str:
        """Cải thiện lệnh bằng cách thay thế synonyms và normalize"""
        enhanced = command.lower().strip()
        
        # Thay thế synonyms
        for main_word, synonyms in self.synonyms.items():
            for synonym in synonyms:
                enhanced = enhanced.replace(synonym, main_word)
        
        # Normalize dấu câu và khoảng trắng
        enhanced = re.sub(r'\s+', ' ', enhanced)
        enhanced = re.sub(r'[^\w\s\u00C0-\u024F\u1E00-\u1EFF]', ' ', enhanced)
        
        return enhanced.strip()
    
    def analyze_text_with_context(self, text: str) -> Dict[str, Any]:
        """Phân tích văn bản với context awareness"""
        # Phân tích cơ bản
        basic_analysis = {
            "intent": self.detect_enhanced_intent(text),
            "entities": self.extract_enhanced_entities(text),
            "sentiment": self.analyze_enhanced_sentiment(text),
            "keywords": self.extract_smart_keywords(text),
            "normalized_text": self.normalize_text(text),
            "reminder_action": self.analyze_reminder_action(text)
        }
        
        # Thêm context analysis
        context_score = self._calculate_context_score(text, basic_analysis)
        complexity = self._assess_complexity(text, basic_analysis)
        confidence = self._calculate_confidence(basic_analysis)
        
        enhanced_analysis = {
            **basic_analysis,
            "context_score": context_score,
            "complexity": complexity,
            "confidence": confidence,
            "enhanced": True
        }
        
        # Học từ tương tác này
        self._learn_from_interaction(text, enhanced_analysis)
        
        return enhanced_analysis
    
    def _search_for_information(self, query: str) -> str:
        """Tìm kiếm thông tin từ các nguồn bên ngoài khi không thể trả lời câu hỏi"""
        try:
            # Kiểm tra xem requests có sẵn không
            requests = get_requests()
            if not requests:
                return "Xin lỗi, tôi không thể tìm kiếm thông tin trực tuyến tại thời điểm này vì thiếu thư viện requests."
            
            # URL encode the query for use in URLs
            import urllib.parse
            encoded_query = urllib.parse.quote(query)
            
            # Thử tìm kiếm với DuckDuckGo Instant Answer API
            try:
                search_url = f"https://api.duckduckgo.com/?q={encoded_query}&format=json&no_html=1&skip_disambig=1"
                response = requests.get(search_url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    # Kiểm tra AbstractText trước
                    if "AbstractText" in data and data["AbstractText"]:
                        # Lưu vào lịch sử tìm kiếm
                        self.search_history.append({
                            "query": query,
                            "result": data["AbstractText"][:200] + "...",  # Giới hạn độ dài
                            "timestamp": datetime.datetime.now().isoformat()
                        })
                        
                        # Giữ chỉ 20 lịch sử tìm kiếm gần nhất
                        if len(self.search_history) > 20:
                            self.search_history.pop(0)
                        
                        return f"Tôi đã tìm thấy thông tin sau về '{query}':\n\n{data['AbstractText'][:500]}..."
                    
                    # Nếu không có AbstractText, kiểm tra các section khác
                    if "RelatedTopics" in data and data["RelatedTopics"]:
                        # Lấy thông tin từ chủ đề liên quan đầu tiên
                        first_topic = data["RelatedTopics"][0]
                        if "Text" in first_topic:
                            # Lưu vào lịch sử tìm kiếm
                            self.search_history.append({
                                "query": query,
                                "result": first_topic["Text"][:200] + "...",  # Giới hạn độ dài
                                "timestamp": datetime.datetime.now().isoformat()
                            })
                            
                            # Giữ chỉ 20 lịch sử tìm kiếm gần nhất
                            if len(self.search_history) > 20:
                                self.search_history.pop(0)
                            
                            return f"Tôi đã tìm thấy thông tin liên quan đến '{query}':\n\n{first_topic['Text'][:500]}..."
            except Exception as e:
                pass  # Continue to next search method
            
            # Nếu DuckDuckGo không có kết quả, thử Wikipedia API
            try:
                wiki_url = f"https://vi.wikipedia.org/api/rest_v1/page/summary/{encoded_query}"
                response = requests.get(wiki_url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if "extract" in data:
                        # Lưu vào lịch sử tìm kiếm
                        self.search_history.append({
                            "query": query,
                            "result": data["extract"][:200] + "...",  # Giới hạn độ dài
                            "timestamp": datetime.datetime.now().isoformat()
                        })
                        
                        # Giữ chỉ 20 lịch sử tìm kiếm gần nhất
                        if len(self.search_history) > 20:
                            self.search_history.pop(0)
                        
                        return f"Tôi đã tìm thấy thông tin sau về '{query}' từ Wikipedia:\n\n{data['extract'][:500]}..."
            except Exception as e:
                pass  # Continue to next search method
            
            # Nếu không tìm thấy thông tin từ các nguồn trên
            return f"Xin lỗi, tôi không thể tìm thấy thông tin về '{query}'. Bạn có thể cung cấp thêm chi tiết không?"
        except Exception as e:
            return f"Xin lỗi, đã có lỗi xảy ra khi tìm kiếm thông tin: {str(e)}"
    
    def _should_search_for_information(self, analysis: Dict[str, Any]) -> bool:
        """Xác định xem có nên tìm kiếm thông tin từ bên ngoài hay không"""
        # Kiểm tra xem đây có phải là câu hỏi không
        intents = analysis.get("intent", {})
        is_question = "question" in intents and intents["question"] > 0.5
        
        # Kiểm tra độ tin cậy của phân tích
        confidence = analysis.get("confidence", 0)
        low_confidence = confidence < 0.4  # Tăng ngưỡng confidence một chút
        
        # Kiểm tra xem có thực thể nào không
        entities = analysis.get("entities", {})
        has_entities = len(entities) > 0
        
        # Kiểm tra các từ khóa câu hỏi đặc trưng
        question_keywords = ["là gì", "là ai", "ở đâu", "bao nhiêu", "thế nào", "tại sao", "khi nào", "ai là"]
        text = analysis.get("normalized_text", "").lower()
        has_question_keywords = any(keyword in text for keyword in question_keywords)
        
        # Loại trừ các câu hỏi mà trợ lý có thể xử lý nội bộ
        internal_question_patterns = [
            r"mấy\s+giờ", 
            r"thời\s+gian",
            r"ngày\s+mấy",
            r"hôm\s+nay\s+là\s+ngày",
            r"mấy\s+ngày\s+nữa"
        ]
        is_internal_question = any(re.search(pattern, text) for pattern in internal_question_patterns)
        
        # Nếu là câu hỏi nội bộ, không tìm kiếm thông tin
        if is_internal_question:
            return False
        
        # Nếu là câu hỏi hoặc có từ khóa câu hỏi, nên tìm kiếm thông tin
        if is_question or has_question_keywords:
            return True
        
        # Nếu độ tin cậy thấp và có thực thể, cũng nên tìm kiếm
        if low_confidence and has_entities:
            return True
            
        return False
    
    def _can_answer_with_known_info(self, analysis: Dict[str, Any]) -> bool:
        """Kiểm tra xem có thể trả lời với thông tin đã biết không"""
        # Đây là một phương thức đơn giản, trong thực tế có thể phức tạp hơn
        # Kiểm tra xem intent có phải là các loại có thể xử lý nội bộ không
        intents = analysis.get("intent", {})
        internal_intents = ["greeting", "farewell", "thanks", "apology", "reminder", "delete_reminder", "list_reminder"]
        
        for intent, score in intents.items():
            if intent in internal_intents and score > 0.5:
                return True
        
        # Kiểm tra xem có từ khóa liên quan đến các chức năng nội bộ không
        keywords = analysis.get("keywords", [])
        internal_keywords = ["nhắc", "nhớ", "lịch", "giờ", "thời gian", "tính", "mở", "đóng", "chạy"]
        if any(keyword in internal_keywords for keyword in keywords):
            return True
            
        return False
    
    def _learn_from_interaction(self, text: str, analysis: Dict[str, Any]):
        """Học từ tương tác người dùng"""
        # Thêm vào lịch sử người dùng
        interaction = {
            "text": text,
            "analysis": analysis,
            "timestamp": datetime.datetime.now().isoformat()
        }
        self.user_history.append(interaction)
        
        # Giữ chỉ 100 lịch sử gần nhất
        if len(self.user_history) > 100:
            self.user_history.pop(0)
        
        # Học các mẫu mới từ ý định và thực thể
        intents = analysis.get("intent", {})
        entities = analysis.get("entities", {})
        
        # Nếu có ý định rõ ràng, học từ các từ khóa liên quan
        if intents:
            main_intent = self._get_main_intent(analysis)
            keywords = analysis.get("keywords", [])
            
            # Cập nhật mẫu đã học cho ý định này
            if main_intent not in self.learned_patterns:
                self.learned_patterns[main_intent] = {
                    "keywords": [],
                    "phrases": [],
                    "count": 0
                }
            
            # Thêm từ khóa mới
            for keyword in keywords:
                if keyword not in self.learned_patterns[main_intent]["keywords"]:
                    self.learned_patterns[main_intent]["keywords"].append(keyword)
            
            # Thêm cụm từ mới
            normalized_text = analysis.get("normalized_text", "")
            if normalized_text and normalized_text not in self.learned_patterns[main_intent]["phrases"]:
                self.learned_patterns[main_intent]["phrases"].append(normalized_text)
            
            # Tăng số lần xuất hiện
            self.learned_patterns[main_intent]["count"] += 1
    
    def _apply_learned_patterns(self, text: str, intent_scores: Dict[str, float]):
        """Áp dụng các mẫu đã học để cải thiện phát hiện ý định"""
        # Kiểm tra các mẫu đã học
        for intent, pattern_data in self.learned_patterns.items():
            # Kiểm tra từ khóa đã học
            learned_keywords = pattern_data.get("keywords", [])
            keyword_matches = sum(1 for keyword in learned_keywords if keyword in text)
            
            # Kiểm tra cụm từ đã học
            learned_phrases = pattern_data.get("phrases", [])
            phrase_matches = sum(1 for phrase in learned_phrases if phrase in text)
            
            # Tính điểm dựa trên các mẫu đã học
            if keyword_matches > 0 or phrase_matches > 0:
                # Tính điểm học tập dựa trên số lần xuất hiện
                learning_weight = min(pattern_data.get("count", 0) / 10.0, 1.0)
                learned_score = (keyword_matches * 0.1 + phrase_matches * 0.2) * learning_weight
                
                # Cập nhật điểm ý định
                if intent in intent_scores:
                    intent_scores[intent] = min(intent_scores[intent] + learned_score, 1.0)
                else:
                    intent_scores[intent] = min(learned_score, 1.0)
        
        return intent_scores
    
    def detect_enhanced_intent(self, text: str) -> Dict[str, float]:
        """Phát hiện ý định được cải tiến với scoring system và học máy"""
        intent_scores = {}
        
        # Kiểm tra các pattern với trọng số khác nhau
        for intent, patterns in self.intent_patterns.items():
            max_score = 0.0
            pattern_matches = 0
            
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    pattern_matches += 1
                    # Scoring system cải tiến
                    base_score = 0.4
                    match_bonus = pattern_matches * 0.15
                    score = min(base_score + match_bonus, 1.0)
                    max_score = max(max_score, score)
            
            if max_score > 0:
                intent_scores[intent] = max_score
        
        # Xử lý đặc biệt cho các intent phức tạp
        if any(word in text for word in ["xóa", "hủy", "delete", "remove"]) and any(word in text for word in ["nhắc", "ghi chú", "lịch", "reminder"]):
            intent_scores["delete_reminder"] = 0.95
        
        if any(word in text for word in ["xem", "hiển thị", "list", "show"]) and any(word in text for word in ["nhắc", "ghi chú", "lịch", "reminder"]):
            intent_scores["list_reminder"] = 0.95
            
        # Áp dụng các mẫu đã học
        intent_scores = self._apply_learned_patterns(text, intent_scores)
            
        # Fallback mechanism
        if not intent_scores:
            # Phân tích dựa trên cấu trúc câu
            if "?" in text or text.endswith("không"):
                intent_scores["question"] = 0.6
            elif any(word in text for word in ["làm", "tạo", "giúp", "mở"]):
                intent_scores["command"] = 0.6
            else:
                intent_scores["unknown"] = 0.8
            
        return intent_scores
        
    def _load_enhanced_intent_patterns(self) -> Dict[str, List[str]]:
        """Tải các mẫu nhận diện ý định được cải tiến"""
        return {
            "question": [
                r"^(?:ai|bạn|trợ lý)\s+(?:có thể|biết|cho\s+(?:tôi|mình|tao|tớ)\s+(?:biết|xem))\s+",
                r"^(?:tôi|mình|tao|tớ)\s+(?:muốn|cần|thích)\s+(?:biết|xem|tìm)\s+",
                r"(?:là\s+(?:gì|sao|thế nào))",
                r"(?:như\s+thế\s+nào)",
                r"(?:ở\s+đâu)",
                r"(?:khi\s+nào)",
                r"(?:ai|người nào)\s+(?:là|đã|sẽ)",
                r"(?:tại\s+sao|vì\s+sao|tại\s+vì|vì|bởi\s+vì)",
                r"(?:thế\s+nào|ra\s+sao|như\s+thế\s+nào)",
                r"(?:có|không)\s+(?:phải|đúng|thật)\s+(?:là|không)",
                r"(?:mấy|bao\s+nhiêu)\s+(?:giờ|phút|giây|ngày|tháng|năm)",
                r"\?\s*$",  # Kết thúc bằng dấu hỏi
                r"(?:giải thích|giải thích cho tôi|giải thích giúp tôi)",
                r"(?:ý nghĩa|nghĩa của)",
                r"(?:có thể cho tôi biết|có thể giải thích)",
                r"(?:làm sao|làm thế nào)\s+(?:để|có thể)"
            ],
            "command": [
                r"^(?:hãy|vui\s+lòng)\s+",
                r"^(?:tôi|mình|tao|tớ)\s+(?:muốn|cần|thích)\s+(?:bạn|trợ lý)\s+",
                r"^(?:giúp|giúp\s+(?:tôi|mình|tao|tớ))\s+",
                r"^(?:làm|tạo|viết|tính|tìm|mở|đóng|lưu|xóa)\s+",
                r"^(?:cho\s+(?:tôi|mình|tao|tớ)\s+(?:xem|biết))\s+",
                r"^(?:khởi động|chạy|start|run|execute)",
                r"(?:thực hiện|thực thi|chạy)\s+(?:ứng dụng|chương trình)",
                r"(?:cài đặt|cấu hình|thiết lập)\s+",
                r"(?:cập nhật|sửa đổi|thay đổi)\s+"
            ],
            "reminder": [
                r"(?:nhắc|nhắc nhở|remind|reminder)\s+(?:tôi|mình|tao|tớ)",
                r"(?:đặt|tạo|thêm)\s+(?:nhắc nhở|lịch|reminder)",
                r"(?:lên lịch|schedule)\s+",
                r"(?:ghi chú|note)\s+(?:về|cho|rằng)",
                r"(?:nhớ|remember)\s+(?:rằng|là|that)",
                r"(?:báo thức|alarm)\s+(?:lúc|vào lúc)",
                r"(?:lịch trình|schedule)\s+(?:cho|của)",
                r"(?:sự kiện|event)\s+(?:sắp tới|tiếp theo)"
            ],
            "delete_reminder": [
                r"(?:xóa|hủy|loại bỏ|delete|remove)\s+(?:nhắc nhở|lịch|reminder|ghi chú)",
                r"(?:bỏ|gỡ)\s+(?:nhắc nhở|lịch|reminder)",
                r"(?:huỷ|cancel)\s+(?:lịch|appointment|meeting)",
                r"(?:không\s+cần|bỏ qua)\s+(?:nhắc nhở|reminder)",
                r"(?:xóa\s+bỏ|xóa\s+hết)\s+(?:tất cả|toàn bộ)\s+(?:nhắc nhở|lịch)",
                r"(?:dọn dẹp|clear)\s+(?:lịch|nhắc nhở)"
            ],
            "list_reminder": [
                r"(?:xem|hiển thị|show|list)\s+(?:nhắc nhở|lịch|reminder)",
                r"(?:có\s+(?:gì|những\s+gì|nhắc nhở\s+nào))",
                r"(?:danh sách|list)\s+(?:nhắc nhở|lịch|reminder)",
                r"(?:kiểm tra|check)\s+(?:lịch|calendar|schedule)",
                r"(?:xem\s+lại|xem\s+lại\s+các)\s+(?:sự kiện|lịch trình)",
                r"(?:nhắc nhở\s+gần\s+đây|nhắc nhở\s+sắp\s+tới)"
            ],
            "greeting": [
                r"^(?:xin\s+chào|chào|hello|hi|hey|good\s+morning|good\s+afternoon|good\s+evening)\s*$",
                r"^(?:chào\s+buổi\s+(?:sáng|trưa|chiều|tối))\s*$",
                r"^(?:chào\s+mừng|welcome)\s+(?:bạn|quay lại)",
                r"^(?:buổi\s+sáng|buổi\s+trưa|buổi\s+chiều|buổi\s+tối)\s+(?:tốt lành|tốt|đẹp trời)"
            ],
            "farewell": [
                r"^(?:tạm\s+biệt|goodbye|bye|see\s+you|hẹn\s+gặp\s+lại)\s*$",
                r"^(?:chúc\s+(?:ngủ\s+ngon|ngủ\s+ngon|ngon\s+giấc))\s*$",
                r"^(?:tạm\s+tạm|bye\s+bye|tạm\s+biệt\s+tạm\s+thời)\s*$",
                r"^(?:đi\s+ngủ|ngủ\s+đi|đi\s+nghỉ)\s+(?:rồi|đây)"
            ],
            "thanks": [
                r"^(?:cảm\s+ơn|thank|thanks|thank\s+you|cám\s+ơn)\s*",
                r"^(?:cảm\s+ơn\s+(?:bạn|trợ lý|nhiều|rất|vô cùng))\s*",
                r"^(?:rất\s+biết\s+ơn|biết\s+ơn|cảm\s+kích)\s*",
                r"^(?:tuyệt\s+vời|tốt\s+lắm|hay\s+lắm)\s+(?:cảm\s+ơn)"
            ],
            "apology": [
                r"^(?:xin\s+lỗi|sorry|i'm\s+sorry|i\s+apologize)\s*",
                r"^(?:tôi|mình|tao|tớ)\s+(?:xin\s+lỗi)\s*",
                r"^(?:rất\s+xin\s+lỗi|thành\s+thật\s+xin\s+lỗi|xin\s+lỗi\s+nhiều)\s*",
                r"^(?:xin\s+lỗi\s+vì|lỗi\s+của\s+tôi)"
            ],
            "ai_enhancement": [
                r"(?:trí\s+tuệ\s+nhân\s+tạo|ai|trí\s+tuệ\s+máy\s+tính)",
                r"(?:học\s+máy|học\s+sâu|machine\s+learning|deep\s+learning)",
                r"(?:dự\s+đoán|gợi\s+ý|dự\s+báo)",
                r"(?:học\s+từ|tự\s+học|cải\s+thiện)",
                r"(?:thông\s+minh|hơn|nâng\s+cấp)"
            ]
        }
    
    def _load_entity_patterns(self) -> Dict[str, List[str]]:
        """Tải các mẫu nhận diện thực thể"""
        return {
            "date": [
                r"(?:ngày|hôm)\s+(?:nay|mai|kia|mốt)",
                r"(?:tuần|tháng|năm)\s+(?:này|sau|trước|tới|qua)",
                r"(?:\d{1,2})[-/](?:\d{1,2})(?:[-/](?:\d{2,4}))?",
                r"(?:thứ\s+(?:hai|ba|tư|năm|sáu|bảy)|chủ\s+nhật)"
            ],
            "time": [
                r"(?:\d{1,2})\s*(?:giờ|h|:|g)\s*(?:\d{1,2})?\s*(?:phút|p|')?",
                r"(?:sáng|trưa|chiều|tối|đêm|khuya)",
                r"(?:bây\s+giờ|hiện\s+tại|lúc\s+này)"
            ],
            "person": [
                r"(?:anh|chị|cô|chú|bác|ông|bà)\s+[A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ][a-zàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]*",
                r"(?:Mr\.|Mrs\.|Ms\.|Dr\.)\s+[A-Z][a-z]*"
            ],
            "location": [
                r"(?:tại|ở|trong|ngoài|gần|xa)\s+(?:[A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ][a-zàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]*)",
                r"(?:thành\s+phố|tỉnh|quận|huyện|phường|xã|đường|phố)\s+(?:[A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ][a-zàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]*)",
                r"(?:văn phong|office|phòng\s+họp|meeting\s+room|hội trường|auditorium)"
            ],
            "number": [
                r"\d+(?:[,.\s]\d+)*(?:\s*(?:triệu|nghìn|tỷ|trăm|chục))?",
                r"(?:một|hai|ba|bốn|năm|sáu|bảy|tám|chín|mười)(?:\s+(?:mười|mươi|trăm|nghìn|triệu|tỷ))*",
                r"(?:vài|nhiều|ít|đôi|cặp|tá|chục)"
            ],
            "priority": [
                r"(?:quan\s+trọng|ưu\s+tiên|khẩn\s+cấp|urgent|important|high|medium|low)",
                r"(?:rất\s+quan\s+trọng|cực\s+kỳ\s+quan\s+trọng|critical)"
            ],
            "duration": [
                r"(?:\d+)\s+(?:phút|giờ|ngày|tuần|tháng|năm)",
                r"(?:nửa|một\s+nửa)\s+(?:phút|giờ|ngày|tuần|tháng|năm)",
                r"(?:từ|trong\s+vòng|khoảng|xấp xỉ)\s+(?:\d+)\s+(?:phút|giờ|ngày)"
            ]
        }
    
    def _load_enhanced_sentiment_words(self) -> Dict[str, float]:
        """Tải từ điển cảm xúc được mở rộng"""
        positive = {
            # Cơ bản
            "tốt": 0.8, "hay": 0.7, "tuyệt": 0.9, "tuyệt vời": 1.0, "xuất sắc": 1.0,
            "thích": 0.7, "yêu": 0.9, "thú vị": 0.6, "hài lòng": 0.8, "vui": 0.7,
            "hạnh phúc": 0.9, "hài hước": 0.6, "dễ chịu": 0.5, "thoải mái": 0.6,
            "đẹp": 0.7, "xinh": 0.6, "đáng yêu": 0.8, "thông minh": 0.7,
            "nhanh": 0.6, "hiệu quả": 0.7, "chính xác": 0.8, "đúng": 0.7,
            # Mở rộng
            "hoàn hảo": 1.0, "tuyệt vời": 1.0, "ấn tượng": 0.8, "tài giỏi": 0.9,
            "cool": 0.7, "awesome": 0.9, "amazing": 1.0, "excellent": 1.0,
            "fantastic": 1.0, "wonderful": 0.9, "great": 0.8, "good": 0.7,
            "nice": 0.6, "fine": 0.5, "ok": 0.3, "okay": 0.3,
            "hữu ích": 0.8, "tiện lợi": 0.7, "thuận tiện": 0.6, "dễ dàng": 0.6
        }
        
        negative = {
            # Cơ bản  
            "tệ": -0.8, "kém": -0.7, "dở": -0.6, "chán": -0.5, "buồn": -0.6,
            "khó chịu": -0.7, "bực": -0.8, "giận": -0.9, "ghét": -0.9, "sợ": -0.7,
            "lo": -0.5, "lo lắng": -0.6, "thất vọng": -0.8, "tồi": -0.7,
            "chậm": -0.6, "sai": -0.7, "lỗi": -0.8, "hỏng": -0.9,
            "xấu": -0.7, "kinh khủng": -0.9, "tồi tệ": -1.0, "khủng khiếp": -1.0,
            # Mở rộng
            "thất bại": -0.9, "thua": -0.7, "không tốt": -0.6, "không hay": -0.5,
            "boring": -0.5, "bad": -0.7, "terrible": -0.9, "awful": -0.9,
            "horrible": -1.0, "disgusting": -1.0, "hate": -0.9, "angry": -0.8,
            "sad": -0.6, "disappointed": -0.8, "frustrated": -0.7, "annoyed": -0.6,
            "phức tạp": -0.4, "khó khăn": -0.6, "rắc rối": -0.5, "phiền phức": -0.5
        }
        
        # Kết hợp từ điển
        sentiment_dict = {}
        sentiment_dict.update(positive)
        sentiment_dict.update(negative)
        return sentiment_dict
    
    def _load_synonyms(self) -> Dict[str, List[str]]:
        """Tải từ điển từ đồng nghĩa"""
        return {
            "xóa": ["hủy", "loại bỏ", "gỡ bỏ", "remove", "delete", "xoá"],
            "tạo": ["làm", "tạo ra", "thiết lập", "create", "make", "build"],
            "xem": ["hiển thị", "liệt kê", "kiểm tra", "show", "view", "list", "display"],
            "nhắc nhở": ["reminder", "ghi chú", "note", "lịch", "calendar", "sự kiện", "event"],
            "mở": ["khởi động", "chạy", "start", "open", "launch", "run"],
            "giờ": ["thời gian", "time", "hour"],
            "ngày mai": ["tomorrow", "mai"],
            "hôm nay": ["today", "nay"],
            "tuần này": ["this week"],
            "tháng này": ["this month"],
            "quan trọng": ["important", "ưu tiên", "priority", "urgent", "khẩn cấp"],
            "cuộc họp": ["meeting", "họp", "hội nghị", "conference"],
            "công việc": ["work", "task", "job", "nhiệm vụ", "việc"],
            "tính toán": ["calculate", "tính", "compute", "math"]
        }

    def analyze_text(self, text: str) -> Dict[str, Any]:
        """Phân tích văn bản đầu vào và trả về kết quả phân tích"""
        text = text.lower().strip()
        
        # Kết quả phân tích
        analysis = {
            "intent": self.detect_intent(text),
            "entities": self.extract_entities(text),
            "sentiment": self.analyze_sentiment(text),
            "keywords": self.extract_keywords(text),
            "normalized_text": self.normalize_text(text),
            "reminder_action": self.analyze_reminder_action(text)
        }
        
        return analysis
        
    def detect_enhanced_intent(self, text: str) -> Dict[str, float]:
        """Phát hiện ý định được cải tiến với scoring system"""
        intent_scores = {}
        
        # Kiểm tra các pattern với trọng số khác nhau
        for intent, patterns in self.intent_patterns.items():
            max_score = 0.0
            pattern_matches = 0
            
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    pattern_matches += 1
                    # Scoring system cải tiến
                    base_score = 0.4
                    match_bonus = pattern_matches * 0.15
                    score = min(base_score + match_bonus, 1.0)
                    max_score = max(max_score, score)
            
            if max_score > 0:
                intent_scores[intent] = max_score
        
        # Xử lý đặc biệt cho các intent phức tạp
        if any(word in text for word in ["xóa", "hủy", "delete", "remove"]) and any(word in text for word in ["nhắc", "ghi chú", "lịch", "reminder"]):
            intent_scores["delete_reminder"] = 0.95
        
        if any(word in text for word in ["xem", "hiển thị", "list", "show"]) and any(word in text for word in ["nhắc", "ghi chú", "lịch", "reminder"]):
            intent_scores["list_reminder"] = 0.95
            
        # Fallback mechanism
        if not intent_scores:
            # Phân tích dựa trên cấu trúc câu
            if "?" in text or text.endswith("không"):
                intent_scores["question"] = 0.6
            elif any(word in text for word in ["làm", "tạo", "giúp", "mở"]):
                intent_scores["command"] = 0.6
            else:
                intent_scores["unknown"] = 0.8
            
        return intent_scores
    
    def extract_enhanced_entities(self, text: str) -> Dict[str, List[str]]:
        """Trích xuất các thực thể với post-processing"""
        entities = {}
        
        for entity_type, patterns in self.entity_patterns.items():
            matches = []
            for pattern in patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    entity_text = match.group(0).strip()
                    # Post-processing: filter out short or invalid entities
                    if len(entity_text) > 1 and entity_text not in ["của", "trong", "với", "và", "là"]:
                        matches.append(entity_text)
            
            if matches:
                # Remove duplicates while preserving order
                entities[entity_type] = list(dict.fromkeys(matches))
        
        return entities
    
    def analyze_enhanced_sentiment(self, text: str) -> Dict[str, float]:
        """Phân tích cảm xúc cải tiến với context awareness"""
        words = re.findall(r'\b\w+\b', text.lower())
        phrases = []
        
        # Tạo các cụm từ 2-3 từ liên tiếp
        for i in range(len(words) - 1):
            phrases.append(words[i] + " " + words[i+1])
            if i < len(words) - 2:
                phrases.append(words[i] + " " + words[i+1] + " " + words[i+2])
        
        # Tính điểm cảm xúc với weight khác nhau
        score = 0.0
        count = 0
        confidence = 0.0
        
        # Kiểm tra cụm từ trước (weight cao hơn)
        for phrase in phrases:
            if phrase in self.sentiment_words:
                weight = 1.5  # Cụm từ có trọng số cao hơn
                score += self.sentiment_words[phrase] * weight
                confidence += abs(self.sentiment_words[phrase]) * weight
                count += weight
        
        # Kiểm tra từng từ
        for word in words:
            if word in self.sentiment_words:
                score += self.sentiment_words[word]
                confidence += abs(self.sentiment_words[word])
                count += 1
        
        # Xử lý negation (phủ định)
        negation_words = ["không", "chẳng", "chả", "đâu", "not", "no", "never"]
        has_negation = any(neg in words for neg in negation_words)
        if has_negation and score != 0:
            score *= -0.8  # Đảo ngược và giảm intensity
        
        # Xử lý intensifiers (từ nhấn mạnh)
        intensifiers = {"rất": 1.3, "cực": 1.5, "vô cùng": 1.4, "very": 1.3, "really": 1.2, "extremely": 1.5}
        for intensifier, multiplier in intensifiers.items():
            if intensifier in words and score != 0:
                score *= multiplier
                confidence *= multiplier
                break
        
        # Tính toán kết quả
        if count > 0:
            avg_score = score / count
            confidence = min(confidence / count, 1.0)
        else:
            avg_score = 0.0
            confidence = 0.0
            
        sentiment = {
            "score": avg_score,
            "confidence": confidence,
            "label": "positive" if avg_score > 0.15 else "negative" if avg_score < -0.15 else "neutral"
        }
        
        return sentiment
    
    def extract_smart_keywords(self, text: str) -> List[str]:
        """Trích xuất từ khóa thông minh với frequency analysis"""
        # Chuẩn hóa text
        text = re.sub(r'[^\w\s\u00C0-\u024F\u1E00-\u1EFF]', ' ', text.lower())
        words = text.split()
        
        # Extended stopwords list
        stopwords = {
            "và", "hoặc", "là", "của", "từ", "với", "các", "những", "một", "có", "không", 
            "được", "trong", "đến", "cho", "về", "để", "theo", "tại", "bởi", "vì", "nếu", 
            "khi", "mà", "như", "thì", "nhưng", "tôi", "bạn", "anh", "chị", "họ", "chúng", 
            "mình", "này", "đó", "đây", "kia", "thế", "vậy", "rồi", "sẽ", "đã", "đang",
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", 
            "with", "by", "from", "up", "about", "into", "through", "during", "before", 
            "after", "above", "below", "between", "among", "is", "are", "was", "were", 
            "be", "been", "being", "have", "has", "had", "do", "does", "did", "will", 
            "would", "could", "should", "may", "might", "must", "can", "shall"
        }
        
        # Filter words và tính frequency
        filtered_words = [word for word in words if word not in stopwords and len(word) > 2]
        word_freq = Counter(filtered_words)
        
        # Lấy top keywords based on frequency và length
        keywords = []
        for word, freq in word_freq.most_common():
            # Bonus cho từ dài hơn và frequency cao
            score = freq * (len(word) / 5.0)
            if score >= 1.0:  # Threshold
                keywords.append(word)
            
            if len(keywords) >= 10:  # Limit số keywords
                break
        
        return keywords
    
    def _get_main_intent(self, analysis: Dict[str, Any]) -> str:
        """Xác định ý định chính từ analysis results"""
        intents = analysis.get("intent", {})
        if not intents:
            return "unknown"
        
        # Sắp xếp theo score và lấy intent cao nhất
        sorted_intents = sorted(intents.items(), key=lambda x: x[1], reverse=True)
        return sorted_intents[0][0]
    
    def _is_reminder_related(self, command: str, analysis: Dict[str, Any]) -> bool:
        """Kiểm tra xem lệnh có liên quan đến reminder hay không"""
        # Kiểm tra từ khóa trực tiếp
        reminder_keywords = ["nhắc", "nhắc nhở", "reminder", "ghi chú", "lịch", "schedule", "calendar"]
        if any(keyword in command.lower() for keyword in reminder_keywords):
            return True
        
        # Kiểm tra intent
        main_intent = self._get_main_intent(analysis)
        if main_intent in ["reminder", "delete_reminder", "list_reminder"]:
            return True
        
        # Kiểm tra reminder_action
        reminder_action = analysis.get("reminder_action", {})
        if reminder_action.get("action_type"):
            return True
        
        return False
    
    def _update_context(self, command: str, analysis: Dict[str, Any]):
        """Cập nhật context memory"""
        context_entry = {
            "command": command,
            "intent": self._get_main_intent(analysis),
            "entities": analysis.get("entities", {}),
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        self.context_memory.append(context_entry)
        
        # Giữ chỉ 10 context entries gần nhất
        if len(self.context_memory) > 10:
            self.context_memory.pop(0)
    
    def _calculate_context_score(self, text: str, analysis: Dict[str, Any]) -> float:
        """Tính điểm relevance dựa trên context"""
        if not self.context_memory:
            return 0.0
        
        # Kiểm tra similarity với các lệnh trước đó
        current_keywords = set(analysis.get("keywords", []))
        total_score = 0.0
        
        for context in self.context_memory[-3:]:  # Chỉ xét 3 context gần nhất
            context_keywords = set()
            for entity_list in context.get("entities", {}).values():
                context_keywords.update(entity_list)
            
            # Tính Jaccard similarity
            if current_keywords or context_keywords:
                intersection = len(current_keywords.intersection(context_keywords))
                union = len(current_keywords.union(context_keywords))
                similarity = intersection / union if union > 0 else 0
                total_score += similarity
        
        return min(total_score / 3, 1.0) if self.context_memory else 0.0
    
    def _assess_complexity(self, text: str, analysis: Dict[str, Any]) -> str:
        """Đánh giá độ phức tạp của command"""
        word_count = len(text.split())
        entity_count = sum(len(entities) for entities in analysis.get("entities", {}).values())
        intent_count = len(analysis.get("intent", {}))
        
        complexity_score = word_count * 0.3 + entity_count * 0.5 + intent_count * 0.2
        
        if complexity_score < 3:
            return "simple"
        elif complexity_score < 7:
            return "medium"
        else:
            return "complex"
    
    def _calculate_confidence(self, analysis: Dict[str, Any]) -> float:
        """Tính confidence score cho analysis"""
        intents = analysis.get("intent", {})
        entities = analysis.get("entities", {})
        sentiment = analysis.get("sentiment", {})
        
        # Intent confidence
        intent_conf = max(intents.values()) if intents else 0.0
        
        # Entity confidence (based on count)
        entity_conf = min(len(entities) * 0.2, 1.0)
        
        # Sentiment confidence
        sentiment_conf = sentiment.get("confidence", 0.0) if sentiment else 0.0
        
        # Weighted average
        overall_confidence = (intent_conf * 0.5 + entity_conf * 0.3 + sentiment_conf * 0.2)
        
        return min(overall_confidence, 1.0)
    
    def _is_question(self, analysis: Dict[str, Any]) -> bool:
        """Kiểm tra xem phân tích có biểu thị một câu hỏi hay không"""
        # Kiểm tra intent
        intents = analysis.get("intent", {})
        if "question" in intents and intents["question"] > 0.5:
            return True
        
        # Kiểm tra các từ khóa câu hỏi đặc trưng trong văn bản chuẩn hóa
        text = analysis.get("normalized_text", "").lower()
        question_indicators = ["là gì", "là ai", "ở đâu", "bao nhiêu", "thế nào", "tại sao", "khi nào", "ai là", "?", "gì", "nào"]
        return any(indicator in text for indicator in question_indicators)
    
    def _extract_search_query(self, command: str, analysis: Dict[str, Any]) -> str:
        """Trích xuất truy vấn tìm kiếm từ lệnh và phân tích"""
        # Lấy văn bản đã chuẩn hóa
        normalized_text = analysis.get("normalized_text", command)
        
        # Với các câu hỏi, thường tốt nhất là giữ nguyên cấu trúc câu hỏi nhưng loại bỏ một số từ không cần thiết
        if self._is_question(analysis):
            # Loại bỏ các từ không cần thiết cho tìm kiếm nhưng giữ cấu trúc câu hỏi
            stop_words = ["tôi", "bạn", "mình", "tao", "tớ", "chúng ta", "họ", "các bạn"]
            query_words = [word for word in normalized_text.split() if word not in stop_words]
            query = " ".join(query_words)
            
            # Đảm bảo truy vấn không quá dài
            if len(query) > 100:
                query = query[:100]
                
            return query.strip()
        
        # Nếu không phải câu hỏi, tiếp tục với logic cũ
        entities = analysis.get("entities", {})
        keywords = analysis.get("keywords", [])
        
        # Ưu tiên các loại thực thể quan trọng cho tìm kiếm
        priority_entities = ["person", "location", "date", "time"]
        search_terms = []
        
        # Thêm các thực thể ưu tiên vào truy vấn
        for entity_type in priority_entities:
            if entity_type in entities:
                search_terms.extend(entities[entity_type])
         
        # Thêm các từ khóa vào truy vấn
        search_terms.extend(keywords[:5])  # Giới hạn số lượng từ khóa
         
        # Loại bỏ các từ trùng lặp và giữ lại tối đa 7 từ (độ dài tối ưu cho tìm kiếm)
        unique_terms = list(dict.fromkeys(search_terms))  # Loại bỏ trùng lặp nhưng giữ thứ tự
        query_terms = unique_terms[:7]
         
        # Tạo truy vấn từ các từ đã chọn
        if query_terms:
            query = " ".join(query_terms)
        else:
            # Nếu không có từ nào, sử dụng văn bản chuẩn hóa
            query = normalized_text
        
        # Loại bỏ các từ không cần thiết cho tìm kiếm
        stop_words = ["là", "của", "trong", "với", "và", "hoặc", "có", "được", "bởi", "tại", "vì", "nếu", "khi", "mà", "như", "thì", "nhưng"]
        query_words = [word for word in query.split() if word not in stop_words]
        query = " ".join(query_words)
        
        # Nếu truy vấn quá ngắn, sử dụng lại lệnh gốc (đã chuẩn hóa)
        if len(query) < 3:
            # Loại bỏ các từ không cần thiết khỏi lệnh gốc
            command_words = [word for word in normalized_text.split() if word not in stop_words]
            query = " ".join(command_words)
             
        # Đảm bảo truy vấn không quá dài
        if len(query) > 100:
            query = query[:100]
            
        return query.strip()
    
    def _format_analysis_result(self, analysis: Dict[str, Any]) -> str:
        """Format detailed analysis results"""
        result = "🧠 Kết quả phân tích ngôn ngữ cải tiến:\n\n"
        
        # Intent với confidence
        intents = analysis.get("intent", {})
        if intents:
            result += "🎯 Ý định: "
            sorted_intents = sorted(intents.items(), key=lambda x: x[1], reverse=True)
            intent_name = sorted_intents[0][0]
            intent_score = sorted_intents[0][1]
            
            intent_map = {
                "question": "Câu hỏi",
                "command": "Yêu cầu/Mệnh lệnh",
                "reminder": "Tạo nhắc nhở",
                "delete_reminder": "Xóa nhắc nhở",
                "list_reminder": "Xem nhắc nhở",
                "greeting": "Lời chào",
                "farewell": "Lời tạm biệt",
                "thanks": "Lời cảm ơn",
                "apology": "Lời xin lỗi",
                "unknown": "Không xác định"
            }
            result += f"{intent_map.get(intent_name, intent_name)} ({intent_score:.2f})\n\n"
        
        # Sentiment với confidence
        sentiment = analysis.get("sentiment", {})
        if sentiment:
            result += "😊 Cảm xúc: "
            sentiment_map = {
                "positive": "Tích cực",
                "negative": "Tiêu cực", 
                "neutral": "Trung tính"
            }
            label = sentiment_map.get(sentiment.get('label'), sentiment.get('label', 'Trung tính'))
            score = sentiment.get('score', 0)
            confidence = sentiment.get('confidence', 0)
            result += f"{label} (điểm: {score:.2f}, tin cậy: {confidence:.2f})\n\n"
        
        # Entities
        entities = analysis.get("entities", {})
        if entities:
            result += "🏷️ Thực thể:\n"
            entity_map = {
                "date": "Ngày tháng",
                "time": "Thời gian",
                "person": "Người",
                "location": "Địa điểm",
                "number": "Số",
                "priority": "Ưu tiên",
                "duration": "Thời lượng"
            }
            for entity_type, entity_list in entities.items():
                result += f"  - {entity_map.get(entity_type, entity_type)}: {', '.join(entity_list)}\n"
            result += "\n"
        
        # Keywords
        keywords = analysis.get("keywords", [])
        if keywords:
            result += f"🔑 Từ khóa: {', '.join(keywords[:8])}\n\n"  # Limit to 8 keywords
        
        # Advanced metrics
        context_score = analysis.get("context_score", 0)
        complexity = analysis.get("complexity", "unknown")
        confidence = analysis.get("confidence", 0)
        
        result += f"📊 Phân tích nâng cao:\n"
        result += f"  - Điểm ngữ cảnh: {context_score:.2f}\n"
        result += f"  - Độ phức tạp: {complexity}\n"
        result += f"  - Độ tin cậy tổng thể: {confidence:.2f}\n\n"
        
        # Normalized text
        result += f"📝 Văn bản chuẩn hóa: {analysis.get('normalized_text', '')}"
        
        return result
        
    def analyze_reminder_action(self, text: str) -> Dict[str, Any]:
        """Phân tích hành động liên quan đến nhắc nhở và ghi chú"""
        result = {
            "action_type": None,
            "reminder_id": None,
            "reminder_content": None,
            "time_info": None
        }
        
        # Xác định loại hành động
        if any(word in text for word in ["xóa", "hủy", "loại bỏ", "bỏ", "xoá", "huỷ", "gỡ bỏ"]):
            result["action_type"] = "delete"
        elif any(word in text for word in ["thêm", "tạo", "đặt", "lên lịch", "nhắc"]):
            result["action_type"] = "add"
        elif any(word in text for word in ["xem", "hiển thị", "liệt kê", "kiểm tra", "có gì", "có những"]):
            result["action_type"] = "list"
        elif any(word in text for word in ["cập nhật", "sửa", "chỉnh sửa", "thay đổi"]):
            result["action_type"] = "update"
        
        # Tìm ID nhắc nhở
        id_match = re.search(r'id[:\s]*(\d+)', text, re.IGNORECASE)
        if id_match:
            result["reminder_id"] = id_match.group(1)
        
        # Tìm nội dung nhắc nhở (sau các từ khóa hành động)
        if result["action_type"] in ["delete", "update"]:
            action_keywords = {
                "delete": ["xóa", "hủy", "loại bỏ", "bỏ", "xoá", "huỷ", "gỡ bỏ"],
                "update": ["cập nhật", "sửa", "chỉnh sửa", "thay đổi"]
            }
            
            for keyword in action_keywords[result["action_type"]]:
                if keyword in text:
                    parts = text.split(keyword, 1)
                    if len(parts) > 1:
                        content = parts[1].strip()
                        # Loại bỏ các từ không cần thiết
                        for word in ["nhắc nhở", "ghi chú", "lịch", "sự kiện", "giúp", "tôi", "cho", "của"]:
                            content = content.replace(word, "").strip()
                        
                        if content:
                            result["reminder_content"] = content
                            break
        
        # Tìm thông tin thời gian
        time_entities = self.extract_entities(text).get("date", []) + self.extract_entities(text).get("time", [])
        if time_entities:
            result["time_info"] = time_entities
        
        return result
    
    def detect_intent(self, text: str) -> Dict[str, float]:
        """Phát hiện ý định từ văn bản"""
        intent_scores = {}
        
        # Kiểm tra các pattern với trọng số khác nhau
        for intent, patterns in self.intent_patterns.items():
            max_score = 0.0
            pattern_matches = 0
            
            for pattern in patterns:
                if re.search(pattern, text):
                    pattern_matches += 1
                    score = 0.5 + (pattern_matches * 0.2)  # Tăng điểm theo số pattern khớp
                    max_score = max(max_score, min(score, 1.0))
            
            if max_score > 0:
                intent_scores[intent] = max_score
        
        # Xử lý đặc biệt cho các intent phức tạp
        if any(word in text for word in ["xóa", "hủy", "delete", "remove"]) and any(word in text for word in ["nhắc", "ghi chú", "lịch", "reminder"]):
            intent_scores["delete_reminder"] = 0.9
        
        if any(word in text for word in ["xem", "hiển thị", "list", "show"]) and any(word in text for word in ["nhắc", "ghi chú", "lịch", "reminder"]):
            intent_scores["list_reminder"] = 0.9
            
        # Nếu không phát hiện được ý định rõ ràng
        if not intent_scores:
            intent_scores["unknown"] = 1.0
            
        return intent_scores
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Trích xuất các thực thể từ văn bản"""
        entities = {}
        
        for entity_type, patterns in self.entity_patterns.items():
            matches = []
            for pattern in patterns:
                for match in re.finditer(pattern, text):
                    matches.append(match.group(0))
            
            if matches:
                entities[entity_type] = matches
        
        return entities
    
    def analyze_sentiment(self, text: str) -> Dict[str, float]:
        """Phân tích cảm xúc trong văn bản"""
        words = re.findall(r'\b\w+\b', text)
        phrases = []
        
        # Tạo các cụm từ 2 từ liên tiếp
        for i in range(len(words) - 1):
            phrases.append(words[i] + " " + words[i+1])
        
        # Tính điểm cảm xúc
        score = 0.0
        count = 0
        
        # Kiểm tra cụm từ trước
        for phrase in phrases:
            if phrase in self.sentiment_words:
                score += self.sentiment_words[phrase]
                count += 1
        
        # Kiểm tra từng từ
        for word in words:
            if word in self.sentiment_words:
                score += self.sentiment_words[word]
                count += 1
        
        # Xác định cảm xúc
        if count > 0:
            avg_score = score / count
        else:
            avg_score = 0.0
            
        sentiment = {
            "score": avg_score,
            "label": "positive" if avg_score > 0.1 else "negative" if avg_score < -0.1 else "neutral"
        }
        
        return sentiment
    
    def extract_keywords(self, text: str) -> List[str]:
        """Trích xuất từ khóa quan trọng từ văn bản"""
        # Loại bỏ dấu câu
        text = text.translate(str.maketrans("", "", string.punctuation))
        
        # Tách từ
        words = text.split()
        
        # Loại bỏ các từ dừng (stopwords)
        stopwords = ["và", "hoặc", "là", "của", "từ", "với", "các", "những", "một", "có", "không", 
                    "được", "trong", "đến", "cho", "về", "để", "theo", "tại", "bởi", "vì", "nếu", 
                    "khi", "mà", "như", "thì", "nhưng", "tôi", "bạn", "anh", "chị", "họ", "chúng", 
                    "mình", "này", "đó", "đây", "kia", "thế", "vậy"]
        
        keywords = [word for word in words if word not in stopwords and len(word) > 1]
        
        # Trả về danh sách từ khóa duy nhất
        return list(set(keywords))
    
    def normalize_text(self, text: str) -> str:
        """Chuẩn hóa văn bản"""
        # Loại bỏ khoảng trắng thừa
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Chuẩn hóa dấu câu
        text = re.sub(r'\s*([,.!?;:])\s*', r'\1 ', text)
        
        # Chuẩn hóa chữ hoa đầu câu
        sentences = re.split(r'([.!?]\s)', text)
        normalized_text = ""
        
        for i in range(0, len(sentences), 2):
            if i < len(sentences):
                sentence = sentences[i].strip()
                if sentence:
                    sentence = sentence[0].upper() + sentence[1:]
                    normalized_text += sentence
                
                if i + 1 < len(sentences):
                    normalized_text += sentences[i + 1]
        
        return normalized_text

# Singleton instance
_nlp_processor = None

def get_nlp_processor() -> EnhancedNLPProcessor:
    """Trả về instance của EnhancedNLPProcessor (singleton)"""
    global _nlp_processor
    if _nlp_processor is None:
        _nlp_processor = EnhancedNLPProcessor()
    return _nlp_processor

def analyze_user_input(text: str) -> Dict[str, Any]:
    """Phân tích đầu vào của người dùng với enhanced capabilities"""
    processor = get_nlp_processor()
    return processor.analyze_text_with_context(text)

def enhance_with_nlp(command: str) -> str:
    """Hàm chính để xử lý lệnh với NLP"""
    if not command:
        return "Vui lòng cung cấp văn bản để phân tích."
    
    # Phân tích văn bản
    analysis = analyze_user_input(command)
    
    # Tạo kết quả phân tích
    result = "📊 Kết quả phân tích ngôn ngữ:\n\n"
    
    # Ý định
    result += "🎯 Ý định: "
    intents = sorted(analysis["intent"].items(), key=lambda x: x[1], reverse=True)
    if intents:
        intent_name = intents[0][0]
        intent_map = {
            "question": "Câu hỏi",
            "command": "Yêu cầu/Mệnh lệnh",
            "greeting": "Lời chào",
            "farewell": "Lời tạm biệt",
            "thanks": "Lời cảm ơn",
            "apology": "Lời xin lỗi",
            "unknown": "Không xác định"
        }
        result += f"{intent_map.get(intent_name, intent_name)} ({intents[0][1]:.2f})\n"
    else:
        result += "Không xác định\n"
    
    # Cảm xúc
    sentiment = analysis["sentiment"]
    result += "😊 Cảm xúc: "
    sentiment_map = {
        "positive": "Tích cực",
        "negative": "Tiêu cực",
        "neutral": "Trung tính"
    }
    result += f"{sentiment_map.get(sentiment['label'], sentiment['label'])} ({sentiment['score']:.2f})\n"
    
    # Thực thể
    if analysis["entities"]:
        result += "🏷️ Thực thể:\n"
        entity_map = {
            "date": "Ngày tháng",
            "time": "Thời gian",
            "person": "Người",
            "location": "Địa điểm",
            "number": "Số"
        }
        for entity_type, entities in analysis["entities"].items():
            result += f"  - {entity_map.get(entity_type, entity_type)}: {', '.join(entities)}\n"
    
    # Từ khóa
    if analysis["keywords"]:
        result += "🔑 Từ khóa: " + ", ".join(analysis["keywords"]) + "\n"
    
    # Văn bản chuẩn hóa
    result += "📝 Văn bản chuẩn hóa: " + analysis["normalized_text"]
    
    return result