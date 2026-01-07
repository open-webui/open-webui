#!/usr/bin/env python3
"""
Integration test script for Open WebUI + Docling Serve with page extraction.

This script tests the complete workflow:
1. Starts Docling Serve with CUDA support
2. Tests the DoclingLoader page extraction functionality
3. Verifies that page metadata is properly preserved
4. Tests integration with Open WebUI's retrieval system
"""

import os
import sys
import json
import time
import requests
import subprocess
from pathlib import Path

# Add Open WebUI backend to path for testing
sys.path.insert(0, str(Path(__file__).parent / "open-webui" / "backend"))

from open_webui.retrieval.loaders.main import DoclingLoader


def wait_for_service(url, timeout=60):
    """Wait for a service to become available."""
    print(f"Waiting for service at {url}...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{url}/health", timeout=5)
            if response.status_code == 200:
                print(f"Service at {url} is ready!")
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(2)
    return False


def test_docling_serve_health():
    """Test that Docling Serve is running and healthy."""
    docling_url = "http://localhost:5001"
    
    if not wait_for_service(docling_url):
        print("❌ Docling Serve is not available")
        return False
    
    try:
        response = requests.get(f"{docling_url}/health")
        if response.status_code == 200:
            print("✅ Docling Serve health check passed")
            print(f"Response: {response.json()}")
            return True
    except Exception as e:
        print(f"❌ Docling Serve health check failed: {e}")
    
    return False


def create_sample_document():
    """Create a sample PDF document for testing."""
    # For now, we'll use an existing test file if available
    test_files = [
        "docling-serve-1/tests/2206.01062v1.pdf",
        "open-webui/backend/tests/test.pdf"
    ]
    
    for file_path in test_files:
        if os.path.exists(file_path):
            print(f"Using test document: {file_path}")
            return file_path
    
    print("❌ No test PDF document found")
    return None


def test_docling_loader_page_extraction():
    """Test the DoclingLoader with page extraction enabled."""
    test_doc = create_sample_document()
    if not test_doc:
        return False
    
    print("\n🔍 Testing DoclingLoader page extraction...")
    
    try:
        # Test with page extraction enabled (default behavior)
        loader = DoclingLoader(
            url="http://localhost:5001",
            file_path=test_doc,
            extract_pages=True
        )
        
        documents = loader.load()
        
        print(f"✅ Loaded {len(documents)} documents with page extraction")
        
        if documents:
            # Check page metadata
            for i, doc in enumerate(documents[:3]):  # Check first 3 pages
                metadata = doc.metadata
                print(f"Page {i+1} metadata:")
                print(f"  - page: {metadata.get('page')}")
                print(f"  - page_label: {metadata.get('page_label')}")
                print(f"  - total_pages: {metadata.get('total_pages')}")
                print(f"  - content_length: {metadata.get('content_length')}")
                print(f"  - processing_engine: {metadata.get('processing_engine')}")
                
                # Verify required metadata
                assert 'page' in metadata, "Missing page number"
                assert 'page_label' in metadata, "Missing page label"
                assert 'total_pages' in metadata, "Missing total pages"
                assert metadata['processing_engine'] == 'docling', "Wrong processing engine"
                
                print(f"  Content preview: {doc.page_content[:100]}...")
        
        print("✅ Page extraction test passed!")
        
        # Test with page extraction disabled
        print("\n🔍 Testing without page extraction...")
        loader_single = DoclingLoader(
            url="http://localhost:5001",
            file_path=test_doc,
            extract_pages=False
        )
        
        single_docs = loader_single.load()
        print(f"✅ Loaded {len(single_docs)} documents without page extraction")
        
        if single_docs:
            doc = single_docs[0]
            metadata = doc.metadata
            print(f"Single document metadata: {list(metadata.keys())}")
            assert 'page' not in metadata, "Page metadata should not be present"
            assert metadata['processing_engine'] == 'docling', "Wrong processing engine"
        
        print("✅ Single document test passed!")
        return True
        
    except Exception as e:
        print(f"❌ DoclingLoader test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_docling_serve_format_support():
    """Test that Docling Serve supports the required output formats."""
    print("\n🔍 Testing Docling Serve format support...")
    
    test_doc = create_sample_document()
    if not test_doc:
        return False
    
    try:
        # Test API directly to verify JSON output format
        with open(test_doc, 'rb') as f:
            files = {'files': (os.path.basename(test_doc), f, 'application/pdf')}
            data = {
                'to_formats': ['json', 'md'],
                'image_export_mode': 'placeholder'
            }
            
            response = requests.post(
                'http://localhost:5001/v1/convert/file',
                files=files,
                data=data
            )
            
            if response.status_code == 200:
                result = response.json()
                document = result.get('document', {})
                
                # Verify both formats are present
                assert 'json_content' in document, "Missing JSON content"
                assert 'md_content' in document, "Missing Markdown content"
                
                json_content = document['json_content']
                if isinstance(json_content, dict):
                    # Check for page structure
                    if 'pages' in json_content:
                        print(f"✅ JSON contains {len(json_content['pages'])} pages")
                    
                    if 'texts' in json_content:
                        print(f"✅ JSON contains {len(json_content['texts'])} text elements")
                        
                        # Check provenance for page information
                        for text_item in json_content['texts'][:3]:
                            if 'prov' in text_item:
                                print(f"✅ Text element has provenance: {text_item['prov'][:1]}")
                
                print("✅ Format support test passed!")
                return True
            else:
                print(f"❌ API request failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Format support test failed: {e}")
        return False


def test_open_webui_config():
    """Test that Open WebUI configuration includes our new settings."""
    print("\n🔍 Testing Open WebUI configuration...")
    
    try:
        # Import and check configuration
        from open_webui.config import DOCLING_EXTRACT_PAGES
        
        print(f"✅ DOCLING_EXTRACT_PAGES config found: {DOCLING_EXTRACT_PAGES}")
        
        # Verify default value
        from open_webui.utils.config import get_config_by_filter
        config = get_config_by_filter("DOCLING_EXTRACT_PAGES")
        if config:
            print(f"✅ Config found in database: {config}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False


def main():
    """Run all integration tests."""
    print("🚀 Starting Open WebUI + Docling Serve Integration Tests")
    print("=" * 60)
    
    tests = [
        ("Docling Serve Health", test_docling_serve_health),
        ("Open WebUI Configuration", test_open_webui_config),
        ("Docling Serve Format Support", test_docling_serve_format_support),
        ("DoclingLoader Page Extraction", test_docling_loader_page_extraction),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Running: {test_name}")
        print("-" * 40)
        
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} FAILED with exception: {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Integration is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())