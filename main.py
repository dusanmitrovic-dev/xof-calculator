import os
import logging
import discord
import asyncio
import traceback
import threading
import signal
import time

from dotenv import load_dotenv
from discord.ext import commands
from discord import app_commands
from logging.handlers import RotatingFileHandler
from concurrent.futures import ThreadPoolExecutor

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

# Global flag for shutdown
shutdown_flag = threading.Event()

class BotInstance:
    def __init__(self, token, instance_id):
        self.token = token
        self.instance_id = instance_id
        self.bot = None
        self.thread = None
        self.loop = None
        
    def run_bot_in_thread(self):
        """This method will be executed in a separate thread"""
        thread_name = f"BotThread-{self.instance_id}"
        threading.current_thread().name = thread_name
        logger.info(f"Starting bot in thread: {thread_name}")
        
        # Create a new event loop for this thread
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        try:
            # Run the setup and start the bot in this thread's event loop
            self.loop.run_until_complete(self.setup_and_start())
        except Exception as e:
            logger.error(f"Bot instance {self.instance_id} failed: {e}")
            logger.error(traceback.format_exc())
        finally:
            self.loop.close()
            logger.info(f"Thread {thread_name} finished")
            
    async def setup_and_start(self):
        """Setup and start the bot within this thread's event loop"""
        await self.setup_hook()
        
        # Create a task to check for shutdown signal
        shutdown_task = asyncio.create_task(self.check_shutdown())
        
        try:
            # Start the bot
            await self.bot.start(self.token)
        except asyncio.CancelledError:
            logger.info(f"Bot instance {self.instance_id} received cancellation")
        finally:
            if not shutdown_task.done():
                shutdown_task.cancel()
            
            if self.bot and self.bot.is_ready():
                await self.bot.close()
                logger.info(f"Bot instance {self.instance_id} closed gracefully")

    async def check_shutdown(self):
        """Check for shutdown signal in a non-blocking way"""
        while not shutdown_flag.is_set():
            await asyncio.sleep(0.5)
        
        logger.info(f"Bot instance {self.instance_id} detected shutdown signal")
        if self.loop:
            for task in asyncio.all_tasks(self.loop):
                if task is not asyncio.current_task():
                    task.cancel()

    async def setup_hook(self):
        """Initialize bot instance with all handlers and extensions"""
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
            logger.info(f"Bot is online as {self.bot.user} in thread {threading.current_thread().name}")
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

        # Other event handlers remain the same as in your original code
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

    def start_in_thread(self):
        """Start the bot instance in a separate thread"""
        if not self.token:
            logger.error(f"Skipping bot instance {self.instance_id} with empty token")
            return None
        
        self.thread = threading.Thread(target=self.run_bot_in_thread)
        self.thread.daemon = True  # Thread will exit when main program exits
        self.thread.start()
        return self.thread

def signal_handler(sig, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {sig}, initiating shutdown...")
    shutdown_flag.set()

def main():
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Termination signal
    
    # Get all tokens from environment variables starting with DISCORD_TOKEN_
    token_pairs = [(k, v) for k, v in os.environ.items() if k.startswith("DISCORD_TOKEN_")]
    
    if not token_pairs:
        logger.critical("No Discord tokens found. Please create .env entries with DISCORD_TOKEN_ prefix.")
        return

    logger.info(f"Starting {len(token_pairs)} bot instances in separate threads...")
    
    # Create and start all bot instances in separate threads
    bot_instances = []
    threads = []
    
    for i, (token_name, token) in enumerate(token_pairs):
        instance = BotInstance(token, i+1)
        bot_instances.append(instance)
        thread = instance.start_in_thread()
        if thread:
            threads.append(thread)
            logger.info(f"Started bot instance {i+1} using token from {token_name}")
    
    # Add a command-line interface for manual shutdown
    logger.info("All bots started. Press Ctrl+C to shutdown gracefully")
    
    # Wait for all threads to complete or for shutdown signal
    try:
        while not shutdown_flag.is_set() and any(thread.is_alive() for thread in threads):
            time.sleep(0.5)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, setting shutdown flag...")
        shutdown_flag.set()
    
    # Give bots time to shut down gracefully
    logger.info("Waiting for all bot threads to shut down...")
    shutdown_timeout = 10  # seconds
    shutdown_start = time.time()
    
    while any(thread.is_alive() for thread in threads) and time.time() - shutdown_start < shutdown_timeout:
        time.sleep(0.5)
    
    # Check if any threads are still alive
    alive_threads = [i+1 for i, thread in enumerate(threads) if thread.is_alive()]
    if alive_threads:
        logger.warning(f"Some bot threads did not shut down gracefully: {alive_threads}")
    else:
        logger.info("All bot threads shut down successfully")
    
    logger.info("Shutdown complete")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        logger.critical(traceback.format_exc())