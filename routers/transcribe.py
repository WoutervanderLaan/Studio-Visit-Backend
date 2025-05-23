from fastapi import APIRouter, UploadFile, Depends, File, HTTPException
from pydantic import BaseModel, Field
from .auth import oauth2_scheme
from faster_whisper import WhisperModel
import os
from typing import Optional

router = APIRouter(tags=["transcribe"])


class TranscriptionRequest(BaseModel):
    file: UploadFile = File()


class TranscriptionReturn(BaseModel):
    transcription: str = Field(
        description="Transcription of the audio file",
        examples=["This is a sample transcription of the audio file."],
    )


class Transcriber:
    def __init__(self, model_size="base", device="cpu", compute_type="int8"):
        self._model = WhisperModel(model_size, device=device, compute_type=compute_type)

    def transcribe(self, file_path: str, beam_size: int = 5) -> str:
        segments, _ = self._model.transcribe(
            file_path, language="en", beam_size=beam_size
        )
        full_transcription = " ".join(segment.text.strip() for segment in segments)

        return full_transcription


transcriber = Transcriber()


@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(description="Audio file to transcribe."),
    token: str = Depends(oauth2_scheme),
) -> dict[str, str]:
    """
    Transcribe an audio file using the transcriber model.
    """
    try:
        if not os.path.exists("tmp"):
            os.mkdir("tmp")

        transcription: Optional[TranscriptionReturn] = None

        with open(f"tmp/{file.filename}", "x"):
            response = transcriber.transcribe(f"tmp/{file.filename}", beam_size=5)
            transcription = TranscriptionReturn(transcription=response)

        os.remove(f"tmp/{file.filename}")

        return transcription.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")
