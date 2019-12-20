"""Utilities for authenticating gmusicapi"""

import os
from socket import AddressFamily
import psutil

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

def authenticate_client(api: Mobileclient):
   if not os.path.exists(OAUTH_FILE):
      api.perform_oauth(OAUTH_FILE)

   device_id = Mobileclient.FROM_MAC_ADDRESS
   api.oauth_login(device_id, oauth_credentials=OAUTH_FILE)
