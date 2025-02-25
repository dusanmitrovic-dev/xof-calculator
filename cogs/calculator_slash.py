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

class CalculatorSlashCommands(commands.GroupCog, name="calculator_slash"):
    def __init__(self, bot):
        self.bot = bot
        super().__init__()
    
    # New interactive slash command
    @app_commands.command(
        name="calculate-workflow",
        description="Calculate earnings using an interactive wizard"
    )
    async def calculate_slash(self, interaction: discord.Interaction):
        """Interactive workflow to calculate earnings"""
        
        # Start the interactive workflow
        await self.start_period_selection(interaction)


async def setup(bot):
    await bot.add_cog(CalculatorSlashCommands(bot))