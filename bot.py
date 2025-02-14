import logging
import asyncio
import aiohttp
import json
import os
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.client.default import DefaultBotProperties

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

WATCHED_ADDRESSES_FILE = "watched_addresses.json"
TX_CACHE_FILE = "tx_cache.json"

WATCHED_ADDRESSES = {}
TX_CACHE = set()

BLOCKSCOUT_API = "https://soneium.blockscout.com/api"

# Load & Save Functions
def load_watched_addresses():
    global WATCHED_ADDRESSES
    try:
        with open(WATCHED_ADDRESSES_FILE, "r") as f:
            WATCHED_ADDRESSES = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        WATCHED_ADDRESSES = {}

def save_watched_addresses():
    with open(WATCHED_ADDRESSES_FILE, "w") as f:
        json.dump(WATCHED_ADDRESSES, f)

def load_tx_cache():
    global TX_CACHE
    try:
        with open(TX_CACHE_FILE, "r") as f:
            TX_CACHE = set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        TX_CACHE = set()

def save_tx_cache():
    with open(TX_CACHE_FILE, "w") as f:
        json.dump(list(TX_CACHE), f)

# Fetch Transactions
async def fetch_transactions(address):
    url = f"{BLOCKSCOUT_API}?module=account&action=tokentx&address={address}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return await response.json()
    except Exception as e:
        logging.error(f"❌ Gagal mengambil transaksi dari Blockscout: {e}")
        return {"result": []}

# Track Transactions
async def track_transactions():
    while True:
        new_tx_detected = False
        notification_queue = asyncio.Queue()

        for address, data in list(WATCHED_ADDRESSES.items()):
            transactions = await fetch_transactions(address)
            if transactions.get("result"):
                for tx in transactions["result"]:
                    tx_hash = tx.get("hash")

                    if tx_hash and tx_hash not in TX_CACHE:
                        TX_CACHE.add(tx_hash)
                        notification_queue.put_nowait((tx, address, data.get("name", "Unknown"), data["chat_id"]))
                        new_tx_detected = True

        if new_tx_detected:
            save_tx_cache()
            await send_notifications(notification_queue)

        logging.info(f"✅ Scan transaksi selesai. Menunggu 30 detik...")
        await asyncio.sleep(30)

# Send Notifications
async def send_notifications(queue):
    while not queue.empty():
        tx, address, name, chat_id = await queue.get()
        try:
            await notify_transaction(tx, address, name, chat_id)
            await asyncio.sleep(2)  # Delay antar pesan
        except Exception as e:
            logging.error(f"❌ Gagal mengirim notifikasi: {e}")

# Notify Transaction
async def notify_transaction(tx, address, name, chat_id):
    try:
        tx_type = await detect_transaction_type(tx, address)
        msg = (f"🔔 <b>Transaksi Baru</b> 🔔\n"
               f"👤 <b>{name}</b>\n"
               f"🔹 Type: {tx_type}\n"
               f"🔗 <a href='https://soneium.blockscout.com/tx/{tx.get('hash')}'>Lihat di Block Explorer</a>")
        await bot.send_message(chat_id, msg)
    except Exception as e:
        logging.error(f"❌ Gagal mengirim notifikasi: {e}")

# Detect Transaction Type
async def detect_transaction_type(tx, address):
    sender = tx.get("from", "").lower()
    receiver = tx.get("to", "").lower()
    value = int(tx.get("value", "0")) if tx.get("value") else 0

    if "tokenSymbol" in tx and "NFT" in tx["tokenSymbol"]:
        return "🎨 NFT Sale" if sender == address.lower() else "🛒 NFT Purchase"

    if "tokenSymbol" in tx:
        return "🔁 Token Transfer"

    if tx.get("input") and tx["input"] != "0x":
        return "🔄 Swap"

    if value > 0:
        return "🔁 ETH Transfer"

    return "🔍 Unknown"

# Telegram Commands
@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer("🚀 Selamat datang di Soneium Tracker!\n"
                         "Gunakan /add <address> <nama> untuk mulai melacak transaksi.")

@dp.message(Command("add"))
async def add_address(message: Message):
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("⚠ Gunakan format: /add <address> <nama>")
        return
    address, name = parts[1], parts[2]
    
    WATCHED_ADDRESSES[address] = {"name": name, "chat_id": message.chat.id}
    save_watched_addresses()
    
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
        save_watched_addresses()
        await message.answer(f"✅ Alamat {address} telah dihapus dari daftar.")
    else:
        await message.answer("⚠ Alamat tidak ditemukan dalam daftar.")

# Main Function
async def main():
    logging.info("🚀 Bot mulai berjalan...")
    load_watched_addresses()
    load_tx_cache()
    asyncio.create_task(track_transactions())
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
