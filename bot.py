import asyncio
import os
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.filters import Command

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")  # Ambil token dari Railway
API_URL = "https://soneium.blockscout.com/api"  # API Blockscout Soneium

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Database sementara: menyimpan chat_id dan alamat yang ingin dilacak
tracked_addresses = {}
last_tx_hashes = {}  # 🔹 Simpan hash transaksi terakhir untuk setiap alamat

async def start_handler(message: Message):
    await message.answer("Halo! Kirimkan alamat wallet yang ingin kamu lacak dengan perintah:\n`/track 0xAlamatWallet`", parse_mode="Markdown")

async def track_address(message: Message):
    args = message.text.split(" ")
    if len(args) < 2:
        await message.answer("Gunakan perintah: `/track <alamat_wallet>`", parse_mode="Markdown")
        return

    address = args[1].lower()  # Ubah ke huruf kecil agar seragam
    chat_id = message.chat.id

    if chat_id not in tracked_addresses:
        tracked_addresses[chat_id] = set()
    
    tracked_addresses[chat_id].add(address)
    last_tx_hashes[address] = None  # 🔹 Inisialisasi hash transaksi terakhir

    await message.answer(f"✅ Alamat `{address}` telah ditambahkan untuk dilacak!", parse_mode="Markdown")

async def check_transactions():
    while True:
        for chat_id, addresses in tracked_addresses.items():
            for address in addresses:
                try:
                    response = requests.get(f"{API_URL}?module=account&action=txlist&address={address}")
                    data = response.json()

                    if "result" in data and data["result"]:
                        last_tx = data["result"][0]  # Ambil transaksi terbaru
                        tx_hash = last_tx["hash"]

                        # 🔹 Cek apakah transaksi sudah dikirim sebelumnya
                        if address in last_tx_hashes and last_tx_hashes[address] == tx_hash:
                            continue  # Jika sama, lewati transaksi ini (tidak dikirim ulang)

                        from_addr = last_tx["from"].lower()
                        to_addr = last_tx["to"].lower()
                        value = int(last_tx["value"]) / (10**18)  # Konversi dari Wei ke SONE
                        input_data = last_tx.get("input", "")

                        # **Menentukan jenis transaksi**
                        if address == from_addr:
                            if input_data and len(input_data) > 10:
                                tx_type = "BUY NFT 🛒"
                            else:
                                tx_type = "SEND 📤"
                        elif address == to_addr:
                            if input_data and len(input_data) > 10:
                                tx_type = "SELL NFT 💰"
                            else:
                                tx_type = "RECEIVE 📥"
                        else:
                            tx_type = "UNKNOWN ❓"

                        message = (f"🚀 **{tx_type}** 🚀\n"
                                   f"🔹 **TX Hash:** [{tx_hash[:10]}...](https://soneium.blockscout.com/tx/{tx_hash})\n"
                                   f"🔹 **Dari:** `{from_addr}`\n"
                                   f"🔹 **Ke:** `{to_addr}`\n"
                                   f"🔹 **Jumlah:** `{value} SONE`")

                        await bot.send_message(chat_id, message, parse_mode="Markdown", disable_web_page_preview=True)

                        # 🔹 Simpan hash transaksi terakhir untuk alamat ini
                        last_tx_hashes[address] = tx_hash

                except Exception as e:
                    print(f"Error saat mengambil transaksi: {e}")

        await asyncio.sleep(60)  # Cek transaksi setiap 60 detik

async def main():
    dp.message.register(start_handler, Command("start"))
    dp.message.register(track_address, Command("track"))

    asyncio.create_task(check_transactions())  # Jalankan pemantauan transaksi
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
