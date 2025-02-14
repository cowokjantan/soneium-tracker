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

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

WATCHED_ADDRESSES_FILE = "watched_addresses.json"
LAST_BLOCK_FILE = "last_block.json"

WATCHED_ADDRESSES = {}
LAST_BLOCK = {}  # Menyimpan block terakhir untuk setiap address

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

def load_last_block():
    global LAST_BLOCK
    try:
        with open(LAST_BLOCK_FILE, "r") as f:
            LAST_BLOCK = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        LAST_BLOCK = {}

def save_last_block():
    with open(LAST_BLOCK_FILE, "w") as f:
        json.dump(LAST_BLOCK, f)

async def fetch_transactions(address):
    url = f"{BLOCKSCOUT_API}?module=account&action=tokentx&address={address}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logging.error(f"❌ Gagal mengambil data transaksi: {response.status}")
                    return {"result": []}
    except Exception as e:
        logging.error(f"❌ Error saat mengambil transaksi: {e}")
        return {"result": []}

async def track_transactions():
    while True:
        new_tx_detected = False
        for address, data in WATCHED_ADDRESSES.items():
            transactions = await fetch_transactions(address)
            if "result" in transactions:
                last_block = int(LAST_BLOCK.get(address, "0"))  # Ambil block terakhir yang tersimpan
                new_last_block = last_block  # Variabel untuk update block terakhir
                
                for tx in transactions["result"]:
                    tx_block = int(tx.get("blockNumber", "0"))
                    if tx_block > last_block:
                        await notify_transaction(tx, address, data["name"], data["chat_id"])
                        new_last_block = max(new_last_block, tx_block)  # Update block tertinggi yang diproses
                        new_tx_detected = True

                if new_tx_detected:
                    LAST_BLOCK[address] = str(new_last_block)  # Simpan last block terbaru
                    save_last_block()

        await asyncio.sleep(30)

async def detect_transaction_type(tx, address):
    sender = tx.get("from", "").lower()
    receiver = tx.get("to", "").lower()
    contract = tx.get("contractAddress", "").lower()
    value = int(tx.get("value", "0"))

    if "tokenSymbol" in tx and "NFT" in tx["tokenSymbol"]:
        if sender == address.lower():
            return "🎨 NFT Sale"
        elif receiver == address.lower():
            return "🛒 NFT Purchase"

    if "tokenSymbol" in tx:
        return "🔁 Token Transfer"

    if tx.get("input", "0x") != "0x":
        return "🔄 Swap"

    if value > 0:
        return "🔁 ETH Transfer"

    return "🔍 Unknown"

async def notify_transaction(tx, address, name, chat_id):
    try:
        tx_type = await detect_transaction_type(tx, address)
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
    LAST_BLOCK[address] = "0"  # Setel block terakhir ke nol saat pertama kali menambahkan address
    save_watched_addresses()
    save_last_block()
    
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
        del LAST_BLOCK[address]
        save_watched_addresses()
        save_last_block()
        await message.answer(f"✅ Alamat {address} telah dihapus dari daftar.")
    else:
        await message.answer("⚠ Alamat tidak ditemukan dalam daftar.")

async def main():
    logging.info("🚀 Bot mulai berjalan...")
    load_watched_addresses()
    load_last_block()
    loop = asyncio.get_event_loop()
    loop.create_task(track_transactions())
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
