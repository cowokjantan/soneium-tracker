import asyncio
import logging
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Message
from aiogram.filters import Command
from collections import defaultdict

TOKEN = "YOUR_BOT_TOKEN"  # Ganti dengan token bot Telegram
BLOCKSCOUT_API = "https://soneium.blockscout.com/api"
CHECK_INTERVAL = 30  # Cek transaksi setiap 30 detik

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Database sementara di memori
user_addresses = defaultdict(set)  # Menyimpan daftar address per user
seen_tx_hashes = set()  # Menyimpan hash transaksi yang sudah dikirim

# 🔹 Perintah /start
@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer("🚀 Selamat datang di *Soneium Tracker*!\n"
                         "Gunakan /add `<address>` untuk mulai melacak transaksi.\n"
                         "Gunakan /list untuk melihat daftar address yang dipantau.\n"
                         "Gunakan /remove `<address>` untuk menghapus address.")

# 🔹 Perintah /add <address>
@dp.message(Command("add"))
async def add_address(message: Message):
    args = message.text.split()
    if len(args) != 2:
        await message.answer("⚠️ Format salah! Gunakan: /add `<address>`")
        return

    address = args[1].lower()
    user_addresses[message.chat.id].add(address)
    await message.answer(f"✅ Address <code>{address}</code> ditambahkan!")

# 🔹 Perintah /list
@dp.message(Command("list"))
async def list_addresses(message: Message):
    addresses = user_addresses.get(message.chat.id, set())
    if not addresses:
        await message.answer("⚠️ Anda belum menambahkan address!")
    else:
        addr_list = "\n".join(f"🔹 <code>{addr}</code>" for addr in addresses)
        await message.answer(f"📋 **Daftar Address yang Dipantau:**\n{addr_list}")

# 🔹 Perintah /remove <address>
@dp.message(Command("remove"))
async def remove_address(message: Message):
    args = message.text.split()
    if len(args) != 2:
        await message.answer("⚠️ Format salah! Gunakan: /remove `<address>`")
        return

    address = args[1].lower()
    if address in user_addresses.get(message.chat.id, set()):
        user_addresses[message.chat.id].remove(address)
        await message.answer(f"✅ Address <code>{address}</code> dihapus dari pemantauan!")
    else:
        await message.answer("⚠️ Address tidak ditemukan dalam daftar pemantauan!")

# 🔹 Fungsi untuk cek transaksi
async def check_transactions():
    while True:
        try:
            for chat_id, addresses in user_addresses.items():
                for address in addresses:
                    url = f"{BLOCKSCOUT_API}/v2/transactions?address={address}"
                    response = requests.get(url)
                    if response.status_code == 200:
                        transactions = response.json().get("items", [])
                        for tx in transactions:
                            tx_hash = tx["hash"]
                            if tx_hash not in seen_tx_hashes:
                                seen_tx_hashes.add(tx_hash)  # Hindari notifikasi duplikat
                                
                                from_addr = tx["from"]["hash"]
                                to_addr = tx["to"]["hash"]
                                tx_type = tx["type"]
                                value = tx.get("value", 0)
                                link = f"{BLOCKSCOUT_API}/tx/{tx_hash}"
                                
                                if tx_type in ["send", "received", "swap", "buyNFT", "sellNFT"]:
                                    msg = (f"🔔 **Transaksi Baru** 🔔\n"
                                           f"💰 <b>{tx_type.upper()}</b>\n"
        
