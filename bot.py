import os
import asyncio
import aiohttp
import json
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.enums.parse_mode import ParseMode
from aiogram.utils.markdown import hlink
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
API_URL = "https://soneium.blockscout.com/api"
CHECK_INTERVAL = 30  # Waktu cek transaksi (detik)

# Inisialisasi bot & dispatcher
bot = Bot(token=TOKEN, default=types.DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Data penyimpanan alamat & transaksi terakhir
watched_addresses = {}  # Format: { "nama": "0x123..." }
seen_tx_hashes = set()

# Perintah /start
@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer("🚀 Bot mulai! Gunakan /add untuk menambahkan alamat.")

# Perintah /add nama alamat
@dp.message(Command("add"))
async def add_address(message: Message):
    try:
        _, nama, address = message.text.split()
        if address.startswith("0x") and len(address) == 42:
            watched_addresses[nama] = address.lower()
            await message.answer(f"✅ Alamat {nama} ({address}) ditambahkan!")
        else:
            await message.answer("⚠️ Format alamat salah!")
    except:
        await message.answer("⚠️ Gunakan format: `/add Nama 0xAlamat`")

# Perintah /list
@dp.message(Command("list"))
async def list_addresses(message: Message):
    if watched_addresses:
        text = "🔍 Alamat yang dipantau:\n" + "\n".join(f"{nama}: {addr}" for nama, addr in watched_addresses.items())
        await message.answer(text)
    else:
        await message.answer("❌ Tidak ada alamat yang dipantau.")

# Fungsi untuk mendapatkan transaksi terbaru
async def get_latest_transactions():
    async with aiohttp.ClientSession() as session:
        for nama, address in watched_addresses.items():
            url = f"{API_URL}?module=account&action=txlist&address={address}"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    for tx in data.get("result", []):
                        tx_hash = tx["hash"]
                        if tx_hash not in seen_tx_hashes:
                            seen_tx_hashes.add(tx_hash)
                            tx_type = classify_transaction(tx, address)
                            tx_link = f"https://soneium.blockscout.com/tx/{tx_hash}"
                            await bot.send_message(
                                chat_id=os.getenv("CHAT_ID"),
                                text=f"🔔 {nama} ({address})\n{tx_type}: {hlink('Lihat transaksi', tx_link)}"
                            )

# Klasifikasi transaksi (send, receive, buy NFT, sell NFT)
def classify_transaction(tx, address):
    if tx["from"].lower() == address:
        if tx.get("input") != "0x":  # Jika ada data tambahan, kemungkinan beli NFT
            return "🛒 Buy NFT"
        return "📤 Send Token"
    elif tx["to"].lower() == address:
        if tx.get("input") != "0x":  # Jika ada data tambahan, kemungkinan jual NFT
            return "💰 Sell NFT"
        return "📥 Received Token"
    return "❓ Unknown Transaction"

# Looping untuk cek transaksi terbaru
async def check_transactions():
    while True:
        await get_latest_transactions()
        await asyncio.sleep(CHECK_INTERVAL)

# Main function
async def main():
    asyncio.create_task(check_transactions())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
