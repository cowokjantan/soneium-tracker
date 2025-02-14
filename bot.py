import asyncio
import logging
import os
import json
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.enums import ParseMode
import aiohttp

# Logging
logging.basicConfig(level=logging.INFO)

# Load token
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ BOT_TOKEN tidak ditemukan! Pastikan sudah diatur di Railway Variables.")

bot = Bot(token=TOKEN, default=types.DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# File untuk menyimpan data pengguna
DATA_FILE = "users.json"

def load_users():
    """Memuat data pengguna dari file JSON."""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as file:
            return json.load(file)
    return {}

def save_users(users):
    """Menyimpan data pengguna ke file JSON."""
    with open(DATA_FILE, "w") as file:
        json.dump(users, file, indent=4)

users = load_users()

@dp.message(Command("start"))
async def start(message: Message):
    await message.answer("👋 Selamat datang di Soneium Tracker!\nGunakan /add <nama> <alamat> untuk mulai melacak.")

@dp.message(Command("add"))
async def add_address(message: Message):
    args = message.text.split()
    if len(args) < 3:
        await message.answer("❌ Format salah! Gunakan: /add <nama> <alamat>")
        return
    
    name, address = args[1], args[2]
    user_id = str(message.chat.id)
    
    if user_id not in users:
        users[user_id] = {}
    users[user_id][name] = address
    save_users(users)
    
    await message.answer(f"✅ Alamat <b>{name}</b> ({address}) ditambahkan!")

@dp.message(Command("remove"))
async def remove_address(message: Message):
    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ Format salah! Gunakan: /remove <nama>")
        return
    
    name = args[1]
    user_id = str(message.chat.id)
    
    if user_id in users and name in users[user_id]:
        del users[user_id][name]
        save_users(users)
        await message.answer(f"✅ Alamat <b>{name}</b> telah dihapus!")
    else:
        await message.answer("⚠️ Nama tidak ditemukan.")

async def fetch_transactions():
    """Mengambil transaksi terbaru untuk semua pengguna."""
    url = "https://soneium.blockscout.com/api/v2/transactions"  # Gantilah dengan endpoint yang benar
    seen_txs = set()
    
    while True:
        async with aiohttp.ClientSession() as session:
            for user_id, addresses in users.items():
                for name, address in addresses.items():
                    params = {"address": address, "limit": 5}  # Ambil 5 transaksi terbaru
                    async with session.get(url, params=params) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            for tx in data.get("items", []):
                                tx_hash = tx["hash"]
                                if tx_hash not in seen_txs:
                                    seen_txs.add(tx_hash)
                                    tx_link = f"<a href='https://soneium.blockscout.com/tx/{tx_hash}'>Lihat Tx</a>"
                                    await bot.send_message(user_id, f"🔄 Transaksi baru untuk <b>{name}</b>: {tx_link}")
        
        await asyncio.sleep(30)  # Cek setiap 30 detik

async def main():
    """Menjalankan bot dan proses tracking."""
    asyncio.create_task(fetch_transactions())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
