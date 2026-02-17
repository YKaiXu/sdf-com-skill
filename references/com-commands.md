# SDF COM Commands Reference

## Overview

COM (also known as COMMODE) is a unique chat program exclusive to SDF. It is command-driven, meaning you are in "command mode" by default and must press a key (spacebar or enter) before you can talk.

## Basic Rules

- Many people idle in COM. Check idle times with `I`. If the room is quiet, say hello but give people time to respond.
- Don't ask how to 'hack'
- Don't use IRC commands (they won't work)
- Don't repeat the same question over and over

## Getting Started

1. Type `com` at the command line to start
2. You start in the 'lobby' room
3. You are in command mode (just a cursor, no prompt)

## Command Reference

### Navigation

| Command | Description |
|---------|-------------|
| `g` | Goto a room (will prompt for room name) |
| `l` | List all open rooms (lowercase L) |
| `q` | Quit COM |

### Communication

| Command | Description |
|---------|-------------|
| `space` or `enter` | Enter input mode to talk |
| `suser@host` | Send private message (requires @host) |
| `suser@host room` | Send private to user in another room |
| `e` | Emote (will prompt for action text) |

### Information

| Command | Description |
|---------|-------------|
| `w` | Who is in current room (lowercase) |
| `Wroomname` | Who is in another room (uppercase) |
| `r` | Review last 18 lines of room history |
| `R` | Extended history (will prompt for line count) |
| `proomname` | Peek into another room |
| `proomname number` | Peek with specific line count |
| `I` | Query user idle times (uppercase) |
| `h` | Command help |
| `U` | Show user membership info (uppercase) |

### Utility

| Command | Description |
|---------|-------------|
| `-` | Toggle backspace behavior (fixes ^H or ^? issues) |
| `+` | Show current UTC time |
| `L` | Post a link to COM |
| `i` | Ignore/unignore a user |

### Line Editing (in input mode)

| Key | Action |
|-----|--------|
| `^u` (Ctrl+U) | Erase entire line |
| `^w` (Ctrl+W) | Erase previous word |

## Common Rooms

- **lobby** - SDF's Welcoming Room (default)
- **spacebar** - Popular general chat room
- **anonradio** - DJ Kumata and music discussion

## Example Session

```
$ com
[you are in 'lobby' among 5]

wliao@iceland
yupeng@otaku
...

> l
    room-name   #    created      time  topic
    --------------------------------------------------------------------------------
    spacebar    16   22-Aug-16  08:49:32  there is life out there
    lobby       1    09-Sep-16  08:49:13  SDF's Welcoming Room
    anonradio   19   09-Sep-16  04:11:06  DJ Kumata!
    --------------------------------------------------------------------------------

> g
:goto> spacebar

[you are in 'spacebar' among 12]
...

> [space]
[yupeng]    hello world!

> r
[shows last 18 lines of conversation]

> q
Unlinking TTY ..
```

## Tips

- Use `r` to see what people were talking about before you joined
- Use `R` with a number for more context (e.g., 50 lines)
- Check `I` to see if people are idle before expecting a response
- The `W` command lets you check who's in other rooms without leaving
- Use `p` to peek at conversation in other rooms

## Troubleshooting

**Backspace shows ^H or ^?**
- Press `-` in command mode to toggle backspace behavior
- Or use `stty` or `bksp` command before starting COM

**How to be in COM multiple times**
- Use `screen` or run SSH twice to different SDF servers

**I accidentally ignored someone**
- Use `i` on the same user again to remove from ignore list