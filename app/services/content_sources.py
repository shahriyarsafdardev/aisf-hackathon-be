def rearrange_content_sources(content_sources):
    for i in range(len(content_sources)):
        id, name, price, price_id = content_sources[i]

        if price == 0.0:
            content_sources[i] = [id, name, price_id, price]

    return content_sources