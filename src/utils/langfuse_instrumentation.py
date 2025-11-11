"""Langfuse instrumentation setup for SQLOp."""

from typing import Optional

try:
    from utils.config import AppConfig
except ImportError:
    from src.utils.config import AppConfig


def initialize_langfuse(config: AppConfig) -> bool:
    """Initialize Langfuse instrumentation.

    Args:
        config: Application configuration with Langfuse settings

    Returns:
        True if initialization successful, False otherwise
    """
    if not config.langfuse.enabled:
        print("Langfuse tracing disabled")
        return False

    try:
        # Initialize Langfuse client with explicit configuration
        import os

        os.environ["LANGFUSE_PUBLIC_KEY"] = config.langfuse.public_key
        os.environ["LANGFUSE_SECRET_KEY"] = config.langfuse.secret_key
        os.environ["LANGFUSE_HOST"] = config.langfuse.host

        # Import after setting environment variables
        from langfuse import Langfuse

        langfuse = Langfuse()

        # Verify authentication
        if not langfuse.auth_check():
            print("Langfuse authentication failed - check your keys")
            return False

        # Initialize instrumentation based on Gemini auth method
        if config.gemini.is_vertex_ai():
            # Vertex AI instrumentation
            try:
                from openinference.instrumentation.vertexai import VertexAIInstrumentor

                VertexAIInstrumentor().instrument()
                print(
                    f"Langfuse tracing enabled for Vertex AI (environment: {config.langfuse.environment})"
                )
            except ImportError:
                print(
                    "Warning: openinference-instrumentation-vertexai not installed, skipping auto-instrumentation"
                )
                print("Manual tracing with @observe decorators will still work")
        else:
            # API key instrumentation
            try:
                from openinference.instrumentation.google_genai import (
                    GoogleGenAIInstrumentor,
                )

                GoogleGenAIInstrumentor().instrument()
                print(
                    f"Langfuse tracing enabled for Google GenAI (environment: {config.langfuse.environment})"
                )
            except ImportError:
                print(
                    "Warning: openinference-instrumentation-google-genai not installed, skipping auto-instrumentation"
                )
                print("Manual tracing with @observe decorators will still work")

        return True

    except Exception as e:
        print(f"Failed to initialize Langfuse: {e}")
        return False


def flush_langfuse():
    """Flush pending Langfuse events.

    Call this before application shutdown to ensure all traces are sent.
    Particularly important for short-lived environments.
    """
    try:
        from langfuse import Langfuse
        langfuse = Langfuse()
        langfuse.flush()
        print("Langfuse events flushed")
    except Exception as e:
        print(f"Error flushing Langfuse: {e}")