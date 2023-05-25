import os
import psycopg2
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from app.core.logging import getLogger
from app.services.content_sources import rearrange_content_sources

load_dotenv()


rds_hostname = os.getenv('RDS_HOSTNAME')
rds_port = os.getenv('RDS_PORT')
rds_db_name = os.getenv('RDS_DB_NAME')
rds_username = os.getenv('RDS_USERNAME')
rds_password = os.getenv('RDS_PASSWORD')


def get_connection():
    conn = psycopg2.connect(
        host=rds_hostname,
        port=rds_port,
        dbname=rds_db_name,
        user=rds_username,
        password=rds_password
    )
    return conn


logger = getLogger()


def execute_query(query, params=None, fetch=True):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(query, params)

        if fetch:
            result = cursor.fetchall()
        else:
            result = None

        conn.commit()
        cursor.close()
        conn.close()

        if fetch:
            return result
        return True
    except Exception as e:
        logger.error(f"An error occurred while executing the query: {e}")
        return None


def check_last_page_read_time(domain):
    select_query = "SELECT MAX(read_time) FROM Pages WHERE domain = %s;"
    result = execute_query(select_query, (domain,))

    if result[0][0] is not None:
        last_read_time = result[0][0].replace(tzinfo=timezone.utc)
        current_time = datetime.now(timezone.utc)
        time_difference = current_time - last_read_time
        return time_difference > timedelta(minutes=2)
    else:
        return False


def execute_query_with_connection(connection, query, params=None, fetch=True):
    cursor = connection.cursor()

    cursor.execute(query, params)

    if fetch:
        result = cursor.fetchall()
    else:
        result = None

    connection.commit()
    cursor.close()

    return result


def create_pages_table():
    create_table_query = '''
    CREATE TABLE IF NOT EXISTS Pages (
        id SERIAL PRIMARY KEY,
        title VARCHAR(2048) NOT NULL,
        url VARCHAR(2048) NOT NULL UNIQUE,
        domain VARCHAR(2048) NOT NULL,
        read_time TIMESTAMP NOT NULL
    );
    '''
    execute_query(create_table_query, fetch=False)


def insert_page(conn, domain, title, url, read_time):
    insert_query = "INSERT INTO pages (domain, title, url, read_time) VALUES (%s, %s, %s, %s) ON CONFLICT (url) DO UPDATE SET domain = EXCLUDED.domain, title = EXCLUDED.title, read_time = EXCLUDED.read_time;"
    execute_query_with_connection(
        conn, insert_query, (domain, title, url, read_time), fetch=False)


def page_exists_with_url(conn, url):
    select_query = "SELECT EXISTS(SELECT 1 FROM Pages WHERE url = %s);"
    result = execute_query_with_connection(conn, select_query, (url,))
    return result[0][0]


def is_domain_exists(domain):
    select_query = "SELECT EXISTS(SELECT 1 FROM Pages WHERE domain = %s);"
    result = execute_query(select_query, (domain,))
    return result[0][0]


def count_pages_with_domain(domain):
    select_query = "SELECT COUNT(*) FROM Pages WHERE domain = %s;"
    result = execute_query(select_query, (domain,))
    return result[0][0]


def insert_connector(name, start_url, base_url):
    insert_query = "INSERT INTO connectors (name, documentation_start_url, documentation_base_url, created_at) VALUES (%s, %s, %s, %s);"
    result = execute_query(
        insert_query, (name, start_url, base_url, datetime.now()), fetch=False)
    return result


def get_connectors():
    query = "SELECT c.name, c.low_code_export_url, COALESCE(p.page_count, 0) as page_count FROM connectors c LEFT JOIN (SELECT domain, COUNT(*) as page_count FROM pages GROUP BY domain) p ON c.documentation_base_url = p.domain ORDER BY c.name;"
    result = execute_query(query, fetch=True)
    return result


def get_connector_details(name):
    select_query = "SELECT name, documentation_base_url, low_code_export_url FROM connectors WHERE name = %s;"
    result = execute_query(select_query, (name,))
    if result:
        return result[0]
    else:
        return None


def update_connector_low_code_export_url(low_code_export_url, base_url):
    update_query = "UPDATE connectors SET low_code_export_url = %(low_code_export_url)s WHERE documentation_base_url = %(base_url)s;"
    params = {
        'low_code_export_url': low_code_export_url,
        'base_url': base_url
    }
    execute_query(update_query, params=params, fetch=False)


def unset_low_code_export_url(name):
    update_query = "UPDATE connectors SET low_code_export_url = NULL WHERE name = %s;"
    execute_query(update_query, (name,), fetch=False)


def get_urls_by_domain(domain):
    select_query = "SELECT url FROM Pages WHERE domain = %s;"
    result = execute_query(select_query, (domain,))

    urls = []

    if result:
        urls = [row[0] for row in result]

    return urls


def does_connector_exist(name):
    select_query = "SELECT EXISTS(SELECT 1 FROM connectors WHERE name = %s);"
    result = execute_query(select_query, (name,))
    return result[0][0]


def find_user(email):
    select_query = "SELECT COUNT(*) FROM users WHERE email = %s;"
    result = execute_query(select_query, (email,),  fetch=True)
    return result[0][0]


def fetch_user(email):
    select_query = "SELECT * FROM users WHERE email = %s;"
    result = execute_query(select_query, (email,),  fetch=True)
    return result


def fetch_user_by_id(user_id):
    select_query = "SELECT * FROM users WHERE id = %s;"
    result = execute_query(select_query, (user_id,),  fetch=True)
    return result


def create_new_user(email, password, fisrtname, lastname):
    select_query = "INSERT INTO users (email, password, first_name, last_name) VALUES ( %s, %s, %s, %s);"
    result = execute_query(
        select_query, (email, password, fisrtname, lastname),  fetch=False)
    return result


def get_content_sources():
    select_query = "SELECT * from content_sources;"
    return execute_query(select_query, fetch=True)


def get_content_sources_for_user(user_id):
    query = """
    SELECT content_sources.*
    FROM content_sources
    INNER JOIN user_content_sources ON content_sources.id = user_content_sources.content_source_id
    WHERE user_content_sources.user_id = %s
    """
    return execute_query(query, params=(user_id,))


def get_content_sources_except_user(user_id):
    query = """
    SELECT content_sources.*
    FROM content_sources
    LEFT JOIN user_content_sources ON content_sources.id = user_content_sources.content_source_id
    WHERE user_content_sources.user_id IS NULL OR user_content_sources.user_id != %s
    """
    return execute_query(query, params=(user_id,))


def get_all_content_sources(user_id):
    user_content_sources = get_content_sources_for_user(user_id)
    remaining_content_sources = get_content_sources_except_user(user_id)
    user_content_sources= rearrange_content_sources(user_content_sources)
    remaining_content_sources = rearrange_content_sources(remaining_content_sources)
    return {"user_content_sources": user_content_sources, "remaining_content_sources": remaining_content_sources}


def add_user_content_source(user_id, content_source_id, customer_id, subscription_id):
    if check_user_and_content_source_existence(user_id, content_source_id) == False:
        return False
    query = """
    INSERT INTO user_content_sources (user_id, content_source_id, customer_id, subscription_id)
    SELECT %s, %s, %s, %s
    WHERE NOT EXISTS (
        SELECT 1 FROM user_content_sources 
        WHERE user_id = %s AND content_source_id = %s
    )
    """
    params = (user_id, content_source_id, customer_id,
              subscription_id, user_id, content_source_id)
    return execute_query(query, params=params, fetch=False)


def remove_user_content_source(user_id, content_source_id):
    query = """
    DELETE FROM user_content_sources 
    WHERE user_id = %s AND content_source_id = %s
    """
    params = (user_id, content_source_id)
    return execute_query(query, params=params, fetch=False)


def check_user_and_content_source_existence(user_id, content_source_id):
    user_exists = execute_query(
        "SELECT 1 FROM users WHERE id = %s", params=(user_id,), fetch=True)
    content_source_exists = execute_query(
        "SELECT 1 FROM content_sources WHERE id = %s", params=(content_source_id,), fetch=True)
    if content_source_exists and user_exists:
        return True
    return False


def get_user_content_source_ids(user_id):
    select_query = "SELECT content_source_id FROM user_content_sources WHERE user_id = %s"
    results = execute_query(select_query, (user_id,))

    if not results:
        return None
    return [result[0] for result in results]


def get_stripe_price_id(content_source_id):
    query = """
    SELECT stripe_price_id FROM content_sources
    WHERE id = %s
    """
    return execute_query(query, params=(content_source_id,), fetch=True)[0][0]


def get_subscription_id(user_id, content_source_id):
    query = """
    SELECT subscription_id FROM user_content_sources 
    WHERE user_id = %s AND content_source_id = %s
    """
    params = (user_id, content_source_id)
    result = execute_query(query, params=params, fetch=True)

    if result and len(result) > 0:
        return result[0][0]

    return None


