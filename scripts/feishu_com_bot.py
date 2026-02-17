#!/usr/bin/env python3
"""
Feishu-COM Bot - Complete integration between Feishu and SDF COM
Handles translation and bidirectional messaging
"""

import asyncio
import json
import re
from typing import Optional
from sdf_com_bridge import COMBridge, FeishuCOMBridge, COMMessage, MessageType


class TranslationService:
    """Translation service - integrate with your preferred API"""
    
    def __init__(self):
        # Cache for common translations
        self.cache = {}
    
    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """
        Translate text between languages
        
        Args:
            text: Text to translate
            source_lang: Source language code ('zh', 'en', etc.)
            target_lang: Target language code ('zh', 'en', etc.)
        
        Returns:
            Translated text
        """
        # Check cache
        cache_key = f"{text}:{source_lang}:{target_lang}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # TODO: Integrate with actual translation API
        # Options:
        # 1. Google Cloud Translation
        # 2. DeepL API
        # 3. Azure Translator
        # 4. OpenAI API
        # 5. Local model (ollama, etc.)
        
        # Placeholder implementation
        if source_lang == 'zh' and target_lang == 'en':
            # Chinese to English
            translated = await self._translate_zh_to_en(text)
        elif source_lang == 'en' and target_lang == 'zh':
            # English to Chinese
            translated = await self._translate_en_to_zh(text)
        else:
            translated = text
        
        # Cache result
        self.cache[cache_key] = translated
        return translated
    
    async def _translate_zh_to_en(self, text: str) -> str:
        """Chinese to English - replace with actual API call"""
        # Placeholder - in production, call translation API
        return f"[EN] {text}"
    
    async def _translate_en_to_zh(self, text: str) -> str:
        """English to Chinese - replace with actual API call"""
        # Placeholder - in production, call translation API
        return f"[中文] {text}"


class FeishuCOMBot:
    """
    Complete bot integrating Feishu and SDF COM
    
    Features:
    - Receive messages from COM, translate to Chinese, send to Feishu
    - Receive commands from Feishu, execute on COM
    - t: prefix translates Chinese to English before sending
    - g: prefix switches rooms
    """
    
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.bridge = COMBridge(username, password)
        self.feishu_bridge = FeishuCOMBridge(self.bridge)
        self.translator = TranslationService()
        
        # Message callbacks
        self.send_to_feishu: Optional[callable] = None
        
    def setup(self):
        """Setup the bot"""
        # Setup COM -> Feishu handler
        self.feishu_bridge.on_feishu_message = self._on_com_message
        self.feishu_bridge.setup_handlers()
    
    async def _on_com_message(self, msg: dict):
        """Handle messages from COM to send to Feishu"""
        if not self.send_to_feishu:
            return
        
        # Translate if needed
        if msg.get('needs_translation') and msg.get('target_lang') == 'zh':
            translated = await self.translator.translate(
                msg['content'],
                'en',
                'zh'
            )
            msg['original_content'] = msg['content']
            msg['content'] = translated
        
        # Format for Feishu
        formatted = self._format_for_feishu(msg)
        
        # Send to Feishu
        await self.send_to_feishu(formatted)
    
    def _format_for_feishu(self, msg: dict) -> str:
        """Format COM message for Feishu display"""
        room = msg.get('room', 'unknown')
        sender = msg.get('from', 'unknown')
        content = msg.get('content', '')
        
        if msg.get('is_private'):
            return f"💌 [私聊] {sender}: {content}"
        
        return f"💬 [{room}] {sender}: {content}"
    
    async def handle_feishu_message(self, text: str) -> str:
        """
        Handle incoming message from Feishu
        
        Command prefixes:
        - t:中文  -> Translate to English and send to COM
        - g:room  -> Goto room
        - w,l,r,h,I -> COM commands
        - q       -> Quit
        - (other) -> Send as raw message
        
        Returns:
            Response message for Feishu
        """
        text = text.strip()
        
        if not text:
            return "请输入命令或消息"
        
        # t: Translate and send
        if text.startswith('t:'):
            chinese = text[2:].strip()
            if not chinese:
                return "请在 t: 后输入要翻译的中文"
            
            # Translate to English
            english = await self.translator.translate(chinese, 'zh', 'en')
            
            # Send to COM
            await self.bridge.say(english)
            
            return f"✅ 已发送翻译: {english}"
        
        # g: Goto room
        elif text.startswith('g:'):
            room = text[2:].strip()
            if not room:
                return "请在 g: 后输入房间名"
            
            await self.bridge.goto(room)
            return f"✅ 已切换到房间: {room}"
        
        # Direct COM commands
        elif text in ['w', 'l', 'r', 'h', 'I', 'q']:
            if text == 'q':
                await self.bridge.stop()
                return "👋 已断开连接"
            
            await self.bridge.send_raw(text)
            return f"✅ 已执行命令: {text}"
        
        # Help command
        elif text in ['help', '帮助']:
            return self._get_help_text()
        
        # Status
        elif text in ['status', '状态']:
            return f"📍 当前房间: {self.bridge.current_room}\n👤 用户名: {self.username}"
        
        # Raw message
        else:
            await self.bridge.say(text)
            return f"✅ 已发送: {text}"
    
    def _get_help_text(self) -> str:
        """Get help text"""
        return """🤖 Feishu-COM Bot 命令帮助

📤 发送消息:
  t:中文内容  - 翻译成英文后发送到 COM
  直接输入    - 原文发送到 COM

🏠 房间操作:
  g:房间名    - 切换到指定房间
  w           - 查看当前房间用户
  l           - 列出所有房间

📜 其他命令:
  r           - 查看最近聊天记录
  h           - 显示 COM 帮助
  I           - 查看用户空闲时间
  status      - 查看当前状态
  help        - 显示此帮助

💡 COM 房间会自动转发到飞书（已翻译为中文）
"""
    
    async def start(self):
        """Start the bot"""
        print(f"🔌 连接到 SDF ({self.username})...")
        await self.bridge.connect()
        print("✅ 已连接!")
        
        print("🚀 启动 COM...")
        await self.bridge.start_com()
        print("✅ COM 已启动!")
        
        # Start bridge
        self._bridge_task = asyncio.create_task(self.bridge.run())
        
        print("🤖 Bot 已就绪!")
        return self
    
    async def stop(self):
        """Stop the bot"""
        await self.bridge.stop()
        self._bridge_task.cancel()
        try:
            await self._bridge_task
        except asyncio.CancelledError:
            pass
        print("👋 Bot 已停止")


# Example usage for testing
async def test_bot():
    """Test the bot in standalone mode"""
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: feishu_com_bot.py <username> <password>")
        sys.exit(1)
    
    username = sys.argv[1]
    password = sys.argv[2]
    
    # Create bot
    bot = FeishuCOMBot(username, password)
    
    # Setup message handler (prints to console for testing)
    async def send_to_feishu(msg: str):
        print(f"\n📨 [发送到飞书] {msg}\n")
    
    bot.send_to_feishu = send_to_feishu
    bot.setup()
    
    # Start
    await bot.start()
    
    # Interactive loop
    print("\n输入命令 (help 查看帮助, q 退出):")
    while True:
        try:
            user_input = await asyncio.get_event_loop().run_in_executor(
                None, input, "> "
            )
            
            response = await bot.handle_feishu_message(user_input)
            print(response)
            
            if user_input.strip() == 'q':
                break
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"错误: {e}")
    
    await bot.stop()


if __name__ == '__main__':
    asyncio.run(test_bot())
