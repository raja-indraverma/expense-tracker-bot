import discord
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from dotenv import load_dotenv
import os
from dateutil.relativedelta import relativedelta

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

# Define categories for the dropdown
categories = ["Food", "Transport", "Entertainment", "Groceries", "Other"]

# This class handles the dropdown (select menu)
class CategorySelect(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=category, value=category) for category in categories]
        super().__init__(placeholder="Choose a category...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        # Store the selected category
        selected_category = self.values[0]
        await interaction.response.send_message(f'Category selected: {selected_category}')
        # Prompt the user for the item and amount
        await interaction.followup.send("Now, please enter the expense in the format: `Item, Amount`.")
        
        # Wait for the user to input the item and amount
        def check(msg):
            return msg.author == interaction.user and isinstance(msg.channel, discord.channel.DMChannel)

        try:
            response = await client_bot.wait_for('message', check=check)
            item, amount = response.content.split(",", 1)
            item = item.strip()
            amount = amount.strip()

            # Get the current date and time
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Append the data to the Google Sheet
            sheet.append_row([now, selected_category, item, amount])

            await interaction.followup.send(f"Expense saved: {item} - {amount} in category {selected_category}.")
        except Exception as e:
            await interaction.followup.send("Invalid format. Please use: `Item, Amount`.")

# View that holds the category selection dropdown
class CategoryDropdownView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(CategorySelect())

        from dateutil.relativedelta import relativedelta

class TimePeriodSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="1 Month", value="1"),
            discord.SelectOption(label="2 Months", value="2"),
            discord.SelectOption(label="6 Months", value="6"),
            discord.SelectOption(label="All Time", value="all"),
        ]
        super().__init__(placeholder="Select time period for summary...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        try:
            selected_value = self.values[0]
            now = datetime.now()

            if selected_value == "all":
                cutoff = None
            else:
                cutoff = now - relativedelta(months=int(selected_value))

            records = sheet.get_all_records()
            category_totals = {}

            for row in records:
                date_str = row.get("Date")
                try:
                    row_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                except:
                    continue  # skip malformed dates

                if cutoff and row_date < cutoff:
                    continue

                category = row.get("Category")
                try:
                    amount = float(row.get("Amount", 0))
                except:
                    continue

                if category:
                    category_totals[category] = category_totals.get(category, 0) + amount

            if not category_totals:
                await interaction.response.send_message("No expenses found for this period.")
                return

            summary_text = f"**Summary for last {selected_value if selected_value != 'all' else 'All Time'}:**\n"
            for category, total in category_totals.items():
                summary_text += f"- **{category}**: {total:.2f}\n"

            await interaction.response.send_message(summary_text)

        except Exception as e:
            await interaction.response.send_message(f"Error generating summary: {e}")

class TimePeriodDropdownView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(TimePeriodSelect())




@client_bot.event
async def on_ready():
    print(f'Bot logged in as {client_bot.user}')

@client_bot.event
@client_bot.event
async def on_message(message):
    if message.author == client_bot.user:
        return

    if isinstance(message.channel, discord.channel.DMChannel):
        if message.content.startswith("!add"):
            await message.channel.send(
                "Please select a category for your expense:",
                view=CategoryDropdownView()
            )

        elif message.content.startswith("!summary"):
            await message.channel.send("Select the time period you'd like a summary for:", view=TimePeriodDropdownView())


        else:
            await message.channel.send("Use `!add` to add an expense or `!summary` to view totals.")


# --- Start Bot ---
client_bot.run(os.getenv("DISCORD_TOKEN"))
