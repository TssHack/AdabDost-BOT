import asyncio
import sqlite3
import logging
import re
import json
from typing import Dict, List

import aiohttp
from telethon import TelegramClient, events, Button
from telethon.errors import MessageNotModifiedError

class Config:
    API_ID = #
    API_HASH = '#'
    BOT_TOKEN = '#'
    GEMINI_API_KEY = '#'
    DEV_USERNAME = 'abj0o'
    DB_NAME = 'adab_flawless.db'
    
    GEMINI_BASE_URL = "https://gemini-api-six-zeta.vercel.app/?model=gemini-2.5-flash"
    MAX_TOKENS = 1500
    DEFAULT_TEMPERATURE = 0.8

class HtmlFormatter:
    
    @staticmethod
    def escape(text: str) -> str:
        return (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;'))
    
    @staticmethod
    def bold(text: str) -> str:
        return f"<b>{text}</b>"
    
    @staticmethod
    def italic(text: str) -> str:
        return f"<i>{text}</i>"

    @staticmethod
    def section_header(title: str) -> str:
        return f"\n━━━━━━━━━━━━━━━━\n{HtmlFormatter.bold(title)}\n"

    @staticmethod
    def format_final(text: str, mode: str, style: str) -> str:
        clean_text = text.replace('*', '').replace('#', '').strip()
        lines = clean_text.split('\n')
        
        header = f"{HtmlFormatter.bold(mode)} | {HtmlFormatter.italic(style)}"
        body_lines = [HtmlFormatter.bold("━━━━━━━━━━━━━━━━")]
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if len(line) < 120 and ' ' in line and line.count(' ') < 15:
                body_lines.append(HtmlFormatter.bold(line))
            else:
                body_lines.append(line)
        
        footer = f"\n\n{HtmlFormatter.italic('Created by Adab Doost AI')}"
        
        return f"{header}\n" + "\n".join(body_lines) + footer

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(Config.DB_NAME, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._init_db()

    def _init_db(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                settings TEXT,
                last_prompt TEXT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()

    def get_user(self, user_id: int) -> Dict:
        self.cursor.execute("SELECT settings, last_prompt FROM users WHERE user_id = ?", (user_id,))
        row = self.cursor.fetchone()
        if row:
            return {
                'settings': json.loads(row[0]),
                'last_prompt': row[1] if row[1] else None
            }
        return {
            'settings': {'mode': 'Poem', 'style': 'Ghazal', 'mood': 'General', 'creativity': '0.7'},
            'last_prompt': None
        }

    def save_settings(self, user_id: int, settings: Dict):
        self.cursor.execute('''
            INSERT INTO users (user_id, settings)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET settings = excluded.settings
        ''', (user_id, json.dumps(settings)))
        self.conn.commit()

    def save_last_prompt(self, user_id: int, prompt: str):
        self.cursor.execute('''
            INSERT INTO users (user_id, last_prompt)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET last_prompt = excluded.last_prompt
        ''', (user_id, prompt))
        self.conn.commit()

    def get_all_users(self) -> List[int]:
        self.cursor.execute("SELECT user_id FROM users")
        return [r[0] for r in self.cursor.fetchall()]

db = Database()

class AIService:
    @staticmethod
    async def generate(prompt_text: str, settings: Dict) -> str:
        mode = settings.get('mode', 'Poem')
        style = settings.get('style', 'Ghazal')
        mood = settings.get('mood', 'General')
        temp = float(settings.get('creativity', '0.7'))
        
        system_instruction = f"""
You are Adab Doost, AI Poet. Developed by Ehsan Fazli.
Mode: {mode}
Style: {style}
Mood: {mood}

Rules:
1. Persian only.
2. No markdown symbols.
3. For poems, separate verses clearly.
        """

        payload = {
            "contents": [
                {
                    "parts": [{"text": f"{system_instruction}\n\nUser: {prompt_text}"}]
                }
            ],
            "generationConfig": {
                "temperature": temp,
                "maxOutputTokens": Config.MAX_TOKENS,
                "topP": 0.9
            }
        }

        url = f"{Config.GEMINI_BASE_URL}&key={Config.GEMINI_API_KEY}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        if 'candidates' in data:
                            return data['candidates'][0]['content']['parts'][0]['text']
                        return "هوش مصنوعی پاسخی نداد."
                    else:
                        err = await response.text()
                        print(f"API Error: {err}")
                        return f"خطای سرور: {response.status}"
        except Exception as e:
            print(f"Connection Error: {e}")
            return "ارتباط قطع شد."

class UI:
    @staticmethod
    def get_main():
        return [
            [Button.inline("🎨 آتلیه شعر", b"mode_create")],
            [Button.inline("🔬 تریبون تحلیل", b"mode_analyze")],
            [Button.inline("⚙️ تنظیمات پیشرفته", b"menu_settings")],
            [Button.url("👤 سازنده", f"t.me/{Config.DEV_USERNAME}")]
        ]

    @staticmethod
    def get_settings():
        return [
            [Button.inline("🎨 انتخاب سبک", b"sub_style")],
            [Button.inline("😊 حال و هوا", b"sub_mood")],
            [Button.inline("🎲 میزان تخیل", b"sub_creativity")],
            [Button.inline("🔙 بازگشت", b"menu_main")]
        ]

    @staticmethod
    def get_styles():
        return [
            [Button.inline("غزل", b"set_style_Ghazal"), Button.inline("شعر نو", b"set_style_Modern")],
            [Button.inline("مثنوی", b"set_style_Mathnawi"), Button.inline("ترانه", b"set_style_Lyrics")],
            [Button.inline("🔙", b"menu_settings")]
        ]

    @staticmethod
    def get_moods():
        return [
            [Button.inline("عاشقانه ❤️", b"set_mood_Romantic"), Button.inline("غمگین 🌧️", b"set_mood_Sad")],
            [Button.inline("شاد ☀️", b"set_mood_Happy"), Button.inline("حماسی ⚔️", b"set_mood_Epic")],
            [Button.inline("🔙", b"menu_settings")]
        ]

    @staticmethod
    def get_creativity():
        return [
            [Button.inline("کم (منطقی)", b"set_creat_0.4"), Button.inline("متعادل (0.7)", b"set_creat_0.7")],
            [Button.inline("زیاد (خلاق)", b"set_creat_0.9"), Button.inline("دیوانه‌وار (1.2)", b"set_creat_1.2")],
            [Button.inline("🔙", b"menu_settings")]
        ]

class AdabDoostBot:
    def __init__(self):
        self.client = TelegramClient('flawless_session', Config.API_ID, Config.API_HASH)
        self.logging_setup()

    def logging_setup(self):
        logging.basicConfig(
            format='%(asctime)s - %(levelname)s - %(message)s',
            level=logging.INFO,
            datefmt='%H:%M:%S'
        )

    async def start(self):
        await self.client.start(bot_token=Config.BOT_TOKEN)
        self.client.add_event_handler(self.on_msg, events.NewMessage(incoming=True))
        self.client.add_event_handler(self.on_query, events.CallbackQuery())
        print("✅ Bot is running.")
        await self.client.run_until_disconnected()

    async def on_msg(self, event):
        user_id = event.chat_id
        text = event.message.message
        sender = event.message.sender
        username = sender.username if sender else "Unknown"

        if not text.strip():
            return

        if text.startswith('/broadcast') and username == Config.DEV_USERNAME:
            msg = text.replace('/broadcast', '').strip()
            await self.broadcast(msg)
            return

        if text == '/start':
            await event.respond(
                HtmlFormatter.bold("به ادب‌دوست نهایی خوش آمدید") + "\nتمام قابلیت‌ها فعال است.",
                buttons=UI.get_main(),
                parse_mode='html'
            )
            return

        data = db.get_user(user_id)
        settings = data['settings']
        db.save_last_prompt(user_id, text)

        status = await event.respond("⏳")

        response = await AIService.generate(text, settings)
        db.save_settings(user_id, settings)

        formatted_res = HtmlFormatter.format_final(response, settings['mode'], settings['style'])
        
        await status.delete()
        await event.respond(
            formatted_res,
            parse_mode='html',
            buttons=[[Button.inline("🔄 بازسازی (Remix)", b"remix_action"), Button.inline("🏠 منو", b"menu_main")]],
            link_preview=False
        )

    async def on_query(self, event):
        user_id = event.chat_id
        data = event.data.decode('utf-8')
        await event.answer()

        try:
            data_obj = db.get_user(user_id)
            settings = data_obj['settings']
            last_prompt = data_obj['last_prompt']

            if data == 'menu_main':
                await event.edit("منوی اصلی", buttons=UI.get_main(), parse_mode='html')

            elif data == 'menu_settings':
                await event.edit("تنظیمات:", buttons=UI.get_settings())

            elif data == 'sub_style':
                await event.edit("انتخاب سبک:", buttons=UI.get_styles())
            elif data == 'sub_mood':
                await event.edit("انتخاب حال و هوا:", buttons=UI.get_moods())
            elif data == 'sub_creativity':
                await event.edit("میزان تخیل:", buttons=UI.get_creativity())

            elif data.startswith('set_style_'):
                val = data.split('_')[-1]
                settings['style'] = val
                db.save_settings(user_id, settings)
                await event.edit(f"سبک به <b>{val}</b> تغییر یافت.", buttons=UI.get_settings(), parse_mode='html')

            elif data.startswith('set_mood_'):
                val = data.split('_')[-1]
                settings['mood'] = val
                db.save_settings(user_id, settings)
                await event.edit(f"حال و هوا: <b>{val}</b>", buttons=UI.get_settings(), parse_mode='html')

            elif data.startswith('set_creat_'):
                val = data.split('_')[-1]
                settings['creativity'] = val
                db.save_settings(user_id, settings)
                await event.edit(f"سطح تخیل: <b>{val}</b>", buttons=UI.get_settings(), parse_mode='html')

            elif data == 'mode_create':
                settings['mode'] = 'Poem'
                db.save_settings(user_id, settings)
                await event.edit("حالت <b>آتلیه شعر</b> فعال شد.", buttons=[[Button.inline("🔙", b"menu_main")]], parse_mode='html')

            elif data == 'mode_analyze':
                settings['mode'] = 'Analysis'
                db.save_settings(user_id, settings)
                await event.edit("حالت <b>تریبون تحلیل</b> فعال شد.", buttons=[[Button.inline("🔙", b"menu_main")]], parse_mode='html')

            elif data == 'remix_action':
                if last_prompt:
                    await event.edit("🔄 در حال بازسازی خلاقانه...")
                    remix_prompt = f"{last_prompt}\n(لطفاً این موضوع را با لحنی کاملاً متفاوت و جدید بازنویسی کن)"
                    response = await AIService.generate(remix_prompt, settings)
                    formatted = HtmlFormatter.format_final(response, settings['mode'], settings['style'])
                    try:
                        await event.edit(
                            formatted,
                            parse_mode='html',
                            buttons=[[Button.inline("🔄", b"remix_action"), Button.inline("🏠", b"menu_main")]]
                        )
                    except MessageNotModifiedError:
                        pass
                else:
                    await event.answer("موضوعی برای بازسازی یافت نشد.", alert=True)

        except Exception as e:
            print(f"Callback Error: {e}")

    async def broadcast(self, message):
        print("Broadcasting...")
        users = db.get_all_users()
        count = 0
        for user_id in users:
            try:
                await self.client.send_message(user_id, message)
                count += 1
                await asyncio.sleep(0.1)
            except Exception:
                continue
        print(f"Broadcast sent to {count} users.")

if __name__ == '__main__':
    bot = AdabDoostBot()
    try:
        asyncio.run(bot.start())
    except KeyboardInterrupt:
        print("Bot stopped.")
