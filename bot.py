import asyncio
import logging
import os
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from config import TOKEN, BLOCKSCOUT_API

# Logging
logging.basicConfig(level=logging.INFO)

# Inisialisasi bot
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

# Simpan daftar address dan tx hash yang sudah dikirim
tracked_addresses = {}
sent_tx_hashes = set()

# ===================== COMMAND HANDLER =====================

@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer("🚀 Selamat datang di Soneium Tracker!\nGunakan /add <address> untuk mulai melacak transaksi.")

@dp.message(Command("add"))
async def add_address(message: Message):
    args = message.text.split()
    if len(args) < 2:
        await message.answer("⚠️ Format salah! Gunakan: /add <address>")
        return

    address = args[1].lower()
    user_id = message.chat.id

    if user_id not in tracked_addresses:
        tracked_addresses[user_id] = []

    if address in tracked_addresses[user_id]:
        await message.answer("✅ Address sudah ditambahkan sebelumnya.")
    else:
        tracked_addresses[user_id].append(address)
        await message.answer(f"✅ Address {address} berhasil ditambahkan!")

@dp.message(Command("list"))
async def list_addresses(message: Message):
    user_id = message.chat.id
    if user_id in tracked_addresses and tracked_addresses[user_id]:
        address_list = "\n".join(tracked_addresses[user_id])
        await message.answer(f"📋 Address yang dipantau:\n{address_list}")
    else:
        await message.answer("⚠️ Anda belum menambahkan address.")

# ===================== TRACKING TRANSAKSI =====================

async def track_transactions():
    while True:
        for user_id, addresses in tracked_addresses.items():
            for address in addresses:
                url = f"{BLOCKSCOUT_API}/v2/addresses/{address}/transactions"
                response = requests.get(url)

                if response.status_code == 200:
                    transactions = response.json()["items"]
                    for tx in transactions[:5]:  # Ambil 5 transaksi terbaru
                        tx_hash = tx["hash"]
                        from_address = tx["from"]
                        to_address = tx["to"]
                        value = int(tx["value"]) / (10**18)  # Ubah ke ETH
                        tx_link = f"{BLOCKSCOUT_API}/tx/{tx_hash}"

                        if tx_hash in sent_tx_hashes:
                            continue  # Lewati jika sudah dikirim sebelumnya

                        if from_address.lower() == address.lower():
                            tx_type = "🔴 Send"
                        elif to_address.lower() == address.lower():
                            tx_type = "🟢 Received"
                        else:
                            tx_type = "🔄 Swap"

                        message = (
                            f"{tx_type}\n"
                            f"💰 <b>{value} ETH</b>\n"
                            f"🔗 <a href='{tx_link}'>Lihat di Explorer</a>"
                        )

                        await bot.send_message(user_id, message, parse_mode="HTML")
                        sent_tx_hashes.add(tx_hash)

        await asyncio.sleep(30)  # Periksa transaksi setiap 30 detik

# ===================== MENJALANKAN BOT =====================

async def main():
    asyncio.create_task(track_transactions())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
