import datetime
import re
import requests
from io import BytesIO
from bs4 import BeautifulSoup
import PyPDF2
import os
import json
from urllib.parse import urljoin, urlparse, urlunparse
from app.services.scrapping.chunk_generator import file_to_vectors, html_to_text
from app.services.postgres_db import get_connection, insert_page, page_exists_with_url
from app.services.pinecone_db import store_vectors
from app.services.s3 import upload_to_s3, remove_and_append_unique_lines
from app.core.logging import getLogger
from scrapingbee import ScrapingBeeClient

logger = getLogger()


async def process_domain(domain, urls, base_url):
    logger.info(f"Processing domain: {domain}")
    url_count = len(urls)

    if url_count == 0:
        logger.info("No URLs to process.")
        return

    processed_urls = 0
    remaining_urls = urls.copy()
    db_connection = get_connection()
    while processed_urls < 20 and len(remaining_urls) > 0:
        chunk_size = min(20 - processed_urls, len(remaining_urls))
        chunk_urls = remaining_urls[:chunk_size]
        remaining_urls = remaining_urls[chunk_size:]

        child_urls = process_pages_chunk(
            domain, chunk_urls, db_connection, base_url)
        processed_urls += chunk_size
        remaining_urls = list(set(remaining_urls + child_urls))
        logger.info(f"Children URL: {len(remaining_urls)} {remaining_urls}")

    db_connection.close()
    if len(remaining_urls) > 0:
        logger.info(f"Recursing on {len(remaining_urls)} child URLs.")
        middle = len(remaining_urls) // 2
        first_half = remaining_urls[:middle]
        second_half = remaining_urls[middle:]

        logger.info("Running process_domain recursion locally.")
        await process_domain(domain, first_half, base_url)
        await process_domain(domain, second_half, base_url)


def process_pages_chunk(domain, urls, db_connection, base_url):
    child_urls = list()
    new_urls = list()
    for url in urls:
        if (page_exists_with_url(db_connection, url)):
            logger.info(f"Skipping page {url} because it already exists.")
            continue
        try:
            child_urls += process_page(db_connection, domain, url, base_url)
        except Exception as e:
            logger.error(f"An error occurred while processing page {url}: {e}")

    new_urls += [url for url in child_urls if not page_exists_with_url(
        db_connection, url)]

    return new_urls


def process_page(db_connection, domain, url, base_url):
    child_links = list()
    try:
        logger.info(f"Processing page: {url}")

        if is_json_url(url):
            return child_links

        try:
            response = download_file(url)
        except Exception as e:
            logger.info(f"An error occurred while downloading page {url}: {e}")
            return child_links

        if response is None:
            return child_links

        try:
            upload_file_to_s3(url, response)
        except Exception as e:
            logger.info(f"An error occurred while uploading to S3: {e}")

        content_type = response.headers.get('Content-Type')
        file_extension = get_file_extension(content_type)
        if file_extension == 'html':
            try:
                child_links += extract_links(domain, response.text, base_url)
            except Exception as e:
                logger.info(f"An error occurred while extracting links: {e}")

        text = html_to_text(
            response.text) if file_extension == 'html' else pdf_to_text(response.content)
        centralized_s3_key = generate_bulk_text_file_key(url)
        unique_text = remove_and_append_unique_lines(text, centralized_s3_key)

        logger.info(f"text data for {url}", unique_text)
        upload_text_to_s3(url, unique_text)
        file_to_vectors(unique_text, url)
        save_page_to_postgres(db_connection, domain, url, response)
    except Exception as e:
        logger.info(
            f"Something went wrong while processing this url: {url} - {e}")

    return child_links


def download_file(url):
    try:
        response = requests.get(url)
        a_list = []
        soup = BeautifulSoup(response.text, 'html.parser')
        a_list = soup.find_all('a', href=True)
        if len(a_list) == 0:
            response = scraping_bee_scrapper(url)

    except requests.RequestException as e:
        logger.error(f"An error occurred while making the request: {e}")
        return

    if response.status_code != 200:
        logger.error(
            f"Request failed with status code: {response.status_code}")
        return

    if not is_web_page_or_pdf(response):
        logger.error("The provided URL is not a valid web page or PDF file.")
        return

    return response


def scraping_bee_scrapper(url):
    client = ScrapingBeeClient(
        api_key=os.getenv("SCRAPING_BEE_API_KEY"))

    response = client.get(url)

    return response


def is_web_page_or_pdf(response):
    try:
        content_type = response.headers.get('Content-Type')
        return content_type is not None and ('text/html' in content_type or 'application/pdf' in content_type)
    except Exception as e:
        logger.error(f"Something went wrong while checking the page type {e}")
        return False


def is_json_url(url):
    parsed_url = urlparse(url)
    file_extension = os.path.splitext(parsed_url.path)[1]
    return file_extension.lower() == '.json'


def generate_bulk_text_file_key(url):
    parsed_url = urlparse(url)
    domain_name = parsed_url.netloc
    filename = domain_name + '-bulk-text.txt'

    return filename


def generate_file_name(url):
    try:
        parsed_url = urlparse(url)
        no_scheme_url = parsed_url.netloc + parsed_url.path
        filename = re.sub(r'[^a-zA-Z0-9_-]+', '-',
                          no_scheme_url).replace('.', '-')
        filename = re.sub(r'^[-_]+|[-_]+$', '', filename)

        return filename
    except Exception as e:
        logger.error(
            f"Something went wrong while generating file name: {url} - {e}")
        return "Error"


def upload_file_to_s3(url, response):
    try:
        filename = generate_file_name(
            url) + '.' + get_file_extension(response.headers.get('Content-Type'))
        file_data = BytesIO(response.content)
        logger.info(f"File data: {file_data}")
        upload_to_s3(file_data, filename)
    except Exception as e:
        logger.error(f"Error uploading file to S3 for URL {url}: {e}")


def upload_text_to_s3(url, markdown_text):
    try:
        filename = generate_file_name(url) + '.txt'
        file_data = BytesIO(markdown_text.encode("utf-8"))
        upload_to_s3(file_data, filename)
    except Exception as e:
        logger.error(f"Error uploading text to S3 for URL {url}: {e}")


def get_domain(url):
    try:
        parsed_url = urlparse(url)
        return f"{parsed_url.scheme}://{parsed_url.netloc}"
    except Exception as e:
        logger.error(
            f"Something went wrong while getting the domain: {url} - {e}")
        return None


def extract_links(domain, html_content, base_url):
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        header = soup.find('header') or soup.find('div', class_='header')
        if header:
            header.decompose()
        footer = soup.find('footer') or soup.find('div', class_='footer')
        if footer:
            footer.decompose()

        links = []
        for a in soup.find_all('a', href=True):
            href = a.get('href')
            try:
                parsed_url = urlparse(href)
                if not parsed_url.scheme and not parsed_url.netloc:
                    href = urljoin(domain, href)

                parsed_url = urlparse(href)
                if parsed_url.scheme in ['http', 'https'] and verify_base_url(base_url, href):
                    parsed_url = parsed_url._replace(query='', fragment='')
                    clean_url = urlunparse(parsed_url)
                    links.append(clean_url)
            except Exception as e:
                logger.error(f"Error while parsing URL {href}: {e}")

        return links
    except Exception as e:
        logger.error(f"Something went wrong while extracting links {e}")
        return []


def get_file_extension(content_type):
    try:
        if 'text/html' in content_type:
            return 'html'
        elif 'application/pdf' in content_type:
            return 'pdf'
        else:
            return 'unknown'
    except Exception as e:
        logger.error(f"Something went wrong while getting file extension {e}")
        return 'unknown'


def pdf_to_text(pdf_content):
    try:
        pdf_file = BytesIO(pdf_content)

        pdf_reader = PyPDF2.PdfReader(pdf_file)

        pdf_text = ""
        for page in pdf_reader.pages:
            pdf_text += page.extract_text()
        return pdf_text
    except Exception as e:
        logger.error(f"Something went wrong while converting pdf to txt {e}")
        return ''


def save_page_to_postgres(db_connection, domain, url, response):
    try:
        logger.info(f"Postgres URL: {url}")
        soup = BeautifulSoup(response.text, 'html.parser')
        title = generate_file_name(url)
        page_title = soup.title.string if soup.title else title
        insert_page(db_connection, domain, page_title,
                    url, datetime.datetime.now())
    except Exception as e:
        logger.error(f"Error saving page to Postgres for URL {url}: {e}")


def store_chunks_in_pinecone(chunks, url):
    try:
        store_vectors(chunks, url)
    except Exception as e:
        logger.error(f"Error storing chunk in Pinecone: {e}")


def verify_base_url(base_url, child_url):
    return child_url.startswith(base_url)
