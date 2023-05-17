import pinecone
import tqdm
import os
import uuid
import openai
from dotenv import load_dotenv
from urllib.parse import urlparse
from app.core.logging import getLogger
from app.services.scrapping.web_parser import get_referenced_urls

load_dotenv()

pinecone_api_key = os.getenv('PINECONE_API_KEY')
pinecone_env = os.getenv('PINECONE_ENV')
pinecone_index_name = os.getenv('PINECONE_INDEX_NAME')
openai_api_key = os.getenv('OPENAI_API_KEY')


pinecone.init(api_key=pinecone_api_key,
              environment=pinecone_env)
index = pinecone.Index(pinecone_index_name)
openai.api_key = openai_api_key

upsert_batch_size = 90

logger = getLogger()


def store_chunks(chunks):
    try:
        for i in range(0, len(chunks), upsert_batch_size):
            index.upsert(vectors=chunks[i:i + upsert_batch_size])
            logger.info(
                f"Stored {min(upsert_batch_size, len(chunks[i:i + upsert_batch_size]))} vectors to pinecone")
    except Exception as e:
        logger.error(
            f"Something went wrong while storing vectors to pinecone: {e}")

# Main function that is used by the scraper


def store_vectors(chunks, url):
    try:
        domain_name = get_domain_name(url)
        vectors = []
        batch_size = 90

        for text in chunks:
            text = url + ' ' + text.replace("\n", ". ")
            embedding = create_embedding(text)
            vectors.append(
                (
                    str(uuid.uuid4()),
                    embedding,
                    {
                        "text": text,
                        "domain": domain_name,
                        "page_urls": generate_url_parts(url),
                        "referenced_urls": get_referenced_urls(text)
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


def generate_url_parts(url):
    url_parts = urlparse(url)
    path_parts = url_parts.path.strip("/").split("/")

    urls = []
    base_url = f"{url_parts.scheme}://{url_parts.netloc}"
    urls.append(url_parts.netloc)

    current_path = base_url
    for part in path_parts:
        current_path += f"/{part}"
        urls.append(current_path)

    return urls


def get_topk_vectors(query, url):
    # url_components = generate_url_parts(url)
    query = query.replace("\n", ". ")
    embedding = create_embedding(query)
    response = index.query(
        vector=embedding,
        filter={
            'urls': url
        },
        top_k=5,
        include_metadata=True
    )

    texts = [match['metadata']['text'] for match in response['matches']]
    return texts


def get_topk_with_domain(query_embedding, filters, verbose=False):
    response = index.query(
        vector=query_embedding,
        filter=filters,
        top_k=5,
        include_metadata=True
    )

    texts = [match['metadata']['text'] for match in response['matches']]

    return texts


def get_domain_name(url):
    parsed_url = urlparse(url)
    domain_name = parsed_url.netloc
    return domain_name


def create_embedding(text):
    return openai.Embedding.create(input=[text], model="text-embedding-ada-002")['data'][0]['embedding']


def delete_vectors_by_domain(target_domain):
    try:
        index.delete(
            filter={
                "domain": {"$eq": "harvest"},
            }
        )
        logger.info(
            f"Deleted vectors from Pinecone with domain: {target_domain}")
    except Exception as e:
        logger.error(
            f"Something went wrong while deleting vectors from Pinecone: {e}")


def store_vectors_with_domain(chunks, domain):
    vectors = []
    batch_size = 90
    total_chunks = len(chunks)

    for chunk in tqdm(chunks, desc="Storing vectors", total=total_chunks):
        chunk = chunk.replace("\n", ". ")
        embedding = create_embedding(chunk)
        vectors.append(
            (
                str(uuid.uuid4()),
                embedding,
                {"text": chunk, 'domain': domain}
            )
        )
        if len(vectors) == batch_size:
            index.upsert(vectors=vectors)
            logger.info(f"Stored {batch_size} vectors to pinecone")
            vectors = []

    if len(vectors) > 0:
        index.upsert(vectors=vectors)
        logger.info(f"Stored {len(vectors)} vectors to pinecone")


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
