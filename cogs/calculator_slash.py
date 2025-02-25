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

    async def start_period_selection(self, interaction: discord.Interaction):
        """First step: Period selection"""
        guild_id = str(interaction.guild_id)
        
        # Load period data
        period_data = await file_handlers.load_json(settings.PERIOD_DATA_FILE, settings.DEFAULT_PERIOD_DATA)
        valid_periods = period_data.get(guild_id, [])
        
        if not valid_periods:
            await interaction.response.send_message("❌ No periods configured! Admins: use !calculateperiodset.", ephemeral=True)
            return
        
        # Create period selection view
        view = PeriodSelectionView(self, valid_periods)
        await interaction.response.send_message("Select a period:", view=view, ephemeral=True)

class PeriodSelectionView(ui.View):
    def __init__(self, cog, periods):
        super().__init__(timeout=180)
        self.cog = cog
        
        # Add a button for each period (limit to 25 due to Discord UI limitations)
        for period in periods[:25]:
            button = ui.Button(label=period, style=discord.ButtonStyle.primary)
            button.callback = lambda i, p=period: self.on_period_selected(i, p)
            self.add_item(button)
    
    async def on_period_selected(self, interaction: discord.Interaction, period: str):
        await self.cog.show_shift_selection(interaction, period)

async def setup(bot):
    await bot.add_cog(CalculatorSlashCommands(bot))