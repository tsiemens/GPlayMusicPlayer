#!/usr/bin/env python3

import argparse
import atexit
from dataclasses import dataclass
import os
import random
import sys
import termios
from time import sleep
import threading

from gmusicapi import Mobileclient
from setproctitle import setproctitle
from system_hotkey import SystemHotkey
import vlc

from gpmp.log import get_logger
from gpmp.threading import Atomic
from gpmp.util import enable_echo, pdb

log = get_logger("main")

oauth_file = Mobileclient.OAUTH_FILEPATH

class MediaPlayer:
   def __init__(self, url):
      self.player = vlc.MediaPlayer(url)

   def __del__(self):
      """NOTE: This MUST not be called from within an event callback from the
      player.
      """
      if self.player.is_playing():
         self.player.stop()

      self.player.release()

   def __getattr__(self, attr):
      return getattr(self.player, attr)

@dataclass
class PlayerEvent:
   event_str: str
   track_index: int

def get_all_songs_dict(api):
   songs = api.get_all_songs()
   return {
         song['id']: {
               'artist': song.get('artist'),
               'title': song.get('title'),
            }
         for song in songs
      }

class TrackPlayer:
   def __init__(self, api, hotkey_mgr):
      self.api = api
      self.hotkey_mgr = hotkey_mgr
      self.setup_hotkeys()
      songs = api.get_all_songs()
      self.songs = get_all_songs_dict(api)
      # List of track ids
      self.tracks_to_play = []
      self.current_track_index = None
      self.current_song_info = Atomic(None)

      self.player = None
      self.pending_events = []
      self.event_handler_thread = None

   def setup_hotkeys(self):
      self.hotkey_mgr.register(('control', 'up'),
                               callback=lambda _: self.toggle_play())
      self.hotkey_mgr.register(('control', 'right'),
                               callback=lambda _: self.play_next_track())
      self.hotkey_mgr.register(('control', 'left'),
                               callback=lambda _: self.handle_previous_track_action())
      self.hotkey_mgr.register(('control', 'shift', 'right'),
                               callback=lambda _: self.skip_to_end())

   def set_tracks_to_play(self, track_ids):
      self.tracks_to_play = track_ids

   def shuffle_tracks(self):
      random.shuffle(self.tracks_to_play)

   def get_position(self):
      if self.player:
         return self.player.get_position()
      return 0.0

   def handle_track_finished(self):
      self.play_next_track()

   def handle_player_event(self, event):
      log.debug("{}".format(event))
      if event.type == vlc.EventType.MediaPlayerEndReached:
         self.pending_events.append(PlayerEvent(str(event.type),
                                                    self.current_track_index))

   def _get_player_for_url(self, url):
      if not self.player:
         self.player = MediaPlayer(url)
      else:
         self.player.set_mrl(url)
      # https://www.olivieraubert.net/vlc/python-ctypes/doc/vlc.EventType-class.html
      event_blacklist = set([vlc.EventType.MediaPlayerTimeChanged,
                             vlc.EventType.MediaPlayerPositionChanged,
                             vlc.EventType.MediaPlayerLengthChanged,
                             vlc.EventType.MediaPlayerBuffering,
                             vlc.EventType.MediaPlayerAudioVolume,
                             vlc.EventType.MediaPlayerAudioDevice,
                             vlc.EventType.MediaPlayerESSelected,
                             vlc.EventType.MediaPlayerESAdded,
                             vlc.EventType.MediaPlayerESDeleted,
                             vlc.EventType.MediaPlayerScrambledChanged,
                             vlc.EventType.MediaPlayerPausableChanged,
                             vlc.EventType.MediaPlayerSeekableChanged,
                             ])
      for attr in dir(vlc.EventType):
         if attr.startswith("Media") or attr.startswith("Vlm"):
            event = getattr(vlc.EventType, attr)
            if event not in event_blacklist:
               self.player.event_manager().event_attach(event,
                                                        self.handle_player_event)

      return self.player

   def play_current_track(self):
      song_id = self.tracks_to_play[self.current_track_index]
      song_info = self.songs.get(song_id)
      song_str = "Unknown - Unknown"
      if song_info:
         song_str = "{0} - {1}".format(song_info['title'], song_info['artist'])
      else:
         log.error("Could not find track info for {}".format(song_id))

      self.current_song_info.value = song_str

      url = self.api.get_stream_url(song_id)
      code = self._get_player_for_url(url).play()
      if code != 0:
         log.error("player.play returned error: {}".format(code))
         return False

      log.info("Started player: OK")
      return True

   def handle_previous_track_action(self):
      if self.player is not None and self.player.get_position() > 0.1:
         # Song is 10% done. Restart the track rather than going back.
         self.player.set_position(0.0)
         return

      if self.current_track_index is None or self.current_track_index <= 0:
         self.current_track_index = 0
      else:
         self.current_track_index -= 1

      self.play_current_track()

   def play_next_track(self):
      log.info("current_track_index {}".format(self.current_track_index))
      if self.current_track_index is None:
         self.current_track_index = 0
      else:
         self.current_track_index += 1

      if self.current_track_index >= len(self.tracks_to_play):
         log.info("Reached end of track list")
         return False

      return self.play_current_track()

   def skip_to_end(self):
      if self.player is not None:
         self.player.set_position(0.97)

   def toggle_play(self):
      if self.player is None:
         self.play_next_track()
      elif self.player.is_playing():
         self.player.pause()
      else:
         code = self.player.play()
         if code != 0:
            log.error("player.play returned error: {}".format(code))

   def do_thread_loop(self):
      if self.pending_events:
         log.debug("n pending_events: {}".format(
                   len(self.pending_events)))
      while self.pending_events:
         event = self.pending_events.pop(0)
         log.debug("event {}".format(event))
         if event.track_index != self.current_track_index:
            log.debug("ignoring event for other track")
            continue

         if event.event_str == str(vlc.EventType.MediaPlayerEndReached):
            log.debug("track finished")
            self.handle_track_finished()

   def start_event_handler_thread(self):
      def player_thread():
         t = threading.currentThread()
         while getattr(t, "do_run", True):
            sleep(0.1)
            self.do_thread_loop()

         log.info("MediaPlayer event handler thread exited")

      self.event_handler_thread = threading.Thread(target=player_thread)
      self.event_handler_thread.start()

   def stop_event_handler_thread(self):
      if self.event_handler_thread is not None:
         self.event_handler_thread.do_run = False
         self.event_handler_thread.join()

def get_user_selected_playlist_tracks(api):
   playlists = api.get_all_user_playlist_contents()
   for i, playlist in enumerate(playlists):
      print("[{0}]: {1}".format(i, playlist['name']))

   index = int(input("\nSelect a playlist. "))
   if index >= len(playlists):
      print("No playlist at that index.")
      return None

   playlist = playlists[index]
   del playlists

   return [t['trackId'] for t in playlist['tracks']]

def run_cli_player(api, hotkey_mgr, play_all_songs=False):
   player = TrackPlayer(api, hotkey_mgr)

   if play_all_songs:
      trackIds = list(player.songs.keys())
   else:
      trackIds = get_user_selected_playlist_tracks(api)

   player.set_tracks_to_play(trackIds)
   player.shuffle_tracks()

   player.toggle_play()
   player.start_event_handler_thread()

   return player

def main():
   setproctitle("gplaymusicplayer")

   parser = argparse.ArgumentParser()
   parser.add_argument('--all-songs', action='store_true',
                       help="Play all songs in the library, rather than selecting a playlist")
   parser.add_argument('--gui', action='store_true',
                       help="Run in GUI mode")
   args = parser.parse_args()

   api = Mobileclient()
   if not os.path.exists(oauth_file):
      api.perform_oauth(oauth_file)

   device_id = Mobileclient.FROM_MAC_ADDRESS
   api.oauth_login(device_id, oauth_credentials=oauth_file)

   hotkey_mgr = SystemHotkey()

   if args.gui:
      from gpmp import gui

      def player_thread():
         run_cli_player(api, hotkey_mgr, play_all_songs=args.all_songs)

      #  t = threading.Thread(target=player_thread)
      #  t.start()

      app = gui.make_app()
      controller = gui.QtController(app)
      app.exec_()

      #  gui.show_gui(app)

      t.do_run = False
      t.join()
   else:
      from gpmp import cliui
      player = run_cli_player(api, hotkey_mgr, play_all_songs=args.all_songs)
      ui = cliui.CliUI(player)
      ui.exec_()

      player.stop_event_handler_thread()

if __name__ == '__main__':
   main()
