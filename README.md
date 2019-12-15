# GPlayMusicPlayer
An UNOFFICIAL player for Google Play Music, written from the ground up using the [gmusicapi](https://github.com/simon-weber/gmusicapi) library.

## Why?
Yes, why would someone write such a thing?

Well, first of all, I am not satisfied with simply running GPM in another tab in my browser, since this does not offer global keyboard shortcuts. Generally the answer to this is to run one of the wrapper apps available, which run the GPM webpage but provide extras like hotkeys, color schemes, etc.

However, I tend to listen to music on a laptop which has a rather small amount of memory (by modern standards). Due to an entire browser instance being required to run the music player, this can really eat up a lot of memory, which sometimes leads to dire effects.

I didn't find another alternative which I found acceptable, so here we are...

## Supported Platforms
- Only been tested on Linux (Ubuntu and Fedora).
- Might work on MacOS (untested)
- Might work on Windows (untested), but would require running from Linux subsystem, or manually re-writing bash scripts for `cmd`

## Features
 - Runs from a custom Qt GUI OR purely from the terminal (much less feature rich though)
 - Play user playlists or your entire library on shuffle
 - GUI has light and dark themes
 - Consumes _less_ memory than running GPM in an entirely new browser instance

### Current Limitations
 - Won't update to changes to the library automatically (requires restart)
 - No search functionality
 - Only plays on shuffle
 
## Installation
1. Install VLC on your machine.
2. Clone this repository and set up.
```
$ git clone https://github.com/tsiemens/GPlayMusicPlayer.git
$ cd ./GPlayMusicPlayer
$ ./setup.sh
```
3. Run `./gplaymusicplayer`. You may want to add a symlink to this script somewhere in your PATH.

## Development
Just follow the installation instructions.

If you need/want to run manual `pip` commands, enter the venv environment:
```
source venv/bin/activate
```

Run `pylint src` to verify compliance with the project standards.
