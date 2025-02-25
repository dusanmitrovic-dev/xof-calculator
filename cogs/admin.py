import discord
from discord.ext import commands
from decimal import Decimal
import logging
from typing import Optional

from config import settings
from utils import file_handlers, validators

logger = logging.getLogger("fox_calculator.admin")

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    async def cog_check(self, ctx):
        """Check if user has administrator permissions for all commands in this cog"""
        return ctx.author.guild_permissions.administrator
