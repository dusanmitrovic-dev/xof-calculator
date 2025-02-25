import os
import logging
import discord
import asyncio

from discord import ui, app_commands
from config import settings
from decimal import Decimal
from datetime import datetime
from discord.ext import commands
from typing import Optional, List, Dict
from utils import file_handlers, validators, calculations

logger = logging.getLogger("xof_calculator.calculator")

class CalculatorCommands(commands.GroupCog, name="calculator"):
    def __init__(self, bot):
        self.bot = bot
        super().__init__()

async def setup(bot):
    await bot.add_cog(CalculatorCommands(bot))