import asyncio
from dotenv import load_dotenv
import os, base64
from agents import Agent, Runner
from openai.types.responses import ResponseTextDeltaEvent


load_dotenv(dotenv_path=".env")


OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_ORG_ID = os.environ.get("OPENAI_ORG_ID")


image_analyzer_agent = Agent(
    name="Image Analyzer Agent",
    model="gpt-4.1",
    instructions="""
    # Identity
    You are a contemporary art critic.
    
    # Instructions
     
    - Describe the provided image in as much detail as possible.
    - Touch on all relevant features of the image (color, style, art historical references, etc.).
    - Provide a critique of the painting.
    """,
)

art_critic_agent = Agent(
    name="Art Critic Agent",
    model="gpt-4.1",
    instructions="""
    # Identity
    You are a snobby contemporary art critic. Nothing meets your standard.
    
    # Instructions
     
    Reply to the user.
    """,
)


def image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
    return encoded_string


async def main(file_path: str):
    b64_image = image_to_base64(file_path)

    result = Runner.run_streamed(
        image_analyzer_agent,
        [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_image",
                        "detail": "auto",
                        "image_url": f"data:image/jpeg;base64,{b64_image}",
                    }
                ],
            },
        ],
    )

    async for event in result.stream_events():
        await asyncio.sleep(0)

        if event.type == "raw_response_event" and isinstance(
            event.data, ResponseTextDeltaEvent
        ):
            yield event.data.delta


async def chat(prompt: str):
    result = Runner.run_streamed(art_critic_agent, input=prompt)

    async for event in result.stream_events():
        await asyncio.sleep(0)

        if event.type == "raw_response_event" and isinstance(
            event.data, ResponseTextDeltaEvent
        ):
            yield event.data.delta

    # return result.final_output
