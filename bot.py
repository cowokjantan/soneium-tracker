import os
import requests
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.enums import ParseMode

# Token Bot Telegram (ambil dari Railway Variables)
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# API Blockscout untuk Soneium
API_URL = "https://soneium.blockscout.com/api?module=account&action=txlist&address="

# Inisialisasi bot dan dispatcher
bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# Menyimpan alamat wallet yang dipantau
tracked_addresses = set()


async def start_handler(message: Message):
    await message.answer("Halo! Kirim alamat wallet Soneium untuk dipantau.")


async def track_wallet_handler(message: Message):
    address = message.text.strip()
    if address.startswith("0x") and len(address) == 42:
        tracked_addresses.add(address)
        await message.answer(f"✅ Alamat <code>{address}</code> ditambahkan untuk dipantau!")
    else:
        await message.answer("❌ Alamat tidak valid. Harus berupa address Soneium yang benar.")


async def check_transactions():
    while True:
        for address in tracked_addresses:
            response = requests.get(f"{API_URL}{address}")
            data = response.json()
            if data.get("status") == "1":
                for tx in data["result"][:1]:  # Ambil transaksi terbaru
                    msg = (f"🔹 <b>Transaksi Baru!</b>\n"
                           f"🔹 <b>Hash:</b> {tx['hash']}\n"
                           f"🔹 <b>Dari:</b> {tx['from']}\n"
                           f"🔹 <b>Ke:</b> {tx['to']}\n"
                           f"🔹 <b>Nilai:</b> {tx['value']}")
                    for chat_id in tracked_addresses:
                        await bot.send_message(chat_id=chat_id, text=msg)
        await asyncio.sleep(30)  # Cek transaksi setiap 30 detik


async def main():
    dp.message.register(start_handler, commands={"start"})
    dp.message.register(track_wallet_handler)

    asyncio.create_task(check_transactions())  # Jalankan tracking transaksi
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
