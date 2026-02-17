---
name: sdf-com
description: Connect to SDF.org via SSH and operate the COM chat program with real-time bidirectional messaging. Supports Feishu integration, message translation (Chinese/English), and event-driven architecture. Use when the user wants to bridge SDF COM chat with Feishu, translate messages, or automate COM interactions.
---

# SDF COM Skill

Complete solution for connecting to SDF.org's COM chat system with real-time bidirectional messaging and translation support.

## Features

- ✅ SSH connection to SDF.org
- ✅ Real-time COM chat monitoring with pyte terminal emulation
- ✅ Bidirectional message bridge (COM ↔ Feishu)
- ✅ Message translation (Chinese ↔ English)
- ✅ Event-driven architecture
- ✅ Command parsing (t:, g:, etc.)
- ✅ Filters system messages, only forwards user chat

## Architecture

```
┌─────────────┐     SSH      ┌─────────────┐     Events     ┌─────────────┐
│   SDF.org   │ ◄──────────► │  COMBridge  │ ◄────────────► │ Feishu Bot  │
│   COM Chat  │   asyncssh   │  + Parser   │   asyncio      │  + Translate│
└─────────────┘              └─────────────┘                └─────────────┘
                                    │
                                    ▼
                           ┌─────────────┐
                           │  pyte Screen│
                           │  (terminal  │
                           │  emulation) │
                           └─────────────┘
```

## Quick Start

### 1. Basic COM Client

```python
from scripts.sdf_com_client import SDFComClient
import asyncio

async def main():
    client = SDFComClient("username", "password")
    await client.connect()
    await client.start_com()
    
    # List rooms
    rooms = await client.get_room_list()
    print(rooms)
    
    # Join room and chat
    await client.goto_room("spacebar")
    await client.say("Hello SDF!")
    
    await client.disconnect()

asyncio.run(main())
```

### 2. Real-time Bridge with Events

```python
from scripts.sdf_com_bridge import COMBridge, COMMessage, MessageType
import asyncio

async def main():
    bridge = COMBridge("username", "password")
    
    # Set up event handlers
    async def on_chat(msg: COMMessage):
        print(f"[{msg.room}] {msg.username}@{msg.host}: {msg.content}")
    
    bridge.on_chat_message = on_chat
    
    # Connect and run
    await bridge.connect()
    await bridge.start_com()
    await bridge.run()  # Runs forever

asyncio.run(main())
```

### 3. Feishu Integration with Translation

```python
from scripts.feishu_com_bot import FeishuCOMBot
import asyncio

async def main():
    # Create bot
    bot = FeishuCOMBot("username", "password")
    
    # Setup Feishu message handler
    async def send_to_feishu(msg: str):
        # Send to Feishu API here
        print(f"To Feishu: {msg}")
    
    bot.send_to_feishu = send_to_feishu
    bot.setup()
    
    # Start
    await bot.start()
    
    # Handle incoming Feishu messages
    response = await bot.handle_feishu_message("t:你好世界")
    # Response: "✅ 已发送翻译: [EN] 你好世界"

asyncio.run(main())
```

## Command Line Usage

### Interactive COM Client
```bash
python scripts/sdf_com_client.py username password
```

### Real-time Bridge
```bash
python scripts/sdf_com_bridge.py username password
```

### Feishu Bot (Test Mode)
```bash
python scripts/feishu_com_bot.py username password
```

## Feishu Bot Commands

| Command | Description |
|---------|-------------|
| `t:中文内容` | Translate Chinese to English and send to COM |
| `g:roomname` | Switch to room (e.g., `g:spacebar`) |
| `w` | List users in current room |
| `l` | List all rooms |
| `r` | Review chat history |
| `h` | Show COM help |
| `I` | Query user idle times |
| `status` | Show current status |
| `help` | Show help |
| `q` | Quit |
| (other text) | Send directly to COM |

## API Reference

### COMBridge

Event-driven bridge for real-time COM interaction.

```python
bridge = COMBridge(username, password)

# Event handlers
bridge.on_chat_message = handler      # User chat messages
bridge.on_system_message = handler    # System messages
bridge.on_private_message = handler   # Private messages

# Methods
await bridge.connect()      # SSH connect
await bridge.start_com()    # Start COM
await bridge.run()          # Run event loop
await bridge.say("msg")     # Send message
await bridge.goto("room")   # Change room
await bridge.stop()         # Disconnect
```

### FeishuCOMBot

High-level bot with translation.

```python
bot = FeishuCOMBot(username, password)
bot.send_to_feishu = your_handler
bot.setup()

await bot.start()
response = await bot.handle_feishu_message("t:你好")
await bot.stop()
```

### COMMessage

Structured message from COM.

```python
@dataclass
class COMMessage:
    timestamp: str
    msg_type: MessageType  # CHAT, SYSTEM, EMOTE, PRIVATE
    username: str
    host: str
    content: str
    room: str
    raw_line: str
```

## Message Flow

### COM → Feishu
1. COMBridge reads terminal output via asyncssh
2. pyte parses terminal screen content
3. Regex extracts structured messages
4. Filters: only CHAT type, not from self
5. Translates English → Chinese
6. Sends to Feishu via callback

### Feishu → COM
1. User sends message to Feishu bot
2. Bot parses command prefix (t:, g:, etc.)
3. If t: prefix: translate Chinese → English
4. Execute command or send message
5. Return confirmation to Feishu

## Translation Integration

The bot includes a placeholder translation service. To integrate with real translation:

### Option 1: Google Translate
```python
from googletrans import Translator

class TranslationService:
    def __init__(self):
        self.translator = Translator()
    
    async def translate(self, text, src, dest):
        result = await self.translator.translate(text, src=src, dest=dest)
        return result.text
```

### Option 2: DeepL
```python
import deepl

class TranslationService:
    def __init__(self, api_key):
        self.translator = deepl.Translator(api_key)
    
    async def translate(self, text, src, dest):
        result = self.translator.translate_text(text, source_lang=src, target_lang=dest)
        return result.text
```

### Option 3: OpenAI
```python
import openai

async def translate(self, text, src, dest):
    response = await openai.ChatCompletion.acreate(
        model="gpt-3.5-turbo",
        messages=[{
            "role": "system",
            "content": f"Translate from {src} to {dest}"
        }, {
            "role": "user",
            "content": text
        }]
    )
    return response.choices[0].message.content
```

## Requirements

```bash
pip install asyncssh pyte
```

Optional for translation:
```bash
pip install googletrans deepl openai
```

## COM Commands Reference

See [references/com-commands.md](references/com-commands.md) for complete COM documentation.

### Quick Reference

| Command | Action |
|---------|--------|
| `space` | Enter input mode |
| `g` | Goto room |
| `l` | List rooms |
| `w` | Who is here |
| `Wroom` | Who is in room |
| `r` | Review history |
| `R` | Extended history |
| `proom` | Peek room |
| `suser@host` | Send private |
| `e` | Emote |
| `I` | Query idle |
| `h` | Help |
| `q` | Quit |

## Troubleshooting

### Connection Issues
- Verify username/password
- Check SSH access to sdf.org
- Ensure account is validated (some features require ARPA)

### Translation Not Working
- The default implementation is a placeholder
- Integrate with actual translation API (see examples above)

### Messages Not Forwarding
- Check that `on_chat_message` handler is set
- Verify message type is CHAT (not SYSTEM)
- Check that username filtering isn't blocking messages

## File Structure

```
sdf-com/
├── SKILL.md                      # This documentation
├── scripts/
│   ├── sdf_com_client.py         # Basic SSH client
│   ├── sdf_com_bridge.py         # Real-time event bridge
│   └── feishu_com_bot.py         # Feishu integration
└── references/
    └── com-commands.md           # COM command reference
```

## Notes

- COM is unique to SDF and only works for logged-in users
- IRC commands don't work in COM
- Some features require ARPA membership or higher
- Users may be idle - check with `I` command