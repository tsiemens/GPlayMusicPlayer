"""Utilities for authenticating gmusicapi"""

import os

from gmusicapi import Mobileclient

OAUTH_FILE = Mobileclient.OAUTH_FILEPATH

def authenticate_client(api: Mobileclient):
   if not os.path.exists(OAUTH_FILE):
      api.perform_oauth(OAUTH_FILE)

   device_id = Mobileclient.FROM_MAC_ADDRESS
   api.oauth_login(device_id, oauth_credentials=OAUTH_FILE)
