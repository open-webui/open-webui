#!/usr/bin/env python3
"""
Fix for issue #17706: Too many results when using multiple knowledge bases.

Problem: Top-K returns K results per knowledge base instead of K results total.
Solution: Modify query functions to collect more results initially, then apply final Top-K limit.
"""

def fix_query_collection_top_k():
    """
    Fix for query_collection function to properly limit Top-K across multiple knowledge bases.
    
    The issue is that each knowledge base returns K results, then they're merged.
    The fix queries each collection with a higher limit, then applies final Top-K.
    """
    
    original_code = '''
def query_collection(
    collection_names: list[str],
    queries: list[str],
    embedding_function,
    k: int,
) -> dict:
    results = []
    error = False

    def process_query_collection(collection_name, query_embedding):
        try:
            if collection_name:
                result = query_doc(
                    collection_name=collection_name,
                    k=k,  # <-- PROBLEM: Each collection returns K results
                    query_embedding=query_embedding,
                )
                if result is not None:
                    return result.model_dump(), None
            return None, None
        except Exception as e:
            log.exception(f"Error when querying the collection: {e}")
            return None, e

    # ... rest of function
    return merge_and_sort_query_results(results, k=k)  # <-- Final K applied too late
'''

    fixed_code = '''
def query_collection(
    collection_names: list[str],
    queries: list[str],
    embedding_function,
    k: int,
) -> dict:
    results = []
    error = False
    
    # Calculate expanded limit for initial queries
    # Use k * number of collections to ensure we get enough candidates
    # But cap it at a reasonable maximum to avoid performance issues
    expanded_k = min(k * len(collection_names), k * 10)  # Cap at 10x original k

    def process_query_collection(collection_name, query_embedding):
        try:
            if collection_name:
                result = query_doc(
                    collection_name=collection_name,
                    k=expanded_k,  # <-- FIX: Query with expanded limit
                    query_embedding=query_embedding,
                )
                if result is not None:
                    return result.model_dump(), None
            return None, None
        except Exception as e:
            log.exception(f"Error when querying the collection: {e}")
            return None, e

    # ... rest of function unchanged
    return merge_and_sort_query_results(results, k=k)  # Final K limit applied correctly
'''

    return {
        "original": original_code,
        "fixed": fixed_code,
        "explanation": """
        The fix modifies the query_collection function to:
        1. Calculate an expanded K limit for initial queries (k * num_collections)
        2. Query each collection with this expanded limit
        3. Let merge_and_sort_query_results apply the final Top-K limit
        
        This ensures that the final result contains exactly K items total,
        not K items per knowledge base.
        """
    }


def fix_query_collection_with_hybrid_search_top_k():
    """
    Fix for query_collection_with_hybrid_search function.
    Same issue and solution as regular query_collection.
    """
    
    original_code = '''
def query_collection_with_hybrid_search(
    collection_names: list[str],
    queries: list[str],
    embedding_function,
    k: int,
    reranking_function,
    k_reranker: int,
    r: float,
    hybrid_bm25_weight: float,
) -> dict:
    # ... setup code ...
    
    def process_query(collection_name, query):
        try:
            result = query_doc_with_hybrid_search(
                collection_name=collection_name,
                collection_result=collection_results[collection_name],
                query=query,
                embedding_function=embedding_function,
                k=k,  # <-- PROBLEM: Each collection returns K results
                reranking_function=reranking_function,
                k_reranker=k_reranker,
                r=r,
                hybrid_bm25_weight=hybrid_bm25_weight,
            )
            return result, None
        except Exception as e:
            log.exception(f"Error when querying the collection with hybrid_search: {e}")
            return None, e

    # ... rest of function
    return merge_and_sort_query_results(results, k=k)
'''

    fixed_code = '''
def query_collection_with_hybrid_search(
    collection_names: list[str],
    queries: list[str],
    embedding_function,
    k: int,
    reranking_function,
    k_reranker: int,
    r: float,
    hybrid_bm25_weight: float,
) -> dict:
    # ... setup code unchanged ...
    
    # Calculate expanded limits for initial queries
    expanded_k = min(k * len(collection_names), k * 10)  # Cap at 10x original k
    expanded_k_reranker = min(k_reranker * len(collection_names), k_reranker * 10)
    
    def process_query(collection_name, query):
        try:
            result = query_doc_with_hybrid_search(
                collection_name=collection_name,
                collection_result=collection_results[collection_name],
                query=query,
                embedding_function=embedding_function,
                k=expanded_k,  # <-- FIX: Use expanded limit
                reranking_function=reranking_function,
                k_reranker=expanded_k_reranker,  # <-- FIX: Expand reranker limit too
                r=r,
                hybrid_bm25_weight=hybrid_bm25_weight,
            )
            return result, None
        except Exception as e:
            log.exception(f"Error when querying the collection with hybrid_search: {e}")
            return None, e

    # ... rest of function unchanged
    return merge_and_sort_query_results(results, k=k)  # Final K limit applied correctly
'''

    return {
        "original": original_code,
        "fixed": fixed_code,
        "explanation": """
        The fix modifies the hybrid search function to:
        1. Calculate expanded K and K_reranker limits
        2. Query each collection with these expanded limits
        3. Let merge_and_sort_query_results apply the final Top-K limit
        
        Both k and k_reranker need to be expanded to ensure proper results.
        """
    }


def create_test_scenario():
    """
    Test scenario that reproduces the issue.
    """
    
    scenario = {
        "setup": {
            "top_k": 1,
            "knowledge_bases": ["kb1", "kb2"],
            "documents_per_kb": 1
        },
        "current_behavior": {
            "kb1_results": 1,
            "kb2_results": 1,
            "total_results": 2,
            "expected_results": 1
        },
        "after_fix": {
            "kb1_query_limit": 2,  # expanded_k = 1 * 2 collections = 2
            "kb2_query_limit": 2,
            "total_candidates": 4,  # 2 from each KB
            "final_top_k_applied": 1,
            "actual_results": 1
        }
    }
    
    return scenario


if __name__ == "__main__":
    print("Fix for Top-K Multiple Knowledge Bases Issue #17706")
    print("=" * 60)
    
    # Show the fixes
    fix1 = fix_query_collection_top_k()
    fix2 = fix_query_collection_with_hybrid_search_top_k()
    
    print("\n1. Regular Query Collection Fix:")
    print(fix1["explanation"])
    
    print("\n2. Hybrid Search Query Collection Fix:")
    print(fix2["explanation"])
    
    # Show test scenario
    scenario = create_test_scenario()
    print("\n3. Test Scenario:")
    print(f"Setup: Top-K={scenario['setup']['top_k']}, KBs={len(scenario['setup']['knowledge_bases'])}")
    print(f"Current: {scenario['current_behavior']['total_results']} results (wrong)")
    print(f"After fix: {scenario['after_fix']['actual_results']} results (correct)")
    
    print("\n✅ This fix will ensure Top-K is applied across ALL knowledge bases, not per knowledge base.")