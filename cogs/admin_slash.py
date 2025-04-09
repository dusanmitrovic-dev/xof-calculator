import asyncio
import os
import re
import json
import glob
import shutil
import discord
import logging
from datetime import datetime

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
        file_path = settings.get_guild_display_path(guild_id)
        display_settings = await file_handlers.load_json(file_path, {
                "ephemeral_responses": True,
                "show_average": True,
                "agency_name": "Agency",
                "show_ids": True,
                "bot_name": "Shift Calculator"
        })
        guild_settings = display_settings
        return guild_settings.get('ephemeral_responses', 
            settings.DEFAULT_DISPLAY_SETTINGS['ephemeral_responses'])

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
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        # Validate input
        if not self.validate_percentage(percentage):
            await interaction.response.send_message(
                "❌ Invalid percentage. Must be between 0 and 100.", 
                ephemeral=ephemeral
            )

            return
        
        # Load existing settings
        file_path = settings.get_guild_commission_path(interaction.guild.id)
        commission_settings = await file_handlers.load_json(file_path, {})
        
        # Ensure 'roles' key exists
        commission_settings.setdefault('roles', {})
        
        # Update role commission_settings
        role_settings = commission_settings['roles'].get(str(role.id), {})
        role_settings['commission_percentage'] = percentage
        commission_settings['roles'][str(role.id)] = role_settings
        
        # Save updated commission_settings
        await file_handlers.save_json(file_path, commission_settings)
        
        # Respond with confirmation
        response = f"✅ Set commission for {role.mention} to "
        response += f"{percentage}%" if percentage is not None else "cleared"
        await interaction.response.send_message(response, ephemeral=ephemeral)
    
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
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        # Validate input
        if not self.validate_hourly_rate(rate):
            await interaction.response.send_message(
                "❌ Invalid hourly rate. Must be a non-negative number.", 
                ephemeral=ephemeral
            )
            return
        
        # Load existing settings
        file_path = settings.get_guild_commission_path(interaction.guild.id)
        commission_settings = await file_handlers.load_json(file_path, {})
        
        # Ensure 'roles' key exists
        commission_settings.setdefault('roles', {})
        
        # Update role settings
        role_settings = commission_settings['roles'].get(str(role.id), {})
        role_settings['hourly_rate'] = rate
        commission_settings['roles'][str(role.id)] = role_settings
        
        # Save updated settings
        await file_handlers.save_json(file_path, commission_settings)
        
        # Respond with confirmation
        response = f"✅ Set hourly rate for {role.mention} to "
        response += f"${rate}/h" if rate is not None else "cleared"
        await interaction.response.send_message(response, ephemeral=ephemeral)
    
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
        override_role: bool = None
    ):
        """Set commission percentage for a specific user"""
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        # Validate input
        if not self.validate_percentage(percentage):
            await interaction.response.send_message(
                "❌ Invalid percentage. Must be between 0 and 100.", 
                ephemeral=ephemeral
            )
            return
        
        # Load existing settings
        file_path = settings.get_guild_commission_path(interaction.guild.id)
        commission_settings = await file_handlers.load_json(file_path, {})
        
        # Ensure 'users' key exists
        commission_settings.setdefault('users', {})
        
        # Update user settings
        user_settings = commission_settings['users'].get(str(user.id), {})
        user_settings['commission_percentage'] = percentage

        if override_role is None:
            override_role = commission_settings['users'].get(str(user.id), {}).get('override_role', False)

        user_settings['override_role'] = override_role
        commission_settings['users'][str(user.id)] = user_settings
        
        # Save updated settings
        await file_handlers.save_json(file_path, commission_settings)
        
        # Respond with confirmation
        response = f"✅ Set commission for {user.mention} to "
        response += f"{percentage}%" if percentage is not None else "cleared"
        response += f" (Override Role: {override_role})"
        await interaction.response.send_message(response, ephemeral=ephemeral)
    
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
        override_role: bool = None
    ):
        """Set hourly rate for a specific user"""
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        # Validate input
        if not self.validate_hourly_rate(rate):
            await interaction.response.send_message(
                "❌ Invalid hourly rate. Must be a non-negative number.", 
                ephemeral=ephemeral
            )
            return
        
        # Load existing settings
        file_path = settings.get_guild_commission_path(interaction.guild.id)
        commission_settings = await file_handlers.load_json(file_path, {})
        
        # Ensure 'users' key exists
        commission_settings.setdefault('users', {})
        
        # Update user settings
        user_settings = commission_settings['users'].get(str(user.id), {})
        user_settings['hourly_rate'] = rate

        if override_role is None:
            override_role = commission_settings['users'].get(str(user.id), {}).get('override_role', False)

        user_settings['override_role'] = override_role
        commission_settings['users'][str(user.id)] = user_settings
        
        # Save updated settings
        await file_handlers.save_json(file_path, commission_settings)
        
        # Respond with confirmation
        response = f"✅ Set hourly rate for {user.mention} to "
        response += f"${rate}/h" if rate is not None else "cleared"
        response += f" (Override Role: {override_role})"
        await interaction.response.send_message(response, ephemeral=ephemeral)
    
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
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        # Load existing settings
        file_path = settings.get_guild_commission_path(interaction.guild.id)
        commission_settings = await file_handlers.load_json(file_path, {})
        
        # Ensure user settings exist
        user_settings = commission_settings['users'].get(str(user.id), {})
        if not user_settings:
            await interaction.response.send_message(
                "❌ No commission settings found for this user.", 
                ephemeral=ephemeral
            )
            return
        
        # Toggle override_role
        user_settings['override_role'] = not user_settings.get('override_role', False)
        commission_settings['users'][str(user.id)] = user_settings
        
        # Save updated settings
        await file_handlers.save_json(file_path, commission_settings)
        
        # Respond with confirmation
        response = f"✅ Toggled role override for {user.mention} to {user_settings['override_role']}"
        await interaction.response.send_message(response, ephemeral=ephemeral)
    
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
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        # Load existing settings
        file_path = settings.get_guild_commission_path(interaction.guild.id)
        guild_settings = await file_handlers.load_json(file_path, {})
        
        # Ensure 'roles' and 'users' keys exist
        guild_settings.setdefault('roles', {})
        guild_settings.setdefault('users', {})

        # Create an embed to display commission settings
        embed = discord.Embed(title="Commission Settings", color=0x009933)
        
        if role:
            # View specific role commission settings
            role_settings = guild_settings['roles'].get(str(role.id), {})
            embed.description = f"Settings for Role: {role.mention}"
            embed.add_field(
                name="Commission", 
                value=f"{role_settings.get('commission_percentage', '❓') or '❓'}%", 
                inline=True
            )
            embed.add_field(
                name="Hourly Rate", 
                value=f"${role_settings.get('hourly_rate', '❓') or '❓'}/h", 
                inline=True
            )
        elif user:
            # View specific user commission settings
            user_settings = guild_settings['users'].get(str(user.id), {})
            embed.description = f"Settings for User: {user.mention}"
            embed.add_field(
                name="Commission", 
                value=f"{user_settings.get('commission_percentage', '❓') or '❓'}%", 
                inline=True
            )
            embed.add_field(
                name="Hourly Rate", 
                value=f"${user_settings.get('hourly_rate', '❓') or '❓'}/h", 
                inline=True
            )
            embed.add_field(
                name="Override Role", 
                value=user_settings.get('override_role', False), 
                inline=True
            )
        else:
            # View all commission settings summary
            embed.description = "Summary of Commission Settings"

            if not guild_settings['roles'] and not guild_settings['users']:
                embed.add_field(name="", value="❌ No settings found", inline=False)
            
            # Role commission settings summary
            role_summary = []
            for role_id, role_data in guild_settings['roles'].items():
                role = interaction.guild.get_role(int(role_id))
                if role:
                    role_summary.append(
                        f"{role.name}: Commission {role_data.get('commission_percentage', '❓') or '❓'}%, "
                        f"Hourly ${role_data.get('hourly_rate', '❓') or '❓'}"
                    )
            
            if role_summary:
                embed.add_field(name="Role Settings", value="\n".join(role_summary), inline=False)
            
            # User commission settings summary
            user_summary = []
            for user_id, user_data in guild_settings['users'].items():
                member = interaction.guild.get_member(int(user_id))
                if member:
                    user_summary.append(
                        f"{member.name}: Commission {user_data.get('commission_percentage', '❓') or '❓'}%, "
                        f"Hourly ${user_data.get('hourly_rate', '❓') or '❓'}, "
                        f"Override: {user_data.get('override_role', False)}"
                    )
            
            if user_summary:
                embed.add_field(name="User Settings", value="\n".join(user_summary), inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)

    async def get_agency_name(self, guild_id):
        file_path = settings.get_guild_display_path(guild_id)
        settings_data = await file_handlers.load_json(file_path, {
            "ephemeral_responses": True,
            "show_average": True,
            "agency_name": "Agency",
            "show_ids": True,
            "bot_name": "Shift Calculator"
        })
        return settings_data.get("agency_name", "Agency")

    async def get_show_ids(self, guild_id):
        file_path = settings.get_guild_display_path(guild_id)
        settings_data = await file_handlers.load_json(file_path, {
            "ephemeral_responses": True,
            "show_average": True,
            "agency_name": "Agency",
            "show_ids": True,
            "bot_name": "Shift Calculator"
        })
        return settings_data.get("show_ids", True)

    async def get_bot_name(self, guild_id):
        file_path = settings.get_guild_display_path(guild_id)
        settings_data = await file_handlers.load_json(file_path, {
            "ephemeral_responses": True,
            "show_average": True,
            "agency_name": "Agency",
            "show_ids": True,
            "bot_name": "Shift Calculator"
        })
        return settings_data.get("bot_name", "Shift Calculator")

    @app_commands.command(name="set-agency-name", description="Set custom agency name for this server")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(name="The custom agency name to display that bot will use")
    async def set_agency_name(self, interaction: discord.Interaction, name: str):
        """Set custom agency name"""
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)
        
        file_path = settings.get_guild_display_path(interaction.guild.id)
        settings_data = await file_handlers.load_json(file_path, {
            "ephemeral_responses": True,
            "show_average": True,
            "agency_name": "Agency",
            "show_ids": True,
            "bot_name": "Shift Calculator"
        })
        
        settings_data["agency_name"] = name
        success = await file_handlers.save_json(file_path, settings_data)
        
        if success:
            await interaction.response.send_message(f"✅ Agency name set to: {name}", ephemeral=ephemeral)
        else:
            await interaction.response.send_message("❌ Failed to save agency name", ephemeral=ephemeral)

    @app_commands.command(name="toggle-id-display", description="Toggle display of IDs in reports")
    @app_commands.default_permissions(administrator=True)
    async def toggle_id_display(self, interaction: discord.Interaction):
        """Toggle ID display"""
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)
        
        file_path = settings.get_guild_display_path(interaction.guild.id)
        settings_data = await file_handlers.load_json(file_path, {
            "ephemeral_responses": True,
            "show_average": True,
            "agency_name": "Agency",
            "show_ids": True,
            "bot_name": "Shift Calculator"
        })
        
        current_setting = settings_data.get("show_ids", True)
        new_setting = not current_setting
        
        settings_data["show_ids"] = new_setting
        success = await file_handlers.save_json(file_path, settings_data)
        
        if success:
            status = f"**enabled**" if new_setting else f"**disabled**"
            await interaction.response.send_message(f"✅ ID display {status}", ephemeral=ephemeral)
        else:
            await interaction.response.send_message("❌ Failed to toggle ID display", ephemeral=ephemeral)

    @app_commands.command(name="set-bot-name", description="Set custom bot name for this server")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(name="The custom name for the bot")
    async def set_bot_name(self, interaction: discord.Interaction, name: str):
        """Set custom bot name"""
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)
        
        file_path = settings.get_guild_display_path(interaction.guild.id)
        settings_data = await file_handlers.load_json(file_path, {
            "ephemeral_responses": True,
            "show_average": True,
            "agency_name": "Agency",
            "show_ids": True,
            "bot_name": "Shift Calculator"
        })
        
        settings_data["bot_name"] = name
        success = await file_handlers.save_json(file_path, settings_data)
        
        if success:
            await interaction.response.send_message(f"✅ Bot name set to: {name}", ephemeral=ephemeral)
        else:
            await interaction.response.send_message("❌ Failed to save bot name", ephemeral=ephemeral)

    
    @app_commands.command(name="view-display-settings", description="View the current display settings")
    @app_commands.default_permissions(administrator=True)
    async def view_display_settings(self, interaction: discord.Interaction):
        """View the current display settings"""
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)
        
        guild_id = interaction.guild.id
        file_path = settings.get_guild_display_path(guild_id)
        guild_settings = await file_handlers.load_json(file_path, {
                "ephemeral_responses": True,
                "show_average": True,
                "agency_name": "Agency",
                "show_ids": True,
                "bot_name": "Shift Calculator"
        })
        
        embed = discord.Embed(title="Display Settings", color=0x00ff00)
        logger.info(f"Ephemeral Responses: {await self.get_ephemeral_setting(guild_id)}")
        embed.add_field(name="Ephemeral Responses", value=await self.get_ephemeral_setting(guild_id), inline=False)
        logger.info(f"Show Averages: {await self.get_average_setting(guild_id)}")
        embed.add_field(name="Show Averages", value=await self.get_average_setting(guild_id), inline=False)
        logger.info(f"Agency Name: {await self.get_agency_name(guild_id)}")
        embed.add_field(name="Agency Name", value=await self.get_agency_name(guild_id), inline=False)
        logger.info(f"Show IDs: {await self.get_show_ids(guild_id)}")
        embed.add_field(name="Show IDs", value=await self.get_show_ids(guild_id), inline=False)
        logger.info(f"Bot Name: {await self.get_bot_name(guild_id)}")
        embed.add_field(name="Bot Name", value=await self.get_bot_name(guild_id), inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)

    async def get_average_setting(self, guild_id):
        guild_settings_file = settings.get_guild_display_path(guild_id)
        guild_settings = await file_handlers.load_json(guild_settings_file, {
            "ephemeral_responses": True,
            "show_average": True,
            "agency_name": "Agency",
            "show_ids": True,
            "bot_name": "Shift Calculator"
        })
        return guild_settings.get("show_average", True)

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
        guild_settings_file = settings.get_guild_display_path(guild_id)
        
        # Load settings data
        guild_settings = await file_handlers.load_json(guild_settings_file, {
            "ephemeral_responses": True,
            "show_average": True,
            "agency_name": "Agency",
            "show_ids": True,
            "bot_name": "Shift Calculator"
        })
        
        # Toggle the show_average setting
        new_setting = not guild_settings.get("show_average", True)
        guild_settings["show_average"] = new_setting
        
        # Save updated settings
        success = await file_handlers.save_json(guild_settings_file, guild_settings)
        
        if success:
            status = "enabled" if new_setting else "disabled"
            logger.info(f"User {interaction.user.name} ({interaction.user.id}) {status} average display for guild {guild_id}")
            await interaction.response.send_message(f"✅ Performance average display is now **{status}**.", ephemeral=ephemeral)
        else:
            logger.error(f"Failed to save display settings for guild {guild_id}")
            await interaction.response.send_message("❌ Failed to update settings. Please try again.", ephemeral=ephemeral)

    # Role Management
    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="set-role", description="Set a role's percentage cut")
    @app_commands.describe(role="The role to configure", percentage="The percentage cut (e.g., 6.5)")
    async def set_role(self, interaction: discord.Interaction, role: discord.Role, percentage: str):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)
        
        try:
            logger.info(f"User {interaction.user.name} used set-role command for role {role.name} with percentage {percentage}")
            
            percentage_decimal = validators.validate_percentage(percentage)
            if percentage_decimal is None:
                await interaction.response.send_message(
                    "❌ Percentage must be a valid number between 0 and 100.", 
                    ephemeral=ephemeral
                )
                return
            
            guild_id = interaction.guild.id
            role_file = settings.get_guild_roles_path(guild_id)
            
            # Load with empty dict as default
            role_data = await file_handlers.load_json(role_file, {})
            
            role_id = str(role.id)
            role_data[role_id] = float(percentage_decimal)
            
            success = await file_handlers.save_json(role_file, role_data)
            
            if success:
                logger.info(f"Role {role.name} ({role_id}) percentage set to {percentage_decimal}% by {interaction.user.name}")
                await interaction.response.send_message(
                    f"✅ {role.name} now has {percentage_decimal}% cut!", 
                    ephemeral=ephemeral
                )
            else:
                logger.error(f"Failed to save role data for {role.name} ({role_id}) by {interaction.user.name}")
                await interaction.response.send_message(
                    "❌ Failed to save role data. Please try again later.", 
                    ephemeral=ephemeral
                )
        except Exception as e:
            logger.error(f"Error in set_role: {str(e)}")
            await interaction.response.send_message(
                "❌ An unexpected error occurred. See logs for details.", 
                ephemeral=ephemeral
            )

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="remove-role", description="Remove a role's percentage configuration")
    @app_commands.describe(role="The role to remove")
    async def remove_role(self, interaction: discord.Interaction, role: discord.Role):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)
        
        try:
            logger.info(f"User {interaction.user.name} used remove-role command for role {role.name}")
            
            guild_id = interaction.guild.id
            role_file = settings.get_guild_roles_path(guild_id)
            role_data = await file_handlers.load_json(role_file, {})
            
            role_id = str(role.id)
            if role_id not in role_data:
                logger.warning(f"Role {role.name} ({role_id}) not found in configuration")
                await interaction.response.send_message(
                    f"❌ {role.name} does not have a configured percentage.", 
                    ephemeral=ephemeral
                )
                return
            
            del role_data[role_id]
            success = await file_handlers.save_json(role_file, role_data)
            
            if success:
                logger.info(f"Role {role.name} ({role_id}) removed from configuration")
                await interaction.response.send_message(
                    f"✅ {role.name} has been removed from percentage configuration!", 
                    ephemeral=ephemeral
                )
            else:
                logger.error(f"Failed to remove role {role.name} ({role_id})")
                await interaction.response.send_message(
                    "❌ Failed to save role data. Please try again later.", 
                    ephemeral=ephemeral
                )
        except Exception as e:
            logger.error(f"Error in remove_role: {str(e)}")
            await interaction.response.send_message(
                "❌ An unexpected error occurred. See logs for details.", 
                ephemeral=ephemeral
            )

    # Shift Management
    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="set-shift", description="Add a valid shift name")
    @app_commands.describe(shift="The name of the shift to add")
    async def set_shift(self, interaction: discord.Interaction, shift: str):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)
        
        try:
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("❌ This command is restricted to administrators.", ephemeral=ephemeral)
                return
            
            logger.info(f"User {interaction.user.name} used set-shift command for shift '{shift}'")
            
            if not shift.strip():
                await interaction.response.send_message("❌ Shift name cannot be empty.", ephemeral=ephemeral)
                return
                
            guild_id = interaction.guild.id
            shift_file = settings.get_guild_shifts_path(guild_id)
            existing_shifts = await file_handlers.load_json(shift_file, [])
            
            # Case-insensitive check but preserve original casing
            if any(shift.lower() == s.lower() for s in existing_shifts):
                await interaction.response.send_message(f"❌ Shift '{shift}' already exists!", ephemeral=ephemeral)
                return
            
            existing_shifts.append(shift.strip())
            success = await file_handlers.save_json(shift_file, existing_shifts)
            
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
        
        try:
            guild_id = interaction.guild.id
            shift_file = settings.get_guild_shifts_path(guild_id)
            existing_shifts = await file_handlers.load_json(shift_file, [])
            
            # Case-insensitive search
            normalized_shift = next((s for s in existing_shifts if s.lower() == shift.lower()), None)
            if normalized_shift is None:
                await interaction.response.send_message(f"❌ Shift '{shift}' doesn't exist!", ephemeral=ephemeral)
                return
            
            existing_shifts.remove(normalized_shift)
            success = await file_handlers.save_json(shift_file, existing_shifts)
            
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
        
        try:
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("❌ This command is restricted to administrators.", ephemeral=ephemeral)
                return

            logger.info(f"User {interaction.user.name} used set-period command for period '{period}'")
            
            if not period.strip():
                await interaction.response.send_message("❌ Period name cannot be empty.", ephemeral=ephemeral)
                return
                
            guild_id = interaction.guild.id
            period_file = settings.get_guild_periods_path(guild_id)
            existing_periods = await file_handlers.load_json(period_file, [])
            
            # Case-insensitive check with original casing preservation
            if any(period.lower() == p.lower() for p in existing_periods):
                await interaction.response.send_message(f"❌ Period '{period}' already exists!", ephemeral=ephemeral)
                return
            
            existing_periods.append(period.strip())
            success = await file_handlers.save_json(period_file, existing_periods)
            
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
        
        try:
            guild_id = interaction.guild.id
            period_file = settings.get_guild_periods_path(guild_id)
            existing_periods = await file_handlers.load_json(period_file, [])
            
            # Case-insensitive search
            normalized_period = next((p for p in existing_periods if p.lower() == period.lower()), None)
            if normalized_period is None:
                await interaction.response.send_message(f"❌ Period '{period}' doesn't exist!", ephemeral=ephemeral)
                return
            
            existing_periods.remove(normalized_period)
            success = await file_handlers.save_json(period_file, existing_periods)
            
            if success:
                await interaction.response.send_message(f"✅ Period '{normalized_period}' removed!", ephemeral=ephemeral)
            else:
                await interaction.response.send_message("❌ Failed to save period data. Please try again later.", ephemeral=ephemeral)
        except Exception as e:
            logger.error(f"Error in remove_period: {str(e)}")
            await interaction.response.send_message("❌ An unexpected error occurred. See logs for details.", ephemeral=ephemeral)

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
        
        try:
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("❌ This command is restricted to administrators.", ephemeral=ephemeral)
                return

            # Parse inputs
            from_num = validators.parse_money(from_range)
            to_num = validators.parse_money(to_range)
            bonus_amount = validators.parse_money(bonus)
            
            # Validation
            if None in (from_num, to_num, bonus_amount):
                await interaction.response.send_message("❌ Invalid number format.", ephemeral=ephemeral)
                return
                
            if from_num >= to_num:
                await interaction.response.send_message("❌ The 'from' value must be less than the 'to' value.", ephemeral=ephemeral)
                return
                
            guild_id = interaction.guild.id
            bonus_file = settings.get_guild_bonus_rules_path(guild_id)
            bonus_rules = await file_handlers.load_json(bonus_file, [])
            
            new_rule = {"from": float(from_num), "to": float(to_num), "amount": float(bonus_amount)}
            
            # Check for overlaps
            for rule in bonus_rules:
                if (from_num <= rule["to"] and to_num >= rule["from"]):
                    await interaction.response.send_message("❌ This rule overlaps with an existing bonus rule.", ephemeral=ephemeral)
                    return
            
            bonus_rules.append(new_rule)
            # Sort rules by 'from' value
            bonus_rules.sort(key=lambda x: x["from"])
            success = await file_handlers.save_json(bonus_file, bonus_rules)
            
            if success:
                response = f"✅ Bonus rule added: ${from_num:,.2f}-${to_num:,.2f} → ${bonus_amount:,.2f}!"
                await interaction.response.send_message(response, ephemeral=ephemeral)
            else:
                await interaction.response.send_message("❌ Failed to save bonus rule.", ephemeral=ephemeral)
                
        except Exception as e:
            logger.error(f"Error in set_bonus_rule: {str(e)}")
            await interaction.response.send_message("❌ An unexpected error occurred. See logs for details.", ephemeral=ephemeral)

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="remove-bonus-rule", description="Remove a bonus rule for a revenue range")
    @app_commands.describe(
        from_range="Lower bound of revenue",
        to_range="Upper bound of revenue"
    )
    async def remove_bonus_rule(self, interaction: discord.Interaction, from_range: str, to_range: str):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)
        
        try:
            # Parse inputs
            from_num = validators.parse_money(from_range)
            to_num = validators.parse_money(to_range)
            
            if None in (from_num, to_num):
                await interaction.response.send_message("❌ Invalid number format.", ephemeral=ephemeral)
                return
                
            guild_id = interaction.guild.id
            bonus_file = settings.get_guild_bonus_rules_path(guild_id)
            bonus_rules = await file_handlers.load_json(bonus_file, [])
            
            # Find exact match
            rule_to_remove = next(
                (rule for rule in bonus_rules 
                if rule["from"] == from_num and rule["to"] == to_num),
                None
            )
            
            if not rule_to_remove:
                await interaction.response.send_message(f"❌ No bonus rule found for ${from_num:,.2f}-${to_num:,.2f}.", ephemeral=ephemeral)
                return
                
            bonus_rules.remove(rule_to_remove)
            success = await file_handlers.save_json(bonus_file, bonus_rules)
            
            if success:
                response = f"✅ Bonus rule removed: ${from_num:,.2f}-${to_num:,.2f}"
                await interaction.response.send_message(response, ephemeral=ephemeral)
            else:
                await interaction.response.send_message("❌ Failed to remove bonus rule.", ephemeral=ephemeral)
                
        except Exception as e:
            logger.error(f"Error in remove_bonus_rule: {str(e)}")
            await interaction.response.send_message("❌ An unexpected error occurred. See logs for details.", ephemeral=ephemeral)

    # List Commands
    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="list-roles", description="List configured roles and percentages")
    async def list_roles(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)
        
        try:
            guild_id = interaction.guild.id
            role_file = settings.get_guild_roles_path(guild_id)
            role_data = await file_handlers.load_json(role_file, {})
            
            if not role_data:
                await interaction.response.send_message("❌ No roles configured.", ephemeral=ephemeral)
                return
                
            embed = discord.Embed(title="Configured Roles", color=discord.Color.blue())
            
            for role_id, percentage in role_data.items():
                role = interaction.guild.get_role(int(role_id))
                role_name = role.name if role else f"Unknown Role ({role_id})"
                embed.add_field(name=role_name, value=f"{percentage}%", inline=True)
            
            await interaction.response.send_message(embed=embed, ephemeral=ephemeral)
            
        except Exception as e:
            logger.error(f"Error in list_roles: {str(e)}")
            await interaction.response.send_message(
                "❌ Failed to load role data.", 
                ephemeral=ephemeral
            )

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="list-shifts", description="List configured shifts")
    async def list_shifts(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)
        
        try:
            guild_id = interaction.guild.id
            shift_file = settings.get_guild_shifts_path(guild_id)
            guild_shifts = await file_handlers.load_json(shift_file, [])
            
            if not guild_shifts:
                await interaction.response.send_message("❌ No shifts configured.", ephemeral=ephemeral)
                return
                
            embed = discord.Embed(title="Configured Shifts", color=discord.Color.blue())
            embed.add_field(name="Shifts", value="\n".join(f"• {shift}" for shift in guild_shifts))
            await interaction.response.send_message(embed=embed, ephemeral=ephemeral)
            
        except Exception as e:
            logger.error(f"Error in list_shifts: {str(e)}")
            await interaction.response.send_message("❌ Failed to load shift data.", ephemeral=ephemeral)

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="list-periods", description="List configured periods")
    async def list_periods(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)
        
        try:
            guild_id = interaction.guild.id
            period_file = settings.get_guild_periods_path(guild_id)
            guild_periods = await file_handlers.load_json(period_file, [])
            
            if not guild_periods:
                await interaction.response.send_message("❌ No periods configured.", ephemeral=ephemeral)
                return
                
            embed = discord.Embed(title="Configured Periods", color=discord.Color.blue())
            embed.add_field(name="Periods", value="\n".join(f"• {period}" for period in guild_periods))
            await interaction.response.send_message(embed=embed, ephemeral=ephemeral)
            
        except Exception as e:
            logger.error(f"Error in list_periods: {str(e)}")
            await interaction.response.send_message("❌ Failed to load period data.", ephemeral=ephemeral)

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="list-bonus-rules", description="List configured bonus rules")
    async def list_bonus_rules(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)
        
        try:
            guild_id = interaction.guild.id
            bonus_file = settings.get_guild_bonus_rules_path(guild_id)
            bonus_rules = await file_handlers.load_json(bonus_file, [])
            
            if not bonus_rules:
                await interaction.response.send_message("❌ No bonus rules configured.", ephemeral=ephemeral)
                return
                
            embed = discord.Embed(title="Bonus Rules", color=discord.Color.green())
            
            for rule in sorted(bonus_rules, key=lambda x: x["from"]):
                embed.add_field(
                    name=f"${rule['from']:,.2f} - ${rule['to']:,.2f}",
                    value=f"Bonus: ${rule['amount']:,.2f}",
                    inline=False
                )

            await interaction.response.send_message(embed=embed, ephemeral=ephemeral)
            
        except Exception as e:
            logger.error(f"Error in list_bonus_rules: {str(e)}")
            await interaction.response.send_message("❌ Failed to load bonus rules.", ephemeral=ephemeral)

    # Model Management
    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="set-model", description="Add a valid model name")
    @app_commands.describe(model="The name of the model to add")
    async def set_model(self, interaction: discord.Interaction, model: str):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        guild_id = interaction.guild.id
        file_path = settings.get_guild_models_path(guild_id)
        
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ This command is restricted to administrators.", ephemeral=ephemeral)
            return
        
        logger.info(f"User {interaction.user.name} used set-model command for model '{model}'")
        
        if not model.strip():
            await interaction.response.send_message("❌ Model name cannot be empty.", ephemeral=ephemeral)
            return
            
        guild_id = str(interaction.guild.id)
        model_data = await file_handlers.load_json(file_path, [])
        existing_models = model_data
        
        if model.lower() in [m.lower() for m in existing_models]:
            await interaction.response.send_message(f"❌ Model '{model}' already exists!", ephemeral=ephemeral)
            return
        
        model_data.append(model)
        success = await file_handlers.save_json(file_path, model_data)
        
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
            await interaction.response.send_message("❌ This command is restricted to administrators.", ephemeral=ephemeral)
            return
        
        guild_id = interaction.guild.id
        file_path = settings.get_guild_models_path(guild_id)
        
        # Load existing models
        try:
            model_data = await file_handlers.load_json(file_path, [])
        
        except Exception as e:
            logger.error(f"Error loading models: {str(e)}")
            await interaction.response.send_message("❌ Failed to load model data.", ephemeral=ephemeral)
            return

        # Find and remove the model
        normalized_model = next((m for m in model_data if m.lower() == model.lower()), None)
        if normalized_model is None:
            await interaction.response.send_message(f"❌ Model '{model}' doesn't exist!", ephemeral=ephemeral)
            return
        
        try:
            model_data.remove(normalized_model)
            success = await file_handlers.save_json(file_path, model_data)
        except Exception as e:
            logger.error(f"Error saving models: {str(e)}")
            success = False

        if success:
            await interaction.response.send_message(f"✅ Model '{normalized_model}' removed!", ephemeral=ephemeral)
        else:
            await interaction.response.send_message("❌ Failed to save model data. Please try again later.", ephemeral=ephemeral)

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="list-models", description="List configured models")
    async def list_models(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        guild_id = interaction.guild.id
        file_path = settings.get_guild_models_path(guild_id)
        
        guild_models = await file_handlers.load_json(file_path, [])
        
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

        guild_name = interaction.guild.name

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Confirm", style=discord.ButtonStyle.danger, custom_id="confirm_clear_earnings"))
        view.add_item(discord.ui.Button(label="Cancel", style=discord.ButtonStyle.success, custom_id="cancel_clear_earnings"))

        async def confirm_callback(interaction):
            await self.reset_earnings(interaction)
            await interaction.response.edit_message(content=f"✅ All earnings data for the guild ({guild_name}) has been successfully cleared.", view=None)

        async def cancel_callback(interaction):
            await interaction.response.edit_message(content="❌ Canceled.", view=None)

        view.children[0].callback = confirm_callback
        view.children[1].callback = cancel_callback
        await interaction.response.send_message("‼️🚨‼ Are you sure you want to clear all earnings data?", view=view, ephemeral=ephemeral)

    
    async def remove_sale_by_id(
        self, 
        interaction: discord.Interaction,
        sale_ids: Optional[list[str]] = None,
        users: Optional[list[discord.User]] = None
    ):
        """Helper function to remove sales by IDs or all sales for multiple users."""
        earnings_data = await file_handlers.load_json(
            settings.get_guild_earnings_path(interaction.guild.id),
            {}
        )

        removed_entries = {}
        total_removed = 0

        try:
            if sale_ids is None:
                # Remove all entries for specified users
                for user in users:
                    user_key = f"<@{user.id}>"
                    if user_key in earnings_data:
                        count = len(earnings_data[user_key])
                        if count > 0:
                            earnings_data[user_key] = []
                            removed_entries[user_key] = {
                                'count': count,
                                'user_obj': user
                            }
                            total_removed += count
            else:
                # Remove specific IDs from specified users (or all users if None)
                sale_ids = list(set(sale_ids))
                target_users = users or [None]  # [None] represents "all users"
                
                for user in target_users:
                    if user:
                        user_key = f"<@{user.id}>"
                        entries = earnings_data.get(user_key, [])
                        original_count = len(entries)
                        earnings_data[user_key] = [e for e in entries if e["id"] not in sale_ids]
                        removed_count = original_count - len(earnings_data[user_key])
                        if removed_count > 0:
                            removed_entries[user_key] = {
                                'count': removed_count,
                                'user_obj': user
                            }
                            total_removed += removed_count
                    else:
                        # Process all users
                        for user_key, entries in list(earnings_data.items()):
                            original_count = len(entries)
                            earnings_data[user_key] = [e for e in entries if e["id"] not in sale_ids]
                            removed_count = original_count - len(earnings_data[user_key])
                            if removed_count > 0:
                                removed_entries[user_key] = {
                                    'count': removed_count,
                                    'user_obj': None
                                }
                                total_removed += removed_count

            if not removed_entries:
                return (False, "❌ No matching sales found for the specified criteria.")

            success = await file_handlers.save_json(
                settings.get_guild_earnings_path(interaction.guild.id),
                earnings_data
            )

            if not success:
                return (False, "❌ Failed to save earnings data.")

            # Build success message with proper user resolution
            message = []
            if sale_ids:
                id_list = ", ".join(f"`{s_id}`" for s_id in sale_ids)
                sale_text = "sales" if len(sale_ids) > 1 else "sale"
                message.append(f"✅ {sale_text.capitalize()} with IDs {id_list} removed:")
            else:
                message.append("✅ All sales removed for:")

            for user_key, data in removed_entries.items():
                user_obj = data['user_obj'] or interaction.guild.get_member(int(re.search(r'\d+', user_key).group()))
                if user_obj:
                    name = f"{user_obj.display_name} (@{user_obj.name})"
                else:
                    name = f"Unknown ({user_key})"
                message.append(f"- `{name}`: {data['count']} entries")

            message.append(f"\nTotal removed: {total_removed} entries")
            return (True, "\n".join(message))

        except Exception as e:
            return (False, f"❌ Error processing request: {str(e)}")

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(
        name="remove-sale",
        description="Remove sales by IDs or all sales for multiple users"
    )
    @app_commands.describe(
        sale_ids="Comma-separated sale IDs (leave empty to remove all for users)",
        users="Comma-separated user mentions to target"
    )
    async def remove_sale(
        self,
        interaction: discord.Interaction,
        sale_ids: Optional[str] = None,
        users: Optional[str] = None
    ):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        # Validate input
        if not sale_ids and not users:
            await interaction.response.send_message(
                "❌ Must provide either sale IDs or user mentions.",
                ephemeral=ephemeral
            )
            return

        # Process user mentions
        user_objs = []
        if users:
            # Extract user IDs from mentions using regex
            user_ids = re.findall(r'<@!?(\d+)>', users)
            if not user_ids:
                await interaction.response.send_message(
                    "❌ Invalid user mentions format. Use @mentions.",
                    ephemeral=ephemeral
                )
                return

            # Convert to User objects
            for user_id in user_ids:
                user = interaction.guild.get_member(int(user_id))
                if user:
                    user_objs.append(user)
                else:
                    await interaction.response.send_message(
                        f"❌ User with ID {user_id} not found in server.",
                        ephemeral=ephemeral
                    )
                    return

        # Process sale IDs
        sale_id_list = None
        if sale_ids:
            sale_id_list = [s_id.strip() for s_id in sale_ids.split(',') if s_id.strip()]
            if not sale_id_list:
                await interaction.response.send_message(
                    "❌ Invalid sale IDs format.",
                    ephemeral=ephemeral
                )
                return
            sale_id_list = list(set(sale_id_list))

        # Count affected entries
        earnings_data = await file_handlers.load_json(
            settings.get_guild_earnings_path(interaction.guild.id),
            {}
        )

        total_entries = 0
        user_counts = {}

        try:
            if sale_id_list:
                # Count entries matching sale IDs
                if user_objs:
                    for user in user_objs:
                        user_key = f"<@{user.id}>"
                        entries = earnings_data.get(user_key, [])
                        count = sum(1 for e in entries if e["id"] in sale_id_list)
                        if count > 0:
                            user_counts[user_key] = {
                                'count': count,
                                'user_obj': user
                            }
                            total_entries += count
                else:
                    # Count across all users
                    for user_key, entries in earnings_data.items():
                        count = sum(1 for e in entries if e["id"] in sale_id_list)
                        if count > 0:
                            user_counts[user_key] = {
                                'count': count,
                                'user_obj': interaction.guild.get_member(int(re.search(r'\d+', user_key).group()))
                            }
                            total_entries += count
            else:
                # Count all entries for specified users
                for user in user_objs:
                    user_key = f"<@{user.id}>"
                    count = len(earnings_data.get(user_key, []))
                    if count > 0:
                        user_counts[user_key] = {
                            'count': count,
                            'user_obj': user
                        }
                        total_entries += count

            if not user_counts:
                await interaction.response.send_message(
                    "❌ No matching sales found for the specified criteria.",
                    ephemeral=ephemeral
                )
                return

            # Build confirmation message
            view = discord.ui.View()
            view.add_item(discord.ui.Button(
                style=discord.ButtonStyle.danger,
                label="Confirm",
                custom_id="confirm_remove"
            ))
            view.add_item(discord.ui.Button(
                style=discord.ButtonStyle.secondary,
                label="Cancel",
                custom_id="cancel_remove"
            ))

            message = ["‼️🚨‼️ Confirm removal of:"]
            if sale_id_list:
                message.append(f"Sales IDs: {', '.join(f'`{s_id}`' for s_id in sale_id_list)}")
            else:
                message.append("ALL SALES for:")
            
            for user_key, data in user_counts.items():
                user_obj = data['user_obj']
                if user_obj:
                    name = f"{user_obj.display_name} (@{user_obj.name})"
                else:
                    name = f"Unknown ({user_key})"
                message.append(f"- `{name}`: {data['count']} entries")
            
            message.append(f"\nTotal entries to remove: {total_entries}")
            
            # Button handlers
            async def confirm_callback(interaction):
                success, result = await self.remove_sale_by_id(
                    interaction,
                    sale_id_list,
                    user_objs if user_objs else None
                )
                await interaction.response.edit_message(content=result, view=None)

            async def cancel_callback(interaction):
                await interaction.response.edit_message(
                    content="❌ Operation canceled.",
                    view=None
                )

            view.children[0].callback = confirm_callback
            view.children[1].callback = cancel_callback

            await interaction.response.send_message(
                "\n".join(message),
                view=view,
                ephemeral=ephemeral
            )

        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error: {str(e)}",
                ephemeral=ephemeral
            )

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
            await self.reset_display(interaction)
            await self.reset_compensation(interaction)
            try:
                await interaction.response.edit_message(content="✅ Configuration data has been reset for this server.", view=None)
            except discord.NotFound:
                logger.error("Ignoring exception in view %r for item %r", self, view, exc_info=True)

        async def cancel_callback(interaction):
            await interaction.response.edit_message(content="❌ Canceled.", view=None)

        view.children[0].callback = confirm_callback
        view.children[1].callback = cancel_callback
        await interaction.response.send_message(content="‼️🚨‼ Are you sure you want to reset all configuration data for this server? Earnings data will not be affected (use: `/clear-earnings`).", view=view, ephemeral=ephemeral)

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="restore-latest-backup", description="Restore the latest config backup (local files + DB sync)")
    async def restore_latest_backup(self, interaction: discord.Interaction):
        """Restores all config .bak files and syncs them to the database."""
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)
        guild_id = str(interaction.guild.id)

        async def confirm_callback(interaction: discord.Interaction):
            # Defer the interaction to prevent timeout
            await interaction.response.defer(ephemeral=ephemeral, thinking=True)

            # Use the specific config directory for the guild
            config_data_dir = settings.get_guild_path(guild_id) # Assuming settings has this helper

            if not os.path.exists(config_data_dir):
                await interaction.edit_original_response(content="❌ Server's configuration data directory not found!", view=None)
                return

            # Find .bak files specifically within the config directory
            backup_files = glob.glob(os.path.join(config_data_dir, "*.bak"))

            if not backup_files:
                await interaction.edit_original_response(content="❌ No configuration backup (.bak) files found!", view=None)
                return

            restored_files = []
            synced_files = []
            failed_restore = []
            failed_sync = []

            # --- Restoration and Sync Loop ---
            for bak_file in backup_files:
                original_file = bak_file[:-4]  # Remove .bak extension
                file_name = os.path.basename(original_file)

                # Skip earnings file if it happens to be in config dir (shouldn't be)
                # Also skip if the original file isn't a known config type for DB sync
                if file_name == settings.EARNINGS_FILE or not file_handlers._is_config_file(original_file):
                     logger.debug(f"Skipping restore/sync for non-config or earnings file: {file_name} in {config_data_dir}")
                     continue

                # 1. Restore Local File
                try:
                    shutil.copy2(bak_file, original_file)
                    logger.info(f"Restored local file {original_file} from backup for guild {guild_id}.")
                    restored_files.append(file_name)

                    # 2. Force Sync to MongoDB
                    try:
                        mongo_synced = await file_handlers.force_sync_to_mongo(original_file)
                        if mongo_synced:
                            synced_files.append(file_name)
                        else:
                            failed_sync.append(file_name)
                            logger.error(f"Failed MongoDB sync for restored file {original_file} (guild {guild_id}).")
                    except Exception as sync_e:
                        logger.error(f"Error during MongoDB sync for restored file {original_file} (guild {guild_id}): {sync_e}", exc_info=True)
                        failed_sync.append(f"{file_name} (Sync Error)")

                except Exception as restore_e:
                    logger.error(f"Failed to restore local file {original_file} from {bak_file} (guild {guild_id}): {restore_e}", exc_info=True)
                    failed_restore.append(f"{file_name} (Restore Error)")
                
                # Optional small delay
                await asyncio.sleep(0.1)


            # --- Build Response Embed ---
            embed = discord.Embed(title="Latest Config Backup Restore Results", color=discord.Color.blue())

            if restored_files:
                 embed.add_field(name="✅ Files Restored Locally", value=f"```\n{', '.join(restored_files)}\n```", inline=False)
            if synced_files:
                 embed.add_field(name="🔄 Files Synced to Database", value=f"```\n{', '.join(synced_files)}\n```", inline=False)

            if failed_restore:
                 embed.color = discord.Color.red()
                 embed.add_field(name="❌ Failed Restores (Local)", value=f"```\n{', '.join(failed_restore)}\n```", inline=False)
            if failed_sync:
                 embed.color = discord.Color.orange() if embed.color != discord.Color.red() else embed.color
                 embed.add_field(name="⚠️ Failed Database Syncs", value=f"```\n{', '.join(failed_sync)}\n```", inline=False)

            if not restored_files and not failed_restore:
                 embed.description = "No configuration files were processed for restore."
                 embed.color = discord.Color.greyple()
            elif not failed_restore and not failed_sync:
                 embed.color = discord.Color.green() # All green if no failures

            await interaction.edit_original_response(embed=embed, view=None)

        async def cancel_callback(interaction: discord.Interaction):
            await interaction.response.edit_message(content="❌ Restore operation canceled.", view=None)

        # --- Confirmation View Setup ---
        view = discord.ui.View(timeout=60) # Add timeout
        confirm_button = discord.ui.Button(label="Confirm Restore & Sync", style=discord.ButtonStyle.danger, custom_id="confirm_restore_backup")
        cancel_button = discord.ui.Button(label="Cancel", style=discord.ButtonStyle.secondary, custom_id="cancel_restore_backup")

        confirm_button.callback = confirm_callback
        cancel_button.callback = cancel_callback

        view.add_item(confirm_button)
        view.add_item(cancel_button)

        # Prevent view timeout from causing issues
        async def on_timeout():
             try:
                 # Edit message to indicate timeout if it hasn't been interacted with
                 await interaction.edit_original_response(content="Restore confirmation timed out.", view=None)
             except discord.NotFound:
                 pass # Message already deleted or changed
             except discord.HTTPException as e:
                 logger.warning(f"Failed to edit message on restore timeout: {e}")
        view.on_timeout = on_timeout


        await interaction.response.send_message(
            content="‼️🚨‼ **Confirm Restore?**\n"
                    "This will restore ALL configuration `.bak` files found in the server's config directory, "
                    "overwriting the current local files.\n"
                    "It will then attempt to **sync each restored file to the database**, overwriting DB data.",
            view=view,
            ephemeral=ephemeral
        )

    async def reset_shift(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        shift_file = settings.get_guild_shifts_path(guild_id)
        await file_handlers.save_json(shift_file, [])

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
        guild_id = interaction.guild.id
        period_file = settings.get_guild_periods_path(guild_id)
        await file_handlers.save_json(period_file, [])

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
        guild_id = interaction.guild.id
        role_file = settings.get_guild_roles_path(guild_id)
        await file_handlers.save_json(role_file, {})

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="reset-role-config", description="Reset role configuration")
    async def reset_role_config(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)
        
        async def reset_action(interaction: discord.Interaction):
            await self.reset_role(interaction)
            await interaction.response.edit_message(
                content="✅ Role configuration reset.", 
                view=None
            )
        
        view = ConfirmButton(reset_action, interaction.user.id)
        await interaction.response.send_message(
            "⚠️ Are you sure you want to reset the role configuration?", 
            view=view, 
            ephemeral=ephemeral
        )

    async def reset_bonus_rules(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        bonus_file = settings.get_guild_bonus_rules_path(guild_id)
        await file_handlers.save_json(bonus_file, [])

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
        await file_handlers.save_json(settings.get_guild_earnings_path(interaction.guild.id), {})
    
    async def reset_models(self, interaction: discord.Interaction): 
        await file_handlers.save_json(settings.get_guild_models_path(interaction.guild.id), [])

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="reset-models-config", description="Reset models configuration")
    async def reset_models_config(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        async def reset_action(interaction: discord.Interaction):
            guild_id = interaction.guild.id
            file_path = settings.get_guild_models_path(guild_id)
            
            try:
                # Reset to default empty list
                success = await file_handlers.save_json(file_path, [])
            except Exception as e:
                logger.error(f"Error resetting models: {str(e)}")
                success = False

            if success:
                await interaction.response.edit_message(content="✅ Model settings reset.", view=None)
            else:
                await interaction.response.edit_message(content="❌ Failed to reset models.", view=None)

        view = ConfirmButton(reset_action, interaction.user.id)
        await interaction.response.send_message(
            "⚠️ Are you sure you want to reset the models configuration?", 
            view=view, 
            ephemeral=ephemeral
        )

    async def reset_compensation(self, interaction: discord.Interaction):
        await file_handlers.save_json(
            settings.get_guild_commission_path(interaction.guild.id),
            {
                "roles": {},
                "users": {}
            }
        )

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="reset-compensation-config", description="Reset compensation configuration")
    async def reset_compensation_config(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        async def reset_action(interaction: discord.Interaction):
            await self.reset_compensation(interaction)
            await interaction.response.edit_message(content="✅ Compensation configuration reset.", view=None)

        view = ConfirmButton(reset_action, interaction.user.id)
        await interaction.response.send_message(
            "⚠️ Are you sure you want to reset the compensation configuration?", 
            view=view, 
            ephemeral=ephemeral
        )

    async def reset_display(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        file_path = settings.get_guild_display_path(guild_id)
        await file_handlers.save_json(file_path, {
                "ephemeral_responses": True,
                "show_average": True,
                "agency_name": "Agency",
                "show_ids": True,
                "bot_name": "Shift Calculator"
        })

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
    @app_commands.command(name="restore-shift-config", description="Restore the latest shift configuration backup")
    async def restore_shift_config(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        async def restore_action(interaction: discord.Interaction):
            file_path = settings.get_guild_shifts_path(interaction.guild.id)
            backup_file = f"{file_path}.bak"
            if os.path.exists(backup_file):
                try:
                    shutil.copy2(backup_file, file_path)
                    logger.info(f"Restored local file {file_path} from backup for guild {interaction.guild.id}.")

                    # Force sync this restored file to MongoDB
                    mongo_synced = await file_handlers.force_sync_to_mongo(file_path)

                    if mongo_synced:
                        await interaction.response.edit_message(content="✅ Shift configuration backup restored locally and synced to database.", view=None)
                    else:
                        await interaction.response.edit_message(content="⚠️ Shift configuration backup restored locally, but failed to sync to database.", view=None)

                except Exception as e:
                    logger.error(f"Error during shift restore/sync for guild {interaction.guild.id}: {e}", exc_info=True)
                    await interaction.response.edit_message(content=f"❌ Error during restore process: {e}", view=None)
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
            guild_id = interaction.guild.id
            period_file = settings.get_guild_periods_path(guild_id)
            backup_file = f"{period_file}.bak"

            if os.path.exists(backup_file):
                try:
                    shutil.copy2(backup_file, period_file)
                    logger.info(f"Restored local file {period_file} from backup for guild {guild_id}.")

                    # Force sync this restored file to MongoDB
                    mongo_synced = await file_handlers.force_sync_to_mongo(period_file)

                    if mongo_synced:
                        await interaction.response.edit_message(
                            content="✅ Period configuration backup restored locally and synced to database.",
                            view=None
                        )
                    else:
                         await interaction.response.edit_message(
                            content="⚠️ Period configuration backup restored locally, but failed to sync to database.",
                            view=None
                        )
                except Exception as e:
                    logger.error(f"Error during period restore/sync for guild {guild_id}: {e}", exc_info=True)
                    await interaction.response.edit_message(content=f"❌ Error during restore process: {e}", view=None)
            else:
                await interaction.response.edit_message(
                    content="❌ No period configuration backup found.",
                    view=None
                )

        view = ConfirmButton(restore_action, interaction.user.id)
        await interaction.response.send_message(
            "⚠️ Are you sure you want to restore the period configuration backup?",
            view=view,
            ephemeral=ephemeral
        )

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="restore-role-backup", description="Restore the latest role configuration backup")
    async def restore_role_backup(self, interaction: discord.Interaction):
        # NOTE: This restores the *old* role_percentages.json.
        # The newer system uses commission_settings.json.
        # Consider deprecating or updating this command.
        # For now, it will restore the old file if it exists.
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        async def restore_action(interaction: discord.Interaction):
            guild_id = interaction.guild.id
            role_file = settings.get_guild_roles_path(guild_id) # OLD FILE PATH
            backup_file = f"{role_file}.bak"

            if os.path.exists(backup_file):
                try:
                    shutil.copy2(backup_file, role_file)
                    logger.info(f"Restored local file {role_file} from backup for guild {guild_id}.")

                    # Force sync this restored file to MongoDB
                    mongo_synced = await file_handlers.force_sync_to_mongo(role_file)

                    if mongo_synced:
                         await interaction.response.edit_message(
                            content="✅ (Legacy) Role percentage configuration backup restored locally and synced to database.",
                            view=None
                        )
                    else:
                        await interaction.response.edit_message(
                            content="⚠️ (Legacy) Role percentage configuration backup restored locally, but failed to sync to database.",
                            view=None
                        )
                except Exception as e:
                    logger.error(f"Error during legacy role restore/sync for guild {guild_id}: {e}", exc_info=True)
                    await interaction.response.edit_message(content=f"❌ Error during restore process: {e}", view=None)

            else:
                await interaction.response.edit_message(
                    content="❌ No (legacy) role configuration backup found.",
                    view=None
                )

        view = ConfirmButton(restore_action, interaction.user.id)
        await interaction.response.send_message(
            "⚠️ This restores the *legacy* role percentage file. Are you sure?",
            view=view,
            ephemeral=ephemeral
        )


    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="restore-bonus-backup", description="Restore the latest bonus rules configuration backup")
    async def restore_bonus_backup(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        async def restore_action(interaction: discord.Interaction):
            guild_id = interaction.guild.id
            bonus_file = settings.get_guild_bonus_rules_path(guild_id)
            backup_file = f"{bonus_file}.bak"

            if os.path.exists(backup_file):
                try:
                    shutil.copy2(backup_file, bonus_file)
                    logger.info(f"Restored local file {bonus_file} from backup for guild {guild_id}.")

                     # Force sync this restored file to MongoDB
                    mongo_synced = await file_handlers.force_sync_to_mongo(bonus_file)

                    if mongo_synced:
                        await interaction.response.edit_message(
                            content="✅ Bonus rules configuration backup restored locally and synced to database.",
                            view=None
                        )
                    else:
                         await interaction.response.edit_message(
                            content="⚠️ Bonus rules configuration backup restored locally, but failed to sync to database.",
                            view=None
                        )
                except Exception as e:
                    logger.error(f"Error during bonus rule restore/sync for guild {guild_id}: {e}", exc_info=True)
                    await interaction.response.edit_message(content=f"❌ Error during restore process: {e}", view=None)
            else:
                await interaction.response.edit_message(
                    content="❌ No bonus rules configuration backup found.",
                    view=None
                )

        view = ConfirmButton(restore_action, interaction.user.id)
        await interaction.response.send_message(
            "⚠️ Are you sure you want to restore the bonus rules configuration backup?",
            view=view,
            ephemeral=ephemeral
        )

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="restore-earnings-backup", description="Restore the latest earnings configuration backup")
    async def restore_earnings_backup(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        async def restore_action(interaction: discord.Interaction):
            file_path = settings.get_guild_earnings_path(interaction.guild.id)
            backup_file = f"{file_path}.bak"
            if os.path.exists(backup_file):
                try:
                    shutil.copy2(backup_file, file_path)
                    logger.info(f"Restored local file {file_path} from backup for guild {interaction.guild.id}.")

                    # Force sync this restored file to MongoDB
                    mongo_synced = await file_handlers.force_sync_to_mongo(file_path)

                    if mongo_synced:
                        await interaction.response.edit_message(content="✅ Earnings data backup restored locally and synced to database.", view=None)
                    else:
                        await interaction.response.edit_message(content="⚠️ Earnings data backup restored locally, but failed to sync to database.", view=None)

                except Exception as e:
                    logger.error(f"Error during earnings restore/sync for guild {interaction.guild.id}: {e}", exc_info=True)
                    await interaction.response.edit_message(content=f"❌ Error during restore process: {e}", view=None)

            else:
                await interaction.response.edit_message(content="❌ No earnings configuration backup found.", view=None)

        view = ConfirmButton(restore_action, interaction.user.id)
        await interaction.response.send_message(
            "‼️🚨‼ Are you sure you want to restore the earnings data backup? This will overwrite current earnings.",
            view=view,
            ephemeral=ephemeral
        )

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="restore-models-backup", description="Restore the latest models configuration backup")
    async def restore_models_backup(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        async def restore_action(interaction: discord.Interaction):
            guild_id = interaction.guild.id
            file_path = settings.get_guild_models_path(guild_id)
            backup_file = f"{file_path}.bak"

            if os.path.exists(backup_file):
                try:
                    shutil.copy2(backup_file, file_path)
                    logger.info(f"Restored local file {file_path} from backup for guild {guild_id}.")

                    # Force sync this restored file to MongoDB
                    mongo_synced = await file_handlers.force_sync_to_mongo(file_path)

                    if mongo_synced:
                        await interaction.response.edit_message(content="✅ Models configuration backup restored locally and synced to database.", view=None)
                    else:
                        await interaction.response.edit_message(content="⚠️ Models configuration backup restored locally, but failed to sync to database.", view=None)

                except Exception as e:
                    logger.error(f"Error during models restore/sync for guild {guild_id}: {e}", exc_info=True)
                    await interaction.response.edit_message(content=f"❌ Error during restore process: {e}", view=None)
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
            guild_id = interaction.guild.id
            file_path = settings.get_guild_commission_path(guild_id)
            backup_file = f"{file_path}.bak"
            if os.path.exists(backup_file):
                try:
                    shutil.copy2(backup_file, file_path)
                    logger.info(f"Restored local file {file_path} from backup for guild {guild_id}.")

                    # Force sync this restored file to MongoDB
                    mongo_synced = await file_handlers.force_sync_to_mongo(file_path)

                    if mongo_synced:
                        await interaction.response.edit_message(content="✅ Compensation configuration backup restored locally and synced to database.", view=None)
                    else:
                        await interaction.response.edit_message(content="⚠️ Compensation configuration backup restored locally, but failed to sync to database.", view=None)

                except Exception as e:
                    logger.error(f"Error during compensation restore/sync for guild {guild_id}: {e}", exc_info=True)
                    await interaction.response.edit_message(content=f"❌ Error during restore process: {e}", view=None)
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
            guild_id = interaction.guild.id
            file_path = settings.get_guild_display_path(guild_id)
            backup_file = f"{file_path}.bak"

            if os.path.exists(backup_file):
                try:
                    shutil.copy2(backup_file, file_path)
                    logger.info(f"Restored local file {file_path} from backup for guild {guild_id}.")

                    # Force sync this restored file to MongoDB
                    mongo_synced = await file_handlers.force_sync_to_mongo(file_path)

                    if mongo_synced:
                        await interaction.response.edit_message(content="✅ Display configuration backup restored locally and synced to database.", view=None)
                    else:
                        await interaction.response.edit_message(content="⚠️ Display configuration backup restored locally, but failed to sync to database.", view=None)

                except Exception as e:
                    logger.error(f"Error during display restore/sync for guild {guild_id}: {e}", exc_info=True)
                    await interaction.response.edit_message(content=f"❌ Error during restore process: {e}", view=None)

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
        guild_id = interaction.guild.id
        file_path = settings.get_guild_display_path(guild_id)
        
        # Load current settings
        current_settings = await file_handlers.load_json(
            file_path, 
            {
                "ephemeral_responses": True,
                "show_average": True,
                "agency_name": "Agency",
                "show_ids": True,
                "bot_name": "Shift Calculator"
            }
        )
        
        # Toggle setting
        new_setting = not current_settings.get('ephemeral_responses', True)
        current_settings['ephemeral_responses'] = new_setting
        
        # Save changes
        success = await file_handlers.save_json(file_path, current_settings)
        
        if success:
            await interaction.response.send_message(
                f"✅ Ephemeral responses {'**enabled**' if new_setting else '**disabled**'}",
                ephemeral=new_setting  # Use new setting for this response
            )
        else:
            await interaction.response.send_message(
                "❌ Failed to update settings",
                ephemeral=True
            )


    @app_commands.command(name="copy-config-from-the-server", description="Copy server configuration from another server")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        source_id="Server ID to copy from",
        include_words="Comma-separated words to include in filenames (substring match)",
        exclude_words="Comma-separated words to exclude from filenames (substring match)",
        create_backup="Whether to create backup before copying"
    )
    async def copy_config(
        self,
        interaction: discord.Interaction,
        source_id: str, 
        include_words: str = None,
        exclude_words: str = 'role_percentages,commission_settings,display_settings',
        create_backup: bool = True
    ):
        """Copy config files with enhanced safety and feedback"""
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        try:
            # Prevent self-copying
            if str(source_id) == str(interaction.guild.id):
                target_dir = os.path.join("data", "config", str(interaction.guild.id))
                
                if not os.path.exists(target_dir):
                    await interaction.response.send_message(
                        "❌ No configuration found to backup",
                        ephemeral=ephemeral
                    )
                    return

                backup_time = datetime.now().strftime("%Y%m%d-%H%M%S")
                backup_path = f"{target_dir}_backup_{backup_time}"
                try:
                    shutil.copytree(target_dir, backup_path)
                    embed = discord.Embed(
                        title="Config Backup Created",
                        description="A backup of the current server configuration was created.",
                        color=discord.Color.green()
                    )
                    embed.add_field(
                        name="Backup Location",
                        value=f"`{os.path.basename(backup_path)}`",
                        inline=False
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=ephemeral)
                except Exception as e:
                    await interaction.response.send_message(
                        f"❌ Backup failed: {str(e)}",
                        ephemeral=ephemeral
                    )
                return

            source_dir = os.path.join("data", "config", source_id)
            target_dir = os.path.join("data", "config", str(interaction.guild.id))
            
            if not os.path.exists(source_dir):
                await interaction.response.send_message(
                    "❌ Source server configuration not found",
                    ephemeral=ephemeral
                )
                return

            include_list = [w.strip().lower() for w in include_words.split(',')] if include_words else []
            exclude_list = [w.strip().lower() for w in exclude_words.split(',')] + [".bak"] # Always exclude backup files
            copied_files = []
            skipped_files = []
            errors = []

            # Backup handling
            backup_path = None
            if create_backup and os.path.exists(target_dir):
                backup_time = datetime.now().strftime("%Y%m%d-%H%M%S")
                backup_path = f"{target_dir}_backup_{backup_time}"
                try:
                    shutil.copytree(target_dir, backup_path)
                except Exception as e:
                    errors.append(f"Backup failed: {str(e)}")

            def should_copy(file_path: str) -> bool:
                fname = os.path.basename(file_path).lower()
                
                # Exclusion checks
                if fname.endswith('.bak') or any(excl in fname for excl in exclude_list):
                    return False
                    
                # Inclusion filter
                if include_list and not any(inc in fname for inc in include_list):
                    return False
                    
                return True

            # File operations
            try:
                for root, dirs, files in os.walk(source_dir):
                    relative_path = os.path.relpath(root, source_dir)
                    dest_root = os.path.join(target_dir, relative_path)
                    
                    os.makedirs(dest_root, exist_ok=True)
                    
                    for file in files:
                        src_path = os.path.join(root, file)
                        dest_path = os.path.join(dest_root, file)
                        
                        if not should_copy(src_path):
                            skipped_files.append(file)
                            continue
                            
                        try:
                            shutil.copy2(src_path, dest_path)
                            copied_files.append(file)
                        except Exception as e:
                            errors.append(f"{file}: {str(e)}")
            except Exception as e:
                errors.append(f"Directory traversal failed: {str(e)}")

            # Build result embed
            embed = discord.Embed(
                title="Config Copy Results",
                color=discord.Color.orange() if errors else discord.Color.green()
            )
            
            if backup_path:
                embed.add_field(
                    name="Backup Created",
                    value=f"`{os.path.basename(backup_path)}`",
                    inline=False
                )
                
            result_stats = [
                f"• Copied: {len(copied_files)} files",
                f"• Skipped: {len(skipped_files)} files",
                f"• Errors: {len(errors)}"
            ]
            embed.add_field(
                name="Statistics",
                value="\n".join(result_stats),
                inline=False
            )
            
            # Add details if files were copied
            if copied_files:
                sample_copied = "\n".join(f"• {f}" for f in copied_files[:5])
                if len(copied_files) > 5:
                    sample_copied += f"\n...and {len(copied_files)-5} more"
                embed.add_field(
                    name="Copied Files",
                    value=f"```{sample_copied}```",
                    inline=False
                )
            else:
                embed.add_field(
                    name="⚠️ Notice",
                    value="No files were copied based on filters",
                    inline=False
                )
                
            # Error reporting
            if errors:
                sample_errors = "\n".join(f"• {e}" for e in errors[:3])
                if len(errors) > 3:
                    sample_errors += f"\n...and {len(errors)-3} more"
                embed.add_field(
                    name="Errors",
                    value=sample_errors,
                    inline=False
                )

            await interaction.response.send_message(embed=embed, ephemeral=ephemeral)

        except Exception as e:
            logger.error(f"Config copy failed: {str(e)}", exc_info=True)
            await interaction.response.send_message(
                f"❌ Critical error during copy: {str(e)}",
                ephemeral=ephemeral
            )

    @app_commands.command(name="manage-backups", description="Manage configuration or earnings backups")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        backup_type="Type of backups to manage",
        action="Action to perform",
        backup_ids="Comma-separated backup IDs to remove (for 'remove' action)"
    )
    @app_commands.choices(backup_type=[
        app_commands.Choice(name="Configuration", value="config"),
        app_commands.Choice(name="Earnings", value="earnings")
    ])
    @app_commands.choices(action=[
        app_commands.Choice(name="List", value="list"),
        app_commands.Choice(name="Remove", value="remove")
    ])
    async def manage_backups(
        self,
        interaction: discord.Interaction,
        backup_type: str,
        action: str,
        backup_ids: str = None
    ):
        """Manage server backups with type selection"""
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)
        guild_id = str(interaction.guild.id)
        
        try:
            # Determine paths based on backup type
            if backup_type == "config":
                base_dir = os.path.join("data", "config")
                pattern = f"{guild_id}_backup_*"
                backup_name = "Configuration"
            else:
                base_dir = os.path.join("data", "earnings")
                pattern = f"{guild_id}_earnings_backup_*"
                backup_name = "Earnings"

            if action == "list":
                backup_dirs = glob.glob(os.path.join(base_dir, pattern))
                backups = []
                
                for dir_path in backup_dirs:
                    dir_name = os.path.basename(dir_path)
                    backup_id = dir_name.split("_backup_")[-1]
                    
                    try:
                        dt = datetime.strptime(backup_id, "%Y%m%d-%H%M%S")
                        formatted_date = dt.strftime("%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        formatted_date = "Unknown date"
                    
                    backups.append((backup_id, dir_name, formatted_date))
                
                # Sort by date
                backups.sort(key=lambda x: x[0], reverse=True)
                
                embed = discord.Embed(
                    title=f"{backup_name} Backups",
                    color=discord.Color.blue()
                )
                
                if not backups:
                    embed.description = "No backups found"
                else:
                    backup_list = []
                    for bid, dir_name, date in backups:
                        backup_list.append(f"• **{bid}**\n  Created: {date}\n  Directory: `{dir_name}`")
                    
                    embed.description = "\n\n".join(backup_list)
                    embed.set_footer(text=f"Total {backup_name.lower()} backups: {len(backups)}")
                
                await interaction.response.send_message(embed=embed, ephemeral=ephemeral)
            
            elif action == "remove":
                if not backup_ids:
                    await interaction.response.send_message(
                        "❌ Please provide backup IDs to remove",
                        ephemeral=ephemeral
                    )
                    return
                    
                backup_id_list = [bid.strip() for bid in backup_ids.split(',')]
                removed = []
                errors = []
                
                for backup_id in backup_id_list:
                    # Validate ID format
                    if not re.fullmatch(r"\d{8}-\d{6}", backup_id):
                        errors.append(f"Invalid ID: {backup_id}")
                        continue
                    
                    dir_name = f"{guild_id}_{'earnings_' if backup_type == 'earnings' else ''}backup_{backup_id}"
                    backup_path = os.path.join(base_dir, dir_name)
                    
                    if not os.path.exists(backup_path):
                        errors.append(f"Backup {backup_id} not found")
                        continue
                    
                    try:
                        shutil.rmtree(backup_path)
                        removed.append(backup_id)
                    except Exception as e:
                        errors.append(f"Failed to remove {backup_id}: {str(e)}")
                
                # Build results embed
                embed = discord.Embed(
                    title=f"{backup_name} Backup Removal",
                    color=discord.Color.green() if not errors else discord.Color.orange()
                )
                
                if removed:
                    embed.add_field(
                        name="Successfully Removed",
                        value="\n".join(f"• `{bid}`" for bid in removed),
                        inline=False
                    )
                
                if errors:
                    embed.add_field(
                        name="Errors",
                        value="\n".join(f"• {e}" for e in errors),
                        inline=False
                    )
                
                await interaction.response.send_message(embed=embed, ephemeral=ephemeral)
        
        except Exception as e:
            logger.error(f"Backup management error: {str(e)}", exc_info=True)
            await interaction.response.send_message(
                f"❌ Critical error: {str(e)}",
                ephemeral=ephemeral
            )

    @app_commands.command(name="copy-earnings-from-the-server", description="Copy earnings data from another server (WARNING: Overwrites current data)")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        source_id="The server ID you want to copy earnings from",
        create_backup="Whether to create backup before copying (recommended)"
    )
    async def copy_earnings(self, interaction: discord.Interaction, source_id: str, create_backup: bool = True):
        """Copy earnings data with backup protection"""
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)
        
        class ConfirmationView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=60)
                self.confirmed = False

            @discord.ui.button(label="Confirm Overwrite", style=discord.ButtonStyle.danger)
            async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
                self.confirmed = True
                await interaction.response.defer()
                self.stop()

            @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
            async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
                await interaction.response.edit_message(content="Operation cancelled", view=None)
                self.stop()

        try:
            if str(source_id) == str(interaction.guild.id):
                target_dir = os.path.join("data", "earnings", str(interaction.guild.id))
                target_file = os.path.join(target_dir, "earnings.json")
                
                if not os.path.exists(target_file):
                    await interaction.response.send_message(
                        "❌ No earnings data found to backup",
                        ephemeral=ephemeral
                    )
                    return

                backup_time = datetime.now().strftime("%Y%m%d-%H%M%S")
                backup_dir_name = f"{interaction.guild.id}_earnings_backup_{backup_time}"
                backup_path = os.path.join("data", "earnings", backup_dir_name)
                
                try:
                    os.makedirs(backup_path, exist_ok=True)
                    shutil.copy2(target_file, os.path.join(backup_path, "earnings.json"))
                    
                    embed = discord.Embed(
                        title="✅ Earnings Backup Created",
                        description="A backup of current earnings data was successfully created.",
                        color=discord.Color.green()
                    )
                    embed.add_field(
                        name="Backup Location",
                        value=f"`{backup_dir_name}`",
                        inline=False
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=ephemeral)
                except Exception as e:
                    await interaction.response.send_message(
                        f"❌ Backup failed: {str(e)}",
                        ephemeral=ephemeral
                    )
                return

            source_path = os.path.join("data", "earnings", source_id, "earnings.json")
            target_dir = os.path.join("data", "earnings", str(interaction.guild.id))
            target_path = os.path.join(target_dir, "earnings.json")
            backup_path = None

            if not os.path.exists(source_path):
                await interaction.response.send_message(
                    f"❌ No earnings data found in source server {source_id}",
                    ephemeral=ephemeral
                )
                return

            # Backup handling
            if create_backup and os.path.exists(target_path):
                backup_time = datetime.now().strftime("%Y%m%d-%H%M%S")
                backup_dir_name = f"{interaction.guild.id}_earnings_backup_{backup_time}"
                backup_path = os.path.join("data", "earnings", backup_dir_name)
                try:
                    os.makedirs(backup_path, exist_ok=True)
                    shutil.copy2(target_path, os.path.join(backup_path, "earnings.json"))
                except Exception as e:
                    await interaction.response.send_message(
                        f"⚠️ Backup failed: {str(e)}",
                        ephemeral=ephemeral
                    )
                    return

            # Load source data for confirmation
            with open(source_path, 'r') as f:
                data = json.load(f)
            
            entry_count = sum(len(entries) for entries in data.values()) if isinstance(data, dict) else len(data)

            # Confirmation view
            class FinalConfirmationView(discord.ui.View):
                def __init__(self):
                    super().__init__(timeout=60)
                    self.confirmed = False

                @discord.ui.button(label="CONFIRM OVERWRITE", style=discord.ButtonStyle.danger)
                async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
                    self.confirmed = True
                    await interaction.response.defer()
                    self.stop()

                @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
                async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
                    await interaction.response.edit_message(content="Operation cancelled", view=None)
                    self.stop()

            # Initial warning
            initial_embed = discord.Embed(
                title="⚠️ Earnings Overwrite Warning",
                description=f"This will replace current data with `{entry_count}` entries from `{source_id}`",
                color=discord.Color.orange()
            )
            if backup_path:
                initial_embed.add_field(
                    name="Backup Created",
                    value=f"`{os.path.basename(backup_path)}`",
                    inline=False
                )
            
            view = FinalConfirmationView()
            await interaction.response.send_message(embed=initial_embed, view=view, ephemeral=ephemeral)
            await view.wait()
            
            if not view.confirmed:
                return

            # Perform copy
            os.makedirs(target_dir, exist_ok=True)
            shutil.copyfile(source_path, target_path)

            # Results embed
            success_embed = discord.Embed(
                title="✅ Earnings Copy Complete",
                description=f"Successfully copied `{entry_count}` entries from `{source_id}`",
                color=discord.Color.green()
            )
            if backup_path:
                success_embed.add_field(
                    name="Backup Created",
                    value=f"`{os.path.basename(backup_path)}`",
                    inline=False
                )
            
            await interaction.edit_original_response(embed=success_embed, view=None)

        except Exception as e:
            logger.error(f"Earnings copy failed: {str(e)}", exc_info=True)
            await interaction.response.send_message(
                f"❌ Critical error: {str(e)}",
                ephemeral=ephemeral
            )

    @app_commands.command(name="view-config", description="View complete server configuration")
    @app_commands.default_permissions(administrator=True)
    async def view_config(self, interaction: discord.Interaction) -> None:
        """Display all server configurations with interactive pagination"""
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)
        guild_id = interaction.guild.id

        #region Helper Functions
        def create_embed(title: str) -> discord.Embed:
            """Create a styled embed template"""
            return discord.Embed(
                title=title,
                color=0x00ff00,
                timestamp=discord.utils.utcnow()
            ).set_footer(text=f"Requested by {interaction.user.display_name}")

        def chunk_content(content: str, title: str, use_code_block: bool = True) -> list[tuple[str, str]]:
            """Split content into embed-safe chunks with optional code block"""
            newline = '\n'
            buffer = []
            chunks = []
            current_length = 0
            
            for line in content.split(newline):
                line_length = len(line) + 1  # +1 for newline character
                if current_length + line_length > 1000:
                    chunk_value = newline.join(buffer)
                    if use_code_block and chunk_value.strip():
                        chunk_value = f"```{chunk_value}```"
                    
                    chunks.append((title, chunk_value if chunk_value.strip() else "**[No entries]**"))
                    buffer = []
                    current_length = 0
                    title = f"{title} (cont.)"
                
                buffer.append(line)
                current_length += line_length
            
            if buffer:
                chunk_value = newline.join(buffer)
                if use_code_block and chunk_value.strip():
                    chunk_value = f"```{chunk_value}```"
                chunks.append((title, chunk_value if chunk_value.strip() else "**[No entries]**"))
            
            return chunks or [(title, "**[No entries]**")]

        async def load_config_section(loader, formatter, section_name: str, use_code_block: bool = True):
            """Load and format a config section with code block option"""
            try:
                raw_data = await loader()
                if not raw_data:
                    return chunk_content("", f"{section_name}\n", use_code_block)
                formatted = formatter(raw_data)
                return chunk_content('\n'.join(formatted), section_name, use_code_block)
            except Exception as e:
                logger.error(f"Config error in {section_name}: {str(e)}")
                return chunk_content("", f"{section_name} Error", use_code_block)

        async def format_compensation(data_type: str, interaction: discord.Interaction) -> list[str]:
            """Format compensation data without code blocks (for mentions)"""
            try:
                from config import settings
                comp_data = await file_handlers.load_json(
                    settings.get_guild_commission_path(interaction.guild.id), {}
                )
                lines = []
                section_data = comp_data.get(data_type, {})
                if not isinstance(section_data, dict):
                    raise ValueError(f"{data_type} section is not a dictionary")
                
                for entry_id, settings in section_data.items():
                    if not entry_id.isdigit():
                        raise ValueError(f"Invalid ID format: {entry_id}")

                    # Get target (role/member) and format mention + name
                    if data_type == "roles":
                        target = interaction.guild.get_role(int(entry_id))
                        display_text = f"**{target.name}**" if target else f"`Unknown Role (ID: {entry_id})`"
                    else:  # users
                        target = interaction.guild.get_member(int(entry_id))
                        display_text = f"**{target.display_name} (@{target.name})**" if target else f"`Unknown User (ID: {entry_id})`"
                        override_role = settings.get('override_role', False)
                    
                    commission = settings.get('commission_percentage', '❓')
                    hourly = settings.get('hourly_rate', '❓')
                    
                    if data_type == "users":
                        lines.append(
                            f"◈ {display_text}\n"
                            f"```• Commission: {commission}%\n"
                            f"• Hourly Rate: ${hourly}/h\n"
                            f"• Override Role: {'Yes```' if settings.get('override_role', False) else 'No```'}"
                        )
                    else:
                        lines.append(
                            f"◈ {display_text}\n"
                            f"```• Commission: {commission}%\n"
                            f"• Hourly Rate: ${hourly}/h\n```"
                        )
                return lines or ["**[No entries]**"]
            except Exception as e:
                logger.error(f"Compensation error: {str(e)}")
                return ["**⚠ Error loading data**"]
        #endregion

        #region Configuration Loaders
        config_sections = []
        
        # Role Percentages
        config_sections.extend(await load_config_section(
            lambda: file_handlers.load_json(settings.get_guild_roles_path(guild_id), {}),
            lambda d: [f"{interaction.guild.get_role(int(k)) or k}: {v}%" for k, v in d.items()],
            "Role Cuts",
            use_code_block=True
        ))

        # Shifts
        config_sections.extend(await load_config_section(
            lambda: file_handlers.load_json(settings.get_guild_shifts_path(guild_id), []),
            lambda d: [f"• {s}" for s in d],
            "Shifts"
        ))

        # Periods
        config_sections.extend(await load_config_section(
            lambda: file_handlers.load_json(settings.get_guild_periods_path(guild_id), []),
            lambda d: [f"• {p}" for p in d],
            "Periods"
        ))

        # Bonus Rules
        config_sections.extend(await load_config_section(
            lambda: file_handlers.load_json(settings.get_guild_bonus_rules_path(guild_id), []),
            lambda d: [f"${r['from']}-${r['to']}: ${r['amount']}" for r in d],
            "Bonuses"
        ))

        # Models
        config_sections.extend(await load_config_section(
            lambda: file_handlers.load_json(settings.get_guild_models_path(guild_id), []),
            lambda d: [f"• {m}" for m in d],
            "Models"
        ))

        # Display Settings
        config_sections.extend(await load_config_section(
            lambda: file_handlers.load_json(settings.get_guild_display_path(guild_id), {}),
            lambda d: [
                f"Ephemeral: {d.get('ephemeral_responses', True)}",
                f"Show Average: {d.get('show_average', True)}",
                f"Agency Name: {d.get('agency_name', 'Agency')}",
                f"Show IDs: {d.get('show_ids', True)}",
                f"Bot Name: {d.get('bot_name', 'Default')}"
            ],
            "Display"
        ))

        # Compensation Data
        config_sections.extend(await load_config_section(
            lambda: format_compensation("roles", interaction),
            lambda d: d,
            "Role Compensation",
            use_code_block=False  # Disable code block
        ))
        config_sections.extend(await load_config_section(
            lambda: format_compensation("users", interaction),
            lambda d: d,
            "User Compensation",
            use_code_block=False  # Disable code block
        ))
        #endregion

        #region Pagination System
        class ConfigView(discord.ui.View):
            def __init__(self, embeds: list[discord.Embed]):
                super().__init__(timeout=180)
                self.embeds = embeds
                self.page = 0
                
                # Initial button state
                self._update_buttons()
                
            def _update_buttons(self):
                self.prev_button.disabled = self.page == 0
                self.next_button.disabled = self.page == len(self.embeds)-1
                
            @discord.ui.button(label="◀", style=discord.ButtonStyle.blurple)
            async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                self.page -= 1
                self._update_buttons()
                await interaction.response.edit_message(
                    embed=self.embeds[self.page],
                    view=self
                )
                
            @discord.ui.button(label="▶", style=discord.ButtonStyle.blurple)
            async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                self.page += 1
                self._update_buttons()
                await interaction.response.edit_message(
                    embed=self.embeds[self.page],
                    view=self
                )
                
            @discord.ui.button(label="✖", style=discord.ButtonStyle.red)
            async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                await interaction.response.defer()
                await interaction.delete_original_response()
                self.stop()

        # Build embeds
        embeds = []
        current_embed = create_embed("Server Configuration")
        field_count = 0
        
        for title, content in config_sections:
            if field_count >= 5 or len(current_embed) > 4000:
                embeds.append(current_embed)
                current_embed = create_embed("Configuration Continued")
                field_count = 0
                
            current_embed.add_field(name=title, value=content, inline=False)
            field_count += 1
            
        if field_count > 0:
            embeds.append(current_embed)
        #endregion

        # Send response
        try:
            if not embeds:
                await interaction.response.send_message("No configuration found", ephemeral=ephemeral)
                return
                
            view = ConfigView(embeds) if len(embeds) > 1 else None
            await interaction.response.send_message(
                embed=embeds[0],
                view=view,
                ephemeral=ephemeral
            )
        except Exception as e:
            logger.error(f"Config display failed: {str(e)}")
            await interaction.response.send_message(
                "Failed to display configuration - data too large",
                ephemeral=ephemeral
            )

    @app_commands.command(name="sync-local-config-to-db", description="Force sync ALL local config files to the database (Overwrites DB)")
    @app_commands.default_permissions(administrator=True)
    async def sync_local_config_to_db(self, interaction: discord.Interaction):
        """Manually synchronizes all local configuration files to the database."""
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)
        guild_id = interaction.guild.id

        config_file_getters = [
            settings.get_guild_shifts_path,
            settings.get_guild_periods_path,
            settings.get_guild_bonus_rules_path,
            settings.get_guild_models_path,
            settings.get_guild_display_path,
            settings.get_guild_commission_path,
            settings.get_guild_roles_path, # Include legacy roles path if needed
        ]

        async def sync_action(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=ephemeral, thinking=True) # Defer as it might take time

            success_files = []
            failed_files = []
            skipped_files = []

            for getter in config_file_getters:
                file_path = getter(guild_id)
                file_name = os.path.basename(file_path)

                if not os.path.exists(file_path):
                    logger.warning(f"Skipping sync for {file_name} (Guild: {guild_id}): Local file not found.")
                    skipped_files.append(file_name)
                    continue

                try:
                    logger.info(f"Attempting force sync for {file_name} (Guild: {guild_id})...")
                    synced = await file_handlers.force_sync_to_mongo(file_path)
                    if synced:
                        success_files.append(file_name)
                        logger.info(f"Successfully synced {file_name} for guild {guild_id}.")
                    else:
                        failed_files.append(file_name)
                        logger.error(f"Failed to sync {file_name} for guild {guild_id}.")
                    # Add a small delay to avoid overwhelming resources if needed
                    await asyncio.sleep(0.1)
                except Exception as e:
                    logger.error(f"Error during force sync of {file_name} for guild {guild_id}: {e}", exc_info=True)
                    failed_files.append(f"{file_name} (Error: {e})")

            # --- Build Response ---
            embed = discord.Embed(title="Local Config -> Database Sync Results", color=discord.Color.blue())
            if success_files:
                embed.add_field(name="✅ Synced Successfully", value="```\n" + "\n".join(success_files) + "\n```", inline=False)
            if failed_files:
                 embed.color = discord.Color.orange() if success_files else discord.Color.red()
                 embed.add_field(name="❌ Sync Failed", value="```\n" + "\n".join(failed_files) + "\n```", inline=False)
            if skipped_files:
                 embed.add_field(name="⚠️ Skipped (Local file missing)", value="```\n" + "\n".join(skipped_files) + "\n```", inline=False)

            if not success_files and not failed_files and not skipped_files:
                 embed.description = "No configuration files found or processed."
                 embed.color = discord.Color.greyple()

            await interaction.followup.send(embed=embed, ephemeral=ephemeral)


        # --- Confirmation View ---
        view = ConfirmButton(sync_action, interaction.user.id)
        await interaction.response.send_message(
            "‼️🚨‼️ **Confirm Sync?**\n"
            "This will **overwrite** the current configuration data in the **database** "
            "with the data found in your **local** bot files for this server.\n"
            "Use this if you've restored local files and need to update the database.",
            view=view,
            ephemeral=ephemeral
        )

    @app_commands.command(name="sync-local-earnings-to-db", description="Force sync local earnings file to the database (Overwrites DB)")
    @app_commands.default_permissions(administrator=True)
    async def sync_local_earnings_to_db(self, interaction: discord.Interaction):
        """Manually synchronizes the local earnings file to the database."""
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)
        guild_id = interaction.guild.id
        file_path = settings.get_guild_earnings_path(guild_id)
        file_name = os.path.basename(file_path)

        async def sync_action(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=ephemeral, thinking=True)

            if not os.path.exists(file_path):
                logger.error(f"Cannot sync {file_name} (Guild: {guild_id}): Local file not found.")
                await interaction.followup.send(f"❌ **Sync Failed:** Local earnings file (`{file_name}`) not found.", ephemeral=ephemeral)
                return

            try:
                logger.info(f"Attempting force sync for {file_name} (Guild: {guild_id})...")
                synced = await file_handlers.force_sync_to_mongo(file_path)
                if synced:
                    logger.info(f"Successfully synced {file_name} for guild {guild_id}.")
                    await interaction.followup.send(f"✅ **Sync Complete:** Local earnings data (`{file_name}`) successfully synced to the database.", ephemeral=ephemeral)
                else:
                    logger.error(f"Failed to sync {file_name} for guild {guild_id}.")
                    await interaction.followup.send(f"❌ **Sync Failed:** Could not sync local earnings data (`{file_name}`) to the database. Check bot logs.", ephemeral=ephemeral)

            except Exception as e:
                logger.error(f"Error during force sync of {file_name} for guild {guild_id}: {e}", exc_info=True)
                await interaction.followup.send(f"❌ **Sync Error:** An unexpected error occurred: {e}", ephemeral=ephemeral)

        # --- Confirmation View ---
        view = ConfirmButton(sync_action, interaction.user.id)
        await interaction.response.send_message(
            "‼️🚨‼️ **Confirm Sync?**\n"
            "This will **overwrite** the current earnings data in the **database** "
            "with the data found in your **local** `earnings.json` file for this server.\n"
            "**USE WITH CAUTION!** This is generally only needed after restoring a local earnings backup.",
            view=view,
            ephemeral=ephemeral
        )


class ConfirmButton(discord.ui.View):
    def __init__(self, action_callback, user_id: int):
        super().__init__()
        self.action_callback = action_callback
        self.user_id = user_id

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.red)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ You cannot use this button.", ephemeral=True)
            return
        
        await self.action_callback(interaction)
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.green)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ You cannot use this button.", ephemeral=True)
            return
        
        await interaction.response.edit_message(content="❌ Cancelled.", view=None)
        self.stop()

async def setup(bot):
    await bot.add_cog(AdminSlashCommands(bot))