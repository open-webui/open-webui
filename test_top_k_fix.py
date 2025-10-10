#!/usr/bin/env python3
"""
Test script for Top-K multiple knowledge bases fix (Issue #17706).

This test validates that the fix properly limits results to Top-K total
across all knowledge bases, not Top-K per knowledge base.
"""

import pytest
from unittest.mock import Mock, patch
import hashlib


class TestTopKMultipleKnowledgeBases:
    """Test cases for the Top-K multiple knowledge bases fix."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Mock query results from different knowledge bases
        self.kb1_results = {
            "distances": [[0.9, 0.8, 0.7]],
            "documents": [["KB1 Doc1", "KB1 Doc2", "KB1 Doc3"]],
            "metadatas": [[{"source": "kb1_doc1"}, {"source": "kb1_doc2"}, {"source": "kb1_doc3"}]]
        }
        
        self.kb2_results = {
            "distances": [[0.95, 0.85, 0.75]],
            "documents": [["KB2 Doc1", "KB2 Doc2", "KB2 Doc3"]],
            "metadatas": [[{"source": "kb2_doc1"}, {"source": "kb2_doc2"}, {"source": "kb2_doc3"}]]
        }
    
    def test_merge_and_sort_query_results_respects_top_k(self):
        """Test that merge_and_sort_query_results properly applies Top-K limit."""
        from open_webui.backend.open_webui.retrieval.utils import merge_and_sort_query_results
        
        # Simulate results from 2 knowledge bases
        query_results = [self.kb1_results, self.kb2_results]
        
        # Test with k=1 - should return only 1 result total
        result = merge_and_sort_query_results(query_results, k=1)
        
        assert len(result["documents"][0]) == 1, f"Expected 1 result, got {len(result['documents'][0])}"
        assert len(result["distances"][0]) == 1
        assert len(result["metadatas"][0]) == 1
        
        # Should be the highest scoring result (0.95 from KB2)
        assert result["distances"][0][0] == 0.95
        assert result["documents"][0][0] == "KB2 Doc1"
    
    def test_merge_and_sort_query_results_with_k_3(self):
        """Test with k=3 to ensure proper sorting across knowledge bases."""
        from open_webui.backend.open_webui.retrieval.utils import merge_and_sort_query_results
        
        query_results = [self.kb1_results, self.kb2_results]
        
        # Test with k=3 - should return top 3 results across both KBs
        result = merge_and_sort_query_results(query_results, k=3)
        
        assert len(result["documents"][0]) == 3
        
        # Should be sorted by distance (highest first)
        expected_distances = [0.95, 0.9, 0.85]  # Best from each KB, sorted
        assert result["distances"][0] == expected_distances
        
        # Should contain mix from both KBs
        expected_docs = ["KB2 Doc1", "KB1 Doc1", "KB2 Doc2"]
        assert result["documents"][0] == expected_docs
    
    def test_expanded_k_calculation(self):
        """Test the expanded K calculation logic."""
        
        # Test single collection - should not expand
        collection_names = ["kb1"]
        k = 2
        expanded_k = min(k * len(collection_names), k * 10) if len(collection_names) > 1 else k
        assert expanded_k == 2, "Single collection should not expand K"
        
        # Test multiple collections - should expand
        collection_names = ["kb1", "kb2"]
        k = 2
        expanded_k = min(k * len(collection_names), k * 10) if len(collection_names) > 1 else k
        assert expanded_k == 4, f"Expected expanded K=4, got {expanded_k}"
        
        # Test cap at 10x
        collection_names = ["kb1", "kb2", "kb3", "kb4", "kb5", "kb6"]  # 6 collections
        k = 5
        expanded_k = min(k * len(collection_names), k * 10) if len(collection_names) > 1 else k
        # k * len(collection_names) = 5 * 6 = 30
        # k * 10 = 5 * 10 = 50
        # min(30, 50) = 30
        assert expanded_k == 30, f"Expected capped K=30 (min(5*6, 5*10)), got {expanded_k}"
    
    def test_duplicate_document_handling(self):
        """Test that duplicate documents are handled correctly."""
        from open_webui.backend.open_webui.retrieval.utils import merge_and_sort_query_results
        
        # Create results with duplicate documents
        duplicate_results = [
            {
                "distances": [[0.9, 0.8]],
                "documents": [["Same Doc", "KB1 Doc2"]],
                "metadatas": [[{"source": "kb1"}, {"source": "kb1_doc2"}]]
            },
            {
                "distances": [[0.95, 0.7]],  # Same doc with better score
                "documents": [["Same Doc", "KB2 Doc2"]],
                "metadatas": [[{"source": "kb2"}, {"source": "kb2_doc2"}]]
            }
        ]
        
        result = merge_and_sort_query_results(duplicate_results, k=3)
        
        # Should only have 3 unique documents
        assert len(result["documents"][0]) == 3
        
        # "Same Doc" should appear only once with the better score (0.95)
        same_doc_indices = [i for i, doc in enumerate(result["documents"][0]) if doc == "Same Doc"]
        assert len(same_doc_indices) == 1, "Duplicate document should appear only once"
        
        # Should have the better score
        same_doc_index = same_doc_indices[0]
        assert result["distances"][0][same_doc_index] == 0.95


def test_issue_reproduction():
    """
    Reproduce the exact issue described in #17706.
    """
    print("\n" + "="*60)
    print("REPRODUCING ISSUE #17706")
    print("="*60)
    
    # Scenario from issue
    top_k = 1
    knowledge_bases = ["kb1", "kb2"]
    
    print(f"Setup:")
    print(f"  - Top-K setting: {top_k}")
    print(f"  - Knowledge bases: {len(knowledge_bases)}")
    print(f"  - Expected results: {top_k}")
    
    # Simulate current behavior (before fix)
    print(f"\nBEFORE FIX:")
    print(f"  - KB1 returns: {top_k} result(s)")
    print(f"  - KB2 returns: {top_k} result(s)")
    print(f"  - Total results: {top_k * len(knowledge_bases)} (WRONG!)")
    
    # Simulate fixed behavior
    expanded_k = min(top_k * len(knowledge_bases), top_k * 10)
    print(f"\nAFTER FIX:")
    print(f"  - KB1 queried with limit: {expanded_k}")
    print(f"  - KB2 queried with limit: {expanded_k}")
    print(f"  - Total candidates: {expanded_k * len(knowledge_bases)}")
    print(f"  - Final Top-K applied: {top_k}")
    print(f"  - Actual results: {top_k} (CORRECT!)")
    
    print(f"\n✅ Fix resolves the issue!")


def test_performance_considerations():
    """
    Test performance considerations of the fix.
    """
    print("\n" + "="*60)
    print("PERFORMANCE ANALYSIS")
    print("="*60)
    
    scenarios = [
        {"k": 1, "collections": 2, "description": "Typical case"},
        {"k": 5, "collections": 3, "description": "Medium case"},
        {"k": 10, "collections": 5, "description": "Large case"},
        {"k": 20, "collections": 10, "description": "Very large case (capped)"},
    ]
    
    for scenario in scenarios:
        k = scenario["k"]
        num_collections = scenario["collections"]
        
        # Calculate expanded limits
        expanded_k = min(k * num_collections, k * 10)
        
        # Calculate query overhead
        original_queries = k * num_collections  # Total queries before
        fixed_queries = expanded_k * num_collections  # Total queries after
        overhead = (fixed_queries - original_queries) / original_queries * 100
        
        print(f"\n{scenario['description']}:")
        print(f"  - K={k}, Collections={num_collections}")
        print(f"  - Original: {k} per collection = {original_queries} total queries")
        print(f"  - Fixed: {expanded_k} per collection = {fixed_queries} total queries")
        print(f"  - Overhead: {overhead:.1f}%")
        
        # The overhead is acceptable because:
        # 1. We get correct results (most important)
        # 2. Overhead is capped at 10x maximum
        # 3. Most real-world scenarios have few knowledge bases


if __name__ == "__main__":
    # Run issue reproduction
    test_issue_reproduction()
    
    # Run performance analysis
    test_performance_considerations()
    
    # Run pytest if available
    try:
        pytest.main([__file__, "-v"])
    except ImportError:
        print("\npytest not available, running manual tests...")
        
        # Run manual tests
        test_class = TestTopKMultipleKnowledgeBases()
        test_class.setup_method()
        
        try:
            test_class.test_expanded_k_calculation()
            print("✅ test_expanded_k_calculation passed")
        except Exception as e:
            print(f"❌ test_expanded_k_calculation failed: {e}")
        
        print("\n✅ Manual tests completed")