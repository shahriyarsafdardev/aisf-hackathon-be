from app.services.plugin_generator.yaml_generator import create_plugin_yaml
from app.services.scrapping.scrapper import process_domain


async def plugin_handler(connector_name, connector_start_url, connector_base_url):
    await process_domain(connector_base_url, [connector_start_url], connector_base_url)
    await create_plugin_yaml(connector_name, connector_base_url)
