import os

from gmusicapi import Mobileclient

oauth_file = Mobileclient.OAUTH_FILEPATH

def authenticate_client(api: Mobileclient):
   if not os.path.exists(oauth_file):
      api.perform_oauth(oauth_file)

   device_id = Mobileclient.FROM_MAC_ADDRESS
   api.oauth_login(device_id, oauth_credentials=oauth_file)

