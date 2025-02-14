import os
import asyncio
import logging
import aiohttp
import json

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.enums.parse_mode import ParseMode
from aiogram.client.default import DefaultBotProperties

# Konfigurasi logging
logging.basicConfig(level=logging.INFO)

# Ambil TOKEN dari environment variables
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ BOT_TOKEN tidak ditemukan! Pastikan sudah diatur di Railway Variables atau .env.")

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# URL API Blockscout
BLOCKSCOUT_API = "https://soneium.blockscout.com/api"

# Database untuk menyimpan alamat pengguna
USER_ADDRESSES = {}  # Format: {chat_id: {"nama1": "0x123...", "nama2": "0x456..."}}
SENT_TX_HASHES = set()  # Menyimpan tx_hash agar tidak mengirim ulang


async def fetch_transactions(address):
    """Mengambil transaksi dari Blockscout API."""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BLOCKSCOUT_API}?module=account&action=txlist&address={address}") as resp:
            if resp.status == 200:
                return await resp.json()
            return None


def filter_transaction(tx):
    """Filter transaksi berdasarkan kategori Send, Received, Buy NFT, Sell NFT."""
    if tx.get("input") == "0x":  # Contoh sederhana (perlu dicek lebih lanjut)
        if tx["from"] == tx["to"]:
            return "Buy NFT"
        return "Send"
    elif tx["to"] == "0x":  # Contoh sederhana (perlu dicek lebih lanjut)
        return "Sell NFT"
    else:
        return "Received"


async def check_transactions():
    """Memeriksa transaksi dan mengirim notifikasi jika ada transaksi baru."""
    while True:
        for chat_id, addresses in USER_ADDRESSES.items():
            for name, address in addresses.items():
                data = await fetch_transactions(address)
                if data and "result" in data:
                    for tx in data["result"]:
                        tx_hash = tx["hash"]
                        if tx_hash not in SENT_TX_HASHES:
                            tx_type = filter_transaction(tx)
                            tx_link = f"https://soneium.blockscout.com/tx/{tx_hash}"
                            message = (
                                f"🔔 <b>Transaksi Baru</b>\n"
                                f"🏷️ <b>Nama:</b> {name}\n"
                                f"🔹 <b>Type:</b> {tx_type}\n"
                                f"💰 <b>Value:</b> {tx['value']} SONE\n"
                                f"🔗 <a href='{tx_link}'>Lihat di Blockscout</a>"
                            )
                            await bot.send_message(chat_id, message)
                            SENT_TX_HASHES.add(tx_hash)
        await asyncio.sleep(30)  # Cek transaksi setiap 30 detik


@dp.message(Command("start"))
async def start(message: Message):
    """Perintah /start untuk menampilkan pesan selamat datang."""
    await message.answer("👋 Selamat datang! Gunakan /add untuk menambahkan alamat yang ingin dipantau.")


@dp.message(Command("add"))
async def add_address(message: Message):
    """Menambahkan alamat ke daftar pemantauan."""
    args = message.text.split(" ")
    if len(args) < 3:
        await message.answer("❌ Format salah! Gunakan: /add nama_address 0xYourWallet")
        return
    
    name = args[1]
    address = args[2]
    
    if message.chat.id not in USER_ADDRESSES:
        USER_ADDRESSES[message.chat.id] = {}
    
    USER_ADDRESSES[message.chat.id][name] = address
    await message.answer(f"✅ Alamat {name} ({address}) berhasil ditambahkan!")


@dp.message(Command("remove"))
async def remove_address(message: Message):
    """Menghapus alamat dari daftar pemantauan."""
    args = message.text.split(" ")
    if len(args) < 2:
        await message.answer("❌ Format salah! Gunakan: /remove nama_address")
        return
    
    name = args[1]
    
    if message.chat.id in USER_ADDRESSES and name in USER_ADDRESSES[message.chat.id]:
        del USER_ADDRESSES[message.chat.id][name]
        await message.answer(f"✅ Alamat {name} berhasil dihapus dari pemantauan!")
    else:
        await message.answer(f"⚠️ Alamat {name} tidak ditemukan dalam daftar pemantauan.")


async def main():
    """Menjalankan bot dan task monitoring."""
    asyncio.create_task(check_transactions())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
