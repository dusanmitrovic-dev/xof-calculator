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
    
    async def show_shift_selection(self, interaction: discord.Interaction, period: str):
        """Second step: Shift selection"""
        guild_id = str(interaction.guild_id)
        
        # Load shift data
        shift_data = await file_handlers.load_json(settings.SHIFT_DATA_FILE, settings.DEFAULT_SHIFT_DATA)
        valid_shifts = shift_data.get(guild_id, [])
        
        if not valid_shifts:
            await interaction.response.send_message("❌ No shifts configured! Admins: use !calculateshiftset.", ephemeral=True)
            return
        
        # Create shift selection view
        view = ShiftSelectionView(self, valid_shifts, period)
        await interaction.response.edit_message(content="Select a shift:", view=view)
    
    async def show_role_selection(self, interaction: discord.Interaction, period: str, shift: str):
        """Third step: Role selection"""
        guild_id = str(interaction.guild_id)
        
        # Load role data
        role_data = await file_handlers.load_json(settings.ROLE_DATA_FILE, settings.DEFAULT_ROLE_DATA)
        
        if guild_id not in role_data or not role_data[guild_id]:
            await interaction.response.edit_message(content="❌ No roles configured! Admins: use !calculateroleset.", view=None)
            return
        
        # Get roles for this guild that are in the configuration
        guild_roles = interaction.guild.roles
        configured_roles = []
        
        for role in guild_roles:
            if str(role.id) in role_data[guild_id]:
                configured_roles.append(role)
        
        if not configured_roles:
            await interaction.response.edit_message(content="❌ No roles configured! Admins: use !calculateroleset.", view=None)
            return
        
        # Create role selection view
        view = RoleSelectionView(self, configured_roles, period, shift)
        await interaction.response.edit_message(content="Select a role:", view=view)
    
    async def show_revenue_input(self, interaction: discord.Interaction, period: str, shift: str, role: discord.Role):
        """Fourth step: Revenue input"""
        # Create revenue input modal
        modal = RevenueInputModal(self, period, shift, role)
        await interaction.response.send_modal(modal)

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

class ShiftSelectionView(ui.View):
    def __init__(self, cog, shifts, period):
        super().__init__(timeout=180)
        self.cog = cog
        self.period = period
        
        # Add a button for each shift
        for shift in shifts[:25]:
            button = ui.Button(label=shift, style=discord.ButtonStyle.primary)
            button.callback = lambda i, s=shift: self.on_shift_selected(i, s)
            self.add_item(button)
    
    async def on_shift_selected(self, interaction: discord.Interaction, shift: str):
        await self.cog.show_role_selection(interaction, self.period, shift)

class RoleSelectionView(ui.View):
    def __init__(self, cog, roles, period, shift):
        super().__init__(timeout=180)
        self.cog = cog
        self.period = period
        self.shift = shift
        
        # Add a button for each role
        for role in roles[:25]:
            button = ui.Button(label=role.name, style=discord.ButtonStyle.primary)
            button.callback = lambda i, r=role: self.on_role_selected(i, r)
            self.add_item(button)
    
    async def on_role_selected(self, interaction: discord.Interaction, role: discord.Role):
        await self.cog.show_revenue_input(interaction, self.period, self.shift, role)

class RevenueInputModal(ui.Modal, title="Enter Gross Revenue"):
    def __init__(self, cog, period, shift, role):
        super().__init__()
        self.cog = cog
        self.period = period
        self.shift = shift
        self.role = role
        
        self.revenue_input = ui.TextInput(
            label="Gross Revenue (e.g. 1269.69)",
            placeholder="Enter amount...",
            required=True
        )
        self.add_item(self.revenue_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        # Parse revenue input
        revenue_str = self.revenue_input.value
        gross_revenue = validators.parse_money(revenue_str)
        
        if gross_revenue is None:
            await interaction.response.send_message("❌ Invalid revenue format. Please use a valid number.", ephemeral=True)
            return
        
        await self.cog.show_model_selection(interaction, self.period, self.shift, self.role, gross_revenue)

async def setup(bot):
    await bot.add_cog(CalculatorSlashCommands(bot))