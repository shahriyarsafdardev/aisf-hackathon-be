import re
from urllib.parse import urlparse
from collections import Counter
from app.services.documentation_parser import query
from app.core.logging import getLogger
from app.services.connector_generation.schema_generator import link_search, clean_urls
from app.services.openai import completion


def most_common_base_url(url_list):
    base_urls = [urlparse(url).netloc for url in url_list]
    return Counter(base_urls).most_common(1)[0][0]


logger = getLogger()


def find_valid_base_url(input_string):
    try:
        url_pattern = re.compile(
            r"(?:(?:https?:\/\/)|(?:\/))[\w\-._~:/?#\[\]@!$&'()*+,;=%{}]+")
        urls = url_pattern.findall(input_string)

        return urls[0] if urls else None
    except Exception as e:
        logger.info(f"Something went wrong while finding valid base url: {e}")
        return ''


def find_valid_base_url(input_string):
    try:
        url_pattern = re.compile(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
        urls = url_pattern.findall(input_string)

        return urls[0] if urls else None
    except Exception as e:
        logger.error(f"Something went wrong while finding valid base url: {e}")
        return ''


def get_base_url(domain, verbose=False):
    # return(most_common_base_url(link_search(
    #     prefix=domain,
    #     suffix='.txt'
    # )))

    # # logger.info(f"search results: {search_results}")
    try:
        links = clean_urls(link_search(
            prefix=domain,
            suffix='.txt'
        ))[:50]
        base_url_query = f'Given the following list of endpoints what is the most likely base url. Some endpoints include a version like "/0/", "/v0/". Give me the url (including https://) and nothing else: {str(links)}'
        base_url_response = completion(base_url_query)
        base_url = find_valid_base_url(base_url_response)
        return base_url
    except Exception as e:
        logger.error(f"Something went wrong while getting base url: {e}")
        return ''
