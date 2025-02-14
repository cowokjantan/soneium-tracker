import os
import asyncio
import logging
import json
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.enums import ParseMode

TOKEN = os.getenv("BOT_TOKEN")
BLOCKSCOUT_API = "https://soneium.blockscout.com/api"
CHECK_INTERVAL = 10  # Cek transaksi setiap 10 detik

bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# Penyimpanan alamat yang dipantau per user
USER_ADDRESSES = {}
LAST_TX_HASHES = {}

# 🔹 Fungsi untuk mengambil transaksi terbaru dari Blockscout
async def get_transactions(address):
    url = f"{BLOCKSCOUT_API}/v2/addresses/{address}/transactions"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()
            return None

# 🔹 Fungsi untuk memfilter transaksi
def filter_transaction(tx):
    if "token_transfers" in tx:
        return True  # Transfer token
    elif "swap" in tx:
        return True  # Swap
    elif "nft_transfers" in tx:
        return True  # Jual/beli NFT
    return False

# 🔹 Fungsi untuk memantau transaksi
async def track_transactions():
    while True:
        for user_id, addresses in USER_ADDRESSES.items():
            for address in addresses:
                transactions = await get_transactions(address)
                if transactions:
                    for tx in transactions:
                        tx_hash = tx["hash"]
                        if tx_hash in LAST_TX_HASHES:
                            continue  # Lewati jika tx sudah dikirim

                        LAST_TX_HASHES[tx_hash] = True
                        link = f"<a href='{BLOCKSCOUT_API}/tx/{tx_hash}'>View on Explorer</a>"
                        msg = f"🔔 Transaksi baru terdeteksi:\n{link}"
                        await bot.send_message(user_id, msg, parse_mode=ParseMode.HTML)
        await asyncio.sleep(CHECK_INTERVAL)

# 🔹 Perintah untuk menambahkan alamat
@dp.message(Command("add"))
async def add_address(message: Message):
    user_id = message.from_user.id
    parts = message.text.split()
    if len(parts) != 2:
        await message.reply("❌ Format salah! Gunakan: /add 0xADDRESS")
        return

    address = parts[1]
    if user_id not in USER_ADDRESSES:
        USER_ADDRESSES[user_id] = []

    if address in USER_ADDRESSES[user_id]:
        await message.reply("⚠️ Alamat ini sudah dipantau!")
        return

    USER_ADDRESSES[user_id].append(address)
    await message.reply(f"✅ Alamat {address} berhasil ditambahkan!")

# 🔹 Perintah untuk melihat alamat yang dipantau
@dp.message(Command("list"))
async def list_addresses(message: Message):
    user_id = message.from_user.id
    if user_id not in USER_ADDRESSES or not USER_ADDRESSES[user_id]:
        await message.reply("🚫 Anda belum menambahkan alamat.")
        return

    addresses = "\n".join(USER_ADDRESSES[user_id])
    await message.reply(f"📌 Alamat yang Anda pantau:\n{addresses}")

# 🔹 Perintah untuk memulai bot
@dp.message(Command("start"))
async def start_command(message: Message):
    await message.reply("🚀 Selamat datang di Soneium Tracker!\nGunakan /add <address> untuk mulai melacak transaksi.")

# 🔹 Menjalankan bot
async def main():
    dp.include_router(dp)
    asyncio.create_task(track_transactions())
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
