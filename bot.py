import os
import requests
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.utils import executor

# Token Bot Telegram (ambil dari BotFather)
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# API Blockscout untuk Soneium
API_URL = "https://soneium.blockscout.com/api?module=account&action=txlist&address="

# Inisialisasi bot dan dispatcher
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# Menyimpan alamat wallet yang dipantau
tracked_addresses = set()

@dp.message_handler(commands=['start'])
async def start(message: Message):
    await message.reply("Halo! Kirim alamat wallet Soneium untuk dipantau.")

@dp.message_handler()
async def add_address(message: Message):
    address = message.text.strip()
    if address.startswith("0x") and len(address) == 42:
        tracked_addresses.add(address)
        await message.reply(f"Alamat {address} ditambahkan untuk dipantau!")
    else:
        await message.reply("Alamat tidak valid. Harus berupa address Soneium yang benar.")

async def check_transactions():
    while True:
        for address in tracked_addresses:
            response = requests.get(f"{API_URL}{address}")
            data = response.json()
            if data.get("status") == "1":
                for tx in data["result"][:1]:  # Ambil transaksi terbaru
                    msg = (f"🔹 Transaksi Baru!\n"
                           f"🔹 Hash: {tx['hash']}\n"
                           f"🔹 Dari: {tx['from']}\n"
                           f"🔹 Ke: {tx['to']}\n"
                           f"🔹 Nilai: {tx['value']}")
                    await bot.send_message(chat_id=message.chat.id, text=msg)
        await asyncio.sleep(30)  # Cek transaksi setiap 30 detik

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(check_transactions())
    executor.start_polling(dp, skip_updates=True)
