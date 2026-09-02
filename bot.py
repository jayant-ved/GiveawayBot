import os
import certifi
import random
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv 

load_dotenv() 

# Force Python and aiohttp to use the installed certificates
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()


# Helper function to read list files
def load_names(filename):
    if not os.path.exists(filename):
        return []
    with open(filename, 'r', encoding='utf-8') as file:
        return [line.strip() for line in file if line.strip()]

# Initialize Bot
intents = discord.Intents.default()
intents.message_content = True  # Tells code to use the Message Content Intent
intents.members = True          # Tells code to use the Server Members Intent

bot = commands.Bot(command_prefix="!", intents=intents)

# Sync Slash Commands on Startup
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Bot is online as {bot.user}")

# Define the /giveaway Command
@bot.tree.command(name="giveaway", description="Draw a winner based on weighted entries!")
@app_commands.checks.has_permissions(administrator=True)  # Only admins can run this
async def giveaway(interaction: discord.Interaction):
    # Load member files from current directory
    all_members = load_names('all_members.txt')
    tier1_bonus = load_names('tier1.txt')
    tier2_bonus = load_names('tier2.txt')
    tier3_bonus = load_names('tier3.txt')
    tier4_bonus = load_names('tier4.txt')

    if not all_members:
        await interaction.response.send_message("❌ Error: No members found in `all_members.txt`.", ephemeral=True)
        return

    participants = []
    weights = []

    for member in all_members:
        participants.append(member)
        if member in tier1_bonus:
            weights.append(5)  # 1 base + 4 bonus
        elif member in tier2_bonus:
            weights.append(4)  # 1 base + 3 bonus
        elif member in tier3_bonus:
            weights.append(3)  # 1 base + 2 bonus
        elif member in tier4_bonus:
            weights.append(2)  # 1 base + 1 bonus
        else:
            weights.append(1)  # 1 base entry

    winner = random.choices(participants, weights=weights, k=1)[0]

    embed = discord.Embed(
        title="🎉 Giveaway Result 🎉",
        description=f"Congratulations to **{winner}** for winning the giveaway!",
        color=discord.Color.gold()
    )
    embed.add_field(name="Total Participants", value=str(len(participants)), inline=True)
    embed.set_footer(text="Weighted random draw completed.")

    await interaction.response.send_message(embed=embed)

# Run the bot
TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
