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

class CalculatorSlashCommands(commands.GroupCog, name="calculate"):
    def __init__(self, bot):
        self.bot = bot
        super().__init__()
    
    # New interactive slash command
    @app_commands.command(
        name="workflow",
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
    
    async def show_model_selection(self, interaction: discord.Interaction, period: str, shift: str, role: discord.Role, gross_revenue: Decimal):
        """Fifth step: Model selection"""
        guild_id = str(interaction.guild_id)
        # Load models data
        models_data = await file_handlers.load_json(settings.MODELS_DATA_FILE, settings.DEFAULT_MODELS_DATA)

        valid_models = models_data.get(guild_id, [])
        
        if not valid_models:
            await interaction.response.send_message("❌ No models configured! Admins: use !set-model.", ephemeral=True)
            return
        
        # Create model selection view
        view = ModelSelectionView(self, valid_models, period, shift, role, gross_revenue)
        await interaction.response.edit_message(content="Select models (optional, you can select multiple):", view=view)

    async def preview_calculation(self, interaction: discord.Interaction, period: str, shift: str, role: discord.Role, 
                                gross_revenue: Decimal, selected_models: List[str]):
        """Preview calculation and show confirmation options"""
        guild_id = str(interaction.guild_id)
        
        # Get role percentage from configuration
        role_data = await file_handlers.load_json(settings.ROLE_DATA_FILE, settings.DEFAULT_ROLE_DATA)
        percentage = Decimal(str(role_data[guild_id][str(role.id)]))
        
        # Load bonus rules
        bonus_rules = await file_handlers.load_json(settings.BONUS_RULES_FILE, settings.DEFAULT_BONUS_RULES)
        guild_bonus_rules = bonus_rules.get(guild_id, [])
        
        # Convert to proper Decimal objects for calculations
        bonus_rule_objects = []
        for rule in guild_bonus_rules:
            rule_obj = {
                "from": Decimal(str(rule.get("from", 0))),
                "to": Decimal(str(rule.get("to", 0))),
                "amount": Decimal(str(rule.get("amount", 0)))
            }
            bonus_rule_objects.append(rule_obj)
        
        # Calculate earnings
        results = calculations.calculate_earnings(
            gross_revenue,
            percentage,
            bonus_rule_objects
        )
        
        # Process models
        models_list = ", ".join(selected_models) if selected_models else ""
        
        # Create embed for preview
        embed = discord.Embed(title="📊 Earnings Calculation (PREVIEW)", color=0x009933)
        current_date = datetime.now().strftime(settings.DATE_FORMAT)
        sender = interaction.user.mention
        
        # Add fields to embed
        fields = [
            ("📅 Date", current_date, True),
            ("✍ Sender", sender, True),
            ("📥 Shift", shift, True),
            ("🎯 Role", role.name, True),
            ("⌛ Period", period, True),
            ("💰 Gross Revenue", f"${float(results['gross_revenue']):,.2f}", True),
            ("💵 Net Revenue", f"${float(results['net_revenue']):,.2f} (80%)", True),
            ("🎁 Bonus", f"${float(results['bonus']):,.2f}", True),
            ("💰 Total Cut", f"${float(results['total_cut']):,.2f}", True),
            ("🎭 Models", models_list, False)
        ]
        
        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)
        
        # Create confirmation view
        view = ConfirmationView(
            self, 
            period, 
            shift, 
            role,
            gross_revenue, 
            selected_models,
            results
        )
        
        await interaction.followup.send(content="Please review your calculation and confirm:", embed=embed, view=view, ephemeral=True)
        await interaction.edit_original_response(content="Preview ready! Please check the new message to confirm your calculation.", view=None)

    async def finalize_calculation(self, interaction: discord.Interaction, period: str, shift: str, role: discord.Role, 
                                gross_revenue: Decimal, selected_models: List[str], results: Dict):
        """Final step: Save and display results to everyone"""
        guild_id = str(interaction.guild_id)
        
        # Save earnings data
        sender = interaction.user.mention
        current_date = datetime.now().strftime(settings.DATE_FORMAT)
        
        # Process models
        models_list = ", ".join(selected_models) if selected_models else ""
        
        # Load earnings data
        earnings_data = await file_handlers.load_json(settings.EARNINGS_FILE, settings.DEFAULT_EARNINGS)
        if sender not in earnings_data:
            earnings_data[sender] = []
        
        # Add new entry
        earnings_data[sender].append({
            "date": current_date,
            "total_cut": float(results["total_cut"]),
            "gross_revenue": float(results["gross_revenue"]),
            "period": period.lower(),
            "shift": shift,
            "role": role.name,
            "models": models_list
        })
        
        # Save updated earnings data
        success = await file_handlers.save_json(settings.EARNINGS_FILE, earnings_data)
        if not success:
            logger.error(f"Failed to save earnings data for {sender}")
            await interaction.followup.send("⚠ Calculation failed to save data. Please try again.", ephemeral=True)
            return
        
        # Create embed for public announcement
        embed = discord.Embed(title="📊 Earnings Calculation", color=0x009933)
        
        # Add fields to embed
        fields = [
            ("📅 Date", current_date, True),
            ("✍ Sender", sender, True),
            ("📥 Shift", shift, True),
            ("🎯 Role", role.name, True),
            ("⌛ Period", period, True),
            ("💰 Gross Revenue", f"${float(results['gross_revenue']):,.2f}", True),
            ("💵 Net Revenue", f"${float(results['net_revenue']):,.2f} (80%)", True),
            ("🎁 Bonus", f"${float(results['bonus']):,.2f}", True),
            ("💰 Total Cut", f"${float(results['total_cut']):,.2f}", True),
            ("🎭 Models", models_list, False)
        ]
        
        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)
        
        # Send the final result to everyone (non-ephemeral)
        await interaction.channel.send(embed=embed)
        
        # Confirm to the user
        await interaction.response.edit_message(content="✅ Calculation confirmed and posted!", embed=None, view=None)

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

class ModelSelectionView(ui.View):
    def __init__(self, cog, models, period, shift, role, gross_revenue):
        super().__init__(timeout=180)
        self.cog = cog
        self.period = period
        self.shift = shift
        self.role = role
        self.gross_revenue = gross_revenue
        self.selected_models = []
        
        # Add a button for each model
        for model in models[:23]:  # Max 23 to leave room for Finish and Clear buttons
            button = ui.Button(label=model, style=discord.ButtonStyle.secondary)
            button.callback = lambda i, m=model: self.on_model_toggled(i, m)
            self.add_item(button)
        
        # Add Continue button
        Continue = ui.Button(label="Continue", style=discord.ButtonStyle.success, row=4)
        Continue.callback = self.on_finish
        self.add_item(Continue)
        
        # Add Clear button
        clear_button = ui.Button(label="Clear Selections", style=discord.ButtonStyle.danger, row=4)
        clear_button.callback = self.on_clear
        self.add_item(clear_button)
    
    async def on_model_toggled(self, interaction: discord.Interaction, model: str):
        # Toggle model selection
        if model in self.selected_models:
            self.selected_models.remove(model)
            # Change button style to show it's not selected
            for item in self.children:
                if isinstance(item, ui.Button) and item.label == model:
                    item.style = discord.ButtonStyle.secondary
        else:
            self.selected_models.append(model)
            # Change button style to show it's selected
            for item in self.children:
                if isinstance(item, ui.Button) and item.label == model:
                    item.style = discord.ButtonStyle.primary
        
        selected_text = ", ".join(self.selected_models) if self.selected_models else "None"
        await interaction.response.edit_message(
            content=f"Select models (optional, you can select multiple):\nSelected: {selected_text}", 
            view=self
        )
    
    async def on_clear(self, interaction: discord.Interaction):
        # Clear all selections
        self.selected_models = []
        
        # Reset all model buttons to not selected state
        for item in self.children:
            if isinstance(item, ui.Button) and item.label not in ["Continue", "Clear Selections"]:
                item.style = discord.ButtonStyle.secondary
        
        await interaction.response.edit_message(
            content="Select models (optional, you can select multiple):\nSelected: None", 
            view=self
        )
    
    async def on_finish(self, interaction: discord.Interaction):
        await interaction.response.defer()
        # Instead of finalizing, show preview with confirmation options
        await self.cog.preview_calculation(
            interaction, 
            self.period, 
            self.shift, 
            self.role, 
            self.gross_revenue, 
            self.selected_models
        )

class ConfirmationView(ui.View):
    def __init__(self, cog, period, shift, role, gross_revenue, selected_models, results):
        super().__init__(timeout=180)
        self.cog = cog
        self.period = period
        self.shift = shift
        self.role = role
        self.gross_revenue = gross_revenue
        self.selected_models = selected_models
        self.results = results
        
        # Add confirm button
        confirm_button = ui.Button(label="Confirm & Post", style=discord.ButtonStyle.success)
        confirm_button.callback = self.on_confirm
        self.add_item(confirm_button)
        
        # Add retry button
        # retry_button = ui.Button(label="Retry Workflow", style=discord.ButtonStyle.primary)
        # retry_button.callback = self.on_retry
        # self.add_item(retry_button)
        
        # Add cancel button
        cancel_button = ui.Button(label="Cancel", style=discord.ButtonStyle.danger)
        cancel_button.callback = self.on_cancel
        self.add_item(cancel_button)
    
    async def on_confirm(self, interaction: discord.Interaction):
        # Finalize and post the calculation to everyone
        await self.cog.finalize_calculation(
            interaction,
            self.period,
            self.shift,
            self.role,
            self.gross_revenue,
            self.selected_models,
            self.results
        )
    
    # async def on_retry(self, interaction: discord.Interaction):
    #     # Start the workflow from the beginning
    #     await interaction.response.edit_message(content="Restarting workflow...", embed=None, view=None)
    #     await self.cog.start_period_selection(interaction)
    
    async def on_cancel(self, interaction: discord.Interaction):
        # Just cancel the workflow
        await interaction.response.edit_message(content="Calculation cancelled.", embed=None, view=None)

async def setup(bot):
    await bot.add_cog(CalculatorSlashCommands(bot))