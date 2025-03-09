import os
import io
import json
import glob
import shutil
import discord
import logging
import asyncio

from decimal import Decimal
from discord import app_commands
from discord.ext import commands
from typing import Optional
from config import settings
from utils import file_handlers, validators

logger = logging.getLogger("xof_calculator.admin_slash")

class AdminSlashCommands(commands.Cog, name="admin"):
    def __init__(self, bot):
        self.bot = bot

    async def get_ephemeral_setting(self, guild_id):
        display_settings = await file_handlers.load_json(settings.DISPLAY_SETTINGS_FILE, settings.DEFAULT_DISPLAY_SETTINGS)
        guild_settings = display_settings.get(str(guild_id), {})
        return guild_settings.get('ephemeral_responses', True)

    def validate_percentage(self, percentage: Optional[float]) -> bool:
        if percentage is None:
            return True
        return 0 <= percentage <= 100

    def validate_hourly_rate(self, rate: Optional[float]) -> bool:
        if rate is None:
            return True
        return rate >= 0
    
    @app_commands.command(name="set-role-commission")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        role="The role to set commission for",
        percentage="Commission percentage (0-100)"
    )
    async def set_role_commission(
        self, 
        interaction: discord.Interaction, 
        role: discord.Role, 
        percentage: Optional[float] = None
    ):
        """Set commission percentage for a specific role"""
        # Validate input
        if not self.validate_percentage(percentage):
            await interaction.response.send_message(
                "❌ Invalid percentage. Must be between 0 and 100.", 
                ephemeral=True
            )

            return
        
        # Load existing settings
        commission_settings = await file_handlers.load_json(settings.COMMISSION_SETTINGS_FILE, {})
        
        # Ensure guild-specific settings exist
        guild_id = str(interaction.guild.id)
        if guild_id not in commission_settings:
            commission_settings[guild_id] = {"roles": {}, "users": {}}
        
        # Ensure 'roles' key exists
        commission_settings[guild_id].setdefault('roles', {})
        
        # Update role commission_settings
        role_settings = commission_settings[guild_id]['roles'].get(str(role.id), {})
        role_settings['commission_percentage'] = percentage
        commission_settings[guild_id]['roles'][str(role.id)] = role_settings
        
        # Save updated commission_settings
        await file_handlers.save_json(settings.COMMISSION_SETTINGS_FILE, commission_settings)
        
        # Respond with confirmation
        response = f"✅ Set commission for {role.mention} to "
        response += f"{percentage}%" if percentage is not None else "cleared"
        await interaction.response.send_message(response, ephemeral=True)
    
    @app_commands.command(name="set-role-hourly")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        role="The role to set hourly rate for",
        rate="Hourly rate in dollars"
    )
    async def set_role_hourly(
        self, 
        interaction: discord.Interaction, 
        role: discord.Role, 
        rate: Optional[float] = None
    ):
        """Set hourly rate for a specific role"""
        # Validate input
        if not self.validate_hourly_rate(rate):
            await interaction.response.send_message(
                "❌ Invalid hourly rate. Must be a non-negative number.", 
                ephemeral=True
            )
            return
        
        # Load existing settings
        commission_settings = await file_handlers.load_json(settings.COMMISSION_SETTINGS_FILE, {})
        
        # Ensure guild-specific settings exist
        guild_id = str(interaction.guild.id)
        if guild_id not in commission_settings:
            commission_settings[guild_id] = {"roles": {}, "users": {}}
        
        # Ensure 'roles' key exists
        commission_settings[guild_id].setdefault('roles', {})
        
        # Update role settings
        role_settings = commission_settings[guild_id]['roles'].get(str(role.id), {})
        role_settings['hourly_rate'] = rate
        commission_settings[guild_id]['roles'][str(role.id)] = role_settings
        
        # Save updated settings
        await file_handlers.save_json(settings.COMMISSION_SETTINGS_FILE, commission_settings)
        
        # Respond with confirmation
        response = f"✅ Set hourly rate for {role.mention} to "
        response += f"${rate}/h" if rate is not None else "cleared"
        await interaction.response.send_message(response, ephemeral=True)
    
    @app_commands.command(name="set-user-commission")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        user="The user to set commission for",
        percentage="Commission percentage (0-100)",
        override_role="Whether to override role settings"
    )
    async def set_user_commission(
        self, 
        interaction: discord.Interaction, 
        user: discord.User, 
        percentage: Optional[float] = None,
        override_role: bool = False
    ):
        """Set commission percentage for a specific user"""
        # Validate input
        if not self.validate_percentage(percentage):
            await interaction.response.send_message(
                "❌ Invalid percentage. Must be between 0 and 100.", 
                ephemeral=True
            )
            return
        
        # Load existing settings
        commission_settings = await file_handlers.load_json(settings.COMMISSION_SETTINGS_FILE, {})
        
        # Ensure guild-specific settings exist
        guild_id = str(interaction.guild.id)
        if guild_id not in commission_settings:
            commission_settings[guild_id] = {"roles": {}, "users": {}}
        
        # Ensure 'users' key exists
        commission_settings[guild_id].setdefault('users', {})
        
        # Update user settings
        user_settings = commission_settings[guild_id]['users'].get(str(user.id), {})
        user_settings['commission_percentage'] = percentage
        user_settings['override_role'] = override_role
        commission_settings[guild_id]['users'][str(user.id)] = user_settings
        
        # Save updated settings
        await file_handlers.save_json(settings.COMMISSION_SETTINGS_FILE, commission_settings)
        
        # Respond with confirmation
        response = f"✅ Set commission for {user.mention} to "
        response += f"{percentage}%" if percentage is not None else "cleared"
        response += f" (Override Role: {override_role})"
        await interaction.response.send_message(response, ephemeral=True)
    
    @app_commands.command(name="set-user-hourly")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        user="The user to set hourly rate for",
        rate="Hourly rate in dollars",
        override_role="Whether to override role settings"
    )
    async def set_user_hourly(
        self, 
        interaction: discord.Interaction, 
        user: discord.User, 
        rate: Optional[float] = None,
        override_role: bool = False
    ):
        """Set hourly rate for a specific user"""
        # Validate input
        if not self.validate_hourly_rate(rate):
            await interaction.response.send_message(
                "❌ Invalid hourly rate. Must be a non-negative number.", 
                ephemeral=True
            )
            return
        
        # Load existing settings
        commission_settings = await file_handlers.load_json(settings.COMMISSION_SETTINGS_FILE, {})
        
        # Ensure guild-specific settings exist
        guild_id = str(interaction.guild.id)
        if guild_id not in commission_settings:
            commission_settings[guild_id] = {"roles": {}, "users": {}}
        
        # Update user settings
        user_settings = commission_settings[guild_id]['users'].get(str(user.id), {})
        user_settings['hourly_rate'] = rate
        user_settings['override_role'] = override_role
        commission_settings[guild_id]['users'][str(user.id)] = user_settings
        
        # Save updated settings
        await file_handlers.save_json(settings.COMMISSION_SETTINGS_FILE, commission_settings)
        
        # Respond with confirmation
        response = f"✅ Set hourly rate for {user.mention} to "
        response += f"${rate}/h" if rate is not None else "cleared"
        response += f" (Override Role: {override_role})"
        await interaction.response.send_message(response, ephemeral=True)
    
    @app_commands.command(name="toggle-user-role-override")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        user="The user to toggle role override for"
    )
    async def set_user_role_override_toggle(
        self, 
        interaction: discord.Interaction, 
        user: discord.User
    ):
        """Toggle role override for a specific user"""
        # Load existing settings
        commission_settings = await file_handlers.load_json(settings.COMMISSION_SETTINGS_FILE, {})
        
        # Ensure guild-specific settings exist
        guild_id = str(interaction.guild.id)
        if guild_id not in commission_settings:
            await interaction.response.send_message(
                "❌ No commission settings found for this guild.", 
                ephemeral=True
            )
            return
        
        # Ensure user settings exist
        user_settings = commission_settings[guild_id]['users'].get(str(user.id), {})
        if not user_settings:
            await interaction.response.send_message(
                "❌ No commission settings found for this user.", 
                ephemeral=True
            )
            return
        
        # Toggle override_role
        user_settings['override_role'] = not user_settings.get('override_role', False)
        commission_settings[guild_id]['users'][str(user.id)] = user_settings
        
        # Save updated settings
        await file_handlers.save_json(settings.COMMISSION_SETTINGS_FILE, commission_settings)
        
        # Respond with confirmation
        response = f"✅ Toggled role override for {user.mention} to {user_settings['override_role']}"
        await interaction.response.send_message(response, ephemeral=True)
    
    @app_commands.command(name="view-compensation-settings")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        role="Optional role to view settings for",
        user="Optional user to view settings for"
    )
    async def view_commission_settings(
        self, 
        interaction: discord.Interaction, 
        role: Optional[discord.Role] = None,
        user: Optional[discord.User] = None
    ):
        """View compensation settings for a role or user"""
        commission_settings = await file_handlers.load_json(settings.COMMISSION_SETTINGS_FILE, {})
        
        # Get guild-specific settings
        guild_id = str(interaction.guild.id)
        guild_settings = commission_settings.get(guild_id, {"roles": {}, "users": {}})
        
        # Create an embed to display commission_settings
        embed = discord.Embed(title="Commission Settings", color=0x009933)
        
        if role:
            # View specific role commission_settings
            role_settings = guild_settings['roles'].get(str(role.id), {})
            embed.description = f"Settings for Role: {role.mention}"
            embed.add_field(
                name="Commission", 
                value=f"{role_settings.get('commission_percentage', 'Not set')}%", 
                inline=True
            )
            embed.add_field(
                name="Hourly Rate", 
                value=f"${role_settings.get('hourly_rate', 'Not set')}/h", 
                inline=True
            )
        elif user:
            # View specific user commission_settings
            user_settings = guild_settings['users'].get(str(user.id), {})
            embed.description = f"Settings for User: {user.mention}"
            embed.add_field(
                name="Commission", 
                value=f"{user_settings.get('commission_percentage', 'Not set')}%", 
                inline=True
            )
            embed.add_field(
                name="Hourly Rate", 
                value=f"${user_settings.get('hourly_rate', 'Not set')}/h", 
                inline=True
            )
            embed.add_field(
                name="Override Role", 
                value=user_settings.get('override_role', False), 
                inline=True
            )
        else:
            # View all commission_settings summary
            embed.description = "Summary of Commission Settings"
            
            # Role commission_settings summary
            role_summary = []
            for role_id, role_data in guild_settings['roles'].items():
                role = interaction.guild.get_role(int(role_id))
                if role:
                    role_summary.append(
                        f"{role.name}: Commission {role_data.get('commission_percentage', 'N/A')}%, "
                        f"Hourly ${role_data.get('hourly_rate', 'N/A')}"
                    )
            
            if role_summary:
                embed.add_field(name="Role Settings", value="\n".join(role_summary), inline=False)
            
            # User commission_settings summary
            user_summary = []
            for user_id, user_data in guild_settings['users'].items():
                member = interaction.guild.get_member(int(user_id))
                if member:
                    user_summary.append(
                        f"{member.name}: Commission {user_data.get('commission_percentage', 'N/A')}%, "
                        f"Hourly ${user_data.get('hourly_rate', 'N/A')}, "
                        f"Override: {user_data.get('override_role', False)}"
                    )
            
            if user_summary:
                embed.add_field(name="User Settings", value="\n".join(user_summary), inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    
    @app_commands.command(
        name="view-display-settings",
        description="View the current display settings"
    )
    @app_commands.default_permissions(administrator=True)
    async def view_display_settings(self, interaction: discord.Interaction):
        """View the current display settings"""
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)
        show_average = await self.get_average_setting(interaction.guild.id)
        
        embed = discord.Embed(
            title="Display Settings",
            description=f"Ephemeral Messages: {ephemeral}\nShow Averages: {show_average}"
        )
        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)

    async def get_average_setting(self, guild_id):
        settings_data = await file_handlers.load_json(settings.DISPLAY_SETTINGS_FILE, settings.DEFAULT_DISPLAY_SETTINGS)
        guild_settings = settings_data.get(str(guild_id), {})
        return guild_settings.get("show_average", False)

    @app_commands.command(
        name="toggle-average",
        description="Toggle whether to show performance averages in calculation embeds"
    )
    @app_commands.default_permissions(administrator=True)
    async def toggle_average(self, interaction: discord.Interaction):
        """Toggle the display of performance averages in calculation embeds"""
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        # Only admins can use this command
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need administrator permissions to use this command.", ephemeral=ephemeral)
            return
        
        guild_id = str(interaction.guild_id)
        
        # Load settings data
        settings_data = await file_handlers.load_json(settings.DISPLAY_SETTINGS_FILE, settings.DEFAULT_DISPLAY_SETTINGS)
        
        # Initialize guild settings if they don't exist
        if guild_id not in settings_data:
            settings_data[guild_id] = {"show_average": False}
        
        # Toggle the show_average setting
        current_setting = settings_data[guild_id].get("show_average", False)
        settings_data[guild_id]["show_average"] = not current_setting
        new_setting = settings_data[guild_id]["show_average"]
        
        # Save updated settings
        success = await file_handlers.save_json(settings.DISPLAY_SETTINGS_FILE, settings_data)
        
        if success:
            status = "enabled" if new_setting else "disabled"
            logger.info(f"User {interaction.user.name} ({interaction.user.id}) {status} average display for guild {guild_id}")
            await interaction.response.send_message(f"✅ Performance average display is now **{status}**.", ephemeral=ephemeral)
        else:
            logger.error(f"Failed to save display settings for guild {guild_id}")
            await interaction.response.send_message("❌ Failed to update settings. Please try again.", ephemeral=ephemeral)

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(
        name="export-earnings-csv",
        description="Export all earnings data as CSV"
    )
    async def export_earnings_csv(self, interaction: discord.Interaction):
        """
        Admin-only command to export earnings data as CSV
        
        Usage: /export-earnings-csv
        """
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ This command is restricted to administrators.", ephemeral=True)
            return
        
        earnings_data = await file_handlers.load_json(settings.EARNINGS_FILE, settings.DEFAULT_EARNINGS)
        
        # Create CSV content
        csv_content = "User,Date,Total Cut,Gross Revenue,Period,Shift,Role,Models\n"
        for user, entries in earnings_data.items():
            for entry in entries:
                csv_content += f'"{user}",{entry["date"]},{entry["total_cut"]},{entry["gross_revenue"]},'
                csv_content += f'{entry["period"]},{entry["shift"]},{entry["role"]},"{entry.get("models", "")}"\n'
        
        # Create file object
        csv_file = discord.File(
            io.BytesIO(csv_content.encode('utf-8')),
            filename="full_earnings_export.csv"
        )
        
        await interaction.response.send_message(
            " Full earnings export (CSV):",
            file=csv_file,
            ephemeral=True
        )

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(
        name="export-earnings-json",
        description="Export all earnings data as JSON"
    )
    async def export_earnings_json(self, interaction: discord.Interaction):
        """
        Admin-only command to export earnings data as JSON
        
        Usage: /export-earnings-json
        """
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ This command is restricted to administrators.", ephemeral=True)
            return
        
        earnings_data = await file_handlers.load_json(settings.EARNINGS_FILE, settings.DEFAULT_EARNINGS)
        
        # Create JSON content
        json_content = json.dumps(earnings_data, indent=4)
        
        # Create file object
        json_file = discord.File(
            io.BytesIO(json_content.encode('utf-8')),
            filename="full_earnings_export.json"
        )
        
        await interaction.response.send_message(
            " Full earnings export (JSON):",
            file=json_file,
            ephemeral=True
        )

    # Role Management
    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="set-role", description="Set a role's percentage cut")
    @app_commands.describe(role="The role to configure", percentage="The percentage cut (e.g., 6.5)")
    async def set_role(self, interaction: discord.Interaction, role: discord.Role, percentage: str):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ This command is restricted to administrators.", ephemeral=True)
            return
        
        try:
            logger.info(f"User {interaction.user.name} ({interaction.user.id}) used set-role command for role {role.name} with percentage {percentage}")
            
            percentage_decimal = validators.validate_percentage(percentage)
            if percentage_decimal is None:
                logger.warning(f"Invalid percentage '{percentage}' provided by {interaction.user.name}")
                await interaction.response.send_message("❌ Percentage must be a valid number between 0 and 100.", ephemeral=ephemeral)
                return
            
            guild_id = str(interaction.guild.id)
            role_id = str(role.id)
            
            role_data = await file_handlers.load_json(settings.ROLE_DATA_FILE, settings.DEFAULT_ROLE_DATA)
            
            if guild_id not in role_data:
                role_data[guild_id] = {}
            role_data[guild_id][role_id] = float(percentage_decimal)
            
            success = await file_handlers.save_json(settings.ROLE_DATA_FILE, role_data)
            
            if success:
                logger.info(f"Role {role.name} ({role_id}) percentage set to {percentage_decimal}% by {interaction.user.name}")
                await interaction.response.send_message(f"✅ {role.name} now has {percentage_decimal}% cut!", ephemeral=ephemeral)
            else:
                logger.error(f"Failed to save role data for {role.name} ({role_id}) by {interaction.user.name}")
                await interaction.response.send_message("❌ Failed to save role data. Please try again later.", ephemeral=ephemeral)
        except Exception as e:
            logger.error(f"Error in set_role: {str(e)}")
            await interaction.response.send_message("❌ An unexpected error occurred. See logs for details.", ephemeral=ephemeral)

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="remove-role", description="Remove a role's percentage configuration")
    @app_commands.describe(role="The role to remove")
    async def remove_role(self, interaction: discord.Interaction, role: discord.Role):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ This command is restricted to administrators.", ephemeral=True)
            return
        
        try:
            logger.info(f"User {interaction.user.name} ({interaction.user.id}) used remove-role command for role {role.name}")
            
            guild_id = str(interaction.guild.id)
            role_id = str(role.id)
            
            role_data = await file_handlers.load_json(settings.ROLE_DATA_FILE, settings.DEFAULT_ROLE_DATA)
            
            if guild_id not in role_data or role_id not in role_data[guild_id]:
                logger.warning(f"Role {role.name} ({role_id}) not found in configuration")
                await interaction.response.send_message(f"❌ {role.name} does not have a configured percentage.", ephemeral=ephemeral)
                return
            
            del role_data[guild_id][role_id]
            success = await file_handlers.save_json(settings.ROLE_DATA_FILE, role_data)
            
            if success:
                logger.info(f"Role {role.name} ({role_id}) removed from configuration")
                await interaction.response.send_message(f"✅ {role.name} has been removed from percentage configuration!", ephemeral=ephemeral)
            else:
                logger.error(f"Failed to remove role {role.name} ({role_id})")
                await interaction.response.send_message("❌ Failed to save role data. Please try again later.", ephemeral=ephemeral)
        except Exception as e:
            logger.error(f"Error in remove_role: {str(e)}")
            await interaction.response.send_message("❌ An unexpected error occurred. See logs for details.", ephemeral=ephemeral)

    # Shift Management
    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="set-shift", description="Add a valid shift name")
    @app_commands.describe(shift="The name of the shift to add")
    async def set_shift(self, interaction: discord.Interaction, shift: str):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)
        
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ This command is restricted to administrators.", ephemeral=True)
            return
        
        try:
            logger.info(f"User {interaction.user.name} used set-shift command for shift '{shift}'")
            
            if not shift.strip():
                await interaction.response.send_message("❌ Shift name cannot be empty.", ephemeral=ephemeral)
                return
                
            guild_id = str(interaction.guild.id)
            shift_data = await file_handlers.load_json(settings.SHIFT_DATA_FILE, settings.DEFAULT_SHIFT_DATA)
            existing_shifts = shift_data.get(guild_id, [])
            
            if validators.validate_shift(shift, existing_shifts) is not None:
                await interaction.response.send_message(f"❌ Shift '{shift}' already exists!", ephemeral=ephemeral)
                return
            
            shift_data.setdefault(guild_id, []).append(shift)
            success = await file_handlers.save_json(settings.SHIFT_DATA_FILE, shift_data)
            
            if success:
                await interaction.response.send_message(f"✅ Shift '{shift}' added!", ephemeral=ephemeral)
            else:
                await interaction.response.send_message("❌ Failed to save shift data. Please try again later.", ephemeral=ephemeral)
        except Exception as e:
            logger.error(f"Error in set_shift: {str(e)}")
            await interaction.response.send_message("❌ An unexpected error occurred. See logs for details.", ephemeral=ephemeral)

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="remove-shift", description="Remove a shift configuration")
    @app_commands.describe(shift="The name of the shift to remove")
    async def remove_shift(self, interaction: discord.Interaction, shift: str):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)
        
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ This command is restricted to administrators.", ephemeral=True)
            return
        
        try:
            guild_id = str(interaction.guild.id)
            shift_data = await file_handlers.load_json(settings.SHIFT_DATA_FILE, settings.DEFAULT_SHIFT_DATA)
            existing_shifts = shift_data.get(guild_id, [])
            
            normalized_shift = validators.validate_shift(shift, existing_shifts)
            if normalized_shift is None:
                await interaction.response.send_message(f"❌ Shift '{shift}' doesn't exist!", ephemeral=ephemeral)
                return
            
            shift_data[guild_id].remove(normalized_shift)
            success = await file_handlers.save_json(settings.SHIFT_DATA_FILE, shift_data)
            
            if success:
                await interaction.response.send_message(f"✅ Shift '{normalized_shift}' removed!", ephemeral=ephemeral)
            else:
                await interaction.response.send_message("❌ Failed to save shift data. Please try again later.", ephemeral=ephemeral)
        except Exception as e:
            logger.error(f"Error in remove_shift: {str(e)}")
            await interaction.response.send_message("❌ An unexpected error occurred. See logs for details.", ephemeral=ephemeral)

    # Period Management
    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="set-period", description="Add a valid period name")
    @app_commands.describe(period="The name of the period to add")
    async def set_period(self, interaction: discord.Interaction, period: str):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)
        
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ This command is restricted to administrators.", ephemeral=True)
            return
        
        try:
            if not period.strip():
                await interaction.response.send_message("❌ Period name cannot be empty.", ephemeral=True)
                return
                
            guild_id = str(interaction.guild.id)
            period_data = await file_handlers.load_json(settings.PERIOD_DATA_FILE, settings.DEFAULT_PERIOD_DATA)
            existing_periods = period_data.get(guild_id, [])
            
            if validators.validate_period(period, existing_periods) is not None:
                await interaction.response.send_message(f"❌ Period '{period}' already exists!", ephemeral=ephemeral)
                return
            
            period_data.setdefault(guild_id, []).append(period)
            success = await file_handlers.save_json(settings.PERIOD_DATA_FILE, period_data)
            
            if success:
                await interaction.response.send_message(f"✅ Period '{period}' added!", ephemeral=ephemeral)
            else:
                await interaction.response.send_message("❌ Failed to save period data. Please try again later.", ephemeral=ephemeral)
        except Exception as e:
            logger.error(f"Error in set_period: {str(e)}")
            await interaction.response.send_message("❌ An unexpected error occurred. See logs for details.", ephemeral=ephemeral)

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="remove-period", description="Remove a period configuration")
    @app_commands.describe(period="The name of the period to remove")
    async def remove_period(self, interaction: discord.Interaction, period: str):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)
        
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ This command is restricted to administrators.", ephemeral=True)
            return
        
        guild_id = str(interaction.guild.id)
        period_data = await file_handlers.load_json(settings.PERIOD_DATA_FILE, settings.DEFAULT_PERIOD_DATA)
        existing_periods = period_data.get(guild_id, [])
        
        normalized_period = validators.validate_period(period, existing_periods)
        if normalized_period is None:
            await interaction.response.send_message(f"❌ Period '{period}' doesn't exist!", ephemeral=ephemeral)
            return
        
        period_data[guild_id].remove(normalized_period)
        success = await file_handlers.save_json(settings.PERIOD_DATA_FILE, period_data)
        
        if success:
            await interaction.response.send_message(f"✅ Period '{normalized_period}' removed!", ephemeral=ephemeral)
        else:
            await interaction.response.send_message("❌ Failed to save period data. Please try again later.", ephemeral=ephemeral)

    # Bonus Rules Management
    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="set-bonus-rule", description="Set a bonus rule for a revenue range")
    @app_commands.describe(
        from_range="Lower bound of revenue (e.g., 1000)",
        to_range="Upper bound of revenue (e.g., 2000)",
        bonus="Bonus amount (e.g., 50)"
    )
    async def set_bonus_rule(self, interaction: discord.Interaction, from_range: str, to_range: str, bonus: str):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)
        
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ This command is restricted to administrators.", ephemeral=True)
            return
        
        from_num = validators.parse_money(from_range)
        to_num = validators.parse_money(to_range)
        bonus_amount = validators.parse_money(bonus)
        
        if None in (from_num, to_num, bonus_amount):
            await interaction.response.send_message("❌ Invalid number format.", ephemeral=ephemeral)
            return
            
        if from_num > to_num:
            await interaction.response.send_message("❌ The 'from' value must be less than or equal to the 'to' value.", ephemeral=ephemeral)
            return
            
        guild_id = str(interaction.guild.id)
        bonus_rules = await file_handlers.load_json(settings.BONUS_RULES_FILE, settings.DEFAULT_BONUS_RULES)
        
        new_rule = {"from": float(from_num), "to": float(to_num), "amount": float(bonus_amount)}
        current_rules = bonus_rules.setdefault(guild_id, [])
        
        if any((from_num <= rule["to"] and to_num >= rule["from"]) for rule in current_rules):
            await interaction.response.send_message("❌ This rule overlaps with an existing bonus rule.", ephemeral=ephemeral)
            return
            
        current_rules.append(new_rule)
        success = await file_handlers.save_json(settings.BONUS_RULES_FILE, bonus_rules)
        
        if success:
            await interaction.response.send_message(f"✅ Bonus rule added: ${float(from_num):,.2f}-${float(to_num):,.2f} → ${float(bonus_amount):,.2f}!", ephemeral=ephemeral)
        else:
            await interaction.response.send_message("❌ Failed to save bonus rule.", ephemeral=ephemeral)

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="remove-bonus-rule", description="Remove a bonus rule for a revenue range")
    @app_commands.describe(
        from_range="Lower bound of revenue",
        to_range="Upper bound of revenue"
    )
    async def remove_bonus_rule(self, interaction: discord.Interaction, from_range: str, to_range: str):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)
        
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ This command is restricted to administrators.", ephemeral=True)
            return
        
        from_num = validators.parse_money(from_range)
        to_num = validators.parse_money(to_range)
        
        if None in (from_num, to_num):
            await interaction.response.send_message("❌ Invalid number format.", ephemeral=ephemeral)
            return
            
        guild_id = str(interaction.guild.id)
        bonus_rules = await file_handlers.load_json(settings.BONUS_RULES_FILE, settings.DEFAULT_BONUS_RULES)
        guild_rules = bonus_rules.get(guild_id, [])
        
        rule_to_remove = next(
            (rule for rule in guild_rules 
             if Decimal(str(rule["from"])) == from_num and Decimal(str(rule["to"])) == to_num),
            None
        )
        
        if not rule_to_remove:
            await interaction.response.send_message(f"❌ No bonus rule found for ${from_num}-${to_num}.", ephemeral=ephemeral)
            return
            
        bonus_rules[guild_id].remove(rule_to_remove)
        success = await file_handlers.save_json(settings.BONUS_RULES_FILE, bonus_rules)
        
        if success:
            await interaction.response.send_message(f"✅ Bonus rule removed: ${float(from_num):,.2f}-${float(to_num):,.2f}", ephemeral=ephemeral)
        else:
            await interaction.response.send_message("❌ Failed to remove bonus rule.", ephemeral=ephemeral)

    # List Commands
    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="list-roles", description="List configured roles and percentages")
    async def list_roles(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        guild_id = str(interaction.guild.id)
        role_data = await file_handlers.load_json(settings.ROLE_DATA_FILE, settings.DEFAULT_ROLE_DATA)
        guild_roles = role_data.get(guild_id, {})
        
        if not guild_roles:
            await interaction.response.send_message("❌ No roles configured.", ephemeral=ephemeral)
            return
            
        embed = discord.Embed(title="Configured Roles", color=discord.Color.blue())

        for role_id, percentage in guild_roles.items():
            role = interaction.guild.get_role(int(role_id))
            role_name = role.name if role else f"Unknown Role ({role_id})"
            embed.add_field(name=role_name, value=f"{percentage}%", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="list-shifts", description="List configured shifts")
    async def list_shifts(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        guild_id = str(interaction.guild.id)
        shift_data = await file_handlers.load_json(settings.SHIFT_DATA_FILE, settings.DEFAULT_SHIFT_DATA)
        guild_shifts = shift_data.get(guild_id, [])
        
        if not guild_shifts:
            await interaction.response.send_message("❌ No shifts configured.", ephemeral=ephemeral)
            return
            
        embed = discord.Embed(title="Configured Shifts", color=discord.Color.blue())
        embed.add_field(name="Shifts", value="\n".join(f"• {shift}" for shift in guild_shifts))
        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="list-periods", description="List configured periods")
    async def list_periods(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        guild_id = str(interaction.guild.id)
        period_data = await file_handlers.load_json(settings.PERIOD_DATA_FILE, settings.DEFAULT_PERIOD_DATA)
        guild_periods = period_data.get(guild_id, [])
        
        if not guild_periods:
            await interaction.response.send_message("❌ No periods configured.", ephemeral=ephemeral)
            return
            
        embed = discord.Embed(title="Configured Periods", color=discord.Color.blue())
        embed.add_field(name="Periods", value="\n".join(f"• {period}" for period in guild_periods))
        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="list-bonus-rules", description="List configured bonus rules")
    async def list_bonus_rules(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        guild_id = str(interaction.guild.id)
        bonus_rules = await file_handlers.load_json(settings.BONUS_RULES_FILE, settings.DEFAULT_BONUS_RULES)
        guild_rules = bonus_rules.get(guild_id, [])
        
        if not guild_rules:
            await interaction.response.send_message("❌ No bonus rules configured.", ephemeral=ephemeral)
            return
            
        embed = discord.Embed(title="Bonus Rules", color=discord.Color.green())
        
        for rule in sorted(guild_rules, key=lambda x: x["from"]):
            embed.add_field(
                name=f"${rule['from']} - ${rule['to']}",
                value=f"Bonus: ${rule['amount']}",
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)

    # Model Management
    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="set-model", description="Add a valid model name")
    @app_commands.describe(model="The name of the model to add")
    async def set_model(self, interaction: discord.Interaction, model: str):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)
        
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ This command is restricted to administrators.", ephemeral=True)
            return
        
        logger.info(f"User {interaction.user.name} used set-model command for model '{model}'")
        
        if not model.strip():
            await interaction.response.send_message("❌ Model name cannot be empty.", ephemeral=ephemeral)
            return
            
        guild_id = str(interaction.guild.id)
        model_data = await file_handlers.load_json(settings.MODELS_DATA_FILE, settings.DEFAULT_MODELS_DATA)
        existing_models = model_data.get(guild_id, [])
        
        if model.lower() in [m.lower() for m in existing_models]:
            await interaction.response.send_message(f"❌ Model '{model}' already exists!", ephemeral=ephemeral)
            return
        
        model_data.setdefault(guild_id, []).append(model)
        success = await file_handlers.save_json(settings.MODELS_DATA_FILE, model_data)
        
        if success:
            await interaction.response.send_message(f"✅ Model '{model}' added!", ephemeral=ephemeral)
        else:
            await interaction.response.send_message("❌ Failed to save model data. Please try again later.", ephemeral=ephemeral)

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="remove-model", description="Remove a model configuration")
    @app_commands.describe(model="The name of the model to remove")
    async def remove_model(self, interaction: discord.Interaction, model: str):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)
        
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ This command is restricted to administrators.", ephemeral=True)
            return
        
        guild_id = str(interaction.guild.id)
        model_data = await file_handlers.load_json(settings.MODELS_DATA_FILE, settings.DEFAULT_MODELS_DATA)
        existing_models = model_data.get(guild_id, [])
        
        normalized_model = next((m for m in existing_models if m.lower() == model.lower()), None)
        if normalized_model is None:
            await interaction.response.send_message(f"❌ Model '{model}' doesn't exist!", ephemeral=ephemeral)
            return
        
        model_data[guild_id].remove(normalized_model)
        success = await file_handlers.save_json(settings.MODELS_DATA_FILE, model_data)
        
        if success:
            await interaction.response.send_message(f"✅ Model '{normalized_model}' removed!", ephemeral=ephemeral)
        else:
            await interaction.response.send_message("❌ Failed to save model data. Please try again later.", ephemeral=ephemeral)

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="list-models", description="List configured models")
    async def list_models(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        guild_id = str(interaction.guild.id)
        model_data = await file_handlers.load_json(settings.MODELS_DATA_FILE, settings.DEFAULT_MODELS_DATA)
        guild_models = model_data.get(guild_id, [])
        
        if not guild_models:
            await interaction.response.send_message("❌ No models configured.", ephemeral=ephemeral)
            return
            
        embed = discord.Embed(title="Configured Models", color=discord.Color.blue())
        embed.add_field(name="Models", value="\n".join(f"• {model}" for model in guild_models))
        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="clear-earnings", description="Clear all earnings data")
    async def clear_earnings(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        # guild_id = str(interaction.guild.id) # todo remove 
        guild_name = interaction.guild.name

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Confirm", style=discord.ButtonStyle.danger, custom_id="confirm_clear_earnings"))
        view.add_item(discord.ui.Button(label="Cancel", style=discord.ButtonStyle.success, custom_id="cancel_clear_earnings"))

        async def confirm_callback(interaction):
            # guild_id = str(interaction.guild.id) # todo remove when you check if it works
            # earnings_data = await file_handlers.load_json(settings.EARNINGS_FILE, settings.DEFAULT_EARNINGS)
            # earnings_data[guild_id] = {}
            # await file_handlers.save_json(settings.EARNINGS_FILE, earnings_data)
            await self.reset_earnings(interaction)
            await interaction.response.edit_message(content=f"✅ All earnings data for the guild ({guild_name}) has been successfully cleared.", view=None)

        async def cancel_callback(interaction):
            await interaction.response.edit_message(content="❌ Canceled.", view=None)

        view.children[0].callback = confirm_callback
        view.children[1].callback = cancel_callback
        await interaction.response.send_message("‼️🚨‼ Are you sure you want to clear all earnings data?", view=view, ephemeral=ephemeral)

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="reset-config", description="Reset all configuration files")
    async def reset_config(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Confirm", style=discord.ButtonStyle.danger, custom_id="confirm_reset_config"))
        view.add_item(discord.ui.Button(label="Cancel", style=discord.ButtonStyle.success, custom_id="cancel_reset_config"))

        async def confirm_callback(interaction):
            await self.reset_shift(interaction)
            await self.reset_period(interaction)
            await self.reset_role(interaction)
            await self.reset_bonus_rules(interaction)
            await self.reset_models(interaction)
            # await self.reset_earnings(interaction) # todo remove
            await self.reset_display(interaction)
            await self.reset_compensation(interaction)
            try:
                await interaction.response.edit_message(content="✅ Configuration data has been reset.", view=None)
            except discord.NotFound:
                logger.error("Ignoring exception in view %r for item %r", self, view, exc_info=True)

        async def cancel_callback(interaction):
            await interaction.response.edit_message(content="❌ Canceled.", view=None)

        view.children[0].callback = confirm_callback
        view.children[1].callback = cancel_callback
        await interaction.response.send_message(content="‼️🚨‼ Are you sure you want to reset all configuration data? Earnings data will not be affected (use: `/clear-earnings`).", view=view, ephemeral=ephemeral)

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="restore-latest-backup", description="Restore the latest backup")
    async def restore_latest_backup(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Confirm", style=discord.ButtonStyle.danger, custom_id="confirm_restore_backup"))
        view.add_item(discord.ui.Button(label="Cancel", style=discord.ButtonStyle.success, custom_id="cancel_restore_backup"))

        async def confirm_callback(interaction):
            await interaction.response.defer(ephemeral=ephemeral)

            cogs_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(cogs_dir)
            data_dir = os.path.join(parent_dir, "data")

            backup_files = glob.glob(os.path.join(data_dir, "*.bak"))

            if not backup_files:
                await interaction.response.edit_message(content="❌ No backup files found!", view=None)
                return

            restored_count = 0
            failed_count = 0

            for bak_file in backup_files:
                if os.path.basename(bak_file) == settings.EARNINGS_FILE + ".bak":
                    continue

                try:
                    original_file = bak_file[:-4]
                    shutil.copy2(bak_file, original_file)
                    restored_count += 1
                except Exception as e:
                    print(f"Failed to restore {bak_file}: {str(e)}")
                    failed_count += 1

            if failed_count == 0:
                await interaction.response.edit_message(content=f"✅ Successfully restored {restored_count} backup files.", view=None)
            else:
                await interaction.response.edit_message(content=f"⚠️ Restored {restored_count} files, but {failed_count} failed. Check console for details.", view=None)

        async def cancel_callback(interaction):
            await interaction.response.edit_message(content="❌ Canceled.", view=None)

        view.children[0].callback = confirm_callback
        view.children[1].callback = cancel_callback
        await interaction.response.send_message(content="‼️🚨‼ Are you sure you want to restore the latest configuration backup?", view=view, ephemeral=ephemeral)

    async def reset_shift(self, interaction: discord.Interaction):
        await file_handlers.save_json(settings.SHIFT_DATA_FILE, settings.DEFAULT_SHIFT_DATA)

    # Reset Individual Config Files
    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="reset-shift-config", description="Reset shift configuration")
    async def reset_shift_config(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        async def reset_action(interaction: discord.Interaction):
            await self.reset_shift(interaction)
            await interaction.response.edit_message(content="✅ Shift configuration reset.", view=None)

        view = ConfirmButton(reset_action, interaction.user.id)

        await interaction.response.send_message(
            "⚠️ Are you sure you want to reset the shift configuration?", 
            view=view, 
            ephemeral=ephemeral
        )

    async def reset_period(self, interaction: discord.Interaction):
        await file_handlers.save_json(settings.PERIOD_DATA_FILE, settings.DEFAULT_PERIOD_DATA)

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="reset-period-config", description="Reset period configuration")
    async def reset_period_config(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        async def reset_action(interaction: discord.Interaction):
            await self.reset_period(interaction)
            await interaction.response.edit_message(content="✅ Period configuration reset.", view=None)

        view = ConfirmButton(reset_action, interaction.user.id)
        await interaction.response.send_message(
            "⚠️ Are you sure you want to reset the period configuration?", 
            view=view, 
            ephemeral=ephemeral
        )

    async def reset_role(self, interaction: discord.Interaction):
        await file_handlers.save_json(settings.ROLE_DATA_FILE, settings.DEFAULT_ROLE_DATA)

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="reset-role-config", description="Reset role configuration")
    async def reset_role_config(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        async def reset_action(interaction: discord.Interaction):
            await self.reset_role(interaction)
            await interaction.response.edit_message(content="✅ Role configuration reset.", view=None)

        view = ConfirmButton(reset_action, interaction.user.id)
        await interaction.response.send_message(
            "⚠️ Are you sure you want to reset the role configuration?", 
            view=view, 
            ephemeral=ephemeral
        )

    async def reset_bonus_rules(self, interaction: discord.Interaction):
        await file_handlers.save_json(settings.BONUS_RULES_FILE, settings.DEFAULT_BONUS_RULES)

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="reset-bonus-config", description="Reset bonus rules configuration")
    async def reset_bonus_config(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        async def reset_action(interaction: discord.Interaction):
            await self.reset_bonus_rules(interaction)
            await interaction.response.edit_message(content="✅ Bonus rules configuration reset.", view=None)

        view = ConfirmButton(reset_action, interaction.user.id)
        await interaction.response.send_message(
            "⚠️ Are you sure you want to reset the bonus rules configuration?", 
            view=view, 
            ephemeral=ephemeral
        )

    async def reset_earnings(self, interaction: discord.Interaction):
        await file_handlers.save_json(settings.EARNINGS_FILE, settings.DEFAULT_EARNINGS)

    # @app_commands.default_permissions(administrator=True) # todo remove reset-earnings-config
    # @app_commands.command(name="reset-earnings-config", description="Reset earnings configuration")
    # async def reset_earnings_config(self, interaction: discord.Interaction):
    #     async def reset_action(interaction: discord.Interaction):
    #         await self.reset_earnings(interaction)
    #         await interaction.response.edit_message(content="✅ Earnings configuration reset.", view=None)

    #     view = ConfirmButton(reset_action, interaction.user.id)
    #     await interaction.response.send_message(
    #         "⚠️ Are you sure you want to reset all earnings data? This will delete all existing earnings entries.", 
    #         view=view, 
    #         ephemeral=True
    #     )
    
    async def reset_models(self, interaction: discord.Interaction): 
        await file_handlers.save_json(settings.MODELS_DATA_FILE, settings.DEFAULT_MODELS_DATA)

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="reset-models-config", description="Reset models configuration")
    async def reset_models_config(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        async def reset_action(interaction: discord.Interaction):
            await self.reset_models(interaction)
            await interaction.response.edit_message(content="✅ Model settings reset.", view=None)

        view = ConfirmButton(reset_action, interaction.user.id)
        await interaction.response.send_message(
            "⚠️ Are you sure you want to reset the models configuration?", 
            view=view, 
            ephemeral=ephemeral
        )

    async def reset_compensation(self, interaction: discord.Interaction):
        await file_handlers.save_json(settings.COMMISSION_SETTINGS_FILE, settings.DEFAULT_COMMISSION_SETTINGS)

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="reset-compensation-config", description="Reset compensation configuration")
    async def reset_compensation_config(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        async def reset_action(interaction: discord.Interaction):
            await self.reset_compensation(interaction)
            await interaction.response.edit_message(content="✅ Commission configuration reset.", view=None)

        view = ConfirmButton(reset_action, interaction.user.id)
        await interaction.response.send_message(
            "⚠️ Are you sure you want to reset the compensation configuration?", 
            view=view, 
            ephemeral=ephemeral
        )

    async def reset_display(self, interaction: discord.Interaction):
        await file_handlers.save_json(settings.DISPLAY_SETTINGS_FILE, settings.DEFAULT_DISPLAY_SETTINGS)

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="reset-display-config", description="Reset display configuration")
    async def reset_display_config(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        async def reset_action(interaction: discord.Interaction):
            await self.reset_display(interaction)
            await interaction.response.edit_message(content="✅ Display configuration reset.", view=None)

        view = ConfirmButton(reset_action, interaction.user.id)
        await interaction.response.send_message(
            "⚠️ Are you sure you want to reset the display configuration?", 
            view=view, 
            ephemeral=ephemeral
        )

    # Restore Backup Methods
    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="restore-shift-backup", description="Restore the latest shift configuration backup")
    async def restore_shift_backup(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        async def restore_action(interaction: discord.Interaction):
            backup_file = os.path.join(settings.DATA_DIRECTORY, f"{settings.SHIFT_DATA_FILE}.bak")
            if os.path.exists(backup_file):
                shutil.copy2(backup_file, os.path.join(settings.DATA_DIRECTORY, settings.SHIFT_DATA_FILE))
                await interaction.response.edit_message(content="✅ Shift configuration backup restored successfully.", view=None)
            else:
                await interaction.response.edit_message(content="❌ No shift configuration backup found.", view=None)

        view = ConfirmButton(restore_action, interaction.user.id)

        await interaction.response.send_message(
            "⚠️ Are you sure you want to restore the shift configuration backup?", 
            view=view, 
            ephemeral=ephemeral
        )

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="restore-period-backup", description="Restore the latest period configuration backup")
    async def restore_period_backup(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        async def restore_action(interaction: discord.Interaction):
            backup_file = os.path.join(settings.DATA_DIRECTORY, f"{settings.PERIOD_DATA_FILE}.bak")
            if os.path.exists(backup_file):
                shutil.copy2(backup_file, os.path.join(settings.DATA_DIRECTORY, settings.PERIOD_DATA_FILE))
                await interaction.response.edit_message(content="✅ Period configuration backup restored successfully.", view=None)
            else:
                await interaction.response.edit_message(content="❌ No period configuration backup found.", view=None)

        view = ConfirmButton(restore_action, interaction.user.id)
        await interaction.response.send_message(
            "⚠️ Are you sure you want to restore the period configuration backup?", 
            view=view, 
            ephemeral=ephemeral
        )

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="restore-role-backup", description="Restore the latest role configuration backup")
    async def restore_role_backup(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        async def restore_action(interaction: discord.Interaction):
            backup_file = os.path.join(settings.DATA_DIRECTORY, f"{settings.ROLE_DATA_FILE}.bak")
            if os.path.exists(backup_file):
                shutil.copy2(backup_file, os.path.join(settings.DATA_DIRECTORY, settings.ROLE_DATA_FILE))
                await interaction.response.edit_message(content="✅ Role configuration backup restored successfully.", view=None)
            else:
                await interaction.response.edit_message(content="❌ No role configuration backup found.", view=None)

        view = ConfirmButton(restore_action, interaction.user.id)
        await interaction.response.send_message(
            "⚠️ Are you sure you want to restore the role configuration backup?", 
            view=view, 
            ephemeral=ephemeral
        )

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="restore-bonus-backup", description="Restore the latest bonus rules configuration backup")
    async def restore_bonus_backup(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        async def restore_action(interaction: discord.Interaction):
            backup_file = os.path.join(settings.DATA_DIRECTORY, f"{settings.BONUS_RULES_FILE}.bak")
            if os.path.exists(backup_file):
                shutil.copy2(backup_file, os.path.join(settings.DATA_DIRECTORY, settings.BONUS_RULES_FILE))
                await interaction.response.edit_message(content="✅ Bonus rules configuration backup restored successfully.", view=None)
            else:
                await interaction.response.edit_message(content="❌ No bonus rules configuration backup found.", view=None)

        view = ConfirmButton(restore_action, interaction.user.id)
        await interaction.response.send_message(
            "⚠️ Are you sure you want to restore the bonus rules configuration backup?", 
            view=view, 
            ephemeral=ephemeral
        )

    @app_commands.default_permissions(administrator=True) # todo double confirm button needed
    @app_commands.command(name="restore-earnings-backup", description="Restore the latest earnings configuration backup")
    async def restore_earnings_backup(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        async def restore_action(interaction: discord.Interaction):
            backup_file = os.path.join(settings.DATA_DIRECTORY, f"{settings.EARNINGS_FILE}.bak")
            if os.path.exists(backup_file):
                shutil.copy2(backup_file, os.path.join(settings.DATA_DIRECTORY, settings.EARNINGS_FILE))
                await interaction.response.edit_message(content="✅ Earnings configuration backup restored successfully.", view=None)
            else:
                await interaction.response.edit_message(content="❌ No earnings configuration backup found.", view=None)

        view = ConfirmButton(restore_action, interaction.user.id)
        await interaction.response.send_message(
            "‼️🚨‼ Are you sure you want to restore the earnings configuration backup?", 
            view=view, 
            ephemeral=ephemeral
        )

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="restore-models-backup", description="Restore the latest models configuration backup")
    async def restore_models_backup(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        async def restore_action(interaction: discord.Interaction):
            backup_file = os.path.join(settings.DATA_DIRECTORY, f"{settings.MODELS_DATA_FILE}.bak")
            if os.path.exists(backup_file):
                shutil.copy2(backup_file, os.path.join(settings.DATA_DIRECTORY, settings.MODELS_DATA_FILE))
                await interaction.response.edit_message(content="✅ Models configuration backup restored successfully.", view=None)
            else:
                await interaction.response.edit_message(content="❌ No models configuration backup found.", view=None)

        view = ConfirmButton(restore_action, interaction.user.id)
        await interaction.response.send_message(
            "⚠️ Are you sure you want to restore the models configuration backup?", 
            view=view, 
            ephemeral=ephemeral
        )

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="restore-compensation-backup", description="Restore the latest compensation configuration backup")
    async def restore_compensation_backup(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        async def restore_action(interaction: discord.Interaction):
            backup_file = os.path.join(settings.DATA_DIRECTORY, f"{settings.COMMISSION_SETTINGS_FILE}.bak")
            if os.path.exists(backup_file):
                shutil.copy2(backup_file, os.path.join(settings.DATA_DIRECTORY, settings.COMMISSION_SETTINGS_FILE))
                await interaction.response.edit_message(content="✅ Compensation configuration backup restored successfully.", view=None)
            else:
                await interaction.response.edit_message(content="❌ No compensation configuration backup found.", view=None)

        view = ConfirmButton(restore_action, interaction.user.id)
        await interaction.response.send_message(
            "⚠️ Are you sure you want to restore the compensation configuration backup?", 
            view=view, 
            ephemeral=ephemeral
        )

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="restore-display-backup", description="Restore the latest display configuration backup")
    async def restore_display_backup(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        async def restore_action(interaction: discord.Interaction):
            backup_file = os.path.join(settings.DATA_DIRECTORY, f"{settings.DISPLAY_SETTINGS_FILE}.bak")
            if os.path.exists(backup_file):
                shutil.copy2(backup_file, os.path.join(settings.DATA_DIRECTORY, settings.DISPLAY_SETTINGS_FILE))
                await interaction.response.edit_message(content="✅ Display configuration backup restored successfully.", view=None)
            else:
                await interaction.response.edit_message(content="❌ No display configuration backup found.", view=None)

        view = ConfirmButton(restore_action, interaction.user.id)
        await interaction.response.send_message(
            "⚠️ Are you sure you want to restore the display configuration backup?", 
            view=view, 
            ephemeral=ephemeral
        )

    @app_commands.command(
        name="toggle-ephemeral",
        description="Toggle whether command responses are ephemeral"
    )
    @app_commands.default_permissions(administrator=True)
    async def toggle_ephemeral(self, interaction: discord.Interaction):
        """Toggle ephemeral responses for admin commands"""
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)
        
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ You need administrator permissions to use this command.",
                ephemeral=True
            )
            return

        display_settings = await file_handlers.load_json(settings.DISPLAY_SETTINGS_FILE, settings.DEFAULT_DISPLAY_SETTINGS)
        guild_id = str(interaction.guild.id)
        current_setting = display_settings.get(guild_id, {}).get('ephemeral_responses', True)
        new_setting = not current_setting

        # Update settings
        if guild_id not in display_settings:
            display_settings[guild_id] = {}
        display_settings[guild_id]['ephemeral_responses'] = new_setting
        
        success = await file_handlers.save_json(settings.DISPLAY_SETTINGS_FILE, display_settings)
        
        if success:
            status = "enabled" if new_setting else "disabled"
            await interaction.response.send_message(
                f"✅ Ephemeral responses are now **{status}**.",
                ephemeral=new_setting
            )
        else:
            await interaction.response.send_message(
                "❌ Failed to update ephemeral settings. Please try again.",
                ephemeral=current_setting
            )

class ConfirmButton(discord.ui.View):
    def __init__(self, action_callback, user_id: int):
        super().__init__()
        self.action_callback = action_callback
        self.user_id = user_id

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.red)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You cannot use this button.", ephemeral=True)
            return
        
        await self.action_callback(interaction)
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.green)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You cannot use this button.", ephemeral=True)
            return
        
        await interaction.response.edit_message(content="Action cancelled.", view=None)
        self.stop()

async def setup(bot):
    await bot.add_cog(AdminSlashCommands(bot))