import os
import asyncio
import logging
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.filters import Command
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Ambil token dari environment variable
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN or not TOKEN.strip():
    raise ValueError("❌ BOT_TOKEN tidak ditemukan! Pastikan sudah diatur di Railway Variables atau .env.")

# Inisialisasi bot dan dispatcher
bot = Bot(token=TOKEN, parse_mode="HTML")
dp = Dispatcher()

# API Blockscout Soneium
BLOCKSCOUT_API = "https://soneium.blockscout.com/api"

# Data tracking (format: {chat_id: {alamat: nama}})
tracked_addresses = {}
last_seen_tx = {}

# Perintah /start
@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer("✅ Bot berjalan!\nGunakan /track <alamat> <nama> untuk mulai tracking.")

# Perintah untuk menambahkan alamat dengan nama
@dp.message(Command("track"))
async def track_address(message: Message):
    args = message.text.split(" ")
    if len(args) < 2:
        await message.answer("❌ Harap masukkan alamat dan (opsional) nama setelah perintah /track.\n\n📌 Contoh: <code>/track 0x1234567890abcdef WalletKu</code>")
        return

    address = args[1]
    name = " ".join(args[2:]) if len(args) > 2 else address  # Jika tidak ada nama, gunakan alamat

    chat_id = message.chat.id
    if chat_id not in tracked_addresses:
        tracked_addresses[chat_id] = {}

    tracked_addresses[chat_id][address] = name
    await message.answer(f"✅ Alamat <code>{address}</code> ({name}) ditambahkan ke tracking!")

# Perintah untuk melihat daftar alamat yang sedang dilacak
@dp.message(Command("list"))
async def list_addresses(message: Message):
    chat_id = message.chat.id
    if chat_id not in tracked_addresses or not tracked_addresses[chat_id]:
        await message.answer("📭 Anda belum melacak alamat apa pun.")
        return

    response = "📋 <b>Daftar Alamat yang Dilacak:</b>\n"
    for address, name in tracked_addresses[chat_id].items():
        response += f"🔹 <b>{name}</b>: <code>{address}</code>\n"

    await message.answer(response)

# Fungsi untuk mengambil transaksi dari Blockscout
async def fetch_transactions(address):
    try:
        url = f"{BLOCKSCOUT_API}?module=account&action=txlist&address={address}"
        response = requests.get(url)
        data = response.json()
        
        if data.get("status") == "1" and "result" in data:
            return data["result"]
        return []
    except Exception as e:
        logging.error(f"Error fetching transactions: {e}")
        return []

# Fungsi untuk menentukan jenis transaksi
def get_transaction_type(tx, address):
    from_addr = tx["from"].lower()
    to_addr = tx["to"].lower() if tx["to"] else None

    if to_addr is None:
        return "UNKNOWN"

    address = address.lower()

    if from_addr == address:
        return "SEND" if "input" not in tx or tx["input"] == "0x" else "SELL"
    if to_addr == address:
        return "RECEIVED" if "input" not in tx or tx["input"] == "0x" else "BUY"

    return "UNKNOWN"

# Fungsi untuk memantau transaksi
async def check_transactions():
    while True:
        for chat_id, addresses in tracked_addresses.items():
            for address, name in addresses.items():
                transactions = await fetch_transactions(address)

                if not transactions:
                    continue
                
                for tx in transactions:
                    tx_hash = tx["hash"]
                    if address not in last_seen_tx:
                        last_seen_tx[address] = set()
                    
                    if tx_hash in last_seen_tx[address]:
                        continue  # Lewati jika sudah dikirim sebelumnya

                    last_seen_tx[address].add(tx_hash)
                    tx_link = f"<a href='https://soneium.blockscout.com/tx/{tx_hash}'>🔗 Lihat TX</a>"

                    # Tentukan jenis transaksi
                    tx_type = get_transaction_type(tx, address)
                    if tx_type == "SEND":
                        message = f"📤 <b>{name} Mengirim:</b> {tx_link}"
                    elif tx_type == "RECEIVED":
                        message = f"📥 <b>{name} Menerima:</b> {tx_link}"
                    elif tx_type == "BUY":
                        message = f"🛒 <b>{name} Membeli NFT:</b> {tx_link}"
                    elif tx_type == "SELL":
                        message = f"💰 <b>{name} Menjual NFT:</b> {tx_link}"
                    else:
                        continue  # Jika tidak diketahui, skip

                    await bot.send_message(chat_id, message)

        await asyncio.sleep(30)  # Cek transaksi setiap 30 detik

# Fungsi utama untuk menjalankan bot
async def main():
    logging.basicConfig(level=logging.INFO)
    asyncio.create_task(check_transactions())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
