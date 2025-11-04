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
        """Convert a UNIX timestamp to a formatted date string in EST timezone."""
        try:
            est_offset = timedelta(hours=-4)
            est_tz = timezone(est_offset)
            date_time = datetime.fromtimestamp(timestamp, tz=est_tz)
            return date_time.strftime("%I:%M:%S %p EST (UTC-4)")
        except (ValueError, TypeError):
            return ""

    def detect_latex_in_message(self, content: str) -> List[Dict[str, Any]]:
        """
        Detect LaTeX code in a chat message content.
        Returns a list of dictionaries containing LaTeX expressions found.
        Based on the frontend katex-extension.ts implementation.
        """
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

    def _convert_svg_to_base64_image(self, html_fragment: str) -> str:
        """
        Convert SVG elements in HTML fragment to base64-encoded image tags.
        
        This function handles KaTeX-generated SVG math symbols and converts them to base64 images
        for reliable PDF rendering in WeasyPrint. It specially handles:
        - Stretchy symbols (vertical lines, sqrt radicals, sqrt overlines)
        - Size constraints to prevent symbols from stretching across the page
        - Positioning for sqrt overlines to appear above content without covering it
        """
        import re
        import base64
        
        svg_pattern = r'<svg[^>]*>.*?</svg>'
        svg_matches = list(re.finditer(svg_pattern, html_fragment, re.DOTALL | re.IGNORECASE))
        
        if not svg_matches:
            return html_fragment
        
        # Extract text content to estimate width for content-aware sizing
        # Remove SVG elements and root symbols to get clean text length
        fragment_without_svg = re.sub(r'<svg[^>]*>.*?</svg>', '', html_fragment, flags=re.DOTALL | re.IGNORECASE)
        fragment_without_svg = re.sub(r'<span[^>]*class=["\'][^"\']*root[^"\']*["\'][^>]*>.*?</span>', '', fragment_without_svg, flags=re.DOTALL | re.IGNORECASE)
        text_content = re.sub(r'<[^>]+>', '', fragment_without_svg)
        text_length = len(text_content.strip())
        # Estimate width: ~5px per character, with minimum 40px for small expressions
        fallback_width = max(40, text_length * 5) if text_length > 0 else 80
        
        result = html_fragment
        for match in reversed(svg_matches):
            svg_html = match.group(0)
            
            try:
                viewbox_match = re.search(r'viewBox=["\']([^"\']+)["\']', svg_html, re.IGNORECASE)
                vb_x = vb_y = vb_width = vb_height = None
                
                if viewbox_match:
                    parts = viewbox_match.group(1).split()
                    if len(parts) >= 4:
                        try:
                            vb_x = float(parts[0])
                            vb_y = float(parts[1])
                            vb_width = float(parts[2])
                            vb_height = float(parts[3])
                        except (ValueError, IndexError):
                            pass
                
                # Parse SVG width and height attributes (in em units)
                # KaTeX uses em units for sizing, which we need to convert to pixels
                svg_width_em = None
                svg_height_em = None
                width_attr_match = re.search(r'width=["\']([^"\']+)["\']', svg_html, re.IGNORECASE)
                height_attr_match = re.search(r'height=["\']([^"\']+)["\']', svg_html, re.IGNORECASE)
                
                if width_attr_match:
                    width_attr = width_attr_match.group(1).lower()
                    em_match = re.search(r'(\d+(?:\.\d+)?)em', width_attr)
                    if em_match:
                        svg_width_em = float(em_match.group(1))
                
                if height_attr_match:
                    height_attr = height_attr_match.group(1).lower()
                    em_match = re.search(r'(\d+(?:\.\d+)?)em', height_attr)
                    if em_match:
                        svg_height_em = float(em_match.group(1))
                
                # Detect stretchy symbols that need special handling
                # Stretchy symbols adjust their size based on content (e.g., sqrt, vertical lines)
                is_stretchy = False
                is_horizontal_stretchy = False  # True for sqrt overlines, horizontal lines
                
                # Detect stretchy by explicit large width values (1e6em, 10000em, 100%, or >= 100em)
                if width_attr_match:
                    width_attr = width_attr_match.group(1).lower()
                    if '1e6' in width_attr or '10000' in width_attr or width_attr == '100%':
                        is_stretchy = True
                    elif svg_width_em and svg_width_em >= 100:
                        is_stretchy = True
                
                # Detect stretchy by aspect ratio of width/height in em units
                if svg_width_em and svg_height_em:
                    # Vertical stretchy: narrow width (< 1em) with tall height (> 1.5em)
                    # This catches sqrt radicals (V-shaped part) and vertical lines
                    if svg_width_em < 1.0 and svg_height_em > 1.5:
                        is_stretchy = True
                    # Horizontal stretchy: wide width (>= 5em) with small height (< 2em)
                    # This catches sqrt overlines (horizontal bar above content)
                    elif svg_width_em >= 5.0 and svg_height_em < 2.0:
                        is_horizontal_stretchy = True
                        is_stretchy = True
                    # Also catch moderately wide overlines (3-5em range)
                    elif svg_width_em >= 3.0 and svg_height_em < 1.5 and svg_width_em > svg_height_em * 3:
                        is_horizontal_stretchy = True
                        is_stretchy = True
                    # Catch inline sqrt overlines (2-3em range, like sqrt(x))
                    elif svg_width_em >= 2.0 and svg_height_em < 1.2 and svg_width_em > svg_height_em * 2.5:
                        is_horizontal_stretchy = True
                        is_stretchy = True
                
                # Fallback: detect stretchy by viewBox aspect ratio when em values aren't available
                if vb_width and vb_height and vb_width > 0 and vb_height > 0:
                    aspect_ratio_width = vb_width / vb_height if vb_height > 0 else 1
                    aspect_ratio_height = vb_height / vb_width if vb_width > 0 else 1
                    # Very skewed aspect ratios indicate stretchy symbols
                    if aspect_ratio_width < 0.1 or aspect_ratio_height > 10.0:
                        is_stretchy = True
                        if aspect_ratio_width > 10.0:
                            is_horizontal_stretchy = True
                    # Moderately wide viewBox (2:1 or wider) likely indicates sqrt overline
                    elif aspect_ratio_width > 2.0:
                        is_horizontal_stretchy = True
                        is_stretchy = True
                
                # Convert em units to pixels (1em ≈ 10px in math context)
                em_to_px = 10.0
                
                # Handle horizontal stretchy elements (sqrt overlines, horizontal lines)
                if is_stretchy and is_horizontal_stretchy:
                    # Detect inline context (piecewise functions, inline math)
                    # Short text length or small em width suggests inline usage
                    is_likely_inline = text_length < 15 or (svg_width_em is not None and svg_width_em < 8.0)
                    
                    # Content-aware width calculation: use tighter constraints for inline sqrt
                    if is_likely_inline:
                        # Very short expressions like sqrt(x) need even smaller constraints
                        if text_length <= 3:
                            content_based_width = min(fallback_width, 50.0)
                            max_width = max(25.0, content_based_width * 0.8)
                        else:
                            content_based_width = min(fallback_width, 80.0)
                            max_width = max(30.0, content_based_width * 0.85)
                    else:
                        # Display mode sqrt: allow larger width but still constrained
                        content_based_width = min(fallback_width, 150.0)
                        max_width = max(50.0, content_based_width * 0.9)
                    
                    if svg_width_em is not None and svg_height_em is not None:
                        calculated_width = svg_width_em * em_to_px
                        if text_length <= 3:
                            svg_width = min(calculated_width, max_width, 40.0)
                        else:
                            svg_width = min(calculated_width, max_width)
                        svg_height = svg_height_em * em_to_px
                        if is_likely_inline:
                            if svg_height > 35.0:
                                svg_height = 35.0
                            if svg_height < 2.5:
                                svg_height = 2.5
                        else:
                            if svg_height > 50.0:
                                svg_height = 50.0
                            if svg_height < 3.0:
                                svg_height = 3.0
                    elif vb_width and vb_height and vb_width > 0 and vb_height > 0:
                        aspect_ratio = vb_width / vb_height if vb_height > 0 else 1
                        if is_likely_inline:
                            estimated_height = max(2.5, min(35.0, vb_height * 0.02))
                        else:
                            estimated_height = max(3.0, min(45.0, vb_height * 0.025))
                        svg_height = estimated_height
                        svg_width = min(estimated_height * aspect_ratio, max_width)
                    else:
                        svg_width = max_width
                        if is_likely_inline:
                            svg_height = 8.0
                        else:
                            svg_height = 10.0
                    
                    fixed_svg = re.sub(r'width=["\'][^"\']*["\']', f'width="{svg_width}px"', svg_html, flags=re.IGNORECASE)
                    fixed_svg = re.sub(r'height=["\'][^"\']*["\']', f'height="{svg_height}px"', fixed_svg, flags=re.IGNORECASE)
                    
                    if 'width=' not in fixed_svg.lower():
                        fixed_svg = re.sub(r'(<svg[^>]*)', f'\\1 width="{svg_width}px"', fixed_svg, flags=re.IGNORECASE)
                    if 'height=' not in fixed_svg.lower():
                        fixed_svg = re.sub(r'(<svg[^>]*)', f'\\1 height="{svg_height}px"', fixed_svg, flags=re.IGNORECASE)
                    
                    if 'viewBox=' not in fixed_svg:
                        fixed_svg = re.sub(r'(<svg[^>]*)', f'\\1 viewBox="{vb_x} {vb_y} {vb_width} {vb_height}"', fixed_svg, flags=re.IGNORECASE)
                    
                    img_width = svg_width
                    img_height = svg_height
                    
                # Handle vertical stretchy symbols (sqrt radicals V-shape, vertical lines)
                elif is_stretchy and svg_width_em is not None and svg_height_em is not None:
                    # Scale up height to make sqrt radicals taller and more prominent
                    # Factor of 2.3 ensures the V-shape properly encompasses the expression
                    height_scale_factor = 2.3
                    scaled_height_em = svg_height_em * height_scale_factor
                    svg_width = max(2.5, svg_width_em * em_to_px)  # Minimum 2.5px for visibility
                    svg_height = scaled_height_em * em_to_px
                    
                    # Ensure minimum height for visibility
                    min_height = 30.0
                    if svg_height < min_height:
                        svg_height = min_height
                    
                    # Clamp to reasonable maximums to prevent pathological cases
                    max_height = 150.0  # Normal maximum
                    absolute_max = 250.0  # Absolute maximum for very tall expressions
                    
                    if svg_height > absolute_max:
                        height_ratio = absolute_max / svg_height
                        svg_height = absolute_max
                        svg_width = max(2.5, svg_width * height_ratio)
                    elif svg_height > max_height:
                        svg_height = max_height
                    
                    fixed_svg = re.sub(r'width=["\'][^"\']*["\']', f'width="{svg_width}px"', svg_html, flags=re.IGNORECASE)
                    fixed_svg = re.sub(r'height=["\'][^"\']*["\']', f'height="{svg_height}px"', fixed_svg, flags=re.IGNORECASE)
                    
                    if 'width=' not in fixed_svg.lower():
                        fixed_svg = re.sub(r'(<svg[^>]*)', f'\\1 width="{svg_width}px"', fixed_svg, flags=re.IGNORECASE)
                    if 'height=' not in fixed_svg.lower():
                        fixed_svg = re.sub(r'(<svg[^>]*)', f'\\1 height="{svg_height}px"', fixed_svg, flags=re.IGNORECASE)
                    
                    if 'viewBox=' not in fixed_svg:
                        fixed_svg = re.sub(r'(<svg[^>]*)', f'\\1 viewBox="{vb_x} {vb_y} {vb_width} {vb_height}"', fixed_svg, flags=re.IGNORECASE)
                    
                    img_width = svg_width
                    img_height = svg_height
                    
                # Handle vertical stretchy detected from viewBox when em values aren't available
                elif is_stretchy and not is_horizontal_stretchy and vb_width and vb_height and vb_width > 0 and vb_height > 0:
                    # Apply same height scaling for sqrt radicals
                    height_scale_factor = 2.3
                    aspect_ratio = vb_height / vb_width if vb_width > 0 else 1
                    # Scale from viewBox coordinates (0.015 factor converts viewBox units to pixels)
                    estimated_width = max(2.5, vb_width * 0.015)
                    estimated_height = vb_height * 0.015 * height_scale_factor
                    
                    svg_width = estimated_width
                    svg_height = estimated_height
                    
                    min_height = 30.0
                    if svg_height < min_height:
                        svg_height = min_height
                    
                    max_height = 150.0
                    absolute_max = 250.0
                    
                    if svg_height > absolute_max:
                        height_ratio = absolute_max / svg_height
                        svg_height = absolute_max
                        svg_width = max(2.5, svg_width * height_ratio)
                    elif svg_height > max_height:
                        svg_height = max_height
                    
                    fixed_svg = re.sub(r'width=["\'][^"\']*["\']', f'width="{svg_width}px"', svg_html, flags=re.IGNORECASE)
                    fixed_svg = re.sub(r'height=["\'][^"\']*["\']', f'height="{svg_height}px"', fixed_svg, flags=re.IGNORECASE)
                    
                    if 'width=' not in fixed_svg.lower():
                        fixed_svg = re.sub(r'(<svg[^>]*)', f'\\1 width="{svg_width}px"', fixed_svg, flags=re.IGNORECASE)
                    if 'height=' not in fixed_svg.lower():
                        fixed_svg = re.sub(r'(<svg[^>]*)', f'\\1 height="{svg_height}px"', fixed_svg, flags=re.IGNORECASE)
                    
                    if 'viewBox=' not in fixed_svg:
                        fixed_svg = re.sub(r'(<svg[^>]*)', f'\\1 viewBox="{vb_x} {vb_y} {vb_width} {vb_height}"', fixed_svg, flags=re.IGNORECASE)
                    
                    img_width = svg_width
                    img_height = svg_height
                    
                else:
                    # Handle non-stretchy SVGs: fix problematic large width values
                    # KaTeX sometimes generates very large width values that need to be clamped
                    fixed_svg = svg_html
                    fixed_svg = re.sub(r'width=["\']1e6em["\']', f'width="{fallback_width}px"', fixed_svg, flags=re.IGNORECASE)
                    fixed_svg = re.sub(r'width=["\']10000em["\']', f'width="{fallback_width}px"', fixed_svg, flags=re.IGNORECASE)
                    fixed_svg = re.sub(r'width=["\']100%["\']', f'width="{fallback_width}px"', fixed_svg, flags=re.IGNORECASE)
                    
                    # Replace any width >= 5em with fallback width (catches missed stretchy symbols)
                    def replace_large_width(match):
                        em_value_str = match.group(1)
                        try:
                            em_value = float(em_value_str)
                            if em_value >= 5:
                                return f'width="{fallback_width}px"'
                        except (ValueError, TypeError):
                            pass
                        return match.group(0)
                    fixed_svg = re.sub(r'width=["\'](\d+(?:\.\d+)?)em["\']', replace_large_width, fixed_svg, flags=re.IGNORECASE)
                    
                    # Check if this might be inline (for appropriate sizing)
                    is_likely_inline_non_stretchy = text_length < 15 or (svg_width_em is not None and svg_width_em < 8.0)
                    
                    potential_sqrt = False
                    if vb_width and vb_height and vb_width > 0 and vb_height > 0:
                        aspect_ratio = vb_width / vb_height if vb_height > 0 else 1
                        if aspect_ratio > 3.0:
                            potential_sqrt = True
                    
                    if svg_width_em is not None:
                        if svg_width_em >= 5.0:
                            if is_likely_inline_non_stretchy:
                                if text_length <= 3:
                                    svg_width_em = 3.0
                                else:
                                    svg_width_em = 4.0
                            else:
                                svg_width_em = 5.0
                        img_width = svg_width_em * em_to_px
                        if is_likely_inline_non_stretchy:
                            if text_length <= 3:
                                max_width = 30.0
                            else:
                                max_width = 40.0
                        else:
                            max_width = 50.0
                        if img_width > max_width:
                            img_width = max_width
                    elif potential_sqrt:
                        if is_likely_inline_non_stretchy and text_length <= 3:
                            img_width = 30.0
                        elif is_likely_inline_non_stretchy:
                            img_width = 40.0
                        else:
                            img_width = 50.0
                    else:
                        img_width = fallback_width
                    
                    img_height = None
                    if svg_height_em is not None:
                        img_height = svg_height_em * em_to_px
                        max_height = 40.0
                        if img_height > max_height:
                            img_height = max_height
                    elif vb_height and vb_width and vb_width > 0:
                        aspect_ratio = vb_height / vb_width
                        img_height = img_width * aspect_ratio
                        max_height = 40.0
                        if img_height > max_height:
                            img_height = max_height
                            if img_height / aspect_ratio < img_width:
                                img_width = img_height / aspect_ratio if aspect_ratio > 0 else fallback_width
                    
                    fixed_svg = re.sub(r'width=["\'][^"\']*["\']', f'width="{img_width}px"', fixed_svg, flags=re.IGNORECASE)
                    if 'width=' not in fixed_svg.lower():
                        fixed_svg = re.sub(r'(<svg[^>]*)', f'\\1 width="{img_width}px"', fixed_svg, flags=re.IGNORECASE)
                    
                    if img_height is not None:
                        fixed_svg = re.sub(r'height=["\'][^"\']*["\']', f'height="{img_height}px"', fixed_svg, flags=re.IGNORECASE)
                        if 'height=' not in fixed_svg.lower():
                            fixed_svg = re.sub(r'(<svg[^>]*)', f'\\1 height="{img_height}px"', fixed_svg, flags=re.IGNORECASE)
                
                svg_bytes = fixed_svg.encode('utf-8')
                svg_base64 = base64.b64encode(svg_bytes).decode('utf-8')
                data_uri = f"data:image/svg+xml;base64,{svg_base64}"
                
                # Create img tag with appropriate positioning
                if is_stretchy and img_height:
                    if is_horizontal_stretchy:
                        # Position sqrt overline above content to prevent overlap
                        # Base offset ensures spacing between overline and content
                        base_offset = max(15.0, img_height * 1.5)
                        # Add extra spacing for longer expressions to accommodate taller content
                        extra_spacing = min(8.0, text_length * 0.3)
                        offset_px = base_offset + extra_spacing
                        container_height = offset_px
                        # Wrap in span with height to reserve space, position overline at top
                        img_tag = f'<span style="display: inline-block; width: {img_width}px; height: {container_height}px; position: relative; vertical-align: baseline; overflow: visible;"><img src="{data_uri}" style="display: block; width: {img_width}px; max-width: {img_width}px; height: {img_height}px; position: absolute; top: 0; left: 0;" /></span>'
                    else:
                        img_tag = f'<img src="{data_uri}" style="display: inline-block; vertical-align: baseline; position: relative; width: {img_width}px; height: {img_height}px; z-index: 0;" />'
                else:
                    if img_width <= 50.0:
                        img_tag = f'<img src="{data_uri}" style="display: inline-block; vertical-align: baseline; position: relative; width: {img_width}px; max-width: {img_width}px; height: auto; z-index: 0;" />'
                    else:
                        img_tag = f'<img src="{data_uri}" style="display: inline-block; vertical-align: baseline; position: relative; width: {img_width}px; height: auto; z-index: 0;" />'
                
                result = result[:match.start()] + img_tag + result[match.end():]
                
                if self.debug_pdf:
                    print(f"PDF: Converted SVG to base64 image (stretchy={is_stretchy}, width={img_width}px, height={img_height if img_height else 'auto'}, text_length={text_length})")
                    
            except Exception as e:
                if self.debug_pdf:
                    print(f"PDF: Failed to convert SVG to base64: {e}")
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
        
        # Pre-process content to ensure lettered items (a), (b), (i), (ii), etc. 
        # and numbered items start on new lines for proper markdown rendering
        # This handles cases where items like "(a)" and "(b)" should be on separate lines
        html_content = self._prepare_markdown_line_breaks(html_content)
        
        # Then convert markdown to HTML (markdown library preserves existing HTML tags by default)
        # This handles **bold**, ## headers, *italic*, etc.
        # Use extensions for better markdown support (tables, fenced code blocks, etc.)
        html_content = markdown.markdown(
            html_content, 
            extensions=['fenced_code', 'tables', 'toc']
        )
        
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

                <div>
                    {html_content}
                </div>
            </div>
            <br/>
          """
        return html_message, []

    def _prepare_markdown_line_breaks(self, content: str) -> str:
        """
        Prepare content for markdown conversion by ensuring lettered items and 
        numbered items start on new lines.
        
        This handles cases where items like "(a)" and "(b)" should be on separate lines
        but might appear on the same line due to single newlines being collapsed by markdown.
        """
        result = content
        
        # Pattern to match lettered/numbered items that appear on the same line
        # We need to ensure each item starts on a new line for proper markdown rendering
        
        # Handle cases where items like "- (a)" appear after text on the same line
        # This ensures items are separated by newlines
        # Match "- (item)" patterns that appear after non-newline characters
        patterns = [
            # Lettered items: (a), (b), etc.
            (r'([^\n])\s*-\s*\(([a-z])\)', r'\1\n- (\2)'),  # lowercase letters
            (r'([^\n])\s*-\s*\(([A-Z])\)', r'\1\n- (\2)'),  # uppercase letters
            # Numbered items: (1), (2), etc.
            (r'([^\n])\s*-\s*\((\d+)\)', r'\1\n- (\2)'),
            # Roman numerals
            (r'([^\n])\s*-\s*\(([ivxlcdm]+)\)', r'\1\n- (\2)'),  # lowercase roman
            (r'([^\n])\s*-\s*\(([IVXLCDM]+)\)', r'\1\n- (\2)'),  # uppercase roman
        ]
        
        for pattern, replacement in patterns:
            result = re.sub(pattern, replacement, result)
        
        # Also handle items without "- " prefix that should be list items
        # Pattern: "(a)" or "(b)" that appear after text (not already part of a list)
        # Convert them to markdown list items
        item_patterns = [
            (r'([^\n-])\s+\(([a-z])\)', r'\1\n- (\2)'),  # lowercase letters with space before
            (r'([^\n-])\s+\(([A-Z])\)', r'\1\n- (\2)'),  # uppercase letters with space before
            (r'([^\n-])\s+\((\d+)\)', r'\1\n- (\2)'),  # numbers with space before
            (r'([^\n-])\s+\(([ivxlcdm]+)\)', r'\1\n- (\2)'),  # lowercase roman with space
            (r'([^\n-])\s+\(([IVXLCDM]+)\)', r'\1\n- (\2)'),  # uppercase roman with space
        ]
        
        for pattern, replacement in item_patterns:
            result = re.sub(pattern, replacement, result)
        
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
        t0 = time.perf_counter()
        latex_expressions = self.detect_latex_in_message(content)
        if not latex_expressions:
            return escape(content)

        # Sort by start position in reverse order so we can replace from end to start
        # This preserves indices when doing string replacements
        latex_expressions.sort(key=lambda x: x['start'], reverse=True)
        html_content = content
        
        if self.debug_pdf or self.debug_latex:
            print("*"*20)
            print(f"PDF: Processing {len(latex_expressions)} LaTeX expressions")
            for idx, latex in enumerate(latex_expressions[:5]):  # Show first 5
                print(f"  [{idx}] {latex['delimiter']} display={latex['display']} expr_preview={repr(latex['expression'][:60])}")
            if len(latex_expressions) > 5:
                print(f"  ... and {len(latex_expressions) - 5} more")
            print("*"*20)
        
        # Prepare expressions for KaTeX rendering
        to_render: list[tuple[str, bool]] = []
        
        for idx, latex in enumerate(latex_expressions):
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
            if self.debug_latex:
                print(f"PDF: LaTeX idx={idx} delimiter={latex['delimiter']} display={latex['display']} expr={repr(expr)}")

        try:
            t1 = time.perf_counter()
            rendered = self.katex_compiler.render_many_to_html(to_render) if to_render else []
            t2 = time.perf_counter()
            if self.debug_pdf:
                print("*"*20, f"\nPDF: KaTeX batch rendered {len(to_render)} items in {t2 - t1:.3f}s\n", "*"*20)
        except Exception as ex:
            if self.debug_pdf:
                print("*"*20, f"\nPDF: KaTeX render error -> fallback: {ex}\n", "*"*20)
            rendered = [escape(e) for e, _ in to_render]

        # Convert SVG elements to base64 images for reliable PDF rendering
        # WeasyPrint has issues with inline SVG, so we convert to base64 images
        final_fragments: list[str] = []
        svg_count = 0
        for idx, fragment in enumerate(rendered):
            if '<svg' in fragment:
                svg_count += 1
                if self.debug_pdf:
                    print(f"PDF: Fragment {idx} contains SVG; converting to base64 image")
                    svg_match = re.search(r'<svg[^>]*>.*?</svg>', fragment, re.DOTALL | re.IGNORECASE)
                    if svg_match:
                        svg_preview = svg_match.group(0)[:200]
                        print(f"PDF: SVG preview: {svg_preview}...")
                try:
                    # Convert SVG to base64 image with proper sizing and positioning
                    converted = self._convert_svg_to_base64_image(fragment)
                    final_fragments.append(converted)
                except Exception as e:
                    if self.debug_pdf:
                        print(f"PDF: SVG conversion failed for fragment {idx}: {e}")
                    # Fallback: keep original fragment (may not render well in PDF)
                    final_fragments.append(fragment)
            else:
                final_fragments.append(fragment)
        
        if self.debug_pdf and svg_count > 0:
            print(f"PDF: Converted {svg_count} SVG elements to base64 images")

        for latex, fragment in zip(latex_expressions, final_fragments):
            html_content = html_content[:latex['start']] + fragment + html_content[latex['end']:]

        html_content = html_content.replace('\\[', '').replace('\\]', '')

        if self.debug_pdf:
            print("*"*20, f"\nPDF: splice complete for {len(latex_expressions)} items, output_len={len(html_content)}\n", "*"*20)
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
            
            html_full = html_body.replace(
                "<head>",
                (
                    "<head>\n"
                    f'<link rel="stylesheet" href="assets/katex/katex.min.css">\n'
                    "<style>\n"
                    f'{self.css}\n'
                    "  .katex, .katex-display {\n"
                    "    white-space: normal !important;\n"
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
