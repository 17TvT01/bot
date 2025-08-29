from features.nlp_processor import get_nlp_processor

def main():
    # Get the NLP processor instance
    nlp_processor = get_nlp_processor()
    
    print("=== Enhanced NLP Processor Demo ===\n")
    
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
    
    for command in test_commands:
        print(f"Input: {command}")
        result = nlp_processor.process_command(command)
        print(f"Output:\n{result}\n")
        print("-" * 50)
    
    # Demonstrate learning capabilities
    print("\n=== Learning Capabilities Demo ===\n")
    
    # First interaction with AI-related command
    print("First interaction with AI-related command:")
    command1 = "tôi muốn học cách sử dụng trí tuệ nhân tạo"
    print(f"Input: {command1}")
    result1 = nlp_processor.process_command(command1)
    print(f"Output:\n{result1}\n")
    print("-" * 50)
    
    # Check if patterns were learned
    print(f"Learned patterns: {list(nlp_processor.learned_patterns.keys())}\n")
    print("-" * 50)
    
    # Second interaction with similar command to see learning in action
    print("Second interaction with similar command:")
    command2 = "học cách dùng ai"
    print(f"Input: {command2}")
    result2 = nlp_processor.process_command(command2)
    print(f"Output:\n{result2}\n")
    print("-" * 50)
    
    # Show user history
    print(f"User interaction history count: {len(nlp_processor.user_history)}")

if __name__ == "__main__":
    main()
