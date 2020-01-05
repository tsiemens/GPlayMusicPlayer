"""Classes for media player and library"""

from dataclasses import dataclass
import random
from time import sleep
import threading

from gmusicapi import Mobileclient
from system_hotkey import SystemHotkey
import vlc

from gpmp.log import get_logger
from gpmp.threading import Atomic

log = get_logger()

class Library:
   def __init__(self, api: Mobileclient):
      self.api = api
      self.songs = None
      self.playlist_meta = None
      self.playlist_contents = None

   def load_core(self):
      self.songs = self._get_all_songs_dict()
      self.playlist_meta = [p for p in self.api.get_all_playlists()
                            if not p['deleted']]
      self.playlist_meta = sorted(self.playlist_meta,
                                  key=lambda p: p['name'])

   def load_playlist_contents(self):
      raw_playlist_contents = self.api.get_all_user_playlist_contents()
      self.playlist_contents = {}
      for pl in raw_playlist_contents:
         trimmed_pl = []
         for track in pl['tracks']:
            track_id = track['trackId']
            trimmed_pl.append(track_id)
            if track_id not in self.songs:
               if 'track' not in track:
                  log.warning("Track %s has no 'track' dict", track_id)
                  continue
               track_info = track['track']
               artist = track_info.get('artist')
               title = track_info.get('title')
               if artist is None or title is None:
                  log.warning("Track %s did not have both title and artist. Found %r, %r",
                              track_id, title, artist)
                  continue
               self.songs[track_id] = {
                  'artist': artist,
                  'title': title,
               }

         self.playlist_contents[pl['id']] = trimmed_pl

   def _get_all_songs_dict(self):
      songs = self.api.get_all_songs()
      return {
         song['id']: {
            'artist': song.get('artist'),
            'title': song.get('title'),
            'song': song,
         }
         for song in songs
      }

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

@dataclass
class TrackTimingInfo:
   position_fract: float
   duration_secs: float

class TrackPlayer:
   # pylint: disable-msg=too-many-instance-attributes

   def __init__(self, api: Mobileclient, hotkey_mgr: SystemHotkey, library: Library):
      self.initialized_val = Atomic(False)
      self.api = api
      self.hotkey_mgr = hotkey_mgr
      self.library = library
      if self.hotkey_mgr:
         self.setup_hotkeys()

      # List of track ids
      self.tracks_to_play = []
      self.current_track_index = Atomic(None)
      self.current_song_info = Atomic(None)

      self.player = None
      self.pending_events = []
      self.event_handler_thread = None

      if api.is_authenticated():
         self.initialize()

   @property
   def initialized(self):
      return self.initialized_val.value

   def initialize(self):
      if self.library.songs is None:
         self.library.load_core()
      self.start_event_handler_thread()
      self.initialized_val.value = True

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
      self.current_track_index.value = None
      if self.player and self.player.is_playing():
         self.player.stop()

   def shuffle_tracks(self):
      random.shuffle(self.tracks_to_play)

   def get_position(self):
      if self.player:
         return self.player.get_position()
      return 0.0

   def get_timing_info(self):
      if self.player:
         return TrackTimingInfo(self.player.get_position(),
                                self.player.get_length() / 1000)
      return None

   def handle_track_finished(self):
      self.play_next_track()

   def handle_player_event(self, event):
      log.debug(event)
      if event.type == vlc.EventType.MediaPlayerEndReached:
         self.pending_events.append(PlayerEvent(str(event.type),
                                                self.current_track_index.value))

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
      song_id = self.tracks_to_play[self.current_track_index.value]
      song_info = self.library.songs.get(song_id)
      song_str = "Unknown - Unknown"
      if song_info:
         song_str = "{0} - {1}".format(song_info['title'], song_info['artist'])
      else:
         log.error("Could not find track info for %s", song_id)

      self.current_song_info.value = song_str

      url = self.api.get_stream_url(song_id)
      code = self._get_player_for_url(url).play()
      if code != 0:
         log.error("player.play returned error: %d", code)
         return False

      log.info("Started player: OK")
      return True

   def handle_previous_track_action(self):
      if self.player is not None and self.player.get_position() > 0.1:
         # Song is 10% done. Restart the track rather than going back.
         self.player.set_position(0.0)
         return

      current_track_index = self.current_track_index.value
      if current_track_index is None or current_track_index <= 0:
         current_track_index = 0
      else:
         current_track_index -= 1
      self.current_track_index.value = current_track_index

      self.play_current_track()

   def play_track_at_index(self, index):
      log.info(index)
      self.current_track_index.value = index
      return self.play_current_track()

   def play_next_track(self):
      current_track_index = self.current_track_index.value
      log.info("current_track_index %d", current_track_index)
      if current_track_index is None:
         current_track_index = 0
      else:
         current_track_index += 1

      if current_track_index >= len(self.tracks_to_play):
         log.info("Reached end of track list")
         return False

      return self.play_track_at_index(current_track_index)

   def set_position(self, pos):
      """Sets the position in the current track.
      pos should be from 0.0 to 1.0
      """
      if self.player is not None:
         self.player.set_position(pos)

   def skip_to_end(self):
      self.set_position(0.97)

   def toggle_play(self):
      if self.player is None:
         self.play_next_track()
      elif self.player.is_playing():
         self.player.pause()
      else:
         code = self.player.play()
         if code != 0:
            log.error("player.play returned error: %d", code)

   def do_thread_loop(self):
      if self.pending_events:
         log.debug("n pending_events: %d", len(self.pending_events))
      while self.pending_events:
         event = self.pending_events.pop(0)
         log.debug("event %r", event)
         if event.track_index != self.current_track_index.value:
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
