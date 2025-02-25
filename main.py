import os
import logging
import discord
import asyncio
import traceback

from dotenv import load_dotenv
from discord.ext import commands
from discord import app_commands
from logging.handlers import RotatingFileHandler

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[ 
        RotatingFileHandler( 
            "logs/bot.log", 
            maxBytes=5*1024*1024,  # 5 MB 
            backupCount=5
        ), 
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("xof_calculator")

# Load environment variables
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    logger.critical("No Discord token found. Please create a .env file with your DISCORD_TOKEN.")
    exit(1)

# Bot setup
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Global error handler
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument: {error.param.name}")
        return
    
    if isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Invalid argument: {str(error)}")
        return
    
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have the required permissions to use this command.")
        return
    
    if isinstance(error, commands.BotMissingPermissions):
        await ctx.send(f"❌ I'm missing the required permissions: {', '.join(error.missing_permissions)}")
        return
    
    # Log the full error with traceback
    logger.error(f"Command error in {ctx.command}: {error}")
    logger.error(traceback.format_exc())
    
    # Notify the user
    await ctx.send("❌ An error occurred while processing your command. The error has been logged.")

# Error handler for app commands (slash commands)
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(f"❌ This command is on cooldown. Try again in {error.retry_after:.2f} seconds.", ephemeral=True)
        return
        
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ You don't have the required permissions to use this command.", ephemeral=True)
        return
        
    if isinstance(error, app_commands.BotMissingPermissions):
        await interaction.response.send_message(f"❌ I'm missing the required permissions: {', '.join(error.missing_permissions)}", ephemeral=True)
        return
    
    # Handle check failures
    if isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        return
        
    # Log the full error with traceback
    logger.error(f"App command error in {interaction.command.name}: {error}")
    logger.error(traceback.format_exc())
        
    # Try to respond if not already responded
    try:
        await interaction.response.send_message("❌ An error occurred while processing your command. The error has been logged.", ephemeral=True)
    except discord.errors.InteractionResponded:
        # If already responded, try to send a followup
        try:
            await interaction.followup.send("❌ An error occurred while processing your command. The error has been logged.", ephemeral=True)
        except:
            pass

# Load cogs
async def load_extensions():
    for filename in os.listdir("cogs"):
        if filename.endswith(".py") and not filename.startswith("_"):
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                logger.info(f"Loaded extension: {filename[:-3]}")
            except Exception as e:
                logger.error(f"Failed to load extension {filename[:-3]}: {e}")
                logger.error(traceback.format_exc())

@bot.event
async def on_ready():
    logger.info(f"Bot is online as {bot.user}")
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching,
        name="shift calculations"
    ))

    # Sync slash commands with Discord
    try:
        synced = await bot.tree.sync()
        logger.info(f"Slash commands synced! {len(synced)} commands")
    except Exception as e:
        logger.error(f"Failed to sync slash commands: {e}")

    # Log server info
    for guild in bot.guilds:
        logger.info(f"Connected to guild: {guild.name} (ID: {guild.id})")

# Run the bot
async def main():
    async with bot:
        await load_extensions()
        await bot.start(TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot was shut down manually")
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        logger.critical(traceback.format_exc())
