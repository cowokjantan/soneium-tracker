import os
import asyncio
import json
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
import aiohttp

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_URL = "https://blockscout.soneium.io/api"
DATA_FILE = "tracked_addresses.json"  # File untuk menyimpan data

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Load data yang tersimpan
def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

# Simpan data ke file
def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(tracked_addresses, f)

tracked_addresses = load_data()  # {chat_id: [address1, address2, ...]}
last_tx_hashes = {}

async def get_latest_transaction(address):
    url = f"{API_URL}?module=account&action=txlist&address={address}&sort=desc"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                transactions = data.get("result", [])
                return transactions[0] if transactions else None
    return None

async def send_transaction_notification(chat_id, tx_data):
    tx_hash = tx_data["hash"]
    from_address = tx_data["from"]
    to_address = tx_data["to"]
    value = int(tx_data["value"]) / 10**18
    message_type = "SEND" if chat_id in tracked_addresses and from_address in tracked_addresses[str(chat_id)] else "RECEIVE"

    if "input" in tx_data and tx_data["input"].startswith("0xa9059cbb"):
        message_type = "BUY"

    message = f"🔔 *{message_type} TRANSACTION DETECTED!*\n\n"
    message += f"🔹 *From:* `{from_address}`\n"
    message += f"🔹 *To:* `{to_address}`\n"
    message += f"💰 *Amount:* {value} Soneium\n"
    message += f"🔗 [View on Explorer](https://blockscout.soneium.io/tx/{tx_hash})"

    await bot.send_message(chat_id, message, parse_mode="Markdown")

async def check_transactions():
    while True:
        for chat_id, addresses in list(tracked_addresses.items()):
            for address in list(addresses):
                tx_data = await get_latest_transaction(address)
                if tx_data:
                    tx_hash = tx_data["hash"]
                    if last_tx_hashes.get(address) != tx_hash:
                        last_tx_hashes[address] = tx_hash
                        await send_transaction_notification(chat_id, tx_data)
        await asyncio.sleep(10)

@dp.message(commands=["start"])
async def start_handler(message: Message):
    chat_id = str(message.chat.id)
    if chat_id in tracked_addresses and tracked_addresses[chat_id]:
        addresses_list = "\n".join(tracked_addresses[chat_id])
        await message.answer(f"👋 Anda sudah melacak alamat berikut:\n\n{addresses_list}\n\nKirim alamat baru untuk menambah!")
    else:
        await message.answer("👋 Selamat datang! Kirim alamat dompet yang ingin Anda lacak.")

@dp.message()
async def track_address_handler(message: Message):
    chat_id = str(message.chat.id)
    address = message.text.strip()

    if len(address) != 42 or not address.startswith("0x"):
        await message.answer("❌ Alamat tidak valid.")
        return

    if chat_id not in tracked_addresses:
        tracked_addresses[chat_id] = []

    if address not in tracked_addresses[chat_id]:
        tracked_addresses[chat_id].append(address)
        save_data()
        await message.answer(f"✅ Alamat {address} telah ditambahkan!")

async def main():
    dp.include_router(dp.router)
    asyncio.create_task(check_transactions())
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
