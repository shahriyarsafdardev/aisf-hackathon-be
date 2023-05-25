import os
from dotenv import load_dotenv
import segment.analytics as analytics

load_dotenv()
analytics.write_key = os.getenv('SEGMENT_WRITE_KEY')

def analytics_error(error, items):
    print("An error occurred:", error)

analytics.debug = True
analytics.on_error = analytics_error

def track_query_logs(user_id, event_name, params):
  analytics.track(user_id, event_name, params)


