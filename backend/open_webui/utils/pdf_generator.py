from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, List
from html import escape
import re
import os

from weasyprint import HTML

from open_webui.env import STATIC_DIR
from open_webui.models.chats import ChatTitleMessagesForm
from .katex_compiler import KaTeXCompiler


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
        self.temp_images = []  # Store temporary image file paths for cleanup
        self.katex_compiler = KaTeXCompiler()  # Initialize KaTeX compiler

        self.css = Path(STATIC_DIR / "assets" / "pdf-style.css").read_text()

    def format_timestamp(self, timestamp: float) -> str:
        """Convert a UNIX timestamp to a formatted date string in EST timezone."""
        try:
            # Create EST timezone (UTC-5) or EDT timezone (UTC-4)
            # For simplicity, we'll use UTC-4 (EDT) as requested in the format
            est_offset = timedelta(hours=-4)  # UTC-4
            est_tz = timezone(est_offset)
            
            # Convert timestamp to EST
            date_time = datetime.fromtimestamp(timestamp, tz=est_tz)
            
            # Format as requested: 12:06:10 PM EST (UTC-4)
            return date_time.strftime("%I:%M:%S %p EST (UTC-4)")
        except (ValueError, TypeError) as e:
            # Log the error if necessary
            return ""

    # Removed legacy splitting helper (not used in WeasyPrint flow)

    def detect_latex_in_message(self, content: str) -> List[Dict[str, Any]]:
        """
        Detect LaTeX code in a chat message content.
        Returns a list of dictionaries containing LaTeX expressions found.
        Based on the frontend katex-extension.ts implementation.
        """
        found_latex = []
        
        # Define patterns for different LaTeX delimiters
        patterns = [
            # Block $$ delimiters (check these first to avoid conflicts)
            (r'\$\$([^$]+?)\$\$', "$$", True),
            # Inline $ delimiters (but not if they're part of $$)
            (r'(?<!\$)\$([^$\n]+?)\$(?!\$)', "$", False),
            # Chemical formulas
            (r'\\ce\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}', "\\ce{}", False),
            # Physical units
            (r'\\pu\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}', "\\pu{}", False),
            # Boxed expressions
            (r'\\boxed\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}', "\\boxed{}", False),
            # Inline \( \) delimiters
            (r'\\\(([^)]+)\\\)', "\\(\\)", False),
            # Block \[ \] delimiters
            (r'\\\[([^\]]+)\\\]', "\\[\\]", True),
            # Equation blocks
            (r'\\begin\{equation\}([^{}]*(?:\{[^{}]*\}[^{}]*)*)\\end\{equation\}', "\\begin{equation}\\end{equation}", True)
        ]
        
        # Track used positions to avoid duplicates
        used_positions = set()
        
        for pattern, delimiter, display in patterns:
            for match in re.finditer(pattern, content, re.MULTILINE | re.DOTALL):
                start, end = match.start(), match.end()
                
                # Skip if this position range is already used
                if any(start < used_end and end > used_start for used_start, used_end in used_positions):
                    continue
                
                latex_expr = match.group(1).strip()  # Remove leading/trailing whitespace
                # Additional validation to ensure we have meaningful content
                if latex_expr and len(latex_expr) > 0 and not latex_expr.isspace():
                    print(f"Detected LaTeX: '{latex_expr}' (delimiter: {delimiter})")
                    found_latex.append({
                        "expression": latex_expr,
                        "full_match": match.group(0),
                        "display": display,
                        "delimiter": delimiter,
                        "start": start,
                        "end": end
                    })
                    # Mark this position range as used
                    used_positions.add((start, end))
        
        return found_latex

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

    # Removed KaTeX->PNG path (WeasyPrint renders KaTeX HTML directly)

    # Matplotlib fallback removed to enforce KaTeX-only rendering

    # Removed image placeholder path (WeasyPrint uses direct KaTeX HTML)

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
        self.print_latex_detected(message)

        # Render LaTeX directly to KaTeX HTML fragments (no image compilation)
        html_content = self._process_latex_to_html(content)
        # Preserve newlines
        escaped_content = html_content.replace("\n", "<br/>")
        
        html_message = f"""
            <div>
                <div>
                    <h4>
                        <strong>{role.title()}</strong>
                        <span style="font-size: 12px;">{model}</span>
                    </h4>
                    <div> {date_str} </div>
                </div>
                <br/>
                <br/>

                <div>
                    {escaped_content}
                </div>
            </div>
            <br/>
          """
        return html_message, []

    def _generate_html_body(self) -> str:
        """Generate the full HTML body for the PDF."""
        escaped_title = escape(self.form_data.title)
        return f"""
        <html>
            <head>
                <meta name="viewport" content="width=device-width, initial-scale=1.0" />
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
        """Convert LaTeX in content to KaTeX-rendered HTML fragments (no PNGs)."""
        latex_expressions = self.detect_latex_in_message(content)
        if not latex_expressions:
            return escape(content)

        # Replace from the end to preserve indices
        latex_expressions.sort(key=lambda x: x['start'], reverse=True)
        html_content = content
        for latex in latex_expressions:
            expr = latex['expression']
            # Insert soft breakpoints to avoid overflow in PDF layout
            expr = self._insert_soft_breaks(expr)
            try:
                fragment = self.katex_compiler.render_to_html(expr, latex['display'])
                print(f"✅ LaTeX rendered successfully: {expr[:50]}...")
            except Exception as e:
                print(f"❌ LaTeX rendering failed for '{expr[:50]}...': {e}")
                fragment = escape(expr)
            # Replace the full matched delimiter range with the fragment
            html_content = html_content[:latex['start']] + fragment + html_content[latex['end']:]

        return html_content

    def _insert_soft_breaks(self, expr: str) -> str:
        """Insert KaTeX-friendly soft breakpoints into long LaTeX expressions.
        Uses \allowbreak around common binary and relation operators so lines can wrap.
        This is conservative to avoid breaking commands.
        """
        # Multi-token operators first
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

        # Single-character operators: + - = , ; :
        # Add allowbreak on both sides where reasonable. Avoid adding inside commands: negative lookbehind for \\ and letters
        # plus
        expr = re.sub(r"(?<![\\\\a-zA-Z0-9])\+", r"\\allowbreak{}+\\allowbreak{}", expr)
        # minus
        expr = re.sub(r"(?<![\\\\a-zA-Z0-9])-", r"\\allowbreak{}-\\allowbreak{}", expr)
        # equals
        expr = re.sub(r"(?<![\\\\a-zA-Z0-9])=", r"\\allowbreak{}=\\allowbreak{}", expr)
        # comma and semicolon and colon (after only)
        expr = expr.replace(",", ",\\allowbreak{}")
        expr = expr.replace(";", ";\\allowbreak{}")
        expr = expr.replace(":", ":\\allowbreak{}")

        # Around parentheses and brackets, allow a break after closing tokens
        expr = expr.replace(")", ")\\allowbreak{}")
        expr = expr.replace("]", "]\\allowbreak{}")

        return expr

    # Removed FPDF message rendering (WeasyPrint renders full HTML)

    # Removed FPDF text cleanup helper

    # Removed FPDF content embedding (unused)

    def generate_chat_pdf(self) -> bytes:
        """
        Generate a PDF from chat messages. Uses WeasyPrint to render HTML with KaTeX.
        """
        try:
            # Build complete HTML document with KaTeX CSS
            messages_html_parts = []
            all_latex_images = []
            for message in self.form_data.messages:
                self.print_latex_detected(message)
                html_message, latex_images = self._build_html_message(message)
                messages_html_parts.append(html_message)
                all_latex_images.extend(latex_images)

            self.messages_html = "\n".join(messages_html_parts)
            html_body = self._generate_html_body()
            # Inject KaTeX CSS link and wrapping rules to avoid cropping long math
            html_full = html_body.replace(
                "<head>",
                (
                    "<head>\n"
                    "<link rel=\"stylesheet\" href=\"https://cdn.jsdelivr.net/npm/katex@0.16.21/dist/katex.min.css\">\n"
                    "<style>\n"
                    "  /* Ensure long KaTeX math wraps within page width */\n"
                    "  .katex, .katex-display {\n"
                    "    white-space: normal !important;\n"
                    "  }\n"
                    "  .katex-display {\n"
                    "    overflow-wrap: anywhere;\n"
                    "    word-break: break-word;\n"
                    "    line-break: anywhere;\n"
                    "    text-align: center;\n"
                    "  }\n"
                    "  /* Constrain KaTeX box to page width */\n"
                    "  .katex-display > .katex {\n"
                    "    display: inline-block;\n"
                    "    max-width: 100%;\n"
                    "  }\n"
                    "  /* Slightly reduce display font to mitigate overflow */\n"
                    "  .katex-display .katex {\n"
                    "    font-size: 1em;\n"
                    "  }\n"
                    "</style>\n"
                )
            )

            # Render PDF via WeasyPrint
            pdf_bytes = HTML(string=html_full).write_pdf()
            return pdf_bytes
        except Exception as e:
            raise e
        finally:
            self.cleanup_temp_images()
