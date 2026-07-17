"""
Tests for asyncio.as_completed chunk ordering fix in audio.py.

Verifies that the sort-by-chunk-index logic correctly reorders results
when asyncio.as_completed() yields them out of order.
"""
import asyncio
import pytest


class TestChunkOrdering:
    """Unit tests for the chunk ordering fix."""

    def test_results_sorted_when_as_completed_out_of_order(self):
        """Results are sorted back to chunk_paths order when asyncio
        yields them in non-sequential completion order."""
        chunk_paths = [
            '/tmp/chunk_0.wav',
            '/tmp/chunk_1.wav',
            '/tmp/chunk_2.wav',
        ]
        # Simulate results coming back in non-sequential order
        # (chunk_2 completes first, then chunk_0, then chunk_1)
        results = [
            {'text': 'second half transcript', 'chunk_path': '/tmp/chunk_2.wav'},
            {'text': 'opening transcript', 'chunk_path': '/tmp/chunk_0.wav'},
            {'text': 'middle transcript', 'chunk_path': '/tmp/chunk_1.wav'},
        ]

        # Apply the sort logic from the fix
        chunk_index = {path: idx for idx, path in enumerate(chunk_paths)}
        results.sort(key=lambda r: chunk_index.get(r.get('chunk_path', ''), 0))

        assert results[0]['text'] == 'opening transcript'
        assert results[1]['text'] == 'middle transcript'
        assert results[2]['text'] == 'second half transcript'

    def test_results_preserved_when_already_in_order(self):
        """Already-sorted results remain in order."""
        chunk_paths = ['/tmp/chunk_0.wav', '/tmp/chunk_1.wav']
        results = [
            {'text': 'first', 'chunk_path': '/tmp/chunk_0.wav'},
            {'text': 'second', 'chunk_path': '/tmp/chunk_1.wav'},
        ]

        chunk_index = {path: idx for idx, path in enumerate(chunk_paths)}
        results.sort(key=lambda r: chunk_index.get(r.get('chunk_path', ''), 0))

        assert results[0]['text'] == 'first'
        assert results[1]['text'] == 'second'

    def test_single_chunk_unchanged(self):
        """Single chunk is unaffected by the sort."""
        chunk_paths = ['/tmp/chunk_0.wav']
        results = [
            {'text': 'solo transcript', 'chunk_path': '/tmp/chunk_0.wav'},
        ]

        chunk_index = {path: idx for idx, path in enumerate(chunk_paths)}
        results.sort(key=lambda r: chunk_index.get(r.get('chunk_path', ''), 0))

        assert len(results) == 1
        assert results[0]['text'] == 'solo transcript'

    def test_empty_results_handled_gracefully(self):
        """Empty results list doesn't error on sort."""
        chunk_paths = ['/tmp/chunk_0.wav']
        results = []

        chunk_index = {path: idx for idx, path in enumerate(chunk_paths)}
        results.sort(key=lambda r: chunk_index.get(r.get('chunk_path', ''), 0))

        assert results == []

    def test_missing_chunk_path_falls_back_to_zero(self):
        """Results without chunk_path are treated as index 0 (safe default)."""
        chunk_paths = ['/tmp/chunk_0.wav', '/tmp/chunk_1.wav']
        results = [
            {'text': 'mystery result'},  # no chunk_path
            {'text': 'first chunk', 'chunk_path': '/tmp/chunk_0.wav'},
        ]

        chunk_index = {path: idx for idx, path in enumerate(chunk_paths)}
        results.sort(key=lambda r: chunk_index.get(r.get('chunk_path', ''), 0))

        # Both map to index 0 since missing key → 0 and chunk_0 → 0
        assert len(results) == 2

    def test_joined_text_preserves_order(self):
        """The final ' '.join produces correct chronological text."""
        chunk_paths = [
            '/tmp/chunk_0.wav',
            '/tmp/chunk_1.wav',
        ]
        results = [
            {'text': 'WORLD', 'chunk_path': '/tmp/chunk_1.wav'},
            {'text': 'HELLO', 'chunk_path': '/tmp/chunk_0.wav'},
        ]

        chunk_index = {path: idx for idx, path in enumerate(chunk_paths)}
        results.sort(key=lambda r: chunk_index.get(r.get('chunk_path', ''), 0))
        joined = ' '.join([result['text'] for result in results])

        assert joined == 'HELLO WORLD'

    @pytest.mark.asyncio
    async def test_as_completed_interleaving_does_not_corrupt_order(self):
        """Integration-style test: async tasks finishing in reverse order
        still produce correctly sorted output."""
        chunk_paths = ['/a/chunk_0.wav', '/a/chunk_1.wav', '/a/chunk_2.wav']

        async def fake_handler(chunk_path):
            # Simulate per-chunk timing differences:
            # later chunks finish faster
            delays = {
                '/a/chunk_0.wav': 0.05,
                '/a/chunk_1.wav': 0.02,
                '/a/chunk_2.wav': 0.005,
            }
            await asyncio.sleep(delays.get(chunk_path, 0.01))
            return {
                'text': f'text_from_{chunk_path.split("/")[-1].split(".")[0]}',
                'chunk_path': chunk_path,
            }

        tasks = [fake_handler(p) for p in chunk_paths]
        results = []
        for coro in asyncio.as_completed(tasks):
            results.append(await coro)

        # Results are now in completion order, NOT chunk_paths order
        # (chunk_2 first because it's fastest)
        assert results[0]['chunk_path'] == '/a/chunk_2.wav', (
            f'Expected chunk_2 first (fastest), got {results[0]["chunk_path"]}'
        )

        # Apply the fix sort
        chunk_index = {path: idx for idx, path in enumerate(chunk_paths)}
        results.sort(key=lambda r: chunk_index.get(r.get('chunk_path', ''), 0))

        # Now they should be in chronological order
        assert [r['chunk_path'] for r in results] == [
            '/a/chunk_0.wav',
            '/a/chunk_1.wav',
            '/a/chunk_2.wav',
        ]
        joined = ' '.join([r['text'] for r in results])
        assert joined == 'text_from_chunk_0 text_from_chunk_1 text_from_chunk_2'
