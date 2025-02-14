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

async def fetch_transactions(address):
    url = f"{BLOCKSCOUT_API}?module=account&action=tokentx&address={address}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            try:
                return await response.json()
            except json.JSONDecodeError:
                return {"result": []}

async def track_transactions():
    while True:
        messages_by_chat = {}
        for address, data in WATCHED_ADDRESSES.items():
            transactions = await fetch_transactions(address)
            if transactions.get("result"):
                for tx in transactions["result"]:
                    tx_hash = tx.get("hash")
                    if tx_hash and tx_hash not in TX_CACHE:
                        TX_CACHE.add(tx_hash)
                        chat_id = data["chat_id"]
                        name = data.get("name", "Unknown")
                        
                        if chat_id not in messages_by_chat:
                            messages_by_chat[chat_id] = []
                        messages_by_chat[chat_id].append((tx, name))
        
        save_tx_cache()
        await send_batch_notifications(messages_by_chat)
        await asyncio.sleep(30)

async def send_batch_notifications(messages_by_chat):
    for chat_id, transactions in messages_by_chat.items():
        try:
            message_text = "🔔 <b>Transaksi Baru</b> 🔔\n"
            for tx, name in transactions:
                tx_type = await detect_transaction_type(tx)
                message_text += (f"👤 <b>{name}</b>\n"
                                 f"🔹 Type: {tx_type}\n"
                                 f"🔗 <a href='https://soneium.blockscout.com/tx/{tx.get('hash')}'>Lihat di Block Explorer</a>\n\n")
            await bot.send_message(chat_id, message_text)
            await asyncio.sleep(2)
        except Exception as e:
            logging.error(f"❌ Gagal mengirim notifikasi: {e}")
            await handle_flood_limit(e)

async def detect_transaction_type(tx):
    if "tokenSymbol" in tx and "NFT" in tx["tokenSymbol"]:
        return "🎨 NFT Sale"
    if "tokenSymbol" in tx:
        return "🔁 Token Transfer"
    if tx.get("input") and tx["input"] != "0x":
        return "🔄 Swap"
    if int(tx.get("value", "0")) > 0:
        return "🔁 ETH Transfer"
    return "🔍 Unknown"

async def handle_flood_limit(error):
    if "Too Many Requests" in str(error):
        retry_after = int(str(error).split("retry after ")[1].split()[0])
        logging.warning(f"⏳ Rate limit terkena, menunggu {retry_after} detik...")
        await asyncio.sleep(retry_after)

@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer("🚀 Selamat datang di Soneium Tracker! Gunakan /add <address> <nama> untuk mulai melacak transaksi.")

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
        return
    msg = "📜 <b>Daftar Alamat yang Dipantau:</b>\n"
    for addr, data in WATCHED_ADDRESSES.items():
        msg += f"- {data['name']}: <code>{addr}</code>\n"
    await message.answer(msg, parse_mode="HTML")

async def main():
    logging.info("🚀 Bot mulai berjalan...")
    load_watched_addresses()
    load_tx_cache()
    asyncio.create_task(track_transactions())
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
