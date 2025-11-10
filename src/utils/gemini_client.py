"""Gemini API client wrapper for SQLOp.

Provides simple interface for text generation and structured JSON output
using Google's Gemini models via Vertex AI or API key authentication.
"""

import json
from typing import Any, Dict, Generator, Optional

from google import genai
from google.genai import types

from utils.config import GeminiConfig


class GeminiClient:
    """Wrapper for Google Gemini API with support for streaming and structured output."""

    def __init__(self, config: GeminiConfig):
        """Initialize Gemini client with given configuration.

        Args:
            config: GeminiConfig with model settings and authentication
        """
        self.config = config

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
        """
        temp = temperature if temperature is not None else self.config.temperature

        generation_config = types.GenerateContentConfig(
            temperature=temp,
            max_output_tokens=8192,
        )

        if stream:
            return self._generate_streaming(prompt, generation_config)
        else:
            response = self._client.models.generate_content(
                model=self.config.model,
                contents=prompt,
                config=generation_config,
            )
            return response.text

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
        response = self._client.models.generate_content_stream(
            model=self.config.model,
            contents=prompt,
            config=config,
        )

        for chunk in response:
            if chunk.text:
                yield chunk.text

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
            >>> result = client.generate_json("Generate 3 users", schema)
        """
        temp = temperature if temperature is not None else self.config.temperature

        generation_config = types.GenerateContentConfig(
            temperature=temp,
            max_output_tokens=8192,
            response_mime_type="application/json",
            response_schema=response_schema,
        )

        response = self._client.models.generate_content(
            model=self.config.model,
            contents=prompt,
            config=generation_config,
        )

        # With response_schema, Gemini guarantees valid JSON (no markdown fences)
        try:
            return json.loads(response.text)
        except json.JSONDecodeError as e:
            # This should rarely happen with schema enforcement
            print(f"Unexpected: Failed to parse JSON with schema. Raw response:")
            print(response.text[:500])
            raise ValueError(
                f"Failed to parse JSON from Gemini response despite schema. Error: {e}"
            ) from e

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
        """
        temp = temperature if temperature is not None else self.config.temperature

        generation_config = types.GenerateContentConfig(
            temperature=temp,
            max_output_tokens=8192,
            response_mime_type="application/json",
        )

        response = self._client.models.generate_content_stream(
            model=self.config.model,
            contents=prompt,
            config=generation_config,
        )

        for chunk in response:
            if chunk.text:
                yield chunk.text
