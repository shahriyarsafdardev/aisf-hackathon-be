import pinecone
import tqdm
import os
import uuid
import openai
from dotenv import load_dotenv
from app.core.logging import getLogger
from app.services.openai import create_embedding

load_dotenv()

pinecone_api_key = os.getenv('PINECONE_API_KEY')
pinecone_env = os.getenv('PINECONE_ENV')
pinecone_index_name = os.getenv('PINECONE_INDEX_NAME')
openai_api_key = os.getenv('OPENAI_API_KEY')


pinecone.init(api_key=pinecone_api_key,
              environment=pinecone_env)
index = pinecone.Index(pinecone_index_name)
openai.api_key = openai_api_key

logger = getLogger()

def store_vectors(texts):
    try:
        vectors = []
        batch_size = 90

        for text in texts:
            embedding = create_embedding(text)
            vectors.append(
                (
                    str(uuid.uuid4()),
                    embedding,
                    {
                        "text": text,
                    }
                )
            )

            if len(vectors) == batch_size:
                index.upsert(vectors=vectors)
                logger.info(f"Stored {batch_size} vectors to pinecone")
                vectors = []

        if len(vectors) > 0:
            index.upsert(vectors=vectors)
    except Exception as e:
        logger.error(
            f"Something went wrong while storing vectors to pinecone: {e}")

def get_topk_with_filters(query_embedding, filters, verbose=False):
    response = index.query(
        vector=query_embedding,
        filter=filters,
        top_k=5,
        include_metadata=True
    )

    texts = [match['metadata']['text'] for match in response['matches']]

    return texts


def delete_vectors(filters):
    try:
        index.delete(
            filter=filters
        )
        logger.info(
            f"Deleted vectors from Pinecone with filters: {filters}")
    except Exception as e:
        logger.error(
            f"Something went wrong while deleting vectors from Pinecone: {e}")


def count_vectors(filters):
    response = index.query(
        vector=create_embedding("random"),
        filter=filters,
        top_k=10,
        include_metadata=False
    )
    return len(response['matches'])


def query_vectors(query, filters={}):
    response = index.query(
        vector=create_embedding(query),
        filter=filters,
        top_k=10,
        include_metadata=True
    )
    return response['matches']
