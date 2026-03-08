from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

from src import config


class LLMClient:

    def __init__(self) -> None:
        self.client =OpenAI(api_key=config.BIELIK_API_KEY,
                       base_url=config.BIELIK_BASE_URL)

        self.model = config.BIELIK_MODEL

    def chat(self, messages: list[ChatCompletionMessageParam]) -> str:
        response = self.client.chat.completions.create(
            model= self.model,
            messages= messages,
            temperature = 0
        )
        if response.choices is None or len(response.choices) == 0:
            raise ValueError("Error in LLM respoonse. No 'choices' found")
        

        if response.choices[0].message is None:
            raise RuntimeError("No messages in LLM response")
        
        content = response.choices[0].message.content


        if not content:
            raise RuntimeError("LLM returned empty response")
        return content