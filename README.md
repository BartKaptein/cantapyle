# Cantapyle

Cantapyle is an MPD client written in Python utilizing Qt. It's practically a clone of the [Sonata client](https://github.com/multani/sonata), only utilizing Qt instead of GTK.

It's named after the [cantabile](https://en.wikipedia.org/wiki/Cantabile), a classical music term like Sonata, only with a Pythonic twist.

It should run on any platform without modification, at least Windows, Linux and FreeBSD work.

## Keyboard shortcuts

Shortcut | Action
-------- | -----
Ctrl+Q | Quit
F1 | Switch to "Playlist" tab
F2 | Switch to "Library" tab
F3 | Switch to "Settings" tab
F5 | Previous song
F6 | Play/Pause song
F7 | Stop song
F8 | Next song
F | Search for song in playlist (esc to close)
G | Scroll to currently playing song

## Dependencies

Obviously, Qt and PyQt are required.

Also, the [python-mpd](https://github.com/Mic92/python-mpd2) library is required.

