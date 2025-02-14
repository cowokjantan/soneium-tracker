import logging
import asyncio
import aiohttp
import json
import os
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.client.default import DefaultBotProperties

# Gunakan environment variable untuk token dan chat ID
TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID", "0"))  # Pastikan nilai default 0 agar tidak error

# Inisialisasi bot dengan default parse_mode
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Data penyimpanan address yang dipantau
WATCHED_ADDRESSES = {}  # { "0x123...": "Nama Address" }
TX_CACHE = set()

# API Blockscout Soneium
BLOCKSCOUT_API = "https://soneium.blockscout.com/api"

async def fetch_transactions(address):
    """Mengambil daftar transaksi untuk address tertentu."""
    url = f"{BLOCKSCOUT_API}?module=account&action=txlist&address={address}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            try:
                return await response.json()
            except json.JSONDecodeError:
                return {"result": []}

async def track_transactions():
    """Memeriksa transaksi baru setiap 30 detik."""
    while True:
        for address, name in WATCHED_ADDRESSES.items():
            data = await fetch_transactions(address)
            if "result" in data:
                for tx in data["result"]:
                    tx_hash = tx["hash"]
                    if tx_hash not in TX_CACHE:
                        TX_CACHE.add(tx_hash)
                        await notify_transaction(tx, name)
        await asyncio.sleep(30)

async def detect_transaction_type(tx):
    """Mendeteksi jenis transaksi."""
    if tx["input"] != "0x":
        return "🔄 Swap"
    elif tx["value"] != "0":
        return "🔁 Transfer"
    elif "NFT" in tx.get("tokenSymbol", ""):  # Cek NFT berdasarkan tokenSymbol
        return "🎨 NFT Sale" if tx["value"] != "0" else "🛒 NFT Purchase"
    return "🔍 Unknown"

async def notify_transaction(tx, name):
    """Mengirim notifikasi transaksi baru ke Telegram."""
    tx_type = await detect_transaction_type(tx)
    msg = (f"🔔 <b>Transaksi Baru</b> 🔔\n"
           f"👤 <b>{name}</b>\n"
           f"🔹 Type: {tx_type}\n"
           f"🔗 <a href='https://soneium.blockscout.com/tx/{tx['hash']}'>Lihat di Block Explorer</a>")

    await bot.send_message(CHAT_ID, msg)

@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer("🚀 Selamat datang di Soneium Tracker!\nGunakan /add <address> <nama> untuk mulai melacak transaksi.")

@dp.message(Command("add"))
async def add_address(message: Message):
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("⚠ Gunakan format: /add <address> <nama>")
        return
    address, name = parts[1], parts[2]
    WATCHED_ADDRESSES[address] = name
    await message.answer(f"✅ Alamat {address} dengan nama {name} berhasil ditambahkan!")

@dp.message(Command("list"))
async def list_addresses(message: Message):
    if not WATCHED_ADDRESSES:
        await message.answer("📭 Belum ada alamat yang dipantau.")
    else:
        msg = "📜 <b>Daftar Alamat yang Dipantau:</b>\n"
        for addr, name in WATCHED_ADDRESSES.items():
            msg += f"- {name}: <code>{addr}</code>\n"
        await message.answer(msg, parse_mode="HTML")

async def main():
    loop = asyncio.get_event_loop()
    loop.create_task(track_transactions())
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
