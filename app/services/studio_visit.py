import asyncio
import base64
import json
import os
from uuid import UUID, uuid4
from agents import Runner, TResponseInputItem
from openai.types.responses import ResponseTextDeltaEvent
from app.core.config import get_settings
from app.models.db import User
from app.models.schemas import Line
from app.services.agents.canvas_agent import canvas_agent
from app.services.agents.art_critic_agent import art_critic_agent

settings = get_settings()

OPENAI_API_KEY = settings.openai_api_key
OPENAI_ORG_ID = settings.openai_org_id


class StudioVisit:
    def __init__(self, session_id: UUID, user: User):
        self.session_id: UUID = session_id
        self.user: User = user

    async def chat(self, input_items: list[TResponseInputItem]):
        result = Runner.run_streamed(art_critic_agent, input=input_items)

        async for event in result.stream_events():
            await asyncio.sleep(0.1)

            if event.type == "raw_response_event" and isinstance(
                event.data, ResponseTextDeltaEvent
            ):
                yield event.data.delta

    async def draw(self, lines: list[Line]):
        os.makedirs("tmp/draw/", exist_ok=True)
        temp_filename = f"{uuid4().hex}.json"

        with open(f"tmp/draw/{temp_filename}", "x") as file:
            json.dump([line.model_dump() for line in lines], file)

        with open(f"tmp/draw/{temp_filename}", "rb") as f:
            file_data = base64.b64encode(f.read()).decode("utf-8")

        result = await Runner.run(
            canvas_agent,
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_file",
                            "filename": temp_filename,
                            "file_data": f"data:application/json;base64,{file_data}",
                        }
                    ],
                },
            ],
        )

        return result.final_output_as(list[Line])
