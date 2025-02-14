import asyncio
import os
import json
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.filters import Command

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")  # Token bot dari Telegram
API_URL = "https://soneium.blockscout.com/api"  # API Blockscout Soneium

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Data penyimpanan alamat & transaksi yang sudah dikirim notifikasi
tracked_addresses = {}  # Format: {chat_id: {address: "name"}}
sent_transactions = set()  # Set untuk menyimpan hash transaksi yang sudah dikirim

# -------------------- COMMAND HANDLERS --------------------

# Start bot
async def start_handler(message: Message):
    await message.answer("🚀 Selamat datang! Kirimkan alamat yang ingin dilacak dengan format:\n\n`/track 0xAlamat NamaAnda`")

# Tambah alamat yang ingin dilacak
async def track_handler(message: Message):
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("❌ Format salah! Gunakan: `/track 0xAlamat NamaAnda`")
        return

    chat_id = message.chat.id
    address = parts[1]
    name = " ".join(parts[2:])  # Menggabungkan nama jika lebih dari satu kata

    if chat_id not in tracked_addresses:
        tracked_addresses[chat_id] = {}

    tracked_addresses[chat_id][address] = name
    await message.answer(f"✅ Alamat `{address}` ({name}) berhasil ditambahkan!")

# Lihat alamat yang sudah tersimpan
async def list_handler(message: Message):
    chat_id = message.chat.id
    if chat_id not in tracked_addresses or not tracked_addresses[chat_id]:
        await message.answer("ℹ Tidak ada alamat yang dilacak.")
        return

    text = "📋 **Alamat yang sedang dilacak:**\n\n"
    for address, name in tracked_addresses[chat_id].items():
        text += f"🔹 `{address}` - {name}\n"

    await message.answer(text)

# Hapus alamat dari daftar
async def untrack_handler(message: Message):
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("❌ Format salah! Gunakan: `/untrack 0xAlamat`")
        return

    chat_id = message.chat.id
    address = parts[1]

    if chat_id in tracked_addresses and address in tracked_addresses[chat_id]:
        del tracked_addresses[chat_id][address]
        await message.answer(f"✅ Alamat `{address}` berhasil dihapus!")
    else:
        await message.answer(f"❌ Alamat `{address}` tidak ditemukan dalam daftar.")

# -------------------- TRANSACTION CHECKING --------------------

# Fungsi untuk mendapatkan transaksi dari API Blockscout
async def fetch_transactions(address):
    url = f"{API_URL}?module=account&action=txlist&address={address}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("result", [])
            return []

# Fungsi untuk memeriksa transaksi baru
async def check_transactions():
    while True:
        try:
            for chat_id, addresses in tracked_addresses.items():
                for address, name in addresses.items():
                    transactions = await fetch_transactions(address)
                    for tx in transactions:
                        tx_hash = tx["hash"]
                        from_address = tx["from"]
                        to_address = tx["to"]
                        value = int(tx["value"]) / 10**18  # Ubah ke ETH
                        token_symbol = "SONE"  # Ubah jika ada token lain

                        # Cek apakah transaksi ini sudah dikirim
                        if tx_hash in sent_transactions:
                            continue

                        # Tentukan jenis transaksi
                        if to_address.lower() == address.lower():
                            tx_type = "RECEIVE"
                        elif from_address.lower() == address.lower():
                            tx_type = "SEND"
                        else:
                            tx_type = "UNKNOWN"

                        message = (
                            f"🔔 **Transaksi Baru**\n"
                            f"🆔 TxHash: `{tx_hash}`\n"
                            f"👤 Dari: `{from_address}`\n"
                            f"📩 Ke: `{to_address}`\n"
                            f"💰 Jumlah: `{value} {token_symbol}`\n"
                            f"📌 Jenis: `{tx_type}`\n"
                        )

                        # Kirim notifikasi ke bot
                        await bot.send_message(chat_id, message)

                        # Simpan hash transaksi agar tidak dikirim ulang
                        sent_transactions.add(tx_hash)

        except Exception as e:
            print(f"Error checking transactions: {e}")

        await asyncio.sleep(10)  # Periksa setiap 10 detik

# -------------------- REGISTER HANDLERS & MAIN --------------------

dp.message.register(start_handler, Command("start"))
dp.message.register(track_handler, Command("track"))
dp.message.register(list_handler, Command("list"))
dp.message.register(untrack_handler, Command("untrack"))

async def main():
    asyncio.create_task(check_transactions())  # Jalankan pemantauan transaksi
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
