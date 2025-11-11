"""Gemini API client wrapper for SQLOp.

Provides simple interface for text generation and structured JSON output
using Google's Gemini models via Vertex AI or API key authentication.
"""

import json
import logging
from typing import Any, Dict, Generator, Optional

from google import genai
from google.api_core import exceptions as google_exceptions
from google.genai import types
from langfuse.decorators import langfuse_context, observe

from utils.config import GeminiConfig

logger = logging.getLogger(__name__)


class GeminiClient:
    """Wrapper for Google Gemini API with support for streaming and structured output."""

    def __init__(self, config: GeminiConfig, enable_tracing: bool = True):
        """Initialize Gemini client with given configuration.

        Args:
            config: GeminiConfig with model settings and authentication
            enable_tracing: Whether to enable Langfuse tracing (default: True)
        """
        self.config = config
        self.enable_tracing = enable_tracing

        # Initialize client based on authentication method
        if self.config.is_vertex_ai():
            # Vertex AI authentication
            self._client = genai.Client(
                vertexai=True,
                project=self.config.gcp_project_id,
                location=self.config.gcp_location,
            )
        else:
            # API key authentication
            self._client = genai.Client(api_key=self.config.api_key)

    @observe(as_type="generation")
    def generate_text(
        self,
        prompt: str,
        stream: bool = False,
        temperature: Optional[float] = None,
    ) -> str | Generator[str, None, None]:
        """Generate text response from a prompt.

        Args:
            prompt: The prompt to send to Gemini
            stream: If True, returns a generator that yields text chunks
            temperature: Override default temperature (0.0-2.0)

        Returns:
            Complete text response (if stream=False) or generator of text chunks (if stream=True)

        Raises:
            google_exceptions.ResourceExhausted: If API quota exceeded
            google_exceptions.DeadlineExceeded: If request times out
        """
        temp = temperature if temperature is not None else self.config.temperature
        max_tokens = 8192

        generation_config = types.GenerateContentConfig(
            temperature=temp,
            max_output_tokens=max_tokens,
        )

        # Track metadata in Langfuse
        if self.enable_tracing:
            langfuse_context.update_current_observation(
                model=self.config.model,
                metadata={
                    "temperature": temp,
                    "max_output_tokens": max_tokens,
                    "stream": stream,
                },
            )

        if stream:
            return self._generate_streaming(prompt, generation_config)

        try:
            response = self._client.models.generate_content(
                model=self.config.model,
                contents=prompt,
                config=generation_config,
            )

            # Track token usage if available
            if self.enable_tracing and hasattr(response, "usage_metadata"):
                usage = response.usage_metadata
                langfuse_context.update_current_observation(
                    usage={
                        "input": usage.prompt_token_count,
                        "output": usage.candidates_token_count,
                        "total": usage.total_token_count,
                    }
                )

            return response.text

        except google_exceptions.ResourceExhausted as e:
            logger.error(f"Gemini API quota exceeded: {e}")
            raise
        except google_exceptions.DeadlineExceeded as e:
            logger.error(f"Gemini API request timeout: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in Gemini API call: {e}")
            raise

    @observe(as_type="generation")
    def _generate_streaming(
        self, prompt: str, config: types.GenerateContentConfig
    ) -> Generator[str, None, None]:
        """Generate streaming text response.

        Args:
            prompt: The prompt to send to Gemini
            config: Generation configuration

        Yields:
            Text chunks as they arrive
        """
        try:
            response = self._client.models.generate_content_stream(
                model=self.config.model,
                contents=prompt,
                config=config,
            )

            for chunk in response:
                if chunk.text:
                    yield chunk.text

        except google_exceptions.ResourceExhausted as e:
            logger.error(f"Gemini API quota exceeded during streaming: {e}")
            raise
        except google_exceptions.DeadlineExceeded as e:
            logger.error(f"Gemini API timeout during streaming: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during streaming: {e}")
            raise

    @observe(as_type="generation")
    def generate_json(
        self,
        prompt: str,
        response_schema: Dict[str, Any],
        temperature: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Generate structured JSON response from a prompt.

        Args:
            prompt: The prompt to send to Gemini
            response_schema: JSON schema to enforce structure (OpenAPI 3.0 format).
                            This guarantees valid JSON output without markdown fences.
            temperature: Override default temperature (0.0-2.0)

        Returns:
            Parsed JSON response as a dictionary or list (matching the schema)

        Raises:
            ValueError: If response cannot be parsed as JSON
            google_exceptions.ResourceExhausted: If API quota exceeded
            google_exceptions.DeadlineExceeded: If request times out

        Example:
            >>> schema = {
            ...     "type": "ARRAY",
            ...     "items": {
            ...         "type": "OBJECT",
            ...         "properties": {
            ...             "name": {"type": "STRING"},
            ...             "age": {"type": "INTEGER"}
            ...         }
            ...     }
            ... }
            >>> result = gemini_client.generate_json("Generate 3 users", schema)
        """
        temp = temperature if temperature is not None else self.config.temperature
        max_tokens = 8192

        generation_config = types.GenerateContentConfig(
            temperature=temp,
            max_output_tokens=max_tokens,
            response_mime_type="application/json",
            response_schema=response_schema,
        )

        # Track metadata in Langfuse
        if self.enable_tracing:
            langfuse_context.update_current_observation(
                model=self.config.model,
                metadata={
                    "temperature": temp,
                    "max_output_tokens": max_tokens,
                    "response_mime_type": "application/json",
                    "schema_enforced": True,
                },
            )

        try:
            response = self._client.models.generate_content(
                model=self.config.model,
                contents=prompt,
                config=generation_config,
            )

            # Track token usage if available
            if self.enable_tracing and hasattr(response, "usage_metadata"):
                usage = response.usage_metadata
                langfuse_context.update_current_observation(
                    usage={
                        "input": usage.prompt_token_count,
                        "output": usage.candidates_token_count,
                        "total": usage.total_token_count,
                    }
                )

            # With response_schema, Gemini guarantees valid JSON (no markdown fences)
            try:
                return json.loads(response.text)
            except json.JSONDecodeError as e:
                # This should rarely happen with schema enforcement
                logger.error(
                    f"Failed to parse JSON with schema. Raw response: {response.text[:500]}"
                )
                raise ValueError(
                    f"Failed to parse JSON from Gemini response despite schema. Error: {e}"
                ) from e
        except google_exceptions.ResourceExhausted as e:
            logger.error(f"Gemini API quota exceeded: {e}")
            raise
        except google_exceptions.DeadlineExceeded as e:
            logger.error(f"Gemini API request timeout: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in Gemini API call: {e}")
            raise

    @observe(as_type="generation")
    def generate_json_stream(
        self,
        prompt: str,
        temperature: Optional[float] = None,
    ) -> Generator[str, None, None]:
        """Generate streaming JSON response (yields raw JSON chunks).

        Args:
            prompt: The prompt to send to Gemini (should request JSON format)
            temperature: Override default temperature (0.0-2.0)

        Yields:
            Raw JSON text chunks as they arrive

        Note:
            This yields raw chunks. You'll need to accumulate and parse the full JSON
            at the end. Useful for showing progress during long generations.

        Raises:
            google_exceptions.ResourceExhausted: If API quota exceeded
            google_exceptions.DeadlineExceeded: If request times out
        """
        temp = temperature if temperature is not None else self.config.temperature
        max_tokens = 8192

        generation_config = types.GenerateContentConfig(
            temperature=temp,
            max_output_tokens=max_tokens,
            response_mime_type="application/json",
        )

        # Track metadata in Langfuse
        if self.enable_tracing:
            langfuse_context.update_current_observation(
                model=self.config.model,
                metadata={
                    "temperature": temp,
                    "max_output_tokens": max_tokens,
                    "response_mime_type": "application/json",
                    "stream": True,
                },
            )

        try:
            response = self._client.models.generate_content_stream(
                model=self.config.model,
                contents=prompt,
                config=generation_config,
            )

            for chunk in response:
                if chunk.text:
                    yield chunk.text

        except google_exceptions.ResourceExhausted as e:
            logger.error(f"Gemini API quota exceeded during JSON streaming: {e}")
            raise
        except google_exceptions.DeadlineExceeded as e:
            logger.error(f"Gemini API timeout during JSON streaming: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during JSON streaming: {e}")
            raise
