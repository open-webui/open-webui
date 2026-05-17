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

        # Simple but effective line-based chunking with overlap
        chunks = []
        lines = text.split('\n')
        
        current_chunk_lines = []
        current_size = 0
        
        for line_idx, line in enumerate(lines):
            line_len = len(line) + 1 # +1 for newline
            
            if current_size + line_len > self.chunk_size and current_chunk_lines:
                # Store current chunk
                chunk_text = '\n'.join(current_chunk_lines)
                chunks.append({
                    'text': chunk_text,
                    'file_path': file_path,
                    'line_start': line_idx - len(current_chunk_lines) + 1,
                    'line_end': line_idx,
                })
                
                # Handle overlap - keep last few lines
                overlap_size = 0
                overlap_lines = []
                for l in reversed(current_chunk_lines):
                    if overlap_size + len(l) + 1 > self.chunk_overlap:
                        break
                    overlap_lines.insert(0, l)
                    overlap_size += len(l) + 1
                
                current_chunk_lines = overlap_lines
                current_size = overlap_size

            current_chunk_lines.append(line)
            current_size += line_len

        if current_chunk_lines:
            chunks.append({
                'text': '\n'.join(current_chunk_lines),
                'file_path': file_path,
                'line_start': len(lines) - len(current_chunk_lines) + 1,
                'line_end': len(lines),
            })

        return chunks

    def chunk_code(self, content: str, file_path: str = '') -> List[Dict[str, Any]]:
        if not content:
            return []

        language = self._detect_language(file_path)
        
        # If it's a known code language, try specialized chunking
        if language in ('python', 'javascript', 'typescript', 'java', 'go', 'rust'):
            try:
                return self._chunk_by_language(content, file_path, language)
            except Exception as e:
                log.warning(f"Specialized chunking failed for {file_path}: {e}")
        
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
            if file_path.lower().endswith(ext):
                return lang
        return None

    def _chunk_by_language(self, content: str, file_path: str, language: str) -> List[Dict[str, Any]]:
        if language == 'python':
            return self._chunk_python(content, file_path)
        elif language in ('javascript', 'typescript'):
            return self._chunk_js_ts(content, file_path)
        # Default for other code: split by common code block patterns
        return self._chunk_code_generically(content, file_path)

    def _chunk_python(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        # Split by class and function definitions
        pattern = r'(^class\s+|^def\s+|^async def\s+)'
        return self._split_by_pattern(content, file_path, pattern, 'python_section')

    def _chunk_js_ts(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        # Split by export, function, class definitions
        pattern = r'(^export\s+|^function\s+|^class\s+|^const\s+\w+\s*=\s*\(|^(var|let)\s+\w+\s*=\s*function)'
        return self._split_by_pattern(content, file_path, pattern, 'js_ts_section')

    def _chunk_code_generically(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        # Split by what looks like a block start at the beginning of a line
        pattern = r'(^func\s+|^type\s+|^package\s+|^import\s+|^struct\s+|^trait\s+|^impl\s+|^enum\s+|^public\s+|^private\s+|^protected\s+)'
        return self._split_by_pattern(content, file_path, pattern, 'code_section')

    def _split_by_pattern(self, content: str, file_path: str, pattern: str, section_type: str) -> List[Dict[str, Any]]:
        chunks = []
        lines = content.split('\n')
        
        current_section = []
        
        for line in lines:
            if re.match(pattern, line):
                if current_section:
                    section_text = '\n'.join(current_section)
                    if len(section_text) > self.chunk_size:
                        chunks.extend(self._chunk_generically(section_text, file_path))
                    else:
                        chunks.append({
                            'text': section_text,
                            'file_path': file_path,
                            'type': section_type
                        })
                current_section = [line]
            else:
                current_section.append(line)
        
        if current_section:
            section_text = '\n'.join(current_section)
            if len(section_text) > self.chunk_size:
                chunks.extend(self._chunk_generically(section_text, file_path))
            else:
                chunks.append({
                    'text': section_text,
                    'file_path': file_path,
                    'type': section_type
                })
        
        return chunks

    def _chunk_generically(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        return self.chunk_text(content, file_path)


chunker = TextChunker()