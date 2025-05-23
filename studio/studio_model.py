from llama_cpp import Llama, CreateCompletionStreamResponse
import asyncio, os
from .rag_db import RagDB


class StudioModel:
    def __init__(self):
        self._llm = Llama(
            model_path="models/Nous-Hermes-2-Mistral-7B-DPO.Q5_K_M.gguf",
            n_ctx=8192,
            n_threads=os.cpu_count(),
            n_gpu_layers=20,
        )

        self._rag_context = RagDB()

    def _generate_prompt(self, user_prompt: str):
        raw_context = self._rag_context.query(user_prompt, k=2)
        context = (
            "\n".join(raw_context["documents"][0]) if raw_context["documents"] else ""
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are Zak Bagans, a ghost hunter and paranormal investigator. You are known for your ghost hunting show, "
                    '"Ghost Adventures," where you explore haunted locations and investigate paranormal phenomena. '
                    "You are passionate about the supernatural and have a deep interest in the history and stories behind the places you visit. "
                    "You are also known for your strong personality and willingness to confront the unknown."
                ),
            },
            {"role": "system", "content": f"(Background info: {context})"},
            {"role": "user", "content": user_prompt},
        ]

        rendered_prompt = ""

        for msg in messages:
            rendered_prompt += (
                f"<|im_start|>{msg['role']}\n{msg['content']}<|im_end|>\n"
            )

        rendered_prompt += "<|im_start|>assistant\n"
        print(f"\n\n[Prompt]:\n{rendered_prompt}")
        return rendered_prompt

    def _respond(self, prompt: str, stream: bool = False):
        return self._llm.create_completion(
            prompt=self._generate_prompt(user_prompt=prompt),
            max_tokens=512,
            stop=["<|im_end|>"],
            echo=False,
            stream=stream,
            repeat_penalty=1.1,
            top_p=0.9,
            temperature=0.7,
        )

    def get_response(self, prompt: str):
        result = self._respond(prompt)
        return result["choices"][0]["text"].strip()  # type: ignore

    async def get_response_async(self, prompt: str):
        for chunk in self._respond(prompt, stream=True):
            await asyncio.sleep(0)

            if not isinstance(chunk, str):
                token = chunk["choices"][0]["text"]
                yield token
