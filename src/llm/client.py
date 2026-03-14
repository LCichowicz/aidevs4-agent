import json
from typing import Any, Sequence
from openai import OpenAI

from src import config


class LLMClient:

    def __init__(self) -> None:
        self.client =OpenAI(api_key=config.BIELIK_API_KEY,
                       base_url=config.BIELIK_BASE_URL)

        self.model = config.BIELIK_MODEL

    def chat(self, messages: Any) -> str:
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
    
    def chat_json_schema(self, messages: Any, schema ) -> Any:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=list(messages),
            temperature=0,
            response_format={
                "type":"json_schema",
                "json_schema": schema
            }
        )

        if response.choices is None or len(response.choices) == 0:
            raise RuntimeError("LLM returned no choices")
        
        messages = response.choices[0].message

        if messages is None or messages.content is None:
            raise RuntimeError("LLM returned empty message")
        
        raw_content = messages.content
        try:
            return json.loads(raw_content)
        except json.JSONDecodeError as e:
            raise RuntimeError(
            f"LLM returned invalid JSON.\n\nResponse:\n{raw_content}"
            ) from e