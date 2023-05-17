import re
from logging import getLogger
from urllib.parse import urlparse

logger = getLogger()

url_pattern = re.compile(
    r"(?:(?:https?:\/\/)|(?:\/))[\w\-._~:/?#\[\]@!$&'()*+,;=%{}]+"
)


def get_referenced_urls(text):
    return re.findall(url_pattern, text)


def get_subset_urls(url):
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


def get_domain(url):
    try:
        parsed_url = urlparse(url)
        return f"{parsed_url.scheme}://{parsed_url.netloc}"
    except Exception as e:
        logger.error(
            f"Something went wrong while getting the domain: {url} - {e}")
        return None
