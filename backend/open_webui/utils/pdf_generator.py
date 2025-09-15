from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Dict, Any, List
from html import escape
import re
import base64
import tempfile
import os
import uuid

from markdown import markdown
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
from matplotlib import mathtext
from PIL import Image

import site
from fpdf import FPDF

from open_webui.env import STATIC_DIR, FONTS_DIR
from open_webui.models.chats import ChatTitleMessagesForm


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

        self.css = Path(STATIC_DIR / "assets" / "pdf-style.css").read_text()

    def format_timestamp(self, timestamp: float) -> str:
        """Convert a UNIX timestamp to a formatted date string."""
        try:
            date_time = datetime.fromtimestamp(timestamp)
            return date_time.strftime("%Y-%m-%d, %H:%M:%S")
        except (ValueError, TypeError) as e:
            # Log the error if necessary
            return ""

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
        
        for pattern, delimiter, display in patterns:
            for match in re.finditer(pattern, content, re.MULTILINE | re.DOTALL):
                latex_expr = match.group(1).strip()  # Remove leading/trailing whitespace
                # Additional validation to ensure we have meaningful content
                if latex_expr and len(latex_expr) > 0 and not latex_expr.isspace():
                    found_latex.append({
                        "expression": latex_expr,
                        "full_match": match.group(0),
                        "display": display,
                        "delimiter": delimiter,
                        "start": match.start(),
                        "end": match.end()
                    })
        
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

    def compile_latex_to_image(self, latex_expr: str, display: bool = False) -> str:
        """
        Compile a LaTeX expression to a temporary image file.
        Returns the file path that can be referenced in HTML.
        """
        try:
            # Configure matplotlib for LaTeX rendering
            plt.rcParams['mathtext.default'] = 'regular'
            plt.rcParams['font.family'] = 'serif'
            plt.rcParams['font.size'] = 12
            
            # More conservative adaptive sizing based on expression length
            expr_length = len(latex_expr)
            
            # Determine base font size and figure dimensions (more conservative)
            if expr_length > 100:  # Very long expressions
                base_fontsize = 12
                fig_width = 6.0
                fig_height = 1.2
            elif expr_length > 50:  # Long expressions
                base_fontsize = 11
                fig_width = 5.0
                fig_height = 1.0
            elif expr_length > 20:  # Medium expressions
                base_fontsize = 10
                fig_width = 4.0
                fig_height = 0.9
            else:  # Short expressions
                base_fontsize = 10
                fig_width = 3.0
                fig_height = 0.8
            
            # Adjust for display mode (block equations) - more conservative
            if display:
                base_fontsize = int(base_fontsize * 1.1)  # Reduced from 1.2
                fig_width = fig_width * 1.1  # Reduced from 1.2
                fig_height = fig_height * 1.1  # Reduced from 1.2
            
            fig, ax = plt.subplots(figsize=(fig_width, fig_height))
            ax.axis('off')
            
            # Render the LaTeX expression
            ax.text(0.5, 0.5, f'${latex_expr}$', 
                   transform=ax.transAxes, 
                   fontsize=base_fontsize,
                   ha='center', va='center',
                   usetex=False)  # Use mathtext instead of LaTeX for better compatibility
            
            # Create a temporary file
            temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            temp_path = temp_file.name
            temp_file.close()
            
            # Save to temporary file with minimal padding
            plt.savefig(temp_path, format='png', dpi=150, bbox_inches='tight', 
                       pad_inches=0.005, facecolor='white', edgecolor='none')
            
            # Store the temp file path for cleanup
            self.temp_images.append(temp_path)
            
            # Clean up matplotlib
            plt.close(fig)
            
            return temp_path
            
        except Exception as e:
            print(f"Error compiling LaTeX '{latex_expr}': {e}")
            # Return a placeholder or the original LaTeX expression
            return f"<span style='color: red; font-family: monospace;'>LaTeX Error: {escape(latex_expr)}</span>"

    def process_latex_in_content(self, content: str) -> tuple[str, List[Dict[str, Any]]]:
        """
        Process content to identify LaTeX expressions and prepare them for PDF embedding.
        Returns the processed content and a list of LaTeX image data for direct PDF embedding.
        """
        latex_expressions = self.detect_latex_in_message(content)
        
        if not latex_expressions:
            return content, []
        
        # Sort by position in reverse order to avoid index shifting
        latex_expressions.sort(key=lambda x: x['start'], reverse=True)
        
        processed_content = content
        latex_images = []
        
        for latex in latex_expressions:
            # Compile LaTeX to image
            img_path = self.compile_latex_to_image(latex['expression'], latex['display'])
            
            # Check if compilation was successful (path exists) or failed (error message)
            if os.path.exists(img_path):
                # Create a placeholder for the LaTeX image
                placeholder = f"[LATEX_IMAGE_{len(latex_images)}]"
                
                # Store image data for later embedding
                latex_images.append({
                    'placeholder': placeholder,
                    'path': img_path,
                    'expression': latex['expression'],
                    'display': latex['display'],
                    'start': latex['start'],
                    'end': latex['end']
                })
                
                # Replace the LaTeX expression with placeholder
                start = latex['start']
                end = latex['end']
                processed_content = processed_content[:start] + placeholder + processed_content[end:]
            else:
                # Use the error message as is
                start = latex['start']
                end = latex['end']
                processed_content = processed_content[:start] + img_path + processed_content[end:]
        
        return processed_content, latex_images

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

        # Process LaTeX expressions and get image data
        processed_content, latex_images = self.process_latex_in_content(content)
        
        # Escape the processed content
        escaped_content = escape(processed_content)

        # Replace newlines with line breaks
        escaped_content = escaped_content.replace("\n", "<br/>")
        
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
        return html_message, latex_images

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

    def _add_message_to_pdf(self, pdf: FPDF, message: Dict[str, Any], latex_images: List[Dict[str, Any]]):
        """Add a single message to the PDF with embedded LaTeX images."""
        role = message.get("role", "user")
        content = message.get("content", "")
        timestamp = message.get("timestamp")
        model = message.get("model") if role == "assistant" else ""

        # Add message header
        pdf.set_font("NotoSans", "b", 14)
        pdf.cell(0, 10, f"{role.title()}", ln=True)
        
        if model:
            pdf.set_font("NotoSans", "", 10)
            pdf.cell(0, 5, f"Model: {model}", ln=True)
        
        if timestamp:
            date_str = self.format_timestamp(timestamp)
            pdf.cell(0, 5, f"Time: {date_str}", ln=True)
        
        pdf.ln(5)
        
        # Process content and add LaTeX images
        self._add_content_with_latex(pdf, content, latex_images)
        
        pdf.ln(10)

    def _clean_text_around_latex(self, text: str) -> str:
        """Clean up text around LaTeX expressions to remove stray symbols."""
        # Remove common LaTeX delimiter artifacts
        text = re.sub(r'\s*\$+\s*', ' ', text)  # Remove stray $ symbols
        text = re.sub(r'\s*\?+\s*', ' ', text)  # Remove stray ? symbols
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        return text.strip()

    def _add_content_with_latex(self, pdf: FPDF, content: str, latex_images: List[Dict[str, Any]]):
        """Add content to PDF with LaTeX images embedded at appropriate positions."""
        if not latex_images:
            # No LaTeX, just add text
            pdf.set_font("NotoSans", "", 12)
            lines = content.split('\n')
            for line in lines:
                if line.strip():  # Only add non-empty lines
                    pdf.multi_cell(0, 6, line, ln=True)
            return
        
        # Sort latex images by position
        latex_images.sort(key=lambda x: x['start'])
        
        current_pos = 0
        pdf.set_font("NotoSans", "", 12)
        
        for latex_img in latex_images:
            # Add text before LaTeX
            if current_pos < latex_img['start']:
                text_before = content[current_pos:latex_img['start']]
                text_before = self._clean_text_around_latex(text_before)
                if text_before:
                    lines = text_before.split('\n')
                    for line in lines:
                        if line.strip():  # Only add non-empty lines
                            pdf.multi_cell(0, 6, line, ln=True)
            
            # Add LaTeX image with page break handling
            try:
                if os.path.exists(latex_img['path']):
                    # Get image dimensions
                    from PIL import Image
                    with Image.open(latex_img['path']) as img:
                        img_width, img_height = img.size
                    
                    # More conservative target size based on expression length
                    expr_length = len(latex_img['expression'])
                    
                    if expr_length > 100:  # Very long expressions
                        target_width = 80  # Reduced from 120
                        target_height = 20  # Reduced from 30
                    elif expr_length > 50:  # Long expressions
                        target_width = 70  # Reduced from 90
                        target_height = 18  # Reduced from 25
                    elif expr_length > 20:  # Medium expressions
                        target_width = 60  # Reduced from 70
                        target_height = 16  # Reduced from 20
                    else:  # Short expressions
                        target_width = 50  # Reduced from 60
                        target_height = 15  # Reduced from 18
                    
                    # Calculate scale to fit within target dimensions
                    scale_x = target_width / (img_width * 0.35)
                    scale_y = target_height / (img_height * 0.35)
                    scale = min(scale_x, scale_y)  # Allow scaling up for better readability
                    
                    # More conservative minimum scale
                    min_scale = 0.6  # Reduced from 0.8 to allow more scaling down
                    max_scale = 1.2  # Add maximum scale to prevent oversizing
                    scale = max(min_scale, min(scale, max_scale))
                    
                    display_width = img_width * 0.35 * scale
                    display_height = img_height * 0.35 * scale
                    
                    # Check if image fits on current page with better margin
                    current_y = pdf.get_y()
                    page_height = pdf.h - pdf.t_margin - pdf.b_margin
                    space_needed = display_height + 10  # Increased margin for safety
                    
                    if current_y + space_needed > page_height:
                        # Image doesn't fit, add page break
                        pdf.add_page()
                        # Add some space after page break for better appearance
                        pdf.ln(5)
                    
                    # Add image
                    pdf.image(latex_img['path'], x=pdf.get_x(), y=pdf.get_y(), 
                            w=display_width, h=display_height)
                    pdf.set_y(pdf.get_y() + display_height + 0.5)
                else:
                    # Fallback to text if image not found
                    pdf.cell(0, 6, f"[LaTeX Error: {latex_img['expression']}]", ln=True)
            except Exception as e:
                print(f"Error adding LaTeX image: {e}")
                pdf.cell(0, 6, f"[LaTeX Error: {latex_img['expression']}]", ln=True)
            
            current_pos = latex_img['end']
        
        # Add remaining text after last LaTeX
        if current_pos < len(content):
            text_after = content[current_pos:]
            text_after = self._clean_text_around_latex(text_after)
            if text_after:
                lines = text_after.split('\n')
                for line in lines:
                    if line.strip():  # Only add non-empty lines
                        pdf.multi_cell(0, 6, line, ln=True)

    def generate_chat_pdf(self) -> bytes:
        """
        Generate a PDF from chat messages with embedded LaTeX images.
        """
        try:
            global FONTS_DIR

            pdf = FPDF()
            pdf.add_page()

            # When running using `pip install` the static directory is in the site packages.
            if not FONTS_DIR.exists():
                FONTS_DIR = Path(site.getsitepackages()[0]) / "static/fonts"
            # When running using `pip install -e .` the static directory is in the site packages.
            # This path only works if `open-webui serve` is run from the root of this project.
            if not FONTS_DIR.exists():
                FONTS_DIR = Path("./backend/static/fonts")

            pdf.add_font("NotoSans", "", f"{FONTS_DIR}/NotoSans-Regular.ttf")
            pdf.add_font("NotoSans", "b", f"{FONTS_DIR}/NotoSans-Bold.ttf")
            pdf.add_font("NotoSans", "i", f"{FONTS_DIR}/NotoSans-Italic.ttf")
            pdf.add_font("NotoSansKR", "", f"{FONTS_DIR}/NotoSansKR-Regular.ttf")
            pdf.add_font("NotoSansJP", "", f"{FONTS_DIR}/NotoSansJP-Regular.ttf")
            pdf.add_font("NotoSansSC", "", f"{FONTS_DIR}/NotoSansSC-Regular.ttf")
            pdf.add_font("Twemoji", "", f"{FONTS_DIR}/Twemoji.ttf")

            pdf.set_font("NotoSans", size=12)
            pdf.set_fallback_fonts(
                ["NotoSansKR", "NotoSansJP", "NotoSansSC", "Twemoji"]
            )

            pdf.set_auto_page_break(auto=True, margin=15)

            # Add title
            pdf.set_font("NotoSans", "b", 16)
            pdf.cell(0, 10, self.form_data.title, ln=True)
            pdf.ln(10)

            # Process each message
            all_latex_images = []
            for message in self.form_data.messages:
                # Check for LaTeX code in the message and print to terminal
                self.print_latex_detected(message)
                
                # Process LaTeX expressions
                processed_content, latex_images = self.process_latex_in_content(message.get("content", ""))
                all_latex_images.extend(latex_images)
                
                # Add message to PDF
                self._add_message_to_pdf(pdf, message, latex_images)

            # Save the pdf
            pdf_bytes = pdf.output()

            return bytes(pdf_bytes)
        except Exception as e:
            raise e
        finally:
            # Clean up temporary image files
            self.cleanup_temp_images()
