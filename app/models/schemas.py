from pydantic import BaseModel, Field


class Token(BaseModel):
    """
    Schema for JWT access token returned after successful authentication.

    Attributes:
        access_token (str): The JWT access token.
        token_type (str): The type of the token (usually 'bearer').
    """

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(..., description="Type of the token (bearer)")


class ImageReturn(BaseModel):
    """
    Schema for the response after uploading an image for critique.

    Attributes:
        filename (str): Hashed filename of the uploaded image.
        size (int): File size in bytes.
        message_id (str): Unique message id to which image belongs.
    """

    filename: str = Field(description="Hashed filename", examples=["xyz.png"])
    size: int = Field(description="File size in bytes", examples=["28632"])
    message_id: str = Field(description="Unique message id to which image belongs")
