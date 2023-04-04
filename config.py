import google.auth
import os
import os.path
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from pathlib import Path


class config():

    def __init__(self):

        if os.path.isfile('.env'):
            env_path = Path('.') / '.env'
            load_dotenv(dotenv_path=env_path)

        # Mandatory environment variables
        self.dns_record_ttl = os.environ.get('DNS_RECORD_DEFAULT_TTL', 300)

        # Required for local testing
        self.auth_key_file_path = os.environ.get('AUTH_KEY_JSON_FILE_PATH')

        if self.auth_key_file_path is None:
            # Running in Google Cloud
            self.credentials, self.project_id = google.auth.default()
        else:
            # Running locally
            self.credentials = Credentials.from_service_account_file(
                self.auth_key_file_path, scopes=['https://www.googleapis.com/auth/cloud-platform'])
            self.project_id = self.credentials.project_id
