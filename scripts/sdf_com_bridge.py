#!/usr/bin/env python3
"""
SDF COM Bridge - Real-time bidirectional message bridge between SDF COM and Feishu
Uses asyncssh for SSH and pyte for terminal emulation
"""

import asyncio
import asyncssh
import pyte
import re
import json
import time
from datetime import datetime
from typing import Callable, Optional, List, Dict
from dataclasses import dataclass, asdict
from enum import Enum


class MessageType(Enum):
    CHAT = "chat"           # Regular user message
    SYSTEM = "system"       # System messages (join/leave/etc)
    EMOTE = "emote"         # Emote actions
    PRIVATE = "private"     # Private messages
    UNKNOWN = "unknown"


@dataclass
class COMMessage:
    """Represents a message from COM"""
    timestamp: str
    msg_type: MessageType
    username: str
    host: str
    content: str
    room: str = ""
    raw_line: str = ""
    
    def to_dict(self):
        return {
            "timestamp": self.timestamp,
            "type": self.msg_type.value,
            "username": self.username,
            "host": self.host,
            "content": self.content,
            "room": self.room,
            "raw": self.raw_line
        }


class COMScreenParser:
    """Parse COM terminal output using pyte"""
    
    def __init__(self, columns: int = 80, lines: int = 24):
        self.screen = pyte.Screen(columns, lines)
        self.stream = pyte.ByteStream(self.screen)
        self.current_room = "lobby"
        
        # Regex patterns for parsing COM messages
        self.patterns = {
            # [username@host] message
            'chat': re.compile(r'\[(\w+)@(\w+)\]\s+(.+)'),
            # username@host DUMPs ... (emote)
            'emote': re.compile(r'(\w+)@(\w+)\s+(DUMPs|appears|disappears|\.+)\s+(.+)'),
            # System messages
            'system': re.compile(r'^(Unlinking|Linking|COM|Lobby|\*\*\*)'),
            # Private message indicator
            'private': re.compile(r'From\s+(\w+)@(\w+):\s*(.+)'),
            # Room header
            'room_header': re.compile(r"\[you are in '(\w+)'"),
        }
    
    def feed(self, data: bytes):
        """Feed raw terminal data to the screen"""
        self.stream.feed(data)
    
    def get_display(self) -> str:
        """Get current screen content as text"""
        lines = []
        for i in range(self.screen.lines):
            line = self.screen.display[i].rstrip()
            if line:
                lines.append(line)
        return '\n'.join(lines)
    
    def parse_messages(self, text: str) -> List[COMMessage]:
        """Parse text into structured messages"""
        messages = []
        timestamp = datetime.now().isoformat()
        
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # Check for room header
            room_match = self.patterns['room_header'].search(line)
            if room_match:
                self.current_room = room_match.group(1)
                continue
            
            # Try to match as chat message
            chat_match = self.patterns['chat'].match(line)
            if chat_match:
                msg = COMMessage(
                    timestamp=timestamp,
                    msg_type=MessageType.CHAT,
                    username=chat_match.group(1),
                    host=chat_match.group(2),
                    content=chat_match.group(3).strip(),
                    room=self.current_room,
                    raw_line=line
                )
                messages.append(msg)
                continue
            
            # Try emote
            emote_match = self.patterns['emote'].match(line)
            if emote_match:
                msg = COMMessage(
                    timestamp=timestamp,
                    msg_type=MessageType.EMOTE,
                    username=emote_match.group(1),
                    host=emote_match.group(2),
                    content=f"{emote_match.group(3)} {emote_match.group(4)}",
                    room=self.current_room,
                    raw_line=line
                )
                messages.append(msg)
                continue
            
            # Try private
            private_match = self.patterns['private'].match(line)
            if private_match:
                msg = COMMessage(
                    timestamp=timestamp,
                    msg_type=MessageType.PRIVATE,
                    username=private_match.group(1),
                    host=private_match.group(2),
                    content=private_match.group(3).strip(),
                    room=self.current_room,
                    raw_line=line
                )
                messages.append(msg)
                continue
            
            # System message
            if self.patterns['system'].match(line):
                msg = COMMessage(
                    timestamp=timestamp,
                    msg_type=MessageType.SYSTEM,
                    username="",
                    host="",
                    content=line,
                    room=self.current_room,
                    raw_line=line
                )
                messages.append(msg)
                continue
        
        return messages


class COMBridge:
    """Bidirectional bridge between SDF COM and external messaging"""
    
    def __init__(self, username: str, password: str, host: str = "sdf.org"):
        self.username = username
        self.password = password
        self.host = host
        self.conn = None
        self.process = None
        self.parser = COMScreenParser()
        
        # Event handlers
        self.on_chat_message: Optional[Callable[[COMMessage], None]] = None
        self.on_system_message: Optional[Callable[[COMMessage], None]] = None
        self.on_private_message: Optional[Callable[[COMMessage], None]] = None
        
        # State
        self.running = False
        self.current_room = "lobby"
        self.message_queue = asyncio.Queue()
        self.command_queue = asyncio.Queue()
        
    async def connect(self):
        """Establish SSH connection"""
        self.conn = await asyncssh.connect(
            self.host,
            username=self.username,
            password=self.password,
            known_hosts=None
        )
        return self.conn
    
    async def start_com(self):
        """Start COM program"""
        if not self.conn:
            raise RuntimeError("Not connected")
        
        self.process = await self.conn.create_process(
            'com',
            term_type='xterm-256color',
            term_size=(80, 24)
        )
        return self.process
    
    async def run(self):
        """Main run loop - starts all tasks"""
        self.running = True
        
        # Start tasks
        tasks = [
            asyncio.create_task(self._read_loop()),
            asyncio.create_task(self._command_loop()),
            asyncio.create_task(self._process_messages()),
        ]
        
        await asyncio.gather(*tasks)
    
    async def _read_loop(self):
        """Continuously read from COM and parse output"""
        buffer = b""
        
        while self.running:
            try:
                # Read available data
                chunk = await asyncio.wait_for(
                    self.process.stdout.read(4096),
                    timeout=0.1
                )
                
                if chunk:
                    buffer += chunk
                    
                    # Feed to terminal emulator
                    self.parser.feed(chunk)
                    
                    # Try to parse complete messages
                    display = self.parser.get_display()
                    messages = self.parser.parse_messages(display)
                    
                    # Queue messages for processing
                    for msg in messages:
                        await self.message_queue.put(msg)
                
            except asyncio.TimeoutError:
                # Process any remaining buffer content
                if buffer:
                    display = self.parser.get_display()
                    messages = self.parser.parse_messages(display)
                    for msg in messages:
                        await self.message_queue.put(msg)
                    buffer = b""
                
            except Exception as e:
                print(f"Read loop error: {e}")
                await asyncio.sleep(1)
    
    async def _command_loop(self):
        """Process commands from queue"""
        while self.running:
            try:
                cmd = await asyncio.wait_for(
                    self.command_queue.get(),
                    timeout=0.5
                )
                
                if cmd['type'] == 'say':
                    await self._send_message(cmd['content'])
                elif cmd['type'] == 'goto':
                    await self._goto_room(cmd['room'])
                elif cmd['type'] == 'raw':
                    await self._send_raw(cmd['command'])
                    
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"Command loop error: {e}")
    
    async def _process_messages(self):
        """Process incoming messages and trigger handlers"""
        seen_messages = set()  # Deduplication
        
        while self.running:
            try:
                msg = await asyncio.wait_for(
                    self.message_queue.get(),
                    timeout=0.5
                )
                
                # Deduplicate based on content
                msg_key = f"{msg.username}:{msg.host}:{msg.content}"
                if msg_key in seen_messages:
                    continue
                seen_messages.add(msg_key)
                
                # Keep set size manageable
                if len(seen_messages) > 1000:
                    seen_messages.clear()
                
                # Trigger appropriate handler
                if msg.msg_type == MessageType.CHAT and self.on_chat_message:
                    await self._call_handler(self.on_chat_message, msg)
                elif msg.msg_type == MessageType.PRIVATE and self.on_private_message:
                    await self._call_handler(self.on_private_message, msg)
                elif msg.msg_type == MessageType.SYSTEM and self.on_system_message:
                    await self._call_handler(self.on_system_message, msg)
                    
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"Message processing error: {e}")
    
    async def _call_handler(self, handler, msg):
        """Safely call a handler"""
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(msg)
            else:
                handler(msg)
        except Exception as e:
            print(f"Handler error: {e}")
    
    async def _send_message(self, message: str):
        """Send a chat message"""
        # Enter input mode (space)
        self.process.stdin.write(b' ')
        await self.process.stdin.drain()
        await asyncio.sleep(0.2)
        
        # Send message
        self.process.stdin.write(message.encode() + b'\n')
        await self.process.stdin.drain()
        await asyncio.sleep(0.3)
    
    async def _goto_room(self, room: str):
        """Switch to a room"""
        self.process.stdin.write(b'g\n')
        await self.process.stdin.drain()
        await asyncio.sleep(0.3)
        
        self.process.stdin.write(room.encode() + b'\n')
        await self.process.stdin.drain()
        await asyncio.sleep(0.5)
        
        self.current_room = room
    
    async def _send_raw(self, command: str):
        """Send raw command"""
        self.process.stdin.write(command.encode() + b'\n')
        await self.process.stdin.drain()
        await asyncio.sleep(0.3)
    
    # Public API for sending commands
    
    async def say(self, message: str):
        """Queue a message to send"""
        await self.command_queue.put({
            'type': 'say',
            'content': message
        })
    
    async def goto(self, room: str):
        """Queue a room change"""
        await self.command_queue.put({
            'type': 'goto',
            'room': room
        })
    
    async def send_raw(self, command: str):
        """Queue a raw command"""
        await self.command_queue.put({
            'type': 'raw',
            'command': command
        })
    
    async def stop(self):
        """Stop the bridge"""
        self.running = False
        if self.process:
            await self.send_raw('q')
            self.process.close()
        if self.conn:
            self.conn.close()


class FeishuCOMBridge:
    """Bridge specifically for Feishu integration with translation"""
    
    def __init__(self, com_bridge: COMBridge):
        self.com = com_bridge
        self.on_feishu_message = None  # Callback for messages to Feishu
        
    def setup_handlers(self):
        """Setup message handlers"""
        self.com.on_chat_message = self._handle_com_chat
        self.com.on_private_message = self._handle_com_private
        
    async def _handle_com_chat(self, msg: COMMessage):
        """Handle chat messages from COM - translate and send to Feishu"""
        # Only forward actual user chat messages
        if msg.msg_type != MessageType.CHAT:
            return
        
        # Skip our own messages
        if msg.username == self.com.username:
            return
        
        # Format message for Feishu
        feishu_msg = {
            'source': 'com',
            'room': msg.room,
            'from': f"{msg.username}@{msg.host}",
            'content': msg.content,
            'needs_translation': True,  # Flag for translation
            'target_lang': 'zh'  # Translate to Chinese
        }
        
        if self.on_feishu_message:
            await self._call_handler(self.on_feishu_message, feishu_msg)
    
    async def _handle_com_private(self, msg: COMMessage):
        """Handle private messages"""
        feishu_msg = {
            'source': 'com',
            'room': 'private',
            'from': f"{msg.username}@{msg.host}",
            'content': msg.content,
            'needs_translation': True,
            'target_lang': 'zh',
            'is_private': True
        }
        
        if self.on_feishu_message:
            await self._call_handler(self.on_feishu_message, feishu_msg)
    
    async def handle_feishu_input(self, text: str) -> dict:
        """Process input from Feishu
        
        Commands:
        - t:中文内容  -> Translate to English and send to COM
        - g:roomname  -> Goto room
        - w           -> Who is in room
        - l           -> List rooms
        - r           -> Review history
        - h           -> Help
        - q           -> Quit
        - raw text    -> Send raw COM command
        """
        text = text.strip()
        
        if text.startswith('t:'):
            # Translate and send
            chinese = text[2:].strip()
            return {
                'action': 'translate_and_send',
                'source': chinese,
                'target_lang': 'en'
            }
        
        elif text.startswith('g:'):
            # Goto room
            room = text[2:].strip()
            await self.com.goto(room)
            return {'action': 'goto', 'room': room}
        
        elif text in ['w', 'l', 'r', 'h', 'I']:
            # Direct COM commands
            await self.com.send_raw(text)
            return {'action': 'command', 'command': text}
        
        elif text == 'q':
            await self.com.stop()
            return {'action': 'quit'}
        
        else:
            # Send as raw message
            await self.com.say(text)
            return {'action': 'say', 'content': text}
    
    async def _call_handler(self, handler, data):
        """Safely call handler"""
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(data)
            else:
                handler(data)
        except Exception as e:
            print(f"Handler error: {e}")


# Simple translation stub - replace with actual translation API
def translate_text(text: str, target_lang: str) -> str:
    """Translate text - placeholder for actual translation service
    
    In production, integrate with:
    - Google Translate API
    - DeepL API
    - Azure Translator
    - Or local model
    """
    # Placeholder - just returns the text with a note
    return f"[TRANSLATE to {target_lang}]: {text}"


async def main():
    """Example usage"""
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: sdf_com_bridge.py <username> <password>")
        sys.exit(1)
    
    username = sys.argv[1]
    password = sys.argv[2]
    
    # Create bridge
    bridge = COMBridge(username, password)
    feishu_bridge = FeishuCOMBridge(bridge)
    feishu_bridge.setup_handlers()
    
    # Setup message handler for Feishu
    async def on_message_to_feishu(msg):
        print(f"\n[TO FEISHU] {json.dumps(msg, ensure_ascii=False, indent=2)}")
    
    feishu_bridge.on_feishu_message = on_message_to_feishu
    
    # Connect
    print(f"Connecting to SDF as {username}...")
    await bridge.connect()
    print("Connected!")
    
    print("Starting COM...")
    await bridge.start_com()
    print("COM started!")
    
    # Start bridge in background
    bridge_task = asyncio.create_task(bridge.run())
    
    # Interactive command loop
    print("\n=== Bridge Ready ===")
    print("Commands:")
    print("  t:中文内容 - Translate and send to COM")
    print("  g:roomname - Goto room")
    print("  w,l,r,h,I - COM commands")
    print("  q - Quit")
    print("  (other) - Send as message\n")
    
    while True:
        try:
            user_input = await asyncio.get_event_loop().run_in_executor(
                None, input, "> "
            )
            
            result = await feishu_bridge.handle_feishu_input(user_input)
            print(f"[Action] {result}")
            
            if result.get('action') == 'quit':
                break
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
    
    print("\nShutting down...")
    await bridge.stop()
    bridge_task.cancel()
    try:
        await bridge_task
    except asyncio.CancelledError:
        pass
    print("Done!")


if __name__ == '__main__':
    asyncio.run(main())