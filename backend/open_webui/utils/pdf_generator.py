from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, List
from html import escape
import re
import os
import time
import multiprocessing as mp
import base64
import markdown
from zoneinfo import ZoneInfo

from weasyprint import HTML
from open_webui.env import STATIC_DIR
from open_webui.models.chats import ChatTitleMessagesForm
from .katex_compiler import KaTeXCompiler

PDF_DEBUG = True
LATEX_DEBUG = True

class PDFGenerator:
    """
    Description:
    The `PDFGenerator` class is designed to create PDF documents from chat messages.
    The process involves transforming markdown content into HTML and then into a PDF format

    Attributes:
    - `form_data`: An instance of `ChatTitleMessagesForm` containing title and messages.

    """

    def __init__(self, form_data: ChatTitleMessagesForm):
        self.html_body = None
        self.messages_html = None
        self.form_data = form_data
        self.temp_images = []
        self.katex_compiler = KaTeXCompiler(debug=LATEX_DEBUG)
        self.debug_latex = LATEX_DEBUG
        self.debug_pdf = PDF_DEBUG

        self.css = Path(STATIC_DIR / "assets" / "pdf-style.css").read_text()

    def format_timestamp(self, timestamp: float) -> str:
        """Convert a UNIX timestamp to a formatted date string in Eastern Time (EST/EDT)."""
        try:
            date_time = datetime.fromtimestamp(timestamp, tz=ZoneInfo("America/New_York"))
            
            # Get timezone abbreviation (EST/EDT) - fallback based on offset if %Z is empty
            tz_abbrev = date_time.strftime("%Z")
            if not tz_abbrev:
                offset_hours = int(date_time.utcoffset().total_seconds() / 3600) if date_time.utcoffset() else -5
                tz_abbrev = "EDT" if offset_hours == -4 else "EST"
            
            # Format UTC offset
            offset_str = date_time.strftime("%z")
            offset_formatted = f"UTC{offset_str[:3]}:{offset_str[3:]}" if offset_str else "UTC"
            
            return date_time.strftime(f"%B %d, %Y %I:%M:%S %p {tz_abbrev} ({offset_formatted})")
        except Exception:
            try:
                return datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%B %d, %Y %I:%M:%S %p UTC")
            except Exception:
                return ""

    def _detect_code_blocks(self, content: str) -> List[tuple[int, int]]:
        """
        Detect code block regions in content.
        Returns a list of (start, end) tuples representing code block regions.
        Handles both fenced code blocks (```...```) and inline code (`...`).
        """
        code_regions = []
        
        # Pattern for fenced code blocks: ```[language]\n...```
        # Matches ```, optional language identifier (word chars, hyphens, spaces), 
        # optional newline, content (non-greedy), then closing ```
        # The pattern handles both ```language\n...``` and ```\n...``` formats
        fenced_pattern = r'```(?:[^\n`]*)?\n?[\s\S]*?```'
        for match in re.finditer(fenced_pattern, content, re.MULTILINE):
            code_regions.append((match.start(), match.end()))
        
        # Pattern for inline code: `...` (but not inside fenced blocks)
        # We need to be careful to not match backticks that are part of fenced blocks
        # Simple approach: find all `...` patterns, then filter out those inside fenced blocks
        inline_pattern = r'`[^`\n]+`'
        for match in re.finditer(inline_pattern, content):
            # Check if this inline code is inside a fenced block
            is_inside_fenced = any(
                match.start() >= fence_start and match.end() <= fence_end
                for fence_start, fence_end in code_regions
            )
            if not is_inside_fenced:
                code_regions.append((match.start(), match.end()))
        
        # Sort by start position for easier checking
        code_regions.sort()
        
        if self.debug_pdf:
            print("*"*20, f"\nPDF: detected {len(code_regions)} code block(s)\n", "*"*20)
        
        return code_regions
    
    def _is_in_code_block(self, position: int, code_regions: List[tuple[int, int]]) -> bool:
        """
        Check if a given position is inside any code block region.
        """
        for start, end in code_regions:
            if start <= position < end:
                return True
        return False

    def detect_latex_in_message(self, content: str) -> List[Dict[str, Any]]:
        """
        Detect LaTeX code in a chat message content.
        Returns a list of dictionaries containing LaTeX expressions found.
        Based on the frontend katex-extension.ts implementation.
        Excludes LaTeX expressions that are inside code blocks.
        """
        # First, detect all code block regions
        code_regions = self._detect_code_blocks(content)
        
        found_latex = []
        # LaTeX delimiter patterns: (regex, delimiter_name, is_display_mode)
        # Display mode expressions are centered and on their own line
        patterns = [
            (r'\$\$(.+?)\$\$', "$$", True),  # Block math: $$...$$
            (r'(?<!\$)\$(.+?)\$(?!\$)', "$", False),  # Inline math: $...$ (not part of $$)
            (r'\\ce\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}', "\\ce{}", False),  # Chemical formulas
            (r'\\pu\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}', "\\pu{}", False),  # Physical units
            (r'\\boxed\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}', "\\boxed{}", False),  # Boxed expressions
            (r'\\\((.*?)\\\)', "\\(\\)", False),  # Inline math: \(...\)
            (r'\\\[(.*?)\\\]', "\\[\\]", True),  # Block math: \[...\]
            (r'\\begin\{equation\}([\s\S]*?)\\end\{equation\}', "\\begin{equation}\\end{equation}", True)  # Equation environment
        ]
        
        # Track used positions to avoid duplicate matches (e.g., $ inside $$)
        used_positions = set()
        
        for pattern, delimiter, display in patterns:
            for match in re.finditer(pattern, content, re.MULTILINE | re.DOTALL):
                start, end = match.start(), match.end()
                
                # Skip if this LaTeX expression is inside a code block
                if self._is_in_code_block(start, code_regions) or self._is_in_code_block(end - 1, code_regions):
                    if self.debug_pdf:
                        print("*"*20, f"\nPDF: Skipping LaTeX in code block at position {start}-{end}, delimiter={delimiter}\n", "*"*20)
                    continue
                
                # Skip pathological matches (likely unmatched delimiters)
                if end - start > 10000:
                    if self.debug_pdf:
                        print("*"*20, f"\nPDF: Skipping pathological LaTeX span length={end-start} delimiter={delimiter}\n", "*"*20)
                    continue
                
                # Skip if this position range overlaps with a previously matched expression
                if any(start < used_end and end > used_start for used_start, used_end in used_positions):
                    continue
                
                latex_expr = match.group(1).strip()
                # Only add if we have meaningful content (not just whitespace)
                if latex_expr and len(latex_expr) > 0 and not latex_expr.isspace():
                    found_latex.append({
                        "expression": latex_expr,
                        "full_match": match.group(0),
                        "display": display,
                        "delimiter": delimiter,
                        "start": start,
                        "end": end
                    })
                    used_positions.add((start, end))
        
        if self.debug_pdf:
            print("*"*20, f"\nPDF: detect_latex_in_message count={len(found_latex)} content_len={len(content)}\n", "*"*20)
        return found_latex

    def _fix_svg_sizing(self, html_fragment: str) -> str:
        """
        Fix SVG sizing issues in HTML fragment, keeping SVG tags embedded directly.
        This preserves the em context that would be lost with base64 image conversion.
        """
        import re
        
        svg_pattern = r'<svg[^>]*>.*?</svg>'
        svg_matches = list(re.finditer(svg_pattern, html_fragment, re.DOTALL | re.IGNORECASE))
        
        if not svg_matches:
            return html_fragment
        
        result = html_fragment
        for match in reversed(svg_matches):
            svg_html = match.group(0)
            
            try:
                # Fix pathological width values (KaTeX placeholders like 1e6em, 10000em)
                # These need to be replaced with reasonable values, but we keep the SVG tag
                fixed_svg = svg_html
                
                # Replace pathological width values - we'll need to calculate proper width based on content
                # For now, let's just remove or replace the problematic width attributes
                # The SVG should size based on viewBox and content
                fixed_svg = re.sub(r'width=["\'](1e6|10000)em["\']', '', fixed_svg, flags=re.IGNORECASE)
                fixed_svg = re.sub(r'width=["\']100%["\']', '', fixed_svg, flags=re.IGNORECASE)
                
                # Keep the SVG tag embedded directly in HTML
                result = result[:match.start()] + fixed_svg + result[match.end():]
            except Exception:
                continue
        
        return result

    def cleanup_temp_images(self):
        """Clean up temporary image files."""
        for temp_path in self.temp_images:
            try:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            except Exception as e:
                print(f"Error cleaning up temp file {temp_path}: {e}")
        self.temp_images.clear()
        
        # Also clean up KaTeX temp images
        if hasattr(self, 'katex_compiler'):
            self.katex_compiler.cleanup_temp_images()
        
        # Clean up any remaining files in the project temp directory
        project_temp_dir = Path(__file__).parent.parent.parent.parent / "temp"
        if project_temp_dir.exists():
            try:
                for temp_file in project_temp_dir.glob("*"):
                    if temp_file.is_file():
                        temp_file.unlink()
            except Exception as e:
                print(f"Error cleaning up project temp directory: {e}")


    def print_latex_detected(self, message: Dict[str, Any]) -> None:
        """
        Check for LaTeX code in a message and print it to terminal if found.
        """
        content = message.get("content", "")
        role = message.get("role", "user")
        
        latex_expressions = self.detect_latex_in_message(content)
        
        if latex_expressions:
            print(f"\n=== LaTeX detected in {role} message ===")
            for i, latex in enumerate(latex_expressions, 1):
                print(f"Expression {i}:")
                print(f"  Type: {'Block' if latex['display'] else 'Inline'}")
                print(f"  Delimiter: {latex['delimiter']}")
                print(f"  Content: {latex['expression']}")
                print(f"  Position: {latex['start']}-{latex['end']}")
                print(f"  Full match: {latex['full_match']}")
                print()

    def _build_html_message(self, message: Dict[str, Any]) -> tuple[str, List[Dict[str, Any]]]:
        """Build HTML for a single message and return LaTeX image data."""
        role = escape(message.get("role", "user"))
        content = message.get("content", "")
        timestamp = message.get("timestamp")

        model = escape(message.get("model") if role == "assistant" else "")

        date_str = escape(self.format_timestamp(timestamp) if timestamp else "")

        # Check for LaTeX code in the message and print to terminal
        if self.debug_latex:
            self.print_latex_detected(message)

        # First process LaTeX expressions (convert LaTeX to HTML)
        html_content = self._process_latex_to_html(content)
        
        # Minimal preprocessing: only fix items that are clearly on the same line
        # when they should be separate (e.g., "text - (a) text - (b)" -> separate lines)
        # This is minimal and doesn't touch well-formed markdown
        html_content = self._fix_broken_list_items(html_content)
        
        # Convert markdown to HTML with extensions that preserve formatting
        # Use markdown extensions for better formatting support
        html_content = markdown.markdown(
            html_content, 
            extensions=['fenced_code', 'tables', 'toc']
        )
        
        # Wrap in markdown-section div for proper CSS styling
        html_message = f"""
            <div>
                <div>
                    <h4>
                        <strong>{role.title()}</strong>
                        <span style=\"font-size: 12px;\">{model}</span>
                    </h4>
                    <div> {date_str} </div>
                </div>
                <br/>
                <br/>

                <div class="markdown-section">
                    {html_content}
                </div>
            </div>
            <br/>
          """
        return html_message, []

    def _fix_broken_list_items(self, content: str) -> str:
        """
        Ensure list items are properly formatted for markdown.
        Markdown requires list items to start at the beginning of lines (or with proper indentation).
        This ensures list items are recognized and separated properly.
        """
        result = content
        
        # First, fix cases where list items appear on the same line as text
        # Fix numbered lists: "text 1. item" -> "text\n1. item"
        result = re.sub(r'([^\n])\s+(\d+\.\s+)', r'\1\n\2', result)
        
        # Fix bullet points: "text - item" -> "text\n- item"  
        result = re.sub(r'([^\n])\s+(-\s+)', r'\1\n\2', result)
        
        # Fix lettered items with dash: "text - (a)" -> "text\n- (a)"
        result = re.sub(r'([^\n])\s+-\s+\(([a-zA-Z0-9ivxlcdmIVXLCDM]+)\)', r'\1\n- (\2)', result)
        
        # Now ensure list items are properly separated from preceding text
        # Split into lines to process line by line
        lines = result.split('\n')
        processed_lines = []
        
        for i, line in enumerate(lines):
            # Check if this line is a list item (preserving indentation)
            is_numbered_list = re.match(r'^\s*\d+\.\s+', line)
            is_bullet_list = re.match(r'^\s*[-*+]\s+', line)
            
            if is_numbered_list or is_bullet_list:
                # If previous line was not a list item and not empty, 
                # ensure there's proper separation (markdown needs this)
                if processed_lines:
                    prev_line = processed_lines[-1].strip()
                    # If previous line has content and is not a list item, add blank line
                    if prev_line:
                        prev_is_list = re.match(r'^\s*[-*+]\s+', processed_lines[-1]) or re.match(r'^\s*\d+\.\s+', processed_lines[-1])
                        if not prev_is_list:
                            # Add blank line before list to help markdown recognize it
                            processed_lines.append('')
            
            processed_lines.append(line)
        
        result = '\n'.join(processed_lines)
        
        # Clean up multiple consecutive blank lines (max 2)
        result = re.sub(r'\n{3,}', '\n\n', result)
        
        return result

    def _generate_html_body(self) -> str:
        """Generate the full HTML body for the PDF."""
        escaped_title = escape(self.form_data.title)
        return f"""
        <html>
            <head>
                <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
            </head>
            <body>
            <div>
                <div>
                    <h2>{escaped_title}</h2>
                    {self.messages_html}
                </div>
            </div>
            </body>
        </html>
        """

    def _process_latex_to_html(self, content: str) -> str:
        """
        Convert LaTeX in content to KaTeX-rendered HTML fragments.
        
        This function:
        1. Detects all LaTeX expressions in the content
        2. Renders them with KaTeX to HTML (which may include SVG elements)
        3. Converts SVG elements to base64-encoded images for PDF compatibility
        4. Replaces the original LaTeX expressions with the rendered HTML
        """
        latex_expressions = self.detect_latex_in_message(content)
        if not latex_expressions:
            return escape(content)

        # Sort by start position in reverse order so we can replace from end to start
        # This preserves indices when doing string replacements
        latex_expressions.sort(key=lambda x: x['start'], reverse=True)
        html_content = content
        
        # Prepare expressions for KaTeX rendering
        to_render: list[tuple[str, bool]] = []
        
        for latex in latex_expressions:
            expr = latex['expression']
            
            # Rebuild expression for special delimiters (boxed, ce, pu)
            # These need to be wrapped in their command syntax
            if latex['delimiter'] in ['\\boxed{}', '\\ce{}', '\\pu{}']:
                expr = latex['delimiter'].replace('{}', '{' + expr + '}')
            elif latex['delimiter'] == '\\[\\boxed{}\\]]':
                expr = '\\boxed{' + expr + '}'
            
            # Insert soft breaks to allow long expressions to wrap in PDF
            expr = self._insert_soft_breaks(expr)
            to_render.append((expr, latex['display']))

        try:
            rendered = self.katex_compiler.render_many_to_html(to_render) if to_render else []
        except Exception:
            rendered = [escape(e) for e, _ in to_render]

        # Fix SVG sizing issues while keeping SVG tags embedded directly in HTML
        # This preserves em context which would be lost with base64 image conversion
        final_fragments: list[str] = []
        for fragment in rendered:
            if '<svg' in fragment:
                try:
                    fixed = self._fix_svg_sizing(fragment)
                    final_fragments.append(fixed)
                except Exception:
                    # Fallback: keep original fragment
                    final_fragments.append(fragment)
            else:
                final_fragments.append(fragment)

        for latex, fragment in zip(latex_expressions, final_fragments):
            html_content = html_content[:latex['start']] + fragment + html_content[latex['end']:]

        html_content = html_content.replace('\\[', '').replace('\\]', '')

        return html_content

    def _render_with_timeout(self, html_full: str, timeout_sec: float = 15.0, use_base_url: bool = True) -> bytes:
        """Render PDF in a separate process with a timeout. Returns bytes or raises TimeoutError."""
        q: mp.Queue = mp.Queue(maxsize=1)

        def _worker(doc_html: str, base_url: str | None):
            try:
                if base_url:
                    data = HTML(string=doc_html, base_url=base_url).write_pdf()
                else:
                    data = HTML(string=doc_html).write_pdf()
                q.put((True, data))
            except Exception as ex:
                q.put((False, str(ex)))

        base_url_val = str(STATIC_DIR) if use_base_url else None
        p = mp.Process(target=_worker, args=(html_full, base_url_val))
        p.daemon = True
        p.start()
        p.join(timeout_sec)
        if p.is_alive():
            if self.debug_pdf:
                print("*"*20, "\nPDF: write_pdf timed out; terminating renderer process\n", "*"*20)
            p.terminate()
            p.join(2)
            raise TimeoutError("WeasyPrint write_pdf timeout")
        ok, payload = q.get() if not q.empty() else (False, 'no result')
        if not ok:
            raise RuntimeError(payload)
        return payload

    def _insert_soft_breaks(self, expr: str) -> str:
        """Insert KaTeX-friendly soft breakpoints into long LaTeX expressions."""
        multi_token_replacements = {
            r"\\cdot": r"\\allowbreak{}\\cdot\\allowbreak{}",
            r"\\times": r"\\allowbreak{}\\times\\allowbreak{}",
            r"\\pm": r"\\allowbreak{}\\pm\\allowbreak{}",
            r"\\mp": r"\\allowbreak{}\\mp\\allowbreak{}",
            r"\\leq": r"\\allowbreak{}\\leq\\allowbreak{}",
            r"\\geq": r"\\allowbreak{}\\geq\\allowbreak{}",
            r"\\approx": r"\\allowbreak{}\\approx\\allowbreak{}",
            r"\\sim": r"\\allowbreak{}\\sim\\allowbreak{}",
        }

        for k, v in multi_token_replacements.items():
            expr = re.sub(k, v, expr)

        expr = re.sub(r"(?<![\\\\a-zA-Z0-9])\+", r"\\allowbreak{}+\\allowbreak{}", expr)
        expr = re.sub(r"(?<![\\\\a-zA-Z0-9])-", r"\\allowbreak{}-\\allowbreak{}", expr)
        expr = re.sub(r"(?<![\\\\a-zA-Z0-9])=", r"\\allowbreak{}=\\allowbreak{}", expr)
        expr = expr.replace(",", ",\\allowbreak{}")
        expr = expr.replace(";", ";\\allowbreak{}")
        expr = expr.replace(":", ":\\allowbreak{}")
        expr = expr.replace(")", ")\\allowbreak{}")
        expr = expr.replace("]", "]\\allowbreak{}")

        return expr

    def generate_chat_pdf(self) -> bytes:
        """
        Generate a PDF from chat messages. Uses WeasyPrint to render HTML with KaTeX.
        """
        try:
            gen_start = time.perf_counter()
            messages_html_parts = []
            all_latex_images = []
            if self.debug_pdf:
                print("*"*20, f"\nPDF: starting build for {len(self.form_data.messages)} messages\n", "*"*20)
            for message in self.form_data.messages:
                if self.debug_latex:
                    self.print_latex_detected(message)
                html_message, latex_images = self._build_html_message(message)
                messages_html_parts.append(html_message)
                all_latex_images.extend(latex_images)

            self.messages_html = "\n".join(messages_html_parts)
            html_body = self._generate_html_body()

            katex_css_path = Path(STATIC_DIR / "assets" / "katex" / "katex.min.css")

            html_full = html_body.replace(
                "<head>",
                (
                    "<head>\n"
                    f'<link rel="stylesheet" href="{katex_css_path}">\n'
                    "<style>\n"
                    f'{self.css}\n'
                    "  .katex, .katex-display {\n"
                    "    white-space: normal !important;\n"
                    "    font-size: 1.15em;\n"
                    "  }\n"
                    "  .katex-display {\n"
                    "    overflow-wrap: anywhere;\n"
                    "    word-break: break-word;\n"
                    "    line-break: anywhere;\n"
                    "    text-align: center;\n"
                    "  }\n"
                    "  .katex-display > .katex {\n"
                    "    display: inline-block;\n"
                    "    max-width: 100%;\n"
                    "  }\n"
                    "  .katex-display .katex {\n"
                    "    font-size: 1em;\n"
                    "  }\n"
                    "  /* Fix for radical symbols in denominators - allow vertical overflow */\n"
                    "  .katex .sqrt > .vlist-t,\n"
                    "  .katex .root > .vlist-t {\n"
                    "    overflow: visible !important;\n"
                    "  }\n"
                    "  .katex .stretchy:has(> svg),\n"
                    "  .katex .sqrt .stretchy,\n"
                    "  .katex .root .stretchy {\n"
                    "    overflow: visible !important;\n"
                    "    min-height: auto !important;\n"
                    "  }\n"
                    "  .katex .sqrt svg,\n"
                    "  .katex .root svg {\n"
                    "    overflow: visible !important;\n"
                    "    max-height: none !important;\n"
                    "  }\n"
                    "  pre, code, pre code {\n"
                    "    overflow-wrap: break-word !important;\n"
                    "    word-wrap: break-word !important;\n"
                    "    word-break: break-all !important;\n"
                    "    white-space: pre-wrap !important;\n"
                    "    max-width: 100% !important;\n"
                    "    box-sizing: border-box !important;\n"
                    "  }\n"
                    "  .markdown-section pre,\n"
                    "  .markdown-section pre code {\n"
                    "    overflow-wrap: break-word !important;\n"
                    "    word-wrap: break-word !important;\n"
                    "    word-break: break-all !important;\n"
                    "    white-space: pre-wrap !important;\n"
                    "    max-width: 100% !important;\n"
                    "    box-sizing: border-box !important;\n"
                    "  }\n"
                    "</style>\n"
                )
            )

            if self.debug_pdf:
                build_elapsed = time.perf_counter() - gen_start
                katex_count = html_full.count('<span class="katex') + html_full.count('<span class="katex-display')
                code_error_count = html_full.count('class="latex-error"')
                svg_count = html_full.count('<svg')
                print("*"*20)
                print(f"PDF: HTML built in {build_elapsed:.3f}s")
                print(f"PDF: html_len={len(html_full)}")
                print(f"PDF: KaTeX fragments={katex_count}, SVG elements={svg_count}, quarantined={code_error_count}")
                print("PDF: starting WeasyPrint write_pdf")
                print("*"*20)
            t_wp0 = time.perf_counter()
            try:
                pdf_bytes = self._render_with_timeout(html_full, timeout_sec=20.0)
            except TimeoutError:
                if self.debug_pdf:
                    print("*"*20, "\nPDF: render timed out; returning error without retry\n", "*"*20)
                raise RuntimeError("PDF generation timed out. Please try again.")
            t_wp1 = time.perf_counter()
            if self.debug_pdf:
                print("*"*20, f"\nPDF: WeasyPrint write_pdf completed in {t_wp1 - t_wp0:.3f}s; total {t_wp1 - gen_start:.3f}s\n", "*"*20)
            return pdf_bytes
        except Exception as e:
            if self.debug_pdf:
                print("*"*20, f"\nPDF: generation failed: {e}\n", "*"*20)
            raise e
        finally:
            self.cleanup_temp_images()
