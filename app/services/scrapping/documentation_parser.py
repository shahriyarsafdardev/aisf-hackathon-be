from app.services.openai import context_based_completion, create_embedding
from app.services.pinecone_db import get_topk_with_domain
from app.core.logging import getLogger

logger = getLogger()


def create_context(texts, verbose=False):
    context = ""
    for text in texts:
        remaining_space = 6000 - len(context)
        if remaining_space == 0:
            break
        if len(text) > remaining_space:
            context += text[:remaining_space]
        else:
            context += text

    if verbose:
        logger.info('Creating context')
        logger.info('Number of texts:', len(texts))
        logger.info(context)

    return context


def query(query, filters={}, model="gpt-3.5-turbo", verbose=False):
    embedding = create_embedding(query)
    nearest_neighbours = get_topk_with_domain(embedding, filters, verbose)
    context = create_context(nearest_neighbours, verbose)
    gpt_response = context_based_completion(context, query, model, verbose)
    return gpt_response


def query_pinecone(query, filters={}, verbose=False):
    embedding = create_embedding(query)
    nearest_neighbours = get_topk_with_domain(embedding, filters, verbose)
    context = create_context(nearest_neighbours, verbose)
    return context
