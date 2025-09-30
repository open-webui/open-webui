import subprocess
import os
import json
from typing import List
from pathlib import Path
import re
from html import escape

"""
This code requires Pango system dependency to run
"""

class KaTeXCompiler:
    """
    Compile LaTeX expressions using KaTeX for better matrix and complex expression support.
    This provides much better support for complex LaTeX expressions compared to matplotlib mathtext.
    """
    
    def __init__(self):
        self.temp_images = []
        self.node_modules_path = self._find_node_modules()
    
    def _find_node_modules(self) -> Path:
        """Find the node_modules directory containing KaTeX."""
        # Try different possible locations
        possible_paths = [
            Path(__file__).parent.parent.parent.parent / "node_modules",
            Path(__file__).parent.parent.parent.parent.parent / "node_modules",
            Path.cwd() / "node_modules",
        ]
        
        for path in possible_paths:
            if path.exists() and (path / "katex").exists():
                return path

        # Fallback to current directory
        return Path.cwd() / "node_modules"
    
    def compile_latex_to_image(self, latex_expr: str, display: bool = False) -> List[str]:
        """
        Compile LaTeX expression to image files using KaTeX.
        Returns a list of file paths that can be referenced in HTML.
        """
        try:
            # Clean and validate the LaTeX expression
            cleaned_expr = self._clean_latex_expression(latex_expr)
            
            # Split long expressions into manageable parts
            latex_parts = self._split_latex_expression(cleaned_expr, max_length=200)
            image_paths = []
            
            for i, part in enumerate(latex_parts):
                # Compile each part using KaTeX
                img_path = self._compile_single_expression(part, display, i)
                if img_path:
                    image_paths.append(img_path)
                else:
                    # Fallback to error message
                    image_paths.append(f"<span style='color: red; font-family: monospace;'>LaTeX Error: {escape(part)}</span>")
            
            return image_paths
            
        except Exception as e:
            print(f"Error in KaTeX compilation: {e}")
            return [f"<span style='color: red; font-family: monospace;'>LaTeX Error: {escape(latex_expr)}</span>"]
    
    def _clean_latex_expression(self, latex_expr: str) -> str:
        """Clean and validate LaTeX expression for KaTeX compatibility."""
        # Remove common problematic characters
        cleaned = latex_expr.strip()
        
        # Handle boxed expressions - KaTeX supports \boxed
        if cleaned.startswith('\\boxed{') and cleaned.endswith('}'):
            # Keep \boxed as KaTeX supports it
            pass
        
        # Don't escape backslashes for LaTeX - they are needed for LaTeX commands
        # Only escape characters that are problematic for JSON
        cleaned = cleaned.replace('"', '\\"')    # Escape quotes for JSON
        cleaned = cleaned.replace('\n', '\\n')   # Escape newlines for JSON
        
        return cleaned
    
    def _split_latex_expression(self, latex_expr: str, max_length: int = 200) -> List[str]:
        """
        Split a long LaTeX expression into smaller parts at logical break points.
        """
        if len(latex_expr) <= max_length:
            return [latex_expr]
        
        # Define splitting patterns with their corresponding characters
        split_patterns = [
            (r'\\\\(?=\s)', '\\\\'),  # Split at line breaks
            (r'\s*=\s*', ' = '),      # Split at equals signs
            (r'\s*\+\s*', ' + '),     # Split at plus signs
            (r'\s*-\s*', ' - '),      # Split at minus signs
            (r'\s*,\s*', ', '),       # Split at commas
            (r'\s*;\s*', '; '),       # Split at semicolons
            (r'\s+', ' '),            # Split at whitespace as last resort
        ]
        
        parts = []
        remaining = latex_expr.strip()
        
        while len(remaining) > max_length:
            split_found = False
            
            for pattern, separator in split_patterns:
                # Find the last occurrence of the pattern within max_length
                matches = list(re.finditer(pattern, remaining[:max_length]))
                if matches:
                    # Use the last match to split
                    last_match = matches[-1]
                    split_pos = last_match.start()
                    
                    # Extract the part before the split
                    part = remaining[:split_pos].strip()
                    if part:
                        parts.append(part)
                    
                    # Update remaining text
                    remaining = remaining[last_match.end():].strip()
                    split_found = True
                    break
            
            if not split_found:
                # If no good split point found, force split at max_length
                parts.append(remaining[:max_length].strip())
                remaining = remaining[max_length:].strip()
        
        # Add any remaining text
        if remaining:
            parts.append(remaining)
        
        return parts
    
    def _compile_single_expression(self, latex_expr: str, display: bool, part_index: int) -> str:
        """Compile a single LaTeX expression to PNG image using KaTeX + wkhtmltoimage (no Chromium)."""
        # Ensure wkhtmltoimage is available
        try:
            check = subprocess.run(["wkhtmltoimage", "--version"], capture_output=True, text=True, timeout=5)
            if check.returncode != 0:
                raise RuntimeError("wkhtmltoimage not available")
        except Exception:
            raise RuntimeError("wkhtmltoimage is required for KaTeX->PNG conversion but was not found on PATH.")

        # Create a temporary Node.js script for KaTeX compilation (CommonJS)
        katex_path = str(self.node_modules_path / "katex")
        display_mode = str(display).lower()

        # Build the script to produce a full HTML file with KaTeX-rendered math
        script_lines = [
            "const katex = require('" + katex_path + "');",
            "const fs = require('fs');",
            "",
            "const latex = " + json.dumps(latex_expr) + ";",
            "const displayMode = " + display_mode + ";",
            "",
            "try {",
            "  const html = katex.renderToString(latex, {",
            "    displayMode: displayMode,",
            "    throwOnError: false,",
            "    trust: true,",
            "    strict: false,",
            "    output: 'html'",
            "  });",
            "  const fullHtml = `",
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            "  <meta charset=\"utf-8\">",
            "  <link rel=\"stylesheet\" href=\"https://cdn.jsdelivr.net/npm/katex@0.16.21/dist/katex.min.css\">",
            "  <style>",
            "    body { margin: 0; padding: 20px; background: white; font-family: 'Times New Roman', serif; }",
            "    .katex-display { margin: 0; text-align: center; }",
            "    .katex { font-size: 18px; }",
            "  </style>",
            "</head>",
            "<body>",
            "  <div class=\"${displayMode ? 'katex-display' : ''}\">${html}</div>",
            "</body>",
            "</html>",
            "`;",
            "  const htmlPath = process.argv[2];",
            "  fs.writeFileSync(htmlPath, fullHtml);",
            "  console.log(JSON.stringify({ success: true, outputPath: htmlPath }));",
            "} catch (error) {",
            "  console.log(JSON.stringify({ success: false, error: error.message }));",
            "}",
        ]

        script_content = "\n".join(script_lines)

        # Create files in project temp dir
        project_temp_dir = Path(__file__).parent.parent.parent.parent / "temp"
        project_temp_dir.mkdir(exist_ok=True)

        script_path = project_temp_dir / f"katex_script_{part_index}.cjs"
        with open(script_path, 'w') as script_file:
            script_file.write(script_content)

        html_path = project_temp_dir / f"katex_part{part_index}.html"
        png_path = project_temp_dir / f"katex_part{part_index}.png"

        # Run Node to produce HTML
        result = subprocess.run([
            'node', str(script_path), str(html_path)
        ], capture_output=True, text=True, timeout=30, cwd=str(self.node_modules_path.parent))

        # Clean up script file
        try:
            os.unlink(script_path)
        except Exception:
            pass

        if result.returncode != 0:
            raise RuntimeError(f"Node.js error: {result.stderr}")

        data = json.loads(result.stdout or '{}')
        if not data.get('success'):
            raise RuntimeError(f"KaTeX error: {data.get('error', 'Unknown error')}")

        # Convert HTML to PNG via wkhtmltoimage (fast, no Chromium)
        conv = subprocess.run([
            'wkhtmltoimage', '--format', 'png', '--quality', '100', '--width', '800', '--height', '200',
            '--disable-smart-shrinking', '--zoom', '1.5', str(html_path), str(png_path)
        ], capture_output=True, text=True, timeout=30)

        if conv.returncode != 0 or not png_path.exists():
            raise RuntimeError(f"wkhtmltoimage failed: {conv.stderr}")

        self.temp_images.append(str(png_path))
        return str(png_path)

    def _compile_with_katex_html(self, latex_expr: str, display: bool, part_index: int) -> str:
        """Legacy helper retained for compatibility; not used when strict PNG output is required."""
        try:
            # Create a temporary Node.js script for KaTeX compilation
            katex_path = str(self.node_modules_path / "katex")
            display_mode = str(display).lower()
            
            # Build the script using string concatenation
            script_lines = [
                "const katex = require('" + katex_path + "');",
                "const fs = require('fs');",
                "",
                "const latex = " + json.dumps(latex_expr) + ";",
                "const displayMode = " + display_mode + ";",
                "",
                "try {",
                "    // Render LaTeX to HTML",
                "    const html = katex.renderToString(latex, {",
                "        displayMode: displayMode,",
                "        throwOnError: false,",
                "        trust: true,",
                "        strict: false,",
                "        output: 'html'",
                "    });",
                "    ",
                "    // Create a complete HTML document",
                "    const fullHtml = `",
                "<!DOCTYPE html>",
                "<html>",
                "<head>",
                "    <meta charset=\"utf-8\">",
                "    <link rel=\"stylesheet\" href=\"https://cdn.jsdelivr.net/npm/katex@0.16.21/dist/katex.min.css\">",
                "    <style>",
                "        body {",
                "            margin: 0;",
                "            padding: 20px;",
                "            background: white;",
                "            font-family: 'Times New Roman', serif;",
                "        }",
                "        .katex-display {",
                "            margin: 0;",
                "            text-align: center;",
                "        }",
                "        .katex {",
                "            font-size: 24px;",
                "        }",
                "    </style>",
                "</head>",
                "<body>",
                "    <div class=\"${displayMode ? 'katex-display' : ''}\">",
                "        ${html}",
                "    </div>",
                "</body>",
                "</html>",
                "`;",
                "    ",
                "    // Write HTML to temporary file",
                "    const htmlPath = process.argv[2];",
                "    fs.writeFileSync(htmlPath, fullHtml);",
                "    ",
                "    console.log(JSON.stringify({",
                "        success: true,",
                "        html: html,",
                "        outputPath: htmlPath,",
                "        method: 'html'",
                "    }));",
                "    ",
                "} catch (error) {",
                "    console.log(JSON.stringify({",
                "        success: false,",
                "        error: error.message",
                "    }));",
                "}"
            ]
            
            script_content = "\n".join(script_lines)
            
            # Create temporary files in project temp directory
            project_temp_dir = Path(__file__).parent.parent.parent.parent / "temp"
            project_temp_dir.mkdir(exist_ok=True)
            
            # Create script file in project temp directory (use .cjs for CommonJS)
            script_path = project_temp_dir / f"katex_script_{part_index}.cjs"
            with open(script_path, 'w') as script_file:
                script_file.write(script_content)
            
            # Create HTML file in project temp directory
            html_path = project_temp_dir / f"katex_part{part_index}.html"
            
            # Run the Node.js script from the project root where node_modules is located
            result = subprocess.run([
                'node', script_path, html_path
            ], capture_output=True, text=True, timeout=30, cwd=str(self.node_modules_path.parent))
            
            # Clean up script file
            os.unlink(script_path)
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                if data['success']:
                    html_path = data['outputPath']
                    if os.path.exists(html_path):
                        # Return HTML path (caller should not use this if PNG is mandatory)
                        self.temp_images.append(html_path)
                        return html_path
                    else:
                        print(f"Output file not found: {html_path}")
                        return None
                else:
                    print(f"KaTeX error: {data.get('error', 'Unknown error')}")
                    return None
            else:
                print(f"Node.js error: {result.stderr}")
                return None
                
        except Exception as e:
            print(f"KaTeX HTML compilation failed: {e}")
            return None
    
    def render_to_html(self, latex_expr: str, display: bool = False) -> str:
        """Render a LaTeX expression to a KaTeX HTML fragment (no images)."""
        try:
            # Ensure Node.js is available
            result = subprocess.run(['node', '--version'], capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                raise RuntimeError('Node.js is required to render KaTeX HTML')

            katex_path = str(self.node_modules_path / 'katex')
            display_mode = str(display).lower()

            script_lines = [
                "const katex = require('" + katex_path + "');",
                "",
                "const latex = " + json.dumps(latex_expr) + ";",
                "const displayMode = " + display_mode + ";",
                "",
                "try {",
                "  const html = katex.renderToString(latex, {",
                "    displayMode: displayMode,",
                "    throwOnError: false,",
                "    trust: true,",
                "    strict: false,",
                "    output: 'html'",
                "  });",
                "  console.log(JSON.stringify({ success: true, html }));",
                "} catch (error) {",
                "  console.log(JSON.stringify({ success: false, error: error.message }));",
                "}",
            ]

            script_content = "\n".join(script_lines)

            project_temp_dir = Path(__file__).parent.parent.parent.parent / 'temp'
            project_temp_dir.mkdir(exist_ok=True)
            script_path = project_temp_dir / 'katex_render_fragment.cjs'
            with open(script_path, 'w') as f:
                f.write(script_content)

            proc = subprocess.run(
                ['node', str(script_path)],
                capture_output=True,
                text=True,
                timeout=15,
                cwd=str(self.node_modules_path.parent)
            )

            try:
                os.unlink(script_path)
            except Exception:
                pass

            if proc.returncode != 0:
                raise RuntimeError(proc.stderr)

            data = json.loads(proc.stdout or '{}')
            if not data.get('success'):
                raise RuntimeError(data.get('error', 'KaTeX render failed'))

            return data['html']
        except Exception as e:
            raise e

    def cleanup_temp_images(self):
        """Clean up temporary image files."""
        for temp_path in self.temp_images:
            try:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            except Exception as e:
                print(f"Error cleaning up temp file {temp_path}: {e}")
        self.temp_images.clear()
        
        # Also clean up any remaining files in the project temp directory
        project_temp_dir = Path(__file__).parent.parent.parent.parent / "temp"
        if project_temp_dir.exists():
            try:
                for temp_file in project_temp_dir.glob("katex_*"):
                    if temp_file.is_file():
                        temp_file.unlink()
            except Exception as e:
                print(f"Error cleaning up project temp directory: {e}")
    
    def is_available(self) -> bool:
        """Check if KaTeX compilation is available."""
        try:
            # Check if Node.js is available
            result = subprocess.run(['node', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                return False
            
            # Check if KaTeX is available
            katex_path = self.node_modules_path / "katex"
            if not katex_path.exists():
                return False
            
            return True
        except:
            return False
