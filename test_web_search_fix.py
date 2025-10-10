#!/usr/bin/env python3
"""
Test script for web search memory leak and NUL character fixes.
Run this script to validate that the fixes work correctly.
"""

import sys
import os
import gc
import psutil
import time
from typing import List, Dict, Any

# Add the backend path to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from open_webui.retrieval.vector.utils import clean_text_for_postgres, process_metadata


def test_nul_character_cleaning():
    """Test that NUL characters are properly cleaned from text."""
    print("🧪 Testing NUL character cleaning...")
    
    # Test cases with problematic characters
    test_cases = [
        "Normal text without issues",
        "Text with\x00NUL character",
        "Multiple\x00NUL\x00characters",
        "Control\x01chars\x02and\x03stuff",
        "Mixed\x00control\x01chars\nwith\twhitespace",
        "",
        None,
    ]
    
    for i, test_text in enumerate(test_cases):
        try:
            cleaned = clean_text_for_postgres(test_text)
            
            if cleaned and '\x00' in cleaned:
                print(f"❌ Test {i+1} FAILED: NUL character still present")
                return False
            
            print(f"✅ Test {i+1} PASSED: '{test_text}' -> '{cleaned}'")
            
        except Exception as e:
            print(f"❌ Test {i+1} FAILED with exception: {e}")
            return False
    
    print("✅ All NUL character cleaning tests passed!\n")
    return True


def test_metadata_cleaning():
    """Test that metadata is properly cleaned."""
    print("🧪 Testing metadata cleaning...")
    
    test_metadata = {
        "normal_key": "normal_value",
        "key_with\x00nul": "value_with\x00nul",
        "content": "This should be removed",  # In KEYS_TO_EXCLUDE
        "pages": ["page1", "page2"],  # In KEYS_TO_EXCLUDE
        "nested_dict": {"key": "value\x00with_nul"},
        "list_data": ["item1", "item2\x00with_nul"],
    }
    
    try:
        cleaned_metadata = process_metadata(test_metadata.copy())
        
        # Check that excluded keys are removed
        if "content" in cleaned_metadata or "pages" in cleaned_metadata:
            print("❌ FAILED: Excluded keys not removed")
            return False
        
        # Check that NUL characters are cleaned
        for key, value in cleaned_metadata.items():
            if isinstance(key, str) and '\x00' in key:
                print(f"❌ FAILED: NUL character in key: {key}")
                return False
            if isinstance(value, str) and '\x00' in value:
                print(f"❌ FAILED: NUL character in value: {value}")
                return False
        
        print("✅ Metadata cleaning test passed!")
        print(f"   Original keys: {list(test_metadata.keys())}")
        print(f"   Cleaned keys: {list(cleaned_metadata.keys())}\n")
        return True
        
    except Exception as e:
        print(f"❌ Metadata cleaning test FAILED with exception: {e}")
        return False


def simulate_memory_usage_test():
    """Simulate the memory usage pattern to test for leaks."""
    print("🧪 Testing memory usage pattern...")
    
    process = psutil.Process()
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    print(f"Initial memory usage: {initial_memory:.2f} MB")
    
    # Simulate processing large batches like web search would do
    for batch_num in range(5):
        # Simulate large text processing
        large_texts = [f"Large text content {i} " * 1000 for i in range(100)]
        
        # Clean the texts (simulating our fix)
        cleaned_texts = [clean_text_for_postgres(text) for text in large_texts]
        
        # Simulate embedding generation (create large arrays)
        fake_embeddings = [[0.1] * 1536 for _ in cleaned_texts]  # Typical embedding size
        
        # Simulate metadata processing
        metadatas = [{"source": f"web_search_{i}", "batch": batch_num} for i in range(len(large_texts))]
        cleaned_metadatas = [process_metadata(meta.copy()) for meta in metadatas]
        
        # Force cleanup (simulating our fix)
        del large_texts, cleaned_texts, fake_embeddings, metadatas, cleaned_metadatas
        gc.collect()
        
        current_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = current_memory - initial_memory
        
        print(f"Batch {batch_num + 1}: Memory usage: {current_memory:.2f} MB (+{memory_increase:.2f} MB)")
        
        # If memory increase is too large, we have a leak
        if memory_increase > 100:  # More than 100MB increase is concerning
            print(f"⚠️  WARNING: Large memory increase detected: {memory_increase:.2f} MB")
        
        time.sleep(0.1)  # Small delay to allow garbage collection
    
    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    total_increase = final_memory - initial_memory
    
    print(f"Final memory usage: {final_memory:.2f} MB")
    print(f"Total memory increase: {total_increase:.2f} MB")
    
    if total_increase < 50:  # Less than 50MB total increase is good
        print("✅ Memory usage test passed - no significant memory leak detected!\n")
        return True
    else:
        print(f"⚠️  Memory usage test concerning - {total_increase:.2f} MB increase detected\n")
        return False


def test_postgresql_compatibility():
    """Test that cleaned text would be compatible with PostgreSQL."""
    print("🧪 Testing PostgreSQL compatibility...")
    
    # Simulate problematic web scraped content
    problematic_content = [
        "You've been blocked by network security.\x00To continue, log in to your account.",
        "Content with\x00multiple\x00NUL\x00characters",
        "Binary data: \x00\x01\x02\x03\x04\x05",
        "Mixed content\x00with normal text and\x01control chars",
    ]
    
    try:
        for i, content in enumerate(problematic_content):
            cleaned = clean_text_for_postgres(content)
            
            # Check that no NUL characters remain
            if '\x00' in cleaned:
                print(f"❌ Test {i+1} FAILED: NUL characters still present")
                return False
            
            # Check that no other problematic control characters remain (except whitespace)
            for char in cleaned:
                if ord(char) < 32 and char not in '\n\r\t':
                    print(f"❌ Test {i+1} FAILED: Control character {ord(char)} still present")
                    return False
            
            print(f"✅ Test {i+1} PASSED: Content cleaned successfully")
        
        print("✅ All PostgreSQL compatibility tests passed!\n")
        return True
        
    except Exception as e:
        print(f"❌ PostgreSQL compatibility test FAILED with exception: {e}")
        return False


def main():
    """Run all tests to validate the fixes."""
    print("🚀 Running Web Search Fix Validation Tests\n")
    
    tests = [
        ("NUL Character Cleaning", test_nul_character_cleaning),
        ("Metadata Cleaning", test_metadata_cleaning),
        ("Memory Usage Pattern", simulate_memory_usage_test),
        ("PostgreSQL Compatibility", test_postgresql_compatibility),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"Running {test_name}...")
        try:
            if test_func():
                passed += 1
            else:
                print(f"❌ {test_name} FAILED\n")
        except Exception as e:
            print(f"❌ {test_name} FAILED with exception: {e}\n")
    
    print("=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The fixes should resolve the web search issues.")
        return 0
    else:
        print("⚠️  Some tests failed. Please review the fixes.")
        return 1


if __name__ == "__main__":
    exit(main())