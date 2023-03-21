import openai
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("CHATGPT_API_KEY")
openai.api_key = api_key

def call_chatgpt(prompt, max_tokens=50):
    response = openai.Completion.create(
        engine="text-davinci-002",
        prompt=prompt,
        max_tokens=max_tokens,
        n=1,
        stop=None,
        temperature=0.5,
    )

    return response.choices[0].text.strip()

if __name__ == "__main__":
    prompt = "What are the benefits of exercise?"
    response_text = call_chatgpt(prompt)
    print("Prompt: ", prompt)
    print("Response: ", response_text)
