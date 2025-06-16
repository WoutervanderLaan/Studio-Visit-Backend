from typing import List
from agents import Agent, CodeInterpreterTool

from app.models.schemas import Line


canvas_agent = Agent(
    name="Canvas Agent",
    model="gpt-4.1",
    output_type=List[Line],
    instructions="""
    # Identity
    You are an artist
    
    # Instructions
    The provided image depicts the drawing in its current state.
    Continue the drawing with new lines in various colors, opacities and sizes, based on the image provided.
    """,
    tools=[
        CodeInterpreterTool(
            tool_config={"type": "code_interpreter", "container": {"type": "auto"}},
        )
    ],
)
