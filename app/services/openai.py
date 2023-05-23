import openai
import os
import time
import random
from dotenv import load_dotenv
from app.core.logging import getLogger

load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')


def create_embedding(text):
    return openai.Embedding.create(input=[text], model="text-embedding-ada-002")['data'][0]['embedding']


logger = getLogger()


def context_based_completion(context, query, model="gtp-3.5-turbo", verbose=False, max_retries=5):
    for attempt in range(max_retries):
        try:
            response = openai.ChatCompletion.create(
                model=model,
                messages=[
                    {"role": "user", "content": f"First check if the user question can be answered using only the information included in the context below. If it can be, then answer. If not, then return: \"None\" \n\n Context:{context} \n\n User question:{query}"},
                ]
            )
            return response['choices'][0]['message']['content']

        except openai.error.RateLimitError:
            # exponential backoff with jitter
            wait_time = (2 ** attempt) + random.random()
            logger.error(
                f"Request exceeded rate limit. Waiting {wait_time} seconds before retrying.")
            time.sleep(wait_time)

    raise Exception(f"Maximum number of retries ({max_retries}) exceeded.")


def completion(query, model="gpt-3.5-turbo", max_retries=5):
    for attempt in range(max_retries):
        try:
            response = openai.ChatCompletion.create(
                model=model,
                messages=[
                    {"role": "user", "content": query},
                ]
            )
            return response['choices'][0]['message']['content']

        except openai.error.RateLimitError:
            # exponential backoff with jitter
            wait_time = (2 ** attempt) + random.random()
            logger.error(
                f"Request exceeded rate limit. Waiting {wait_time} seconds before retrying.")
            time.sleep(wait_time)

    raise Exception(f"Maximum number of retries ({max_retries}) exceeded.")


def ask_gpt(query, model="gpt-3.5-turbo"):
    response = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "user", "content": query},
        ]
    )
    return response['choices'][0]['message']['content']
