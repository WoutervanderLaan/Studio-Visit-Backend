from dotenv import load_dotenv
import os, base64, json, uuid, asyncio
from agents import Runner, TResponseInputItem
from openai.types.responses import ResponseTextDeltaEvent
from app.core.config import get_settings
from app.models.schemas import Line
from typing import List
from app.services.agents.canvas_agent import canvas_agent
from app.services.agents.art_critic_agent import art_critic_agent


load_dotenv(dotenv_path=".env.development")
settings = get_settings()


OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_ORG_ID = os.environ.get("OPENAI_ORG_ID")


async def chat(input_items: list[TResponseInputItem]):
    result = Runner.run_streamed(art_critic_agent, input=input_items)

    async for event in result.stream_events():
        await asyncio.sleep(0.1)

        if event.type == "raw_response_event" and isinstance(
            event.data, ResponseTextDeltaEvent
        ):
            yield event.data.delta


async def draw(lines: List[Line]):
    os.makedirs("tmp/draw/", exist_ok=True)
    temp_filename = f"{uuid.uuid4().hex}.json"

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

    return result.final_output_as(List[Line])
