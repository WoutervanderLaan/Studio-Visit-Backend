from pydantic import BaseModel, Field
from typing import List


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


class Line(BaseModel):
    points: List[float | int]
    color: str
    size: int
    opacity: float
    timestamp: int
    type: int


class DrawRequest(BaseModel):
    lines: List[Line] = Field(description="The drawing lines to continue on.")


class SessionReturn(BaseModel):
    visit_id: str
