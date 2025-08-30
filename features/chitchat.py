import re
import unicodedata
from typing import List

# Keywords and patterns for casual small talk in Vietnamese
# Include both accented and unaccented/common-typed variants for robustness
keywords: List[str] = [
    # greetings
    "chào", "xin chào", "hello", "hi", "alo",
    # how are you
    "khỏe", "khoe", "dạo này", "sao rồi", "thế nào",
    # thanks
    "cảm ơn", "cam on", "thanks", "thank you",
    # goodbye
    "tạm biệt", "tam biet", "bye", "hẹn gặp",
    # identity / capability
    "bạn là ai", "ban la ai", "giới thiệu", "gioi thieu", "là gì", "la gi",
    # small talk topics
    "trò chuyện", "tro chuyen", "tâm sự", "tam su", "buồn", "vui",
    # jokes
    "đùa", "dua", "kể chuyện cười", "chuyện cười", "joke",
]

patterns: List[str] = [
    "xin chào",
    "bạn khỏe không",
    "ban khoe khong",
    "dạo này thế nào",
    "cam on ban",
    "cảm ơn bạn",
    "tạm biệt",
    "bạn là ai",
    "ban la ai",
    "kể chuyện cười",
    "kể một câu đùa",
    "noi chuyen voi toi",
]


def _strip_diacritics(s: str) -> str:
    try:
        return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    except Exception:
        return s


def _normalize(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r"\s+", " ", s)
    # best-effort fix common punctuation noise
    s = re.sub(r"[^\w\sáàảãạăắằẳẵặâấầẩẫậđéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵ]", " ", s)
    return s


def _match_any(text: str, words: List[str]) -> bool:
    t1 = _normalize(text)
    t2 = _strip_diacritics(t1)
    for w in words:
        w1 = _normalize(w)
        if w1 and (w1 in t1 or _strip_diacritics(w1) in t2):
            return True
    return False


def _select_reply(user_text: str) -> str:
    t = _normalize(user_text)
    t_no = _strip_diacritics(t)

    # Greetings
    if _match_any(t, ["xin chào", "chào", "hello", "hi", "alo", "chao ban"]):
        return "Chào bạn! Mình ở đây nè. Bạn muốn trò chuyện về điều gì?"

    # How are you / states
    if _match_any(t, ["khỏe không", "khoe khong", "dạo này thế nào", "the nao roi", "sao roi"]):
        return "Mình luôn sẵn sàng và cảm thấy ổn! Còn bạn thì sao?"

    # Thanks
    if _match_any(t, ["cảm ơn", "cam on", "thank"]):
        return "Không có gì đâu! Rất vui được giúp bạn."

    # Goodbye
    if _match_any(t, ["tạm biệt", "tam biet", "bye", "hẹn gặp", "hen gap"]):
        return "Tạm biệt bạn! Hẹn gặp lại nhé."

    # Identity / intro
    if _match_any(t, ["bạn là ai", "ban la ai", "giới thiệu", "gioi thieu", "ban lam gi", "la gi"]):
        return (
            "Mình là trợ lý giúp bạn làm việc nhanh hơn: xem thời tiết, mở ứng dụng, ghi nhớ, tính toán, "
            "và trò chuyện khi bạn cần. Cứ nói mình biết bạn muốn làm gì nhé!"
        )

    # Jokes
    if _match_any(t, ["đùa", "dua", "chuyện cười", "ke chuyen cuoi", "joke"]):
        return "Có một con vịt đi qua, con còn lại... đi sau. 😄 (Đùa nhẹ thôi nè)"

    # Mood/support
    if _match_any(t, ["buồn", "met moi", "stress", "chán", "chan"]):
        return (
            "Nghe có vẻ bạn đang không ổn. Mình luôn ở đây để lắng nghe. "
            "Bạn muốn tâm sự đôi chút hay làm điều gì đó thư giãn không?"
        )

    # Default small talk response
    return "Mình có thể trò chuyện cùng bạn. Bạn muốn nói về điều gì?"


def chitchat(command: str = "") -> str:
    """Handle casual conversation in Vietnamese."""
    return _select_reply(command or "")

