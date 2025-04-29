import discord
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# --- Google Sheets Setup ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(os.getenv('GOOGLE_CREDENTIALS_PATH'), scope)
client = gspread.authorize(creds)
sheet = client.open("expenses").sheet1  # Assumes first sheet

# --- Discord Bot Setup ---
intents = discord.Intents.default()
intents.messages = True
client_bot = discord.Client(intents=intents)

@client_bot.event
async def on_ready():
    print(f'Bot logged in as {client_bot.user}')

@client_bot.event
async def on_message(message):
    if message.author == client_bot.user:
        return

    if isinstance(message.channel, discord.channel.DMChannel):  # Only respond to DMs
        try:
            # Expected format: "Item, Amount"
            item, amount = message.content.split(",", 1)
            item = item.strip()
            amount = amount.strip()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sheet.append_row([now, item, amount])
            await message.channel.send(f"Saved: {item} - {amount}")
        except Exception as e:
            await message.channel.send("Invalid format. Use: `Item, Amount`")

# --- Start Bot ---
client_bot.run(os.getenv("DISCORD_TOKEN"))
