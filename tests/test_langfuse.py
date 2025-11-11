"""Test Langfuse integration."""

from utils.config import AppConfig
from utils.langfuse_instrumentation import initialize_langfuse


def test_langfuse_config():
    """Test that Langfuse configuration loads correctly."""
    config = AppConfig.from_env()

    print(f"\nLangfuse enabled: {config.langfuse.enabled}")
    print(f"Langfuse host: {config.langfuse.host}")
    print(f"Langfuse environment: {config.langfuse.environment}")

    assert config.langfuse is not None
    assert config.langfuse.host is not None


def test_langfuse_connection():
    """Test that Langfuse can connect and authenticate."""
    config = AppConfig.from_env()

    if not config.langfuse.enabled:
        print("⚠️  Langfuse is disabled in configuration")
        return

    print("\nInitializing Langfuse...")
    success = initialize_langfuse(config)

    assert success, "Langfuse initialization failed"

    # Test auth check
    from langfuse import Langfuse
    langfuse = Langfuse()

    print("\nTesting authentication...")
    assert langfuse.auth_check(), "Langfuse authentication failed"

    print("✅ Langfuse is properly configured and authenticated!")


if __name__ == "__main__":
    # Allow running directly for quick testing
    print("=" * 60)
    print("Testing Langfuse Integration")
    print("=" * 60)

    print("\n1. Testing Langfuse configuration...")
    test_langfuse_config()

    print("\n2. Testing Langfuse connection...")
    test_langfuse_connection()

    print("\n" + "=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)