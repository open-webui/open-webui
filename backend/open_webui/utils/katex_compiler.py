import subprocess
import os
import json
from typing import List
from pathlib import Path
import re
from html import escape
import time
import logging

"""
This code requires Pango system dependency to run
"""

class KaTeXCompiler:
    """
    Compile LaTeX expressions using KaTeX for better matrix and complex expression support.
    This provides much better support for complex LaTeX expressions compared to matplotlib mathtext.
    """
    
    def __init__(self, debug: bool = False):
        self.temp_images = []
        self.node_modules_path = self._find_node_modules()
        self._cache = {}
        self._logger = logging.getLogger(__name__)
        self._debug = debug

    def _find_node_modules(self) -> Path:
        """Find the node_modules directory containing KaTeX."""
        # Try different possible locations
        possible_paths = [
            Path(__file__).parent.parent.parent.parent / "node_modules",
            Path(__file__).parent.parent.parent.parent.parent / "node_modules",
            Path(__file__).parent / "node_modules",
            Path.cwd() / "node_modules",
        ]
        
        for path in possible_paths:
            if path.exists() and (path / "katex").exists():
                print("*"*20, f"Found node_modules at {path}. Current working directory is {Path.cwd()}", "*"*20)
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

        # Use /tmp directory (works in OpenShift)
        project_temp_dir = Path('/tmp')

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
            
            # Use /tmp directory (works in OpenShift)
            project_temp_dir = Path('/tmp')
            
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
            # Cache check
            cache_key = (latex_expr, bool(display))
            if cache_key in self._cache:
                return self._cache[cache_key]
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

            # Use /tmp directory (works in OpenShift)
            project_temp_dir = Path('/tmp')
            
            script_path = project_temp_dir / 'katex_render_fragment.cjs'
            with open(script_path, 'w') as f:
                f.write(script_content)

            t0 = time.perf_counter()
            proc = subprocess.run(
                ['node', str(script_path)],
                capture_output=True,
                text=True,
                timeout=15,
                cwd=str(self.node_modules_path.parent)
            )
            t1 = time.perf_counter()

            try:
                os.unlink(script_path)
            except Exception:
                pass

            if proc.returncode != 0:
                raise RuntimeError(proc.stderr)

            data = json.loads(proc.stdout or '{}')
            if not data.get('success'):
                raise RuntimeError(data.get('error', 'KaTeX render failed'))

            html = data['html']
            self._cache[cache_key] = html
            if self._debug:
                self._logger.info(
                    f"KaTeX: single render display={display} len={len(latex_expr)} took {t1 - t0:.3f}s"
                )
            return html
        except Exception as e:
            raise e

    def render_many_to_html(self, items: list[tuple[str, bool]]) -> list[str]:
        """Batch render multiple LaTeX expressions to KaTeX HTML in a single Node process."""
        # Prepare results with cache hits filled
        results: list[str | None] = []
        to_render = []
        index_map = []
        for idx, (expr, display) in enumerate(items):
            key = (expr, bool(display))
            if key in self._cache:
                results.append(self._cache[key])
            else:
                results.append(None)
                index_map.append(idx)
                to_render.append({"latex": expr, "display": bool(display)})

        if not to_render:
            # All cached
            return [r for r in results if r is not None]

        # Ensure Node.js is available
        chk = subprocess.run(['node', '--version'], capture_output=True, text=True, timeout=5)
        if chk.returncode != 0:
            # Fallback: render individually
            for j, item in zip(index_map, to_render):
                html = self.render_to_html(item["latex"], item["display"])
                self._cache[(item["latex"], item["display"])] = html
                results[j] = html
            return [r if r is not None else '' for r in results]

        katex_path = str(self.node_modules_path / 'katex')
        payload = json.dumps(to_render)

        script_lines = [
            "const katex = require('" + katex_path + "');",
            "let input = '';",
            "process.stdin.on('data', c => input += c);",
            "process.stdin.on('end', () => {",
            "  try {",
            "    const items = JSON.parse(input);",
            "    const out = items.map(it => {",
            "      try {",
            "        const html = katex.renderToString(it.latex, {",
            "          displayMode: !!it.display, throwOnError: false, trust: true, strict: false, output: 'html'",
            "        });",
            "        return { success: true, html };",
            "      } catch (e) {",
            "        return { success: false, error: e.message };",
            "      }",
            "    });",
            "    process.stdout.write(JSON.stringify(out));",
            "  } catch (e) {",
            "    process.stdout.write(JSON.stringify({ fatal: true, error: e.message }));",
            "  }",
            "});",
        ]
        script_content = "\n".join(script_lines)

        tmp_dir = Path('/tmp')
        script_path = tmp_dir / 'katex_render_many.cjs'
        with open(script_path, 'w') as f:
            f.write(script_content)

        t0 = time.perf_counter()
        proc = subprocess.run(
            ['node', str(script_path)],
            input=payload,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(self.node_modules_path.parent)
        )
        t1 = time.perf_counter()

        try:
            os.unlink(script_path)
        except Exception:
            pass

        if proc.returncode != 0:
            raise RuntimeError(proc.stderr or 'KaTeX batch render failed')

        data = json.loads(proc.stdout or '[]')
        if isinstance(data, dict) and data.get('fatal'):
            raise RuntimeError(data.get('error', 'KaTeX batch fatal error'))
        if not isinstance(data, list) or len(data) != len(to_render):
            raise RuntimeError('KaTeX batch returned unexpected result')

        for idx, item, res in zip(index_map, to_render, data):
            if not res.get('success'):
                raise RuntimeError(res.get('error', 'KaTeX render failed'))
            html = res['html']
            self._cache[(item["latex"], item["display"])] = html
            results[idx] = html

        if self._debug:
            self._logger.info(
                f"KaTeX: batch render count={len(to_render)} cached={len(items)-len(to_render)} took {t1 - t0:.3f}s payload_len={len(payload)}"
            )

        return [r if r is not None else '' for r in results]

    def cleanup_temp_images(self):
        """Clean up temporary image files."""
        for temp_path in self.temp_images:
            try:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            except Exception as e:
                print(f"Error cleaning up temp file {temp_path}: {e}")
        self.temp_images.clear()
        
        # Clean up any remaining KaTeX files in /tmp
        temp_dir = Path('/tmp')
        if temp_dir.exists():
            try:
                for pattern in ("katex_*", "weasyprint-*"):
                    for temp_file in temp_dir.glob(pattern):
                        if temp_file.is_file():
                            temp_file.unlink()
            except Exception as e:
                print(f"Error cleaning up temp directory {temp_dir}: {e}")

    
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
