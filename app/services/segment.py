import os
from dotenv import load_dotenv
import segment.analytics as analytics

load_dotenv()
analytics.write_key = os.getenv('SEGMENT_WRITE_KEY')


def identify_user(user):
    analytics.identify(user[0], {
        'Email': user[1],
        'First Name': user[3],
        'Last Name': user[4],
    })
    analytics.flush()


def track_event(user_id, event_name, params):
    analytics.track(user_id, event_name, params)
    analytics.flush()
