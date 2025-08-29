#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for verifying the search functionality in the NLP processor.
"""

import sys
import os

# Add the parent directory to the path so we can import the features module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from features.nlp_processor import get_nlp_processor

def test_search_functionality():
    """Test the search functionality with various queries."""
    processor = get_nlp_processor()
    
    # Test cases that should trigger search
    test_cases = [
        "Hồ Chí Minh là ai?",
        "Tháp Eiffel ở đâu?",
        "Chiều cao của núi Everest là bao nhiêu?",
        "Ai là người phát minh ra điện thoại?",
        "Thủ đô của Pháp là gì?"
    ]
    
    print("Testing search functionality...")
    print("=" * 50)
    
    for i, command in enumerate(test_cases, 1):
        print(f"\nTest {i}: {command}")
        print("-" * 30)
        
        # Analyze the command first to see what the analysis looks like
        analysis = processor.analyze_text_with_context(command)
        print(f"Analysis: {analysis}")
        
        # Check if search should be triggered
        should_search = processor._should_search_for_information(analysis)
        print(f"Should search: {should_search}")
        
        # If search should be triggered, show the search query
        if should_search:
            search_query = processor._extract_search_query(command, analysis)
            print(f"Search query: '{search_query}'")
        
        # Process the command
        result = processor.process_command(command)
        print(f"Result: {result}")
        print("-" * 30)
    
    # Test cases that should not trigger search
    non_search_cases = [
        "Xin chào",
        "Cảm ơn bạn",
        "Mấy giờ rồi?",
        "Tạm biệt",
        "Nhắc tôi ngày mai đi làm"
    ]
    
    print("\n\nTesting non-search functionality...")
    print("=" * 50)
    
    for i, command in enumerate(non_search_cases, 1):
        print(f"\nTest {i}: {command}")
        print("-" * 30)
        
        # Analyze the command first to see what the analysis looks like
        analysis = processor.analyze_text_with_context(command)
        print(f"Analysis: {analysis}")
        
        # Check if search should be triggered
        should_search = processor._should_search_for_information(analysis)
        print(f"Should search: {should_search}")
        
        # Process the command
        result = processor.process_command(command)
        print(f"Result: {result}")
        print("-" * 30)

if __name__ == "__main__":
    test_search_functionality()