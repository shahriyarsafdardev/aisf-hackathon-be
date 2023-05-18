

import re
import pprint
import concurrent.futures
from collections import defaultdict
from dotenv import load_dotenv
from urllib.parse import urlparse, urlunparse
from app.services.scrapping.documentation_parser import query
from app.services.s3 import list_objects, read_object
from app.core.logging import getLogger
from app.services.scrapping.link_parser import link_search_s3


load_dotenv()

logger = getLogger()


def clean_urls(url_list, base_url=""):
    clean_url_list = []
    for url in url_list:
        parsed = urlparse(url)
        cleaned = parsed._replace(query="", fragment="")
        clean_url = urlunparse(cleaned).rstrip('/')
        if base_url in clean_url:
            clean_url_list.append(clean_url)

    return list(set(clean_url_list))


def make_slug(s):
    s = s.lower()
    s = re.sub(r'\.', '-', s)
    s = re.sub(r'[^a-z0-9 -]', '', s)
    s = re.sub(r'\s+', '-', s)
    s = s.strip()
    return s


def string_to_dict(s):
    try:
        lines = s.split('\n')
        d = {}
        for line in lines:
            if line:  # Ignore empty lines
                key, value = line.split(': ')
                d[key.strip()] = value.strip()
        return d
    except Exception as e:
        return None


def regex_search(regex, prefix='', suffix=''):
    files = list_objects([prefix, suffix])
    pattern = re.compile(regex)
    uniq_strings = []

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {executor.submit(read_object, file) for file in files}
        for future in concurrent.futures.as_completed(futures):
            file_content = future.result()
            uniq_strings.extend(pattern.findall(file_content))

    return uniq_strings


def link_search(prefix='', suffix='', verbose=False):
    search_results = regex_search(
        r"(['\"\(\[\]-]?(?:https?://)?(?:www\.)?[a-zA-Z0-9-]+\.[a-zA-Z0-9.]+(?:/[^\s]*)?['\"\(\[\]-]?)",
        prefix,
        suffix
    )
    if verbose:
        logger.info(len(search_results))
        pprint.pprint(search_results)
    return [link.strip('\'"()-[]') for link in search_results]


# prompt_examples = """
# Url: https://sentry.io/api/0/organizations/{{organization_slug}}/repos/{{repo_id}}/commits/
# Description: This endpoint returns a list of commits for a given repository in the organization.
# Type: GET
# Returned Object: commits

# Url: https://sentry.io/api/0/projects/{{organization_slug}}/{{project_slug}}/
# Description: This endpoint returns a list of user feedback within a project.
# Type: GET
# Returned Object: user_feedbacks

# Url: https://sentry.io/api/0/organizations/{{organization_slug}}/event/
# Description: Retrieves discover (also known as events) data for a given organization in table format.
# Type: GET
# Returned Object: events

# Url: https://sentry.io/api/0/full_moons/{{organization_slug}}/
# Description: This endpoint retrieves details on an individual full moon including various details such as membership access, features, and teams.
# Type: GET
# Returned Object: full_moons

# Url: https://sentry.io/api/0/organizations/{{organization_slug}}/releases/{{version}}/files/{{file_id}}/
# Description: Delete a file for a given release.
# Type: DELETE

# Url: https://sentry.io/api/0/organization/{{organization_slug}}/monitors/{{monitor_slug}}/checkin/
# Description: Creates a new check-in for a monitor.
# Type: POST
# Returned Object: checkins

# Url: https://sentry.io/api/0/issues/{{issue_id}}/tags/{{key}}/
# Description: Returns details for given tag key related to an issue.
# Type: GET
# Returned Object: tags
# """

prompt_examples = """
Url: endpoint
Description: This endpoint returns ..........
Type: corresponding restful api method
Returned Object: object name
"""


def generate_schemas(base_url, domain, search_results, verbose=False):
    # search_results = link_search_s3(
    #     [f"{make_slug(domain)}", '.txt'], unique=True, verbose=verbose)

    if verbose:
        logger.info(f"number of matches: {len(search_results)}")
        logger.info(search_results)

    object_details = defaultdict(list)
    for endpoint in search_results:
        endpoint_details = string_to_dict(query(
            f"""Describe the {endpoint} endpoint in a format that matches the following examples: {prompt_examples}.
            Note that the "Returned Object" should always be plural, lowercase with underscores instead of spaces.""",
            {'referenced_urls': endpoint},
            verbose=False
        ))

        if endpoint_details is not None and \
            "Returned Object" in endpoint_details and \
            "/" not in endpoint_details["Returned Object"] and \
            "None" not in endpoint_details["Returned Object"] and \
                " " not in endpoint_details["Returned Object"]:
            object_details[endpoint_details["Returned Object"]].append(
                endpoint_details)

        logger.info(f"endpoint_details: {endpoint_details}")

    if verbose:
        for object, endpoints in object_details.items():
            logger.info(f"\n\n\n{object}: {len(endpoints)}")
            logger.info(f"{endpoints}\n\n\n")

    return object_details
