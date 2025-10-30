"""Test script for Gemini client functionality."""

from utils.config import AppConfig
from utils.gemini_client import GeminiClient


def test_text_generation():
    """Test basic text generation."""
    print("🧪 Testing basic text generation...")
    config = AppConfig.from_env()
    client = GeminiClient(config.gemini)

    response = client.generate_text("Say 'Hello from Gemini!' and nothing else.")
    print(f"✓ Response: {response}\n")


def test_streaming():
    """Test streaming text generation."""
    print("🧪 Testing streaming text generation...")
    config = AppConfig.from_env()
    client = GeminiClient(config.gemini)

    print("✓ Streaming response: ", end="", flush=True)
    for chunk in client.generate_text(
        "Count from 1 to 5, one number per line.", stream=True
    ):
        print(chunk, end="", flush=True)
    print("\n")


def test_json_generation():
    """Test structured JSON generation."""
    print("🧪 Testing JSON generation...")
    config = AppConfig.from_env()
    client = GeminiClient(config.gemini)

    prompt = """Generate a JSON object with the following structure:
    {
        "message": "Hello from Gemini",
        "numbers": [1, 2, 3],
        "success": true
    }"""

    response = client.generate_json(prompt)
    print(f"✓ JSON response: {response}")
    print(f"✓ Type: {type(response)}\n")


def test_json_streaming():
    """Test streaming JSON generation."""
    print("🧪 Testing JSON streaming...")
    config = AppConfig.from_env()
    client = GeminiClient(config.gemini)

    prompt = """Generate a JSON array of 3 fruits with their colors:
    [
        {"name": "apple", "color": "red"},
        {"name": "banana", "color": "yellow"},
        {"name": "grape", "color": "purple"}
    ]"""

    print("✓ Streaming JSON: ", end="", flush=True)
    chunks = []
    for chunk in client.generate_json_stream(prompt):
        print(chunk, end="", flush=True)
        chunks.append(chunk)

    # Parse the complete JSON
    import json

    full_json = "".join(chunks)
    parsed = json.loads(full_json)
    print(f"\n✓ Parsed: {parsed}\n")


if __name__ == "__main__":
    print("=" * 60)
    print("🍜 SQLop - Gemini Client Test Suite")
    print("=" * 60)
    print()

    try:
        test_text_generation()
        test_streaming()
        test_json_generation()
        test_json_streaming()

        print("=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
