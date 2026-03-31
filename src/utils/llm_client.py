from openai import OpenAI
from src.utils.config import OPENAI_API_KEY, OPENAI_MODEL
from src.services.usage_tracker import log_llm


class LLMClient:
    def __init__(self, api_key=OPENAI_API_KEY, model=OPENAI_MODEL):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def ask(self, prompt, temperature=0.0):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )

        usage = getattr(response, "usage", None)
        input_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
        output_tokens = getattr(usage, "completion_tokens", 0) if usage else 0

        log_llm(
            model=self.model,
            input_tokens=input_tokens or 0,
            output_tokens=output_tokens or 0,
            success=True,
        )

        return response.choices[0].message.content


llm = LLMClient()