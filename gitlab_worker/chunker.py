import re
import logging
from typing import List, Dict, Any, Optional

from .config import CHUNK_SIZE, CHUNK_OVERLAP

log = logging.getLogger(__name__)


class TextChunker:
    def __init__(self, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_text(self, text: str, file_path: str = '') -> List[Dict[str, Any]]:
        if not text or not text.strip():
            return []

        chunks = []
        lines = text.split('\n')
        current_chunk = []
        current_size = 0

        for i, line in enumerate(lines):
            line_length = len(line)
            if current_size + line_length > self.chunk_size and current_chunk:
                chunk_text = '\n'.join(current_chunk)
                chunks.append({
                    'text': chunk_text,
                    'file_path': file_path,
                    'line_start': len('\n'.join(current_chunk[:len(current_chunk) - 1])) + 1 if len(current_chunk) > 1 else 1,
                    'line_end': len('\n'.join(current_chunk)),
                })

                overlap_lines = current_chunk[-self.chunk_overlap // 50:] if self.chunk_overlap > 0 else []
                current_chunk = overlap_lines + [line]
                current_size = sum(len(l) for l in current_chunk)
            else:
                current_chunk.append(line)
                current_size += line_length + 1

        if current_chunk:
            chunk_text = '\n'.join(current_chunk)
            chunks.append({
                'text': chunk_text,
                'file_path': file_path,
                'line_start': 1,
                'line_end': len(current_chunk),
            })

        return chunks

    def chunk_code(self, content: str, file_path: str = '') -> List[Dict[str, Any]]:
        if not content:
            return []

        language = self._detect_language(file_path)
        if language:
            return self._chunk_by_language(content, file_path, language)
        return self._chunk_generically(content, file_path)

    def _detect_language(self, file_path: str) -> Optional[str]:
        ext_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.go': 'go',
            '.rs': 'rust',
            '.cpp': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.hpp': 'cpp',
            '.cs': 'csharp',
            '.rb': 'ruby',
            '.php': 'php',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.scala': 'scala',
            '.sql': 'sql',
            '.sh': 'bash',
            '.bash': 'bash',
            '.zsh': 'bash',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.json': 'json',
            '.xml': 'xml',
            '.html': 'html',
            '.css': 'css',
            '.md': 'markdown',
            '.rst': 'rst',
        }
        for ext, lang in ext_map.items():
            if file_path.endswith(ext):
                return lang
        return None

    def _chunk_by_language(self, content: str, file_path: str, language: str) -> List[Dict[str, Any]]:
        if language == 'python':
            return self._chunk_python(content, file_path)
        elif language in ('javascript', 'typescript'):
            return self._chunk_js_ts(content, file_path)
        return self._chunk_generically(content, file_path)

    def _chunk_python(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        chunks = []
        pattern = r'(^class\s+|^def\s+|^async def\s+|^import\s+|^from\s+)'

        sections = []
        lines = content.split('\n')
        current_section = []

        for line in lines:
            if re.match(pattern, line.strip()):
                if current_section:
                    sections.append('\n'.join(current_section))
                current_section = [line]
            else:
                current_section.append(line)

        if current_section:
            sections.append('\n'.join(current_section))

        for section in sections:
            if len(section) > self.chunk_size:
                chunks.extend(self._chunk_generically(section, file_path))
            elif section.strip():
                chunks.append({
                    'text': section,
                    'file_path': file_path,
                    'type': 'python_section',
                })

        return chunks

    def _chunk_js_ts(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        chunks = []
        pattern = r'(^export\s+(function|class|const|let|var)|^(function|class|const|let|var)\s+\w+)'

        sections = []
        lines = content.split('\n')
        current_section = []

        for line in lines:
            if re.match(pattern, line.strip()):
                if current_section:
                    sections.append('\n'.join(current_section))
                current_section = [line]
            else:
                current_section.append(line)

        if current_section:
            sections.append('\n'.join(current_section))

        for section in sections:
            if len(section) > self.chunk_size:
                chunks.extend(self._chunk_generically(section, file_path))
            elif section.strip():
                chunks.append({
                    'text': section,
                    'file_path': file_path,
                    'type': 'js_ts_section',
                })

        return chunks

    def _chunk_generically(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        return self.chunk_text(content, file_path)


chunker = TextChunker()