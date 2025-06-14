import os, hashlib
from PIL import Image
from io import BytesIO
import uuid
import os


def convert_to_png_and_save(
    contents: bytes,
    user_id: str,
    output_dir: str = "uploads",
) -> str:
    """
    Validates and converts an image to PNG format.

    Args:
        contents: Raw bytes of the uploaded image.
        output_dir: Directory to save the converted PNG.

    Returns:
        The hashed filename.
    """
    try:
        image = Image.open(BytesIO(contents))
    except Exception as e:
        raise ValueError("Invalid image file") from e

    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGBA")

    user_output_dir = f"{output_dir}/{user_id}"

    os.makedirs(user_output_dir, exist_ok=True)

    temp_filename = f"{uuid.uuid4().hex}.png"
    hash_object = hashlib.sha256(temp_filename.encode())
    hashed_filename = hash_object.hexdigest() + ".png"

    file_path = os.path.join(user_output_dir, hashed_filename)

    counter = 1  # Ensure unique filename

    while os.path.exists(file_path):
        hashed_filename = f"{hash_object.hexdigest()}_{counter}.png"
        file_path = os.path.join(user_output_dir, hashed_filename)
        counter += 1

    with open(file_path, "wb") as f:
        f.write(contents)

    return hashed_filename
