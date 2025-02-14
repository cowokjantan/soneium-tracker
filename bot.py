import os
import asyncio
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")  # Ambil token dari Railway ENV
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Data penyimpanan address dan chat_id
tracked_addresses = {}  # Format: {address: {"name": nama, "chat_id": chat_id}}
seen_transactions = set()  # Menyimpan hash transaksi yang sudah dikirim

# URL API Blockscout untuk Soneium
BLOCKSCOUT_API = "https://explorer.soneium.io/api"

# 🟢 Command untuk Memulai Bot
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer("👋 Halo! Kirimkan alamat wallet yang ingin kamu lacak:\n\nGunakan format:\n`/add 0x1234abcd Nama_Wallet`")

# 🟢 Command untuk Menambahkan Address
@dp.message(Command("add"))
async def add_address(message: types.Message):
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("⚠️ Format salah! Gunakan: `/add 0x1234abcd Nama_Wallet`")
        return

    address = parts[1].lower()
    name = " ".join(parts[2:])
    tracked_addresses[address] = {"name": name, "chat_id": message.chat.id}

    await message.answer(f"✅ Address `{address}` (`{name}`) berhasil ditambahkan!")

# 🟢 Command untuk Melihat Address yang Dilacak
@dp.message(Command("list"))
async def list_addresses(message: types.Message):
    if not tracked_addresses:
        await message.answer("⚠️ Belum ada address yang dilacak!")
        return

    text = "📋 **Address yang Dilacak:**\n\n"
    for addr, data in tracked_addresses.items():
        text += f"🔹 `{addr}` - {data['name']}\n"

    await message.answer(text)

# 🟢 Command untuk Menghapus Address
@dp.message(Command("remove"))
async def remove_address(message: types.Message):
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("⚠️ Gunakan: `/remove 0x1234abcd`")
        return

    address = parts[1].lower()
    if address in tracked_addresses:
        del tracked_addresses[address]
        await message.answer(f"✅ Address `{address}` berhasil dihapus!")
    else:
        await message.answer(f"⚠️ Address `{address}` tidak ditemukan!")

# 🔄 Fungsi untuk Mengecek Transaksi Baru
async def check_transactions():
    while True:
        print("🔍 Mengecek transaksi baru...")  # Debug log
        for address, data in tracked_addresses.items():
            chat_id = data["chat_id"]
            name = data["name"]

            try:
                url = f"{BLOCKSCOUT_API}?module=account&action=txlist&address={address}"
                response = requests.get(url).json()

                if "result" in response:
                    for tx in response["result"]:
                        tx_hash = tx["hash"]
                        from_addr = tx["from"].lower()
                        to_addr = tx["to"].lower()
                        value = int(tx["value"]) / (10 ** 18)

                        # Cek apakah transaksi sudah dikirim sebelumnya
                        if tx_hash in seen_transactions:
                            continue
                        seen_transactions.add(tx_hash)

                        # Tentukan jenis transaksi
                        if from_addr == address:
                            msg_type = "Send" if value > 0 else "Sell NFT"
                        elif to_addr == address:
                            msg_type = "Receive" if value > 0 else "Buy NFT"
                        else:
                            continue  # Abaikan transaksi yang tidak relevan

                        # Kirim notifikasi ke Telegram
                        message = f"🔔 **{msg_type} Alert!**\n\n"
                        message += f"💳 Address: `{name}`\n"
                        message += f"🔍 Tx Hash: `{tx_hash}`\n"
                        message += f"💰 Amount: `{value} SONE`\n"
                        await bot.send_message(chat_id, message)

            except Exception as e:
                print(f"⚠️ Error fetching transactions: {e}")

        await asyncio.sleep(30)  # Cek transaksi setiap 30 detik

# 🔥 Jalankan Bot
async def main():
    asyncio.create_task(check_transactions())  # Jalankan pengecekan transaksi di background
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
