import re
from typing import Tuple, Optional

keywords = ["tính", "cộng", "trừ", "nhân", "chia", "bằng", "kết quả"]

patterns = [
    "tính ... cộng ...",
    "cộng ... với ...",
    "... cộng ... bằng mấy",
    "tính ... trừ ...",
    "trừ ... cho ...",
    "... trừ ... bằng mấy",
    "tính ... nhân ...",
    "nhân ... với ...",
    "... nhân ... bằng mấy",
    "tính ... chia ...",
    "chia ... cho ...",
    "... chia ... bằng mấy",
    "kết quả của ... cộng ...",
    "kết quả của ... trừ ...",
    "kết quả của ... nhân ...",
    "kết quả của ... chia ..."
]

def extract_numbers_and_operator(text: str) -> Tuple[Optional[float], Optional[str], Optional[float]]:
    """
    Extracts numbers and operator from text.
    Returns tuple of (first_number, operator, second_number)
    """
    # Normalize spaces and lowercase
    text = ' ' + text.lower() + ' '
    
    # Extract numbers
    numbers = []
    number_matches = re.finditer(r'\d+(?:\.\d+)?', text)
    for match in number_matches:
        numbers.append(float(match.group()))
        
    if len(numbers) != 2:
        return None, None, None
        
    num1, num2 = numbers
    
    # Normalize text for easier matching
    text = text.lower()
    
    # Determine operator
    if any(word in text for word in ["cộng", "thêm", "với", "+"]):
        return num1, "+", num2
    elif any(word in text for word in ["trừ", "bớt", "-"]):
        return num1, "-", num2
    elif any(word in text for word in ["nhân", "x", "*"]):
        return num1, "*", num2
    elif any(word in text for word in ["chia", "/"]):
        return num1, "/", num2
    
    return None, None, None

def calculator(expression: str) -> str:
    """
    Performs a basic calculation from a natural language string.
    Examples: 
    - "tính 25 chia 5"
    - "7 nhân với 8 bằng mấy"
    - "kết quả của 10 chia 2 là bao nhiêu"
    """
    # Extract numbers and operator
    num1, op, num2 = extract_numbers_and_operator(expression)
    
    if num1 is None or op is None or num2 is None:
        return "Xin lỗi, tôi không hiểu phép tính này.\nVí dụ: 'tính 5 cộng 3' hoặc '10 chia 2 bằng mấy'"

    try:
        if op == '+':
            result = num1 + num2
        elif op == '-':
            result = num1 - num2
        elif op == '*':
            result = num1 * num2
        elif op == '/':
            if num2 == 0:
                return "Không thể chia cho số không."
            result = num1 / num2
        else:
            return "Toán tử không hợp lệ."

        # Format result nicely
        return f"Kết quả là: {result:.5f}" if result != int(result) else f"Kết quả là: {int(result)}"

    except (ValueError, IndexError):
        return "Phép tính không hợp lệ. Vui lòng thử lại với cú pháp đúng."
    except Exception as e:
        return f"Có lỗi xảy ra khi tính toán: {str(e)}"
