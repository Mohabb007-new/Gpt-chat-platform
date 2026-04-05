import openai
import os
import base64
from typing import Optional, Generator

openai.api_key = os.getenv("OPENAI_API_KEY")

# Small 1x1 transparent PNG used for test fallbacks
_TEST_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII="
)


def _is_fake_mode() -> bool:
    if os.getenv("FORCE_FAKE_OPENAI"):
        return True
    if os.getenv("OPENAI_API_KEY"):
        return False
    try:
        from flask import current_app
        if current_app and current_app.config.get("TESTING"):
            return True
    except Exception:
        pass
    return True


def get_chat_response(prompt: str) -> str:
    if _is_fake_mode():
        return f"(test) Echo: {prompt}"
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


def get_chat_response_stream(messages: list) -> Generator[str, None, None]:
    """Yield token deltas one at a time. In fake mode yields words with a space."""
    if _is_fake_mode():
        text = f"(test) Echo: {messages[-1]['content']}"
        for word in text.split():
            yield word + " "
        return

    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        stream=True,
    )
    for chunk in response:
        delta = chunk.choices[0].delta.content or ""
        if delta:
            yield delta


def get_image_response(prompt: str, response_type: str) -> Optional[bytes | dict]:
    if _is_fake_mode():
        image_base64 = _TEST_PNG_B64
    else:
        response = openai.images.generate(model="gpt-image-1", prompt=prompt)
        image_base64 = response.data[0].b64_json

    if response_type.lower() == "base64":
        return {"base64": image_base64, "version": "0.1.0"}
    elif response_type.lower() == "image":
        return base64.b64decode(image_base64)
    return None
