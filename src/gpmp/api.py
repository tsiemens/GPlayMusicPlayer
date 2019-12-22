"""A wrapper around the gmusicapi client, and utilities for using it"""

import os
from socket import AddressFamily

import psutil
import requests

import gmusicapi.clients.mobileclient as mc
from gmusicapi import Mobileclient

from gpmp.log import get_logger

log = get_logger()

OAUTH_FILE = Mobileclient.OAUTH_FILEPATH

_orig_getmac = mc.getmac

def _get_intf_mac():
   lowest_mac = 0x1000000000000
   lowest_mac_str = None
   lowest_mac_name = None
   ifs = psutil.net_if_addrs()
   for ifname, ifnicaddrs in ifs.items():
      for ifnicaddr in ifnicaddrs:
         if ifnicaddr.family == AddressFamily.AF_PACKET:
            # MAC
            mac_int = int(ifnicaddr.address.replace(":", ""), 16)
            if mac_int > 0 and mac_int < lowest_mac:
               lowest_mac = mac_int
               lowest_mac_str = ifnicaddr.address
               lowest_mac_name = ifname

   if lowest_mac_name is not None:
      log.info("Using intf %s's MAC: %d (%s)", lowest_mac_name, lowest_mac, lowest_mac_str)
      return lowest_mac
   return None

def _getmac():
   """This is a workaround for the implementation of gmusicapi when given
   Mobileclient.FROM_MAC_ADDRESS, though adapted to try a little harder to
   provide a valid MAC int.
   """
   mac_int = _orig_getmac()
   if (mac_int >> 40) % 2:
      # As per RFC 4122, bit 40 is set if getnode could not find an ID, so it returns
      # a random one with bit 40 set, but this could change between calls, or
      # between system restarts.
      # mobileclient refuses to allow bit 40 to be set, so we need to dig a little
      # to get a stable MAC.
      log.warning("getnode has 40th bit set (device id was randomized). "
                  "Manually retrieving interface mac")
      intf_mac_int = _get_intf_mac()
      if intf_mac_int is not None:
         return intf_mac_int
   return mac_int

mc.getmac = _getmac

class Client:
   def __init__(self):
      self.api = Mobileclient()
      self._client_authenticated = False

   def _authenticate_client(self):
      if not os.path.exists(OAUTH_FILE):
         self.api.perform_oauth(OAUTH_FILE)

      device_id = Mobileclient.FROM_MAC_ADDRESS
      self.api.oauth_login(device_id, oauth_credentials=OAUTH_FILE)

   def authenticate(self):
      if self._client_authenticated:
         # Get a new client and reauthenticate
         self.api = Mobileclient()
      self._authenticate_client()
      self._client_authenticated = True

   def __getattr__(self, attr):
      '''For other attributes, grab it from the Mobileclient'''
      attrval = getattr(self.api, attr)
      if callable(attrval):
         # Sometimes we will get timeouts (and possibly other exceptions) when
         # the API has existed for a while. In this case, we need to get a new
         # Mobileclient and reauthenticate it.
         # Wrap the Mobileclient's method such that it can handle this kind
         # of failure once.
         def wrapper(*args, **kwargs):
            try:
               return attrval(*args, **kwargs)
            except requests.exceptions.ReadTimeout as e:
               log.warning("ReadTimeout calling %s:%r"
                           "\nReauthenticating client and retrying.", attr, e)
               self.authenticate()
               return getattr(self.api, attr)(*args, **kwargs)
         return wrapper
      return attrval
