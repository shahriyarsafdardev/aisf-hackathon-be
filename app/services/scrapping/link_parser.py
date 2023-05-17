from urllib.parse import urlparse, urlunparse
from app.core.logging import getLogger
from app.services.s3 import list_objects, read_object
from termcolor import colored
from itertools import chain
import concurrent.futures
import re
from dotenv import load_dotenv
load_dotenv()


logger = getLogger()

# This function should be in teh s3 service


def regex_search(regex, file_name_filters, verbose=False):
    files = list_objects(file_name_filters)
    print("files", files)
    pattern = re.compile(regex)
    matches = []

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {executor.submit(read_object, file) for file in files}
        for future in concurrent.futures.as_completed(futures):
            file_content = future.result()
            for match in pattern.finditer(file_content):
                matches.append(match.group())
                if verbose:
                    start = max(0, match.start() - 50)
                    end = min(len(file_content), match.end() + 50)
                    buffer = file_content[start:match.start()] + \
                        colored(match.group(), 'red') + \
                        file_content[match.end():end]
                    logger.info(f"Found a match: {buffer}")

    return list(matches)


link_regex = r'\s/(\S+)'


def filter_links(links, file_name_filters, unique=True, verbose=False):
    filtered_links = [s for s in links if not any(c.isdigit(
    ) and s[i+1].isdigit() or c == '/' and s[i+1] == '/' for i, c in enumerate(s[:-1]))]
    filtered_links = [urlunparse(urlparse(link)._replace(
        query="", fragment="")) for link in filtered_links]

    if unique:
        filtered_links = list(set(filtered_links))

    if verbose:
        logger.info("\n".join(filtered_links))
        logger.info(
            f"{len(filtered_links)} links found in files matching {file_name_filters}:")

    return filtered_links


def link_search_s3(file_name_filters, unique=True, verbose=False):

    links = regex_search(link_regex, file_name_filters, verbose)
    links = filter_links(links, file_name_filters, unique, verbose)

    return links


def link_search_text(text, unique=True, verbose=False):
    # links = re.findall(link_regex, text)

    pattern = re.compile(link_regex)
    links = []
    for match in pattern.finditer(text):
        links.append(match.group())

    logger.info(f"links to add as reference: {links}")

    links = filter_links(links, file_name_filters=[],
                         unique=unique, verbose=verbose)

    return links


def link_search_within_file(file_content, unique=True, verbose=False):
    matches = []
    pattern = re.compile(link_regex)
    for match in pattern.finditer(file_content):
        matches.append(match.group())
        if verbose:
            start = max(0, match.start() - 50)
            end = min(len(file_content), match.end() + 50)
            buffer = file_content[start:match.start()] + \
                colored(match.group(), 'red') + \
                file_content[match.end():end]
            logger.info(f"Found a match: {buffer}")
    if unique:
        return list(set(matches))
    return list(matches)
