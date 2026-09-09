import os
import certifi

os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()

import random
import asyncio
import aiohttp
import re
import discord
import requests
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

# Tokens
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
COC_API_TOKEN = os.getenv("COC_API_TOKEN")

# All clan's tags
CLAN_TAGS = [

    "#RQ2RQ2U9" , "#2YCCGYP2J", "#2LUPRRQG9", "#P9QCJRUQ",
    "#2Y90Q2GJV", "#UVGRR9V2" , "#2VP9PY2U" , "#UQ0L8VVJ",
    "#CGU9PJJJ" , "#QQ0YPJ02" , "#RVJPRLG8" , "#28U9PG0GL",
    "#R92YP9JY" , "#VUU9JJ2V" , "#P28Y08G8" , "#RCUPQPP2",
    "#L0JQVCYL" , "#2LUPRRQG9", "#Q99CG88V"
]

# Function to parse ClashPerk embed description
def parse_clashperk_embed(embed_description: str):
    ranked_names = []
    lines = embed_description.split("\n")

    for line in lines:
        line = line.strip()
        # Matches: [Rank] [Time] [Score] [Player Name]
        match = re.search(r"^\s*(\d+)\s+.*?\s+\d+\s+(.+)$", line)
        if match:
            rank = int(match.group(1))
            name = match.group(2).strip()
            ranked_names.append((rank, name))
            
    ranked_names.sort(key=lambda x: x[0])
    return [name for rank, name in ranked_names]

# Fetches clan members data from CoC API
async def fetch_clan_members(session, clan_tag, headers):
    formatted_tag = clan_tag.strip().replace('#', '%23')
    url = f"https://api.clashofclans.com/v1/clans/{formatted_tag}/members"

    try:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                # UPDATED: Now returns a dict with both name and donations
                return [{"name": member["name"], "tag": member["tag"], "donations": member.get("donations", 0)} for member in data.get("items", [])]
            else:
                print(f"Failed to fetch clan {clan_tag}: Status {response.status}")
                return []
    except Exception as e:
        print(f"Error fetching clan {clan_tag}: {e}")
        return []

# Initializes Bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Slash Commands on Startup
@bot.event
async def on_ready():
    print("MY DISCLOUD IP IS:", requests.get('https://api.ipify.org').text)
    await bot.tree.sync()
    print(f"✅ Bot is online as {bot.user}")

# Define /giveaway Command
@bot.tree.command(name="giveaway", description="Fetch all 20 clans and apply ClashPerk activity bonuses!")
@app_commands.describe(
    channel="The channel where ClashPerk posted the activity list", 
    min_donations="Minimum donation requirement for a member to enter"
)
@app_commands.default_permissions(manage_messages=True)
async def giveaway(interaction: discord.Interaction, channel: discord.TextChannel, min_donations: int = 0):
    await interaction.response.defer()

    if not COC_API_TOKEN:
        await interaction.followup.send("❌ Error: `COC_API_TOKEN` missing in `.env`.", ephemeral=True)
        return

    # Fetches ClashPerk's ranked list from selected channel
    ranked_players = []
    async for message in channel.history(limit=25):
        if message.embeds:
            for embed in message.embeds:
                if (embed.title and "Active Members" in embed.title) or (embed.description and "LAST-ON" in embed.description):
                    ranked_players = parse_clashperk_embed(embed.description)
                    break
            if ranked_players:
                break

    # Fetches all players data across given clans via CoC API concurrently
    headers = {
        "Authorization": f"Bearer {COC_API_TOKEN}",
        "Accept": "application/json"
    }

    async with aiohttp.ClientSession() as session:
        tasks = [fetch_clan_members(session, tag, headers) for tag in CLAN_TAGS]
        results = await asyncio.gather(*tasks)

    all_members = [member for clan in results for member in clan]

    if not all_members:
        await interaction.followup.send("❌ Error: Could not fetch members from Clash of Clans API.")
        return

    # Maps player names to their rank (Rank 1 to 99)
    rank_map = {name: rank + 1 for rank, name in enumerate(ranked_players)}

    participants = []
    weights = []

    # Assigns base entry + bonus entries and also filters donation count of members
    for member_data in all_members:
        name = member_data["name"]
        tag = member_data["tag"]
        donations = member_data["donations"]
        
        if donations < min_donations:
            continue
            
        participants.append((name, tag))
        rank = rank_map.get(name, None)

        if rank and 1 <= rank <= 3:
            weights.append(5) # 4 bonus entries
        elif rank and 4 <= rank <= 10:
            weights.append(4) # 3 bonus entries
        elif rank and 11 <= rank <= 50:
            weights.append(3) # 2 bonus entries
        elif rank and 51 <= rank <= 99:
            weights.append(2) # 1 bonus entry
        else:
            weights.append(1) # 1 base entry

    if not participants:
        await interaction.followup.send(f"❌ No eligible members met the criteria of **{min_donations}+ donations**.")
        return

    winner_name, winner_tag = random.choices(participants, weights=weights, k=1)[0]
    winner_rank = rank_map.get(winner_name)

    # Builds and sends result embed
    embed = discord.Embed(
        title="🎉 Giveaway Result 🎉",
        description=f"Congratulations to **{winner_name} ({winner_tag})** for winning the giveaway!",
        color=discord.Color.gold()
    )
    embed.add_field(name="Clans Scanned", value=str(len(CLAN_TAGS)), inline=True)
    embed.add_field(name="Total Pool", value=f"{len(participants)} players", inline=True)
    
    if min_donations >= 0:
        embed.add_field(name="Donation Requirement", value=f"{min_donations}+ donations", inline=True)
        

    embed.set_footer(text="Live clan data & ClashPerk activity weights calculated.")

    await interaction.followup.send(embed=embed)

# 6. Runs the bot
bot.run(DISCORD_TOKEN)