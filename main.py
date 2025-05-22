import os
import logging
import discord
import asyncio
import traceback

from dotenv import load_dotenv
from pymongo import MongoClient
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

class BotInstance:
    def __init__(self, token, mongo_uri):
        self.token = token
        self.mongo_uri = mongo_uri
        self.mongo_client = None
        self.database = None
        self.bot = None

    async def setup_hook(self):
        """Initialize bot instance with all handlers and extensions"""
        # Initialize MongoDB connection
        if self.mongo_uri:
            try:
                self.mongo_client = MongoClient(self.mongo_uri)
                self.database = self.mongo_client.get_database()
                logger.info(f"Connected to MongoDB for bot with token: {self.token[:5]}...")
            except Exception as e:
                logger.error(f"Failed to connect to MongoDB for bot: {e}")

        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True

        self.bot = commands.Bot(command_prefix='!', intents=intents)
        self.register_events()
        await self.load_extensions()

    def register_events(self):
        """Register event handlers for the bot instance"""
        @self.bot.event
        async def on_ready():
            logger.info(f"Bot is online as {self.bot.user}")
            await self.bot.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.watching,
                    name="shift calculations"
                )
            )

            try:
                synced = await self.bot.tree.sync()
                logger.info(f"Slash commands synced for {self.bot.user}! {len(synced)} commands")
            except Exception as e:
                logger.error(f"Failed to sync slash commands for {self.bot.user}: {e}")

            for guild in self.bot.guilds:
                logger.info(f"{self.bot.user} connected to guild: {guild.name} (ID: {guild.id})")

        @self.bot.event
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
            
            logger.error(f"[{self.bot.user}] Command error in {ctx.command}: {error}")
            logger.error(traceback.format_exc())
            await ctx.send("❌ An error occurred while processing your command. The error has been logged.")

        @self.bot.tree.error
        async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
            if isinstance(error, app_commands.CommandOnCooldown):
                await interaction.response.send_message(
                    f"❌ This command is on cooldown. Try again in {error.retry_after:.2f} seconds.",
                    ephemeral=True
                )
                return
                
            if isinstance(error, app_commands.MissingPermissions):
                await interaction.response.send_message(
                    "❌ You don't have the required permissions to use this command.",
                    ephemeral=True
                )
                return
                
            if isinstance(error, app_commands.BotMissingPermissions):
                await interaction.response.send_message(
                    f"❌ I'm missing the required permissions: {', '.join(error.missing_permissions)}",
                    ephemeral=True
                )
                return
            
            if isinstance(error, app_commands.CheckFailure):
                await interaction.response.send_message(
                    "❌ You don't have permission to use this command.",
                    ephemeral=True
                )
                return
                
            logger.error(f"[{self.bot.user}] App command error in {interaction.command.name}: {error}")
            logger.error(traceback.format_exc())
            
            try:
                await interaction.response.send_message(
                    "❌ An error occurred while processing your command. The error has been logged.",
                    ephemeral=True
                )
            except discord.errors.InteractionResponded:
                try:
                    await interaction.followup.send(
                        "❌ An error occurred while processing your command. The error has been logged.",
                        ephemeral=True
                    )
                except:
                    pass

    async def load_extensions(self):
        """Load cogs for this bot instance"""
        for filename in os.listdir("cogs"):
            if filename.endswith(".py") and not filename.startswith("_"):
                try:
                    await self.bot.load_extension(f"cogs.{filename[:-3]}")
                    logger.info(f"Loaded extension {filename[:-3]} for {self.bot.user}")
                except Exception as e:
                    logger.error(f"Failed to load extension {filename[:-3]} for {self.bot.user}: {e}")
                    logger.error(traceback.format_exc())

    async def start(self):
        """Start the bot instance"""
        if not self.token:
            logger.error("Skipping bot instance with empty token")
            return

        try:
            await self.setup_hook()
            await self.bot.start(self.token)
        except Exception as e:
            logger.error(f"Bot instance failed: {e}")
            logger.error(traceback.format_exc())
        finally:
            if self.bot:
                await self.bot.close()
            if self.mongo_client:
                self.mongo_client.close()

async def main():
    # Get all tokens and MongoDB URIs from environment variables
    tokens_and_uris = {
        k.split("_", 2)[-1]: (v, os.getenv(f"MONGODB_URI_{k.split('_', 2)[-1]}"))
        for k, v in os.environ.items() if k.startswith("DISCORD_TOKEN_")
    }

    print("Tokens and URIs:", tokens_and_uris)  # Debugging line

    if not tokens_and_uris:
        logger.critical("No Discord tokens or MongoDB URIs found. Please update your .env file.")
        return

    logger.info(f"Starting {len(tokens_and_uris)} bot instances...")

    # Create and start all bot instances
    bots = [
        BotInstance(token, mongo_uri)
        for _, (token, mongo_uri) in tokens_and_uris.items()
    ]
    await asyncio.gather(*(bot.start() for bot in bots))

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bots were shut down manually")
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        logger.critical(traceback.format_exc())