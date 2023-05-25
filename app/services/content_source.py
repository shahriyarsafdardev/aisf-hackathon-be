from app.services.postgres_db import get_content_sources_except_ids, get_content_sources_for_user


def get_all_content_sources(user_id):
    user_content_sources = get_content_sources_for_user(user_id)
    user_content_source_ids = [source[0] for source in user_content_sources]
    remaining_content_sources = get_content_sources_except_ids(
        user_content_source_ids)
    user_content_sources = rearrange_content_sources(user_content_sources)
    remaining_content_sources = rearrange_content_sources(
        remaining_content_sources)
    return {"user_content_sources": user_content_sources, "remaining_content_sources": remaining_content_sources}


def rearrange_content_sources(content_sources):
    if content_sources is None:
        return []

    def sorting_key(content_source):
        id, name, price, price_id = content_source
        return price_id == '' or price == 0.0

    content_sources.sort(key=sorting_key)
    return content_sources
