"""Security guard using LLM Guard for prompt injection and jailbreak detection."""

from typing import Optional, Tuple

from langfuse.decorators import observe


class SecurityGuard:
    """Security scanner for detecting malicious prompts."""

    def __init__(self, enable_tracing: bool = True):
        """Initialize security guard with LLM Guard scanners.

        Args:
            enable_tracing: Whether to enable Langfuse tracing (default: True)
        """
        self.enable_tracing = enable_tracing

        try:
            from llm_guard.input_scanners import PromptInjection, Toxicity
            from llm_guard.input_scanners.prompt_injection import MatchType

            # Initialize scanners
            self.prompt_injection_scanner = PromptInjection(
                threshold=0.5,  # 0-1, lower = stricter
                match_type=MatchType.FULL,  # Check entire prompt
            )

            self.toxicity_scanner = Toxicity(
                threshold=0.7,  # 0-1, lower = stricter
                use_onnx=False,  # Use transformers (slower but more accurate)
            )

            self.enabled = True
            print("SecurityGuard initialized with LLM Guard scanners")

        except ImportError:
            print(
                "Warning: llm-guard not installed, security scanning disabled"
            )
            print("Install with: pip install llm-guard")
            self.enabled = False
            self.prompt_injection_scanner = None
            self.toxicity_scanner = None

    @observe()
    def check_prompt_safety(
        self, prompt: str, check_toxicity: bool = True
    ) -> Tuple[bool, str, float]:
        """Check prompt for security issues.

        Args:
            prompt: The user prompt to check
            check_toxicity: Whether to also check for toxic content

        Returns:
            Tuple of (is_safe, risk_level, risk_score)
            - is_safe: True if prompt passes all checks
            - risk_level: "low", "medium", or "high"
            - risk_score: 0-1, where 1 is highest risk
        """
        if not self.enabled:
            return True, "low", 0.0

        max_risk_score = 0.0
        issues = []

        try:
            # Check for prompt injection
            sanitized_prompt, is_valid, risk_score = (
                self.prompt_injection_scanner.scan(prompt)
            )

            if not is_valid:
                issues.append("prompt_injection")
                max_risk_score = max(max_risk_score, risk_score)

            # Check for toxicity if requested
            if check_toxicity:
                sanitized_prompt, is_valid, risk_score = (
                    self.toxicity_scanner.scan(prompt)
                )

                if not is_valid:
                    issues.append("toxicity")
                    max_risk_score = max(max_risk_score, risk_score)

            # Determine risk level
            if max_risk_score >= 0.7:
                risk_level = "high"
            elif max_risk_score >= 0.4:
                risk_level = "medium"
            else:
                risk_level = "low"

            is_safe = len(issues) == 0
            return is_safe, risk_level, max_risk_score

        except Exception as e:
            print(f"Error during security check: {e}")
            # Fail open (allow prompt) but log the error
            return True, "low", 0.0

    @observe()
    def detect_jailbreak(self, prompt: str) -> Tuple[bool, float]:
        """Detect jailbreak attempts in prompts.

        Note: LLM Guard's PromptInjection scanner covers jailbreak detection.

        Args:
            prompt: The user prompt to check

        Returns:
            Tuple of (is_jailbreak, confidence_score)
        """
        if not self.enabled:
            return False, 0.0

        try:
            # Use prompt injection scanner for jailbreak detection
            _, is_valid, risk_score = self.prompt_injection_scanner.scan(prompt)

            is_jailbreak = not is_valid
            return is_jailbreak, risk_score

        except Exception as e:
            print(f"Error during jailbreak detection: {e}")
            return False, 0.0
