import os
import dotenv

dotenv.load_dotenv()


def set_hubspot_headers():
    access_token = os.getenv('HUBSPOT_ACCESS_TOKEN')
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    
    return headers