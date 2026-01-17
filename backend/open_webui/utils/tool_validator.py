"""
Tool Output Validator

Validates LLM tool output against regex rules:
- allow: At least one pattern must match for valid output
- forbidden: No pattern should match (any match = invalid)

On validation failure, triggers recovery flow similar to tool-unsupported handling.
"""

import re
import logging
from typing import Optional, Dict, Tuple
from dataclasses import dataclass

from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("MAIN", logging.INFO))


@dataclass
class ValidationResult:
    """Result of validating tool output"""

    is_valid: bool
    error_type: Optional[str] = None  # 'no_allow_match', 'forbidden_match'
    error_details: Optional[str] = None  # Specific pattern that failed
    matched_allow_pattern: Optional[str] = None  # Which allow pattern matched


class ToolValidator:
    """Validates tool output against regex rules"""

    def __init__(self, validation_rules: Optional[Dict] = None):
        """
        Args:
            validation_rules: Dict with 'allow' and 'forbidden' regex patterns
                {
                    "allow": {"pattern_name": "regex_pattern", ...},
                    "forbidden": {"pattern_name": "regex_pattern", ...}
                }
        """
        self.rules = validation_rules or {}
        self.allow_patterns = self._compile_patterns(self.rules.get("allow", {}))
        self.forbidden_patterns = self._compile_patterns(self.rules.get("forbidden", {}))

        log.debug(
            f"[TOOL VALIDATOR] Initialized with {len(self.allow_patterns)} allow, "
            f"{len(self.forbidden_patterns)} forbidden patterns"
        )

    def _compile_patterns(self, patterns: Dict[str, str]) -> Dict[str, re.Pattern]:
        """Compile regex patterns, logging any compilation errors"""
        compiled = {}
        for name, pattern in patterns.items():
            try:
                compiled[name] = re.compile(pattern, re.DOTALL | re.MULTILINE)
            except re.error as e:
                log.error(f"[TOOL VALIDATOR] Invalid regex pattern '{name}': {e}")
        return compiled

    def _strip_latex_content(self, text: str) -> str:
        """
        Strip LaTeX math content from text before validation.

        This allows mathematical notation (like pi, theta, etc.) inside
        LaTeX delimiters without triggering forbidden pattern matches.

        Args:
            text: Input text with potential LaTeX content

        Returns:
            Text with LaTeX content replaced by placeholders
        """
        import re
        # Remove inline LaTeX: $...$
        text = re.sub(r'\$[^$]+\$', '[LATEX]', text)
        # Remove display LaTeX: $$...$$
        text = re.sub(r'\$\$[^$]+\$\$', '[LATEX]', text)
        # Remove LaTeX blocks: \[...\] or \(...\)
        text = re.sub(r'\\\[[^\]]+\\\]', '[LATEX]', text)
        text = re.sub(r'\\\([^\)]+\\\)', '[LATEX]', text)
        return text

    def validate(self, output: str) -> ValidationResult:
        """
        Validate tool output against rules.

        Validation logic:
        1. Check forbidden patterns first - any match = invalid
        2. Check allow patterns - at least one must match for valid output
        3. If no allow patterns defined, skip allow check

        Note: LaTeX math content ($...$, $$...$$, etc.) is stripped before
        validation to allow mathematical notation without triggering false positives.

        Args:
            output: Tool output string to validate

        Returns:
            ValidationResult with is_valid and error details
        """
        log.debug(f"[TOOL VALIDATOR] Validating output ({len(output)} chars)")

        # Strip LaTeX content to avoid false positives on math symbols
        output_for_validation = self._strip_latex_content(output)
        log.debug(f"[TOOL VALIDATOR] After stripping LaTeX: {len(output_for_validation)} chars")

        # Step 1: Check forbidden patterns
        for name, pattern in self.forbidden_patterns.items():
            if pattern.search(output_for_validation):
                log.warning(f"[TOOL VALIDATOR] Forbidden pattern matched: {name}")
                return ValidationResult(
                    is_valid=False,
                    error_type="forbidden_match",
                    error_details=f"Output matches forbidden pattern: {name}",
                )

        # Step 2: Check allow patterns (if any defined)
        if self.allow_patterns:
            for name, pattern in self.allow_patterns.items():
                if pattern.search(output_for_validation):
                    log.debug(f"[TOOL VALIDATOR] Allow pattern matched: {name}")
                    return ValidationResult(is_valid=True, matched_allow_pattern=name)

            # No allow pattern matched
            log.warning("[TOOL VALIDATOR] No allow pattern matched")
            return ValidationResult(
                is_valid=False,
                error_type="no_allow_match",
                error_details="Output does not match any allowed pattern",
            )

        # No allow patterns defined - pass validation
        log.debug("[TOOL VALIDATOR] No allow patterns defined, validation passed")
        return ValidationResult(is_valid=True)

    def has_rules(self) -> bool:
        """Check if any validation rules are defined"""
        return bool(self.allow_patterns or self.forbidden_patterns)


def validate_tool_output(
    output: str, validation_rules: Optional[Dict]
) -> Tuple[bool, Optional[str]]:
    """
    Convenience function to validate tool output.

    Args:
        output: Tool output to validate
        validation_rules: Validation rules dict

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not validation_rules:
        return (True, None)

    validator = ToolValidator(validation_rules)
    result = validator.validate(output)

    if result.is_valid:
        return (True, None)
    else:
        return (False, result.error_details)
