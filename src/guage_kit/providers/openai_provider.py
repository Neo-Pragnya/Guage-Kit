from typing import Any, Dict
import openai

class OpenAIProvider:
    def __init__(self, api_key: str):
        openai.api_key = api_key

    def generate(self, prompt: str, model: str = "text-davinci-003", **kwargs: Any) -> Dict[str, Any]:
        response = openai.ChatCompletion.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            **kwargs
        )
        return response.choices[0].message['content']

    def evaluate(self, prompt: str, expected_output: str, model: str = "text-davinci-003", **kwargs: Any) -> float:
        generated_output = self.generate(prompt, model=model, **kwargs)
        # Here you can implement a comparison logic to evaluate the generated output against the expected output
        # For simplicity, we will return a dummy score
        return 1.0 if generated_output == expected_output else 0.0