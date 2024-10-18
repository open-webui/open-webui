from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Dict, Any, List

from markdown import markdown

import site
from fpdf import FPDF

from open_webui.env import STATIC_DIR, FONTS_DIR
from open_webui.apps.webui.models.chats import ChatTitleMessagesForm


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

        self.css = Path(STATIC_DIR / "assets" / "pdf-style.css").read_text()

    def format_timestamp(self, timestamp: float) -> str:
        """Convert a UNIX timestamp to a formatted date string."""
        try:
            date_time = datetime.fromtimestamp(timestamp)
            return date_time.strftime("%Y-%m-%d, %H:%M:%S")
        except (ValueError, TypeError) as e:
            # Log the error if necessary
            return ""

    def _build_html_message(self, message: Dict[str, Any]) -> str:
        """Build HTML for a single message."""
        role = message.get("role", "user")
        content = message.get("content", "")
        timestamp = message.get("timestamp")

        model = message.get("model") if role == "assistant" else ""

        date_str = self.format_timestamp(timestamp) if timestamp else ""

        # extends pymdownx extension to convert markdown to html.
        # - https://facelessuser.github.io/pymdown-extensions/usage_notes/
        html_content = markdown(content, extensions=["pymdownx.extra"])

        html_message = f"""
              <div class="message">
                  <small> {date_str} </small>
                  <div>
                      <h2>
                          <strong>{role.title()}</strong>
                          <small class="text-muted">{model}</small>
                      </h2>
                  </div>
                  <div class="markdown-section">
                      {html_content}
                  </div>
              </div>
          """
        return html_message

    def _generate_html_body(self) -> str:
        """Generate the full HTML body for the PDF."""
        return f"""
        <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
            </head>
            <body>
                <div class="container"> 
                    <div class="text-center">
                        <h1>{self.form_data.title}</h1>
                    </div>
                    <div>
                        {self.messages_html}
                    </div>
                </div>
            </body>
        </html>
        """

    def generate_chat_pdf(self) -> bytes:
        """
        Generate a PDF from chat messages.
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

            pdf.set_font("NotoSans", size=12)
            pdf.set_fallback_fonts(["NotoSansKR", "NotoSansJP", "NotoSansSC"])

            pdf.set_auto_page_break(auto=True, margin=15)

            # Build HTML messages
            messages_html_list: List[str] = [
                self._build_html_message(msg) for msg in self.form_data.messages
            ]
            self.messages_html = "<div>" + "".join(messages_html_list) + "</div>"

            # Generate full HTML body
            self.html_body = self._generate_html_body()

            pdf.write_html(self.html_body)

            # Save the pdf with name .pdf
            pdf_bytes = pdf.output()

            return bytes(pdf_bytes)
        except Exception as e:
            raise e
