from features.nlp_processor import get_nlp_processor

def main():
    # Get the NLP processor instance
    nlp_processor = get_nlp_processor()
    
    # Test commands to showcase enhanced NLP capabilities
    test_commands = [
        "xin chào",
        "tôi muốn xem nhắc nhở của mình",
        "xóa nhắc nhở",
        "trí tuệ nhân tạo",
        "là gì",
        "hẹn gặp vào ngày mai lúc 3 giờ",
        "Tôi rất vui với kết quả này!",
        "Làm thế nào để tôi có thể mở Notepad?",
        "Dự đoán lệnh cho tôi."
    ]
    
    print("=== Enhanced NLP Processor Demo ===\n")
    
    for command in test_commands:
        print(f"Input: {command}")
        result = nlp_processor.process_command(command)
        print(f"Output:\n{result}\n")
        print("-" * 50)

if __name__ == "__main__":
    main()
