import logging
import asyncio
import aiohttp
import json
import os
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message

TOKEN = os.getenv("BOT_TOKEN")
from aiogram.enums import ParseMode

bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)

dp = Dispatcher()

WATCHED_ADDRESSES = {}
TX_CACHE = set()

BLOCKSCOUT_API = "https://soneium.blockscout.com/api"

async def fetch_transactions(address):
    url = f"{BLOCKSCOUT_API}?module=account&action=txlist&address={address}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()

async def track_transactions():
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

async def notify_transaction(tx, name):
    tx_type = "🔄 Swap" if tx["input"] != "0x" else "🔁 Transfer"
    if "NFT" in tx_type:
        tx_type = "🎨 NFT Sale" if tx["value"] != "0" else "🛒 NFT Purchase"
    msg = (f"🔔 <b>Transaksi Baru</b> 🔔\n"
           f"👤 <b>{name}</b>\n"
           f"🔹 Type: {tx_type}\n"
           f"🔗 <a href='https://soneium.blockscout.com/tx/{tx['hash']}'>Lihat di Block Explorer</a>")
    await bot.send_message(os.getenv("CHAT_ID"), msg, parse_mode="HTML")

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
