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

# Gunakan environment variable untuk token
TOKEN = os.getenv("BOT_TOKEN")

# Inisialisasi bot dengan default parse_mode
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# File penyimpanan data
WATCHED_ADDRESSES_FILE = "watched_addresses.json"
TX_CACHE_FILE = "tx_cache.json"

# Data address yang dipantau & transaksi yang sudah dikirim
WATCHED_ADDRESSES = {}  # { "0x123...": {"name": "Nama Address", "chat_id": 12345678} }
TX_CACHE = set()  # Set untuk menyimpan hash transaksi

# API Blockscout Soneium
BLOCKSCOUT_API = "https://soneium.blockscout.com/api"

def load_watched_addresses():
    """Memuat daftar address dari file saat bot dimulai."""
    global WATCHED_ADDRESSES
    try:
        with open(WATCHED_ADDRESSES_FILE, "r") as f:
            WATCHED_ADDRESSES = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        WATCHED_ADDRESSES = {}

def save_watched_addresses():
    """Menyimpan daftar address ke file."""
    with open(WATCHED_ADDRESSES_FILE, "w") as f:
        json.dump(WATCHED_ADDRESSES, f)

def load_tx_cache():
    """Memuat cache transaksi dari file saat bot dimulai."""
    global TX_CACHE
    try:
        with open(TX_CACHE_FILE, "r") as f:
            TX_CACHE = set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        TX_CACHE = set()

def save_tx_cache():
    """Menyimpan cache transaksi ke file."""
    with open(TX_CACHE_FILE, "w") as f:
        json.dump(list(TX_CACHE), f)

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
        new_tx_detected = False
        for address, data in WATCHED_ADDRESSES.items():
            transactions = await fetch_transactions(address)
            if "result" in transactions:
                for tx in transactions["result"]:
                    tx_hash = tx["hash"]
                    if tx_hash not in TX_CACHE:
                        TX_CACHE.add(tx_hash)
                        await notify_transaction(tx, data["name"], data["chat_id"])
                        new_tx_detected = True
        if new_tx_detected:
            save_tx_cache()  # Simpan cache jika ada transaksi baru
        await asyncio.sleep(30)

async def detect_transaction_type(tx):
    """Mendeteksi jenis transaksi."""
    if tx["input"] != "0x":
        return "🔄 Swap"
    elif tx["value"] != "0":
        return "🔁 Transfer"
    elif "tokenSymbol" in tx and "NFT" in tx["tokenSymbol"]:  
        return "🎨 NFT Sale" if tx["value"] != "0" else "🛒 NFT Purchase"
    return "🔍 Unknown"

async def notify_transaction(tx, name, chat_id):
    """Mengirim notifikasi transaksi baru ke pemilik address"""
    try:
        tx_type = await detect_transaction_type(tx)
        msg = (f"🔔 <b>Transaksi Baru</b> 🔔\n"
               f"👤 <b>{name}</b>\n"
               f"🔹 Type: {tx_type}\n"
               f"🔗 <a href='https://soneium.blockscout.com/tx/{tx['hash']}'>Lihat di Block Explorer</a>")
        await bot.send_message(chat_id, msg)
    except Exception as e:
        logging.error(f"❌ Gagal mengirim notifikasi: {e}")

@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer("🚀 Selamat datang di Soneium Tracker!\n"
                         "Gunakan /add 'wallet_address' 'nama' untuk mulai melacak transaksi.")

@dp.message(Command("add"))
async def add_address(message: Message):
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("⚠ Gunakan format: /add <address> <nama>")
        return
    address, name = parts[1], parts[2]
    
    WATCHED_ADDRESSES[address] = {"name": name, "chat_id": message.chat.id}
    save_watched_addresses()  # Simpan daftar address ke file
    
    await message.answer(f"✅ Alamat {address} dengan nama {name} berhasil ditambahkan!")

@dp.message(Command("list"))
async def list_addresses(message: Message):
    if not WATCHED_ADDRESSES:
        await message.answer("📭 Belum ada alamat yang dipantau.")
    else:
        msg = "📜 <b>Daftar Alamat yang Dipantau:</b>\n"
        for addr, data in WATCHED_ADDRESSES.items():
            msg += f"- {data['name']}: <code>{addr}</code>\n"
        await message.answer(msg, parse_mode="HTML")

@dp.message(Command("remove"))
async def remove_address(message: Message):
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("⚠ Gunakan format: /remove <address>")
        return
    address = parts[1]

    if address in WATCHED_ADDRESSES:
        del WATCHED_ADDRESSES[address]
        save_watched_addresses()  # Simpan perubahan
        await message.answer(f"✅ Alamat {address} telah dihapus dari daftar.")
    else:
        await message.answer("⚠ Alamat tidak ditemukan dalam daftar.")

async def main():
    logging.info("🚀 Bot mulai berjalan...")
    load_watched_addresses()  # Muat daftar address sebelum mulai
    load_tx_cache()  # Muat cache transaksi sebelum mulai
    loop = asyncio.get_event_loop()
    loop.create_task(track_transactions())
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
