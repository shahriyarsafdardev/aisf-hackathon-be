import re
import uuid
import html2text
from bs4 import BeautifulSoup, Tag
from dotenv import load_dotenv
from app.services.scrapping.web_parser import get_subset_urls
from app.services.openai import create_embedding
from app.services.pinecone_db import store_chunks
from app.services.scrapping.link_parser import link_search_text


load_dotenv()


def html_to_text(file_content):
    try:
        soup = BeautifulSoup(file_content, 'html.parser')
        header = soup.find('header') or soup.find('div', class_='header')
        if header:
            header.decompose()
        footer = soup.find('footer') or soup.find('div', class_='footer')
        if footer:
            footer.decompose()

        # Find all heading tags
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])

        # Modify the heading tags
        for heading in headings:
            # Extract the text from the heading
            heading_text = heading.get_text()

            # Create a new heading tag with the extracted text
            new_heading = Tag(name=heading.name)
            new_heading.string = heading_text

            # Replace the original heading with the new one
            heading.replace_with(new_heading)

        modified_html_content = str(soup)

        converter = html2text.HTML2Text()
        converter.ignore_links = True
        converter.ignore_images = True
        text = converter.handle(modified_html_content)
        return text
    except Exception as e:
        return ''


def split_into_chunks(text, max_length=500):
    chunks = []
    current_chunk = ''

    # Split the text by markdown headers
    paragraphs = re.split(r'(\n*#{1,6} .*\n*)', text)
    header_pattern = re.compile(r'(\n*#{1,6} .*\n*)')
    new_paragraphs = []
    current_title = None

    for paragraph in paragraphs:
        if header_pattern.match(paragraph):
            current_title = paragraph
        else:
            if current_title:
                new_paragraphs.append(current_title + "\n" + paragraph)
                current_title = None
            else:
                pass

    paragraphs = new_paragraphs

    for idx, paragraph in enumerate(paragraphs):
        if len(current_chunk) + len(paragraph) + 1 <= max_length:
            current_chunk += "\n"+paragraph
        else:
            # If the current chunk is not empty, append it to the chunks list
            if current_chunk:
                chunks.append(current_chunk)

            # Start a new chunk with the current paragraph
            current_chunk = paragraph

    # Append the last chunk if not empty
    if current_chunk:
        chunks.append(current_chunk.strip())

    chunks = [chunk.strip() for chunk in chunks]

    return chunks


def file_to_vectors(file_content, file_url):
    chunks = split_into_chunks(file_content)
    chunks = [text_slice_to_vector(chunk, file_url) for chunk in chunks]
    store_chunks(chunks)
    return chunks


def text_slice_to_vector(text, file_url):
    return (
        str(uuid.uuid4()),
        create_embedding(text),
        {
            "text": text,
            "page_urls": get_subset_urls(file_url),
            "referenced_urls": link_search_text(text)
        }
    )
