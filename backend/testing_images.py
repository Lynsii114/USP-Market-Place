"""Small, real image payloads used by API tests."""
import base64
from io import BytesIO

from PIL import Image


def image_payload(image_format="PNG"):
    buffer = BytesIO()
    Image.new("RGB", (2, 2), "navy").save(buffer, format=image_format)
    mime = {"PNG": "png", "JPEG": "jpeg", "WEBP": "webp", "AVIF": "avif", "GIF": "gif"}[image_format]
    return f"data:image/{mime};base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


TEST_PHOTO = image_payload()
