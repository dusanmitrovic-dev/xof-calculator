# --- START OF FILE admin_slash.py ---

import os
import re
import json
import glob
import shutil
import discord
import logging
import aiofiles # <--- Added import
from datetime import datetime

from discord import app_commands
from discord.ext import commands
from typing import Optional, List # <--- Added List
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
        success = await file_handlers.save_json(file_path, commission_settings)

        # Respond with confirmation
        if success:
            response = f"✅ Set commission for {role.mention} to "
            response += f"{percentage}%" if percentage is not None else "cleared"
            await interaction.response.send_message(response, ephemeral=ephemeral)
        else:
            await interaction.response.send_message("❌ Failed to save settings.", ephemeral=ephemeral)

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
        success = await file_handlers.save_json(file_path, commission_settings)

        # Respond with confirmation
        if success:
            response = f"✅ Set hourly rate for {role.mention} to "
            response += f"${rate}/h" if rate is not None else "cleared"
            await interaction.response.send_message(response, ephemeral=ephemeral)
        else:
            await interaction.response.send_message("❌ Failed to save settings.", ephemeral=ephemeral)

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

        # Preserve existing override setting if not provided
        if override_role is None:
            override_role = user_settings.get('override_role', False)

        user_settings['override_role'] = override_role
        commission_settings['users'][str(user.id)] = user_settings

        # Save updated settings
        success = await file_handlers.save_json(file_path, commission_settings)

        # Respond with confirmation
        if success:
            response = f"✅ Set commission for {user.mention} to "
            response += f"{percentage}%" if percentage is not None else "cleared"
            response += f" (Override Role: {override_role})"
            await interaction.response.send_message(response, ephemeral=ephemeral)
        else:
            await interaction.response.send_message("❌ Failed to save settings.", ephemeral=ephemeral)

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

        # Preserve existing override setting if not provided
        if override_role is None:
            override_role = user_settings.get('override_role', False)

        user_settings['override_role'] = override_role
        commission_settings['users'][str(user.id)] = user_settings

        # Save updated settings
        success = await file_handlers.save_json(file_path, commission_settings)

        # Respond with confirmation
        if success:
            response = f"✅ Set hourly rate for {user.mention} to "
            response += f"${rate}/h" if rate is not None else "cleared"
            response += f" (Override Role: {override_role})"
            await interaction.response.send_message(response, ephemeral=ephemeral)
        else:
            await interaction.response.send_message("❌ Failed to save settings.", ephemeral=ephemeral)

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
        user_settings = commission_settings.get('users', {}).get(str(user.id)) # Safer access
        if not user_settings:
            await interaction.response.send_message(
                "❌ No settings found for this user. Use `/set-user-commission` or `/set-user-hourly` first.",
                ephemeral=ephemeral
            )
            return

        # Toggle override_role
        user_settings['override_role'] = not user_settings.get('override_role', False)
        commission_settings['users'][str(user.id)] = user_settings

        # Save updated settings
        success = await file_handlers.save_json(file_path, commission_settings)

        # Respond with confirmation
        if success:
            response = f"✅ Toggled role override for {user.mention} to **{user_settings['override_role']}**"
            await interaction.response.send_message(response, ephemeral=ephemeral)
        else:
            await interaction.response.send_message("❌ Failed to save settings.", ephemeral=ephemeral)

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
        embed = discord.Embed(title="Compensation Settings", color=0x009933)

        if role:
            # View specific role commission settings
            role_settings = guild_settings['roles'].get(str(role.id), {})
            commission = role_settings.get('commission_percentage')
            hourly = role_settings.get('hourly_rate')

            embed.description = f"Settings for Role: {role.mention}"
            embed.add_field(
                name="Commission",
                value=f"{commission}%" if commission is not None else "Not Set",
                inline=True
            )
            embed.add_field(
                name="Hourly Rate",
                value=f"${hourly}/h" if hourly is not None else "Not Set",
                inline=True
            )
        elif user:
            # View specific user commission settings
            user_settings = guild_settings['users'].get(str(user.id), {})
            commission = user_settings.get('commission_percentage')
            hourly = user_settings.get('hourly_rate')
            override = user_settings.get('override_role', False)

            embed.description = f"Settings for User: {user.mention}"
            embed.add_field(
                name="Commission",
                value=f"{commission}%" if commission is not None else "Not Set",
                inline=True
            )
            embed.add_field(
                name="Hourly Rate",
                value=f"${hourly}/h" if hourly is not None else "Not Set",
                inline=True
            )
            embed.add_field(
                name="Override Role",
                value=f"{'Yes' if override else 'No'}",
                inline=True
            )
        else:
            # View all commission settings summary
            embed.description = "Summary of Compensation Settings"

            if not guild_settings['roles'] and not guild_settings['users']:
                embed.add_field(name="", value="❌ No compensation settings found for this server.", inline=False)
            else:
                 # Role commission settings summary
                role_summary = []
                for role_id, role_data in guild_settings['roles'].items():
                    role_obj = interaction.guild.get_role(int(role_id))
                    if role_obj:
                        commission = role_data.get('commission_percentage')
                        hourly = role_data.get('hourly_rate')
                        role_summary.append(
                            f"**{role_obj.name}**: "
                            f"Comm: {commission if commission is not None else '❓'}% | "
                            f"Hourly: ${hourly if hourly is not None else '❓'}"
                        )

                if role_summary:
                    # Split into multiple fields if too long
                    current_field = ""
                    for line in role_summary:
                        if len(current_field) + len(line) + 1 > 1024:
                            embed.add_field(name="Role Settings (cont.)", value=current_field, inline=False)
                            current_field = ""
                        current_field += line + "\n"
                    if current_field:
                        embed.add_field(name="Role Settings", value=current_field, inline=False)


                # User commission settings summary
                user_summary = []
                for user_id, user_data in guild_settings['users'].items():
                    member = interaction.guild.get_member(int(user_id))
                    if member:
                        commission = user_data.get('commission_percentage')
                        hourly = user_data.get('hourly_rate')
                        override = user_data.get('override_role', False)
                        user_summary.append(
                            f"**{member.display_name}**: "
                            f"Comm: {commission if commission is not None else '❓'}% | "
                            f"Hourly: ${hourly if hourly is not None else '❓'} | "
                            f"Override: {'Yes' if override else 'No'}"
                        )

                if user_summary:
                    current_field = ""
                    for line in user_summary:
                         if len(current_field) + len(line) + 1 > 1024:
                             embed.add_field(name="User Settings (cont.)", value=current_field, inline=False)
                             current_field = ""
                         current_field += line + "\n"
                    if current_field:
                         embed.add_field(name="User Settings", value=current_field, inline=False)


        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)

    async def get_agency_name(self, guild_id):
        file_path = settings.get_guild_display_path(guild_id)
        settings_data = await file_handlers.load_json(file_path, settings.DEFAULT_DISPLAY_SETTINGS.copy())
        return settings_data.get("agency_name", settings.DEFAULT_DISPLAY_SETTINGS['agency_name'])

    async def get_show_ids(self, guild_id):
        file_path = settings.get_guild_display_path(guild_id)
        settings_data = await file_handlers.load_json(file_path, settings.DEFAULT_DISPLAY_SETTINGS.copy())
        return settings_data.get("show_ids", settings.DEFAULT_DISPLAY_SETTINGS['show_ids'])

    async def get_bot_name(self, guild_id):
        file_path = settings.get_guild_display_path(guild_id)
        settings_data = await file_handlers.load_json(file_path, settings.DEFAULT_DISPLAY_SETTINGS.copy())
        return settings_data.get("bot_name", settings.DEFAULT_DISPLAY_SETTINGS['bot_name'])

    @app_commands.command(name="set-agency-name", description="Set custom agency name for this server")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(name="The custom agency name to display that bot will use")
    async def set_agency_name(self, interaction: discord.Interaction, name: str):
        """Set custom agency name"""
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        file_path = settings.get_guild_display_path(interaction.guild.id)
        settings_data = await file_handlers.load_json(file_path, settings.DEFAULT_DISPLAY_SETTINGS.copy())

        settings_data["agency_name"] = name
        success = await file_handlers.save_json(file_path, settings_data)

        if success:
            await interaction.response.send_message(f"✅ Agency name set to: **{name}**", ephemeral=ephemeral)
        else:
            await interaction.response.send_message("❌ Failed to save agency name", ephemeral=ephemeral)

    @app_commands.command(name="toggle-id-display", description="Toggle display of IDs in reports")
    @app_commands.default_permissions(administrator=True)
    async def toggle_id_display(self, interaction: discord.Interaction):
        """Toggle ID display"""
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        file_path = settings.get_guild_display_path(interaction.guild.id)
        settings_data = await file_handlers.load_json(file_path, settings.DEFAULT_DISPLAY_SETTINGS.copy())

        current_setting = settings_data.get("show_ids", settings.DEFAULT_DISPLAY_SETTINGS['show_ids'])
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
        settings_data = await file_handlers.load_json(file_path, settings.DEFAULT_DISPLAY_SETTINGS.copy())

        settings_data["bot_name"] = name
        success = await file_handlers.save_json(file_path, settings_data)

        if success:
            await interaction.response.send_message(f"✅ Bot name set to: **{name}**", ephemeral=ephemeral)
        else:
            await interaction.response.send_message("❌ Failed to save bot name", ephemeral=ephemeral)


    @app_commands.command(name="view-display-settings", description="View the current display settings")
    @app_commands.default_permissions(administrator=True)
    async def view_display_settings(self, interaction: discord.Interaction):
        """View the current display settings"""
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        guild_id = interaction.guild.id
        file_path = settings.get_guild_display_path(guild_id)
        guild_settings = await file_handlers.load_json(file_path, settings.DEFAULT_DISPLAY_SETTINGS.copy())

        embed = discord.Embed(title="Display Settings", color=0x00ff00)
        embed.add_field(name="Ephemeral Responses", value=guild_settings.get('ephemeral_responses', settings.DEFAULT_DISPLAY_SETTINGS['ephemeral_responses']), inline=False)
        embed.add_field(name="Show Averages", value=guild_settings.get('show_average', settings.DEFAULT_DISPLAY_SETTINGS['show_average']), inline=False)
        embed.add_field(name="Agency Name", value=guild_settings.get('agency_name', settings.DEFAULT_DISPLAY_SETTINGS['agency_name']), inline=False)
        embed.add_field(name="Show IDs", value=guild_settings.get('show_ids', settings.DEFAULT_DISPLAY_SETTINGS['show_ids']), inline=False)
        embed.add_field(name="Bot Name", value=guild_settings.get('bot_name', settings.DEFAULT_DISPLAY_SETTINGS['bot_name']), inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)

    async def get_average_setting(self, guild_id):
        guild_settings_file = settings.get_guild_display_path(guild_id)
        guild_settings = await file_handlers.load_json(guild_settings_file, settings.DEFAULT_DISPLAY_SETTINGS.copy())
        return guild_settings.get("show_average", settings.DEFAULT_DISPLAY_SETTINGS['show_average'])

    @app_commands.command(
        name="toggle-average",
        description="Toggle whether to show performance averages in calculation embeds"
    )
    @app_commands.default_permissions(administrator=True)
    async def toggle_average(self, interaction: discord.Interaction):
        """Toggle the display of performance averages in calculation embeds"""
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        guild_id = str(interaction.guild_id) # Use string for consistency if needed
        guild_settings_file = settings.get_guild_display_path(guild_id)

        # Load settings data
        guild_settings = await file_handlers.load_json(guild_settings_file, settings.DEFAULT_DISPLAY_SETTINGS.copy())

        # Toggle the show_average setting
        current_setting = guild_settings.get("show_average", settings.DEFAULT_DISPLAY_SETTINGS['show_average'])
        new_setting = not current_setting
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

    # Role Management (legacy role cut - maybe remove later or merge into commission)
    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="set-role", description="[Legacy] Set a role's percentage cut")
    @app_commands.describe(role="The role to configure", percentage="The percentage cut (e.g., 6.5)")
    async def set_role(self, interaction: discord.Interaction, role: discord.Role, percentage: str):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)
        await interaction.response.defer(ephemeral=ephemeral)

        try:
            logger.info(f"User {interaction.user.name} used set-role command for role {role.name} with percentage {percentage}")

            percentage_decimal = validators.validate_percentage(percentage)
            if percentage_decimal is None:
                await interaction.followup.send(
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
                await interaction.followup.send(
                    f"✅ [Legacy] {role.name} now has {percentage_decimal}% cut!",
                    ephemeral=ephemeral
                )
            else:
                logger.error(f"Failed to save role data for {role.name} ({role_id}) by {interaction.user.name}")
                await interaction.followup.send(
                    "❌ Failed to save legacy role data. Please try again later.",
                    ephemeral=ephemeral
                )
        except Exception as e:
            logger.error(f"Error in set_role: {str(e)}")
            await interaction.followup.send(
                "❌ An unexpected error occurred. See logs for details.",
                ephemeral=ephemeral
            )

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="remove-role", description="[Legacy] Remove a role's percentage configuration")
    @app_commands.describe(role="The role to remove")
    async def remove_role(self, interaction: discord.Interaction, role: discord.Role):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)
        await interaction.response.defer(ephemeral=ephemeral)

        try:
            logger.info(f"User {interaction.user.name} used remove-role command for role {role.name}")

            guild_id = interaction.guild.id
            role_file = settings.get_guild_roles_path(guild_id)
            role_data = await file_handlers.load_json(role_file, {})

            role_id = str(role.id)
            if role_id not in role_data:
                logger.warning(f"Role {role.name} ({role_id}) not found in legacy configuration")
                await interaction.followup.send(
                    f"❌ {role.name} does not have a configured legacy percentage.",
                    ephemeral=ephemeral
                )
                return

            del role_data[role_id]
            success = await file_handlers.save_json(role_file, role_data)

            if success:
                logger.info(f"Role {role.name} ({role_id}) removed from legacy configuration")
                await interaction.followup.send(
                    f"✅ {role.name} has been removed from legacy percentage configuration!",
                    ephemeral=ephemeral
                )
            else:
                logger.error(f"Failed to remove legacy role {role.name} ({role_id})")
                await interaction.followup.send(
                    "❌ Failed to save legacy role data. Please try again later.",
                    ephemeral=ephemeral
                )
        except Exception as e:
            logger.error(f"Error in remove_role: {str(e)}")
            await interaction.followup.send(
                "❌ An unexpected error occurred. See logs for details.",
                ephemeral=ephemeral
            )

    # Shift Management
    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="set-shift", description="Add a valid shift name")
    @app_commands.describe(shift="The name of the shift to add")
    async def set_shift(self, interaction: discord.Interaction, shift: str):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)
        await interaction.response.defer(ephemeral=ephemeral)

        try:
            logger.info(f"User {interaction.user.name} used set-shift command for shift '{shift}'")

            if not shift.strip():
                await interaction.followup.send("❌ Shift name cannot be empty.", ephemeral=ephemeral)
                return

            guild_id = interaction.guild.id
            shift_file = settings.get_guild_shifts_path(guild_id)
            existing_shifts = await file_handlers.load_json(shift_file, [])

            # Case-insensitive check but preserve original casing
            if any(shift.lower() == s.lower() for s in existing_shifts):
                await interaction.followup.send(f"❌ Shift '{shift}' already exists!", ephemeral=ephemeral)
                return

            existing_shifts.append(shift.strip())
            success = await file_handlers.save_json(shift_file, existing_shifts)

            if success:
                await interaction.followup.send(f"✅ Shift '{shift}' added!", ephemeral=ephemeral)
            else:
                await interaction.followup.send("❌ Failed to save shift data. Please try again later.", ephemeral=ephemeral)
        except Exception as e:
            logger.error(f"Error in set_shift: {str(e)}", exc_info=True)
            await interaction.followup.send("❌ An unexpected error occurred. See logs for details.", ephemeral=ephemeral)

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="remove-shift", description="Remove a shift configuration")
    @app_commands.describe(shift="The name of the shift to remove")
    async def remove_shift(self, interaction: discord.Interaction, shift: str):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)
        await interaction.response.defer(ephemeral=ephemeral)

        try:
            guild_id = interaction.guild.id
            shift_file = settings.get_guild_shifts_path(guild_id)
            existing_shifts = await file_handlers.load_json(shift_file, [])

            # Case-insensitive search
            normalized_shift = next((s for s in existing_shifts if s.lower() == shift.lower()), None)
            if normalized_shift is None:
                await interaction.followup.send(f"❌ Shift '{shift}' doesn't exist!", ephemeral=ephemeral)
                return

            existing_shifts.remove(normalized_shift)
            success = await file_handlers.save_json(shift_file, existing_shifts)

            if success:
                await interaction.followup.send(f"✅ Shift '{normalized_shift}' removed!", ephemeral=ephemeral)
            else:
                await interaction.followup.send("❌ Failed to save shift data. Please try again later.", ephemeral=ephemeral)
        except Exception as e:
            logger.error(f"Error in remove_shift: {str(e)}", exc_info=True)
            await interaction.followup.send("❌ An unexpected error occurred. See logs for details.", ephemeral=ephemeral)

    # Period Management
    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="set-period", description="Add a valid period name")
    @app_commands.describe(period="The name of the period to add")
    async def set_period(self, interaction: discord.Interaction, period: str):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)
        await interaction.response.defer(ephemeral=ephemeral)

        try:
            logger.info(f"User {interaction.user.name} used set-period command for period '{period}'")

            if not period.strip():
                await interaction.followup.send("❌ Period name cannot be empty.", ephemeral=ephemeral)
                return

            guild_id = interaction.guild.id
            period_file = settings.get_guild_periods_path(guild_id)
            existing_periods = await file_handlers.load_json(period_file, [])

            # Case-insensitive check with original casing preservation
            if any(period.lower() == p.lower() for p in existing_periods):
                await interaction.followup.send(f"❌ Period '{period}' already exists!", ephemeral=ephemeral)
                return

            existing_periods.append(period.strip())
            success = await file_handlers.save_json(period_file, existing_periods)

            if success:
                await interaction.followup.send(f"✅ Period '{period}' added!", ephemeral=ephemeral)
            else:
                await interaction.followup.send("❌ Failed to save period data. Please try again later.", ephemeral=ephemeral)
        except Exception as e:
            logger.error(f"Error in set_period: {str(e)}", exc_info=True)
            await interaction.followup.send("❌ An unexpected error occurred. See logs for details.", ephemeral=ephemeral)

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="remove-period", description="Remove a period configuration")
    @app_commands.describe(period="The name of the period to remove")
    async def remove_period(self, interaction: discord.Interaction, period: str):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)
        await interaction.response.defer(ephemeral=ephemeral)

        try:
            guild_id = interaction.guild.id
            period_file = settings.get_guild_periods_path(guild_id)
            existing_periods = await file_handlers.load_json(period_file, [])

            # Case-insensitive search
            normalized_period = next((p for p in existing_periods if p.lower() == period.lower()), None)
            if normalized_period is None:
                await interaction.followup.send(f"❌ Period '{period}' doesn't exist!", ephemeral=ephemeral)
                return

            existing_periods.remove(normalized_period)
            success = await file_handlers.save_json(period_file, existing_periods)

            if success:
                await interaction.followup.send(f"✅ Period '{normalized_period}' removed!", ephemeral=ephemeral)
            else:
                await interaction.followup.send("❌ Failed to save period data. Please try again later.", ephemeral=ephemeral)
        except Exception as e:
            logger.error(f"Error in remove_period: {str(e)}", exc_info=True)
            await interaction.followup.send("❌ An unexpected error occurred. See logs for details.", ephemeral=ephemeral)

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
        await interaction.response.defer(ephemeral=ephemeral)

        try:
            # Parse inputs
            from_num = validators.parse_money(from_range)
            to_num = validators.parse_money(to_range)
            bonus_amount = validators.parse_money(bonus)

            # Validation
            if None in (from_num, to_num, bonus_amount):
                await interaction.followup.send("❌ Invalid number format.", ephemeral=ephemeral)
                return

            if from_num >= to_num:
                await interaction.followup.send("❌ The 'from' value must be less than the 'to' value.", ephemeral=ephemeral)
                return

            guild_id = interaction.guild.id
            bonus_file = settings.get_guild_bonus_rules_path(guild_id)
            bonus_rules = await file_handlers.load_json(bonus_file, [])

            new_rule = {"from": float(from_num), "to": float(to_num), "amount": float(bonus_amount)}

            # Check for overlaps
            for rule in bonus_rules:
                # Convert stored rule values to Decimal for comparison
                rule_from = validators.parse_money(rule.get('from', '0'))
                rule_to = validators.parse_money(rule.get('to', '0'))

                if rule_from is None or rule_to is None: continue # Skip invalid stored rules

                if (from_num < rule_to and to_num > rule_from): # More precise overlap check
                    await interaction.followup.send(
                        f"❌ This rule (${from_num:,.2f}-${to_num:,.2f}) overlaps with an existing rule (${rule_from:,.2f}-${rule_to:,.2f}).",
                        ephemeral=ephemeral
                    )
                    return

            bonus_rules.append(new_rule)
            # Sort rules by 'from' value
            bonus_rules.sort(key=lambda x: x["from"])
            success = await file_handlers.save_json(bonus_file, bonus_rules)

            if success:
                response = f"✅ Bonus rule added: ${from_num:,.2f} - ${to_num:,.2f} → Bonus: ${bonus_amount:,.2f}!"
                await interaction.followup.send(response, ephemeral=ephemeral)
            else:
                await interaction.followup.send("❌ Failed to save bonus rule.", ephemeral=ephemeral)

        except Exception as e:
            logger.error(f"Error in set_bonus_rule: {str(e)}", exc_info=True)
            await interaction.followup.send("❌ An unexpected error occurred. See logs for details.", ephemeral=ephemeral)

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="remove-bonus-rule", description="Remove a bonus rule for a revenue range")
    @app_commands.describe(
        from_range="Lower bound of revenue",
        to_range="Upper bound of revenue"
    )
    async def remove_bonus_rule(self, interaction: discord.Interaction, from_range: str, to_range: str):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)
        await interaction.response.defer(ephemeral=ephemeral)

        try:
            # Parse inputs
            from_num = validators.parse_money(from_range)
            to_num = validators.parse_money(to_range)

            if None in (from_num, to_num):
                await interaction.followup.send("❌ Invalid number format.", ephemeral=ephemeral)
                return

            guild_id = interaction.guild.id
            bonus_file = settings.get_guild_bonus_rules_path(guild_id)
            bonus_rules = await file_handlers.load_json(bonus_file, [])

            # Find exact match based on float comparison (handle potential precision issues if needed)
            # It's generally safer to compare Decimal if inputs were parsed as Decimal
            rule_to_remove = next(
                (rule for rule in bonus_rules
                if abs(float(rule.get("from", 0)) - float(from_num)) < 1e-9 and abs(float(rule.get("to", 0)) - float(to_num)) < 1e-9),
                None
            )

            if not rule_to_remove:
                await interaction.followup.send(f"❌ No bonus rule found for ${from_num:,.2f}-${to_num:,.2f}.", ephemeral=ephemeral)
                return

            bonus_rules.remove(rule_to_remove)
            success = await file_handlers.save_json(bonus_file, bonus_rules)

            if success:
                response = f"✅ Bonus rule removed: ${from_num:,.2f}-${to_num:,.2f}"
                await interaction.followup.send(response, ephemeral=ephemeral)
            else:
                await interaction.followup.send("❌ Failed to remove bonus rule.", ephemeral=ephemeral)

        except Exception as e:
            logger.error(f"Error in remove_bonus_rule: {str(e)}", exc_info=True)
            await interaction.followup.send("❌ An unexpected error occurred. See logs for details.", ephemeral=ephemeral)

    # List Commands
    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="list-roles", description="[Legacy] List configured legacy roles and percentages")
    async def list_roles(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)
        await interaction.response.defer(ephemeral=ephemeral)

        try:
            guild_id = interaction.guild.id
            role_file = settings.get_guild_roles_path(guild_id)
            role_data = await file_handlers.load_json(role_file, {})

            if not role_data:
                await interaction.followup.send("❌ No legacy roles configured.", ephemeral=ephemeral)
                return

            embed = discord.Embed(title="Configured Legacy Roles", color=discord.Color.blue())

            for role_id, percentage in role_data.items():
                role = interaction.guild.get_role(int(role_id))
                role_name = role.name if role else f"Unknown Role ({role_id})"
                embed.add_field(name=role_name, value=f"{percentage}%", inline=True)

            await interaction.followup.send(embed=embed, ephemeral=ephemeral)

        except Exception as e:
            logger.error(f"Error in list_roles: {str(e)}", exc_info=True)
            await interaction.followup.send(
                "❌ Failed to load legacy role data.",
                ephemeral=ephemeral
            )

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="list-shifts", description="List configured shifts")
    async def list_shifts(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)
        await interaction.response.defer(ephemeral=ephemeral)

        try:
            guild_id = interaction.guild.id
            shift_file = settings.get_guild_shifts_path(guild_id)
            guild_shifts = await file_handlers.load_json(shift_file, [])

            if not guild_shifts:
                await interaction.followup.send("❌ No shifts configured.", ephemeral=ephemeral)
                return

            embed = discord.Embed(title="Configured Shifts", color=discord.Color.blue())
            embed.description = "\n".join(f"• {shift}" for shift in guild_shifts) if guild_shifts else "No shifts set."
            # embed.add_field(name="Shifts", value="\n".join(f"• {shift}" for shift in guild_shifts))
            await interaction.followup.send(embed=embed, ephemeral=ephemeral)

        except Exception as e:
            logger.error(f"Error in list_shifts: {str(e)}", exc_info=True)
            await interaction.followup.send("❌ Failed to load shift data.", ephemeral=ephemeral)

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="list-periods", description="List configured periods")
    async def list_periods(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)
        await interaction.response.defer(ephemeral=ephemeral)

        try:
            guild_id = interaction.guild.id
            period_file = settings.get_guild_periods_path(guild_id)
            guild_periods = await file_handlers.load_json(period_file, [])

            if not guild_periods:
                await interaction.followup.send("❌ No periods configured.", ephemeral=ephemeral)
                return

            embed = discord.Embed(title="Configured Periods", color=discord.Color.blue())
            embed.description = "\n".join(f"• {period}" for period in guild_periods) if guild_periods else "No periods set."
            # embed.add_field(name="Periods", value="\n".join(f"• {period}" for period in guild_periods))
            await interaction.followup.send(embed=embed, ephemeral=ephemeral)

        except Exception as e:
            logger.error(f"Error in list_periods: {str(e)}", exc_info=True)
            await interaction.followup.send("❌ Failed to load period data.", ephemeral=ephemeral)

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="list-bonus-rules", description="List configured bonus rules")
    async def list_bonus_rules(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)
        await interaction.response.defer(ephemeral=ephemeral)

        try:
            guild_id = interaction.guild.id
            bonus_file = settings.get_guild_bonus_rules_path(guild_id)
            bonus_rules = await file_handlers.load_json(bonus_file, [])

            if not bonus_rules:
                await interaction.followup.send("❌ No bonus rules configured.", ephemeral=ephemeral)
                return

            embed = discord.Embed(title="Bonus Rules", color=discord.Color.green())
            description = []
            for rule in sorted(bonus_rules, key=lambda x: float(x.get("from", 0))):
                 from_val = float(rule.get('from', 0))
                 to_val = float(rule.get('to', 0))
                 amount = float(rule.get('amount', 0))
                 description.append(f"• **${from_val:,.2f} - ${to_val:,.2f}**: Bonus ${amount:,.2f}")

            embed.description = "\n".join(description) if description else "No rules set."

            await interaction.followup.send(embed=embed, ephemeral=ephemeral)

        except Exception as e:
            logger.error(f"Error in list_bonus_rules: {str(e)}", exc_info=True)
            await interaction.followup.send("❌ Failed to load bonus rules.", ephemeral=ephemeral)

    # Model Management
    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="set-model", description="Add a valid model name")
    @app_commands.describe(model="The name of the model to add")
    async def set_model(self, interaction: discord.Interaction, model: str):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)
        await interaction.response.defer(ephemeral=ephemeral)

        guild_id = interaction.guild.id
        file_path = settings.get_guild_models_path(guild_id)

        logger.info(f"User {interaction.user.name} used set-model command for model '{model}'")

        if not model.strip():
            await interaction.followup.send("❌ Model name cannot be empty.", ephemeral=ephemeral)
            return

        model_data = await file_handlers.load_json(file_path, [])

        if model.lower() in [m.lower() for m in model_data]:
            await interaction.followup.send(f"❌ Model '{model}' already exists!", ephemeral=ephemeral)
            return

        model_data.append(model.strip()) # Ensure stripped name is added
        success = await file_handlers.save_json(file_path, model_data)

        if success:
            await interaction.followup.send(f"✅ Model '{model.strip()}' added!", ephemeral=ephemeral)
        else:
            await interaction.followup.send("❌ Failed to save model data. Please try again later.", ephemeral=ephemeral)

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="remove-model", description="Remove a model configuration")
    @app_commands.describe(model="The name of the model to remove")
    async def remove_model(self, interaction: discord.Interaction, model: str):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)
        await interaction.response.defer(ephemeral=ephemeral)

        guild_id = interaction.guild.id
        file_path = settings.get_guild_models_path(guild_id)

        # Load existing models
        try:
            model_data = await file_handlers.load_json(file_path, [])
        except Exception as e:
            logger.error(f"Error loading models: {str(e)}")
            await interaction.followup.send("❌ Failed to load model data.", ephemeral=ephemeral)
            return

        # Find and remove the model (case-insensitive)
        normalized_model = next((m for m in model_data if m.lower() == model.lower()), None)
        if normalized_model is None:
            await interaction.followup.send(f"❌ Model '{model}' doesn't exist!", ephemeral=ephemeral)
            return

        try:
            model_data.remove(normalized_model)
            success = await file_handlers.save_json(file_path, model_data)
        except Exception as e:
            logger.error(f"Error saving models: {str(e)}")
            success = False

        if success:
            await interaction.followup.send(f"✅ Model '{normalized_model}' removed!", ephemeral=ephemeral)
        else:
            await interaction.followup.send("❌ Failed to save model data. Please try again later.", ephemeral=ephemeral)

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="list-models", description="List configured models")
    async def list_models(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)
        await interaction.response.defer(ephemeral=ephemeral)

        guild_id = interaction.guild.id
        file_path = settings.get_guild_models_path(guild_id)

        guild_models = await file_handlers.load_json(file_path, [])

        if not guild_models:
            await interaction.followup.send("❌ No models configured.", ephemeral=ephemeral)
            return

        embed = discord.Embed(title="Configured Models", color=discord.Color.blue())
        embed.description = "\n".join(f"• {model}" for model in guild_models) if guild_models else "No models set."
        # embed.add_field(name="Models", value="\n".join(f"• {model}" for model in guild_models))
        await interaction.followup.send(embed=embed, ephemeral=ephemeral)

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="clear-earnings", description="Clear all earnings data for this server")
    async def clear_earnings(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        guild_name = interaction.guild.name

        async def confirm_callback(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=ephemeral, thinking=True) # Defer early
            success = await self.reset_earnings(interaction)
            if success:
                await interaction.followup.send(content=f"✅ All earnings data for the guild ({guild_name}) has been successfully cleared.", ephemeral=ephemeral)
            else:
                await interaction.followup.send(content=f"❌ Failed to clear earnings data for {guild_name}. Check logs.", ephemeral=ephemeral)
            # No need to edit the original message view=None as followup is used

        async def cancel_callback(interaction: discord.Interaction):
            await interaction.response.edit_message(content="❌ Operation Canceled.", view=None)

        view = discord.ui.View(timeout=180)
        confirm_button = discord.ui.Button(label="Confirm Clear All", style=discord.ButtonStyle.danger)
        cancel_button = discord.ui.Button(label="Cancel", style=discord.ButtonStyle.secondary)

        confirm_button.callback = confirm_callback
        cancel_button.callback = cancel_callback

        view.add_item(confirm_button)
        view.add_item(cancel_button)

        await interaction.response.send_message(
            "‼️🚨‼ **Permanently delete all earnings data for this server? This cannot be undone.**",
            view=view,
            ephemeral=ephemeral
        )


    async def remove_sale_by_id(
        self,
        interaction: discord.Interaction,
        sale_ids: Optional[list[str]] = None,
        users: Optional[list[discord.User]] = None
    ) -> tuple[bool, str]:
        """Helper function to remove sales by IDs or all sales for multiple users."""
        guild_id = interaction.guild.id
        earnings_file = settings.get_guild_earnings_path(guild_id)
        earnings_data = await file_handlers.load_json(earnings_file, {})

        removed_entries = {}
        total_removed = 0
        changed = False

        try:
            original_data = json.dumps(earnings_data) # For comparison later

            if sale_ids is None and users:
                # Remove all entries for specified users
                for user in users:
                    user_key = f"<@{user.id}>"
                    if user_key in earnings_data and earnings_data[user_key]:
                        count = len(earnings_data[user_key])
                        logger.info(f"Removing all {count} entries for user {user.id} ({user_key}) in guild {guild_id}")
                        earnings_data[user_key] = []
                        removed_entries[user_key] = {'count': count, 'user_obj': user}
                        total_removed += count
                        changed = True
            elif sale_ids:
                # Remove specific IDs from specified users (or all users if users is None)
                sale_id_set = set(sale_ids) # Use set for faster lookups
                target_user_keys = [f"<@{u.id}>" for u in users] if users else list(earnings_data.keys())

                for user_key in target_user_keys:
                    if user_key in earnings_data:
                        original_user_entries = earnings_data[user_key]
                        # Filter out entries whose ID is in the set to remove
                        filtered_entries = [e for e in original_user_entries if e.get("id") not in sale_id_set]

                        removed_count = len(original_user_entries) - len(filtered_entries)
                        if removed_count > 0:
                            earnings_data[user_key] = filtered_entries
                            user_obj = users.get(int(user_key.strip('<@>'))) if users else interaction.guild.get_member(int(user_key.strip('<@>')))
                            removed_entries[user_key] = {
                                'count': removed_count,
                                'user_obj': user_obj
                            }
                            total_removed += removed_count
                            changed = True
                            logger.info(f"Removed {removed_count} specific sales for user {user_key} in guild {guild_id}")
            else:
                # This case should ideally not be reached due to checks in the command
                return (False, "❌ Invalid operation: Must specify users if no sale IDs are given.")


            if not changed:
                return (False, "❌ No matching sales found for the specified criteria or no changes were made.")

            # Save only if data actually changed
            success = await file_handlers.save_json(earnings_file, earnings_data)

            if not success:
                return (False, "❌ Failed to save updated earnings data locally.")

            # Build success message with proper user resolution
            message_parts = []
            if sale_ids:
                id_list_str = ", ".join(f"`{s_id}`" for s_id in sale_ids[:10]) # Limit display
                if len(sale_ids) > 10: id_list_str += "..."
                sale_text = "sales" if len(sale_ids) > 1 else "sale"
                message_parts.append(f"✅ {sale_text.capitalize()} with IDs {id_list_str} removed:")
            elif users:
                message_parts.append("✅ All sales removed for:")

            for user_key, data in removed_entries.items():
                user_obj = data['user_obj'] # Use the stored object
                if user_obj:
                    name = f"{user_obj.display_name} (@{user_obj.name})"
                else:
                    # Attempt to resolve again if somehow lost
                    member = interaction.guild.get_member(int(user_key.strip('<@>')))
                    name = f"{member.display_name} (@{member.name})" if member else f"Unknown ({user_key})"
                message_parts.append(f"- `{name}`: {data['count']} entries")

            message_parts.append(f"\nTotal removed: {total_removed} entries")
            return (True, "\n".join(message_parts))

        except Exception as e:
            logger.error(f"Error processing remove_sale_by_id for guild {guild_id}: {e}", exc_info=True)
            return (False, f"❌ Error processing request: {str(e)}")

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(
        name="remove-sale",
        description="Remove sales by IDs or all sales for multiple users"
    )
    @app_commands.describe(
        sale_ids="Comma-separated sale IDs (leave empty to remove all for specified users)",
        users="Comma-separated user mentions to target (leave empty to target sales IDs across all users)"
    )
    async def remove_sale(
        self,
        interaction: discord.Interaction,
        sale_ids: Optional[str] = None,
        users: Optional[str] = None
    ):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)
        await interaction.response.defer(ephemeral=ephemeral, thinking=True)

        # Validate input: Must provide sale_ids OR users
        if not sale_ids and not users:
            await interaction.followup.send(
                "❌ Please provide either `sale_ids` or `users` to target.",
                ephemeral=ephemeral
            )
            return

        # Process user mentions
        user_objs_map = {} # Store as dict for faster lookup later if needed
        if users:
            user_id_mentions = re.findall(r'<@!?(\d+)>', users)
            if not user_id_mentions:
                await interaction.followup.send(
                    "❌ Invalid user mentions format. Use @mention, separated by commas or spaces.",
                    ephemeral=ephemeral
                )
                return

            invalid_users = []
            for user_id_str in user_id_mentions:
                user_id = int(user_id_str)
                member = interaction.guild.get_member(user_id)
                if member:
                    user_objs_map[user_id] = member
                else:
                    invalid_users.append(user_id_str)

            if invalid_users:
                await interaction.followup.send(
                    f"❌ Could not find the following users in this server: {', '.join(invalid_users)}",
                    ephemeral=ephemeral
                )
                return
            if not user_objs_map: # Should not happen if validation passed, but safety check
                 await interaction.followup.send("❌ No valid users specified.", ephemeral=ephemeral)
                 return


        # Process sale IDs
        sale_id_list = []
        if sale_ids:
            sale_id_list = [s_id.strip() for s_id in re.split(r'[,\s]+', sale_ids) if s_id.strip()] # Split by comma or space
            if not sale_id_list:
                 # Allow empty sale_ids ONLY if users are provided
                 if not users:
                    await interaction.followup.send(
                        "❌ Invalid sale IDs format. Provide comma or space-separated IDs.",
                        ephemeral=ephemeral
                    )
                    return
            else:
                # Validate IDs if provided (basic check, could add regex)
                if any(not re.match(r'^\d+-\d+$', s_id) for s_id in sale_id_list): # Example format check
                     await interaction.followup.send(
                         "❌ Invalid sale ID format detected. Expected format like `timestamp-random`.",
                         ephemeral=ephemeral
                     )
                     return
                sale_id_list = list(set(sale_id_list)) # Remove duplicates


        # --- Preview Count Logic ---
        earnings_data = await file_handlers.load_json(
            settings.get_guild_earnings_path(interaction.guild.id),
            {}
        )
        total_entries_to_remove = 0
        entries_to_remove_details = {} # Key: user_key, Value: count

        try:
            if not sale_id_list and user_objs_map:
                # Count all entries for specified users
                for user_id, user_obj in user_objs_map.items():
                    user_key = f"<@{user_id}>"
                    count = len(earnings_data.get(user_key, []))
                    if count > 0:
                        entries_to_remove_details[user_key] = {'count': count, 'user_obj': user_obj}
                        total_entries_to_remove += count
            elif sale_id_list:
                # Count entries matching sale IDs
                sale_id_set = set(sale_id_list)
                target_user_keys = [f"<@{uid}>" for uid in user_objs_map.keys()] if user_objs_map else earnings_data.keys()

                for user_key in target_user_keys:
                    entries = earnings_data.get(user_key, [])
                    count = sum(1 for e in entries if e.get("id") in sale_id_set)
                    if count > 0:
                        user_id = int(user_key.strip('<@>'))
                        user_obj = user_objs_map.get(user_id) or interaction.guild.get_member(user_id)
                        entries_to_remove_details[user_key] = {'count': count, 'user_obj': user_obj}
                        total_entries_to_remove += count

            if not entries_to_remove_details:
                await interaction.followup.send(
                    "❌ No matching sales found for the specified criteria.",
                    ephemeral=ephemeral
                )
                return

            # --- Build Confirmation ---
            confirm_view = discord.ui.View(timeout=180)
            confirm_button = discord.ui.Button(style=discord.ButtonStyle.danger, label="Confirm Removal", custom_id="confirm_remove_sale")
            cancel_button = discord.ui.Button(style=discord.ButtonStyle.secondary, label="Cancel", custom_id="cancel_remove_sale")

            async def confirm_callback(interaction: discord.Interaction):
                await interaction.response.defer(ephemeral=ephemeral, thinking=True)
                # Pass the map instead of list for remove_sale_by_id
                success, result = await self.remove_sale_by_id(
                    interaction,
                    sale_id_list if sale_id_list else None, # Pass list or None
                    user_objs_map if user_objs_map else None # Pass map or None
                )
                await interaction.followup.send(content=result, ephemeral=ephemeral)
                # Disable buttons on the original message
                try:
                    await interaction.message.edit(view=None)
                except discord.NotFound: pass # Message might be gone
                confirm_view.stop()

            async def cancel_callback(interaction: discord.Interaction):
                await interaction.response.edit_message(content="❌ Operation canceled.", view=None)
                confirm_view.stop()

            confirm_button.callback = confirm_callback
            cancel_button.callback = cancel_callback
            confirm_view.add_item(confirm_button)
            confirm_view.add_item(cancel_button)

            message_parts = ["‼️🚨‼️ **Confirm Removal**\n"]
            if sale_id_list:
                id_list_display = ", ".join(f"`{s_id}`" for s_id in sale_id_list[:10])
                if len(sale_id_list) > 10: id_list_display += "..."
                message_parts.append(f"Sales IDs: {id_list_display}")
            else:
                message_parts.append("ALL SALES for:")

            user_details_parts = []
            for user_key, data in entries_to_remove_details.items():
                user_obj = data['user_obj']
                name = f"{user_obj.display_name} (@{user_obj.name})" if user_obj else f"Unknown ({user_key})"
                user_details_parts.append(f"- `{name}`: {data['count']} entries")

            # Limit display if too many users
            if len(user_details_parts) > 10:
                 message_parts.extend(user_details_parts[:10])
                 message_parts.append(f"...and {len(user_details_parts) - 10} more users.")
            else:
                 message_parts.extend(user_details_parts)

            message_parts.append(f"\n**Total entries to remove: {total_entries_to_remove}**")

            await interaction.followup.send(
                "\n".join(message_parts),
                view=confirm_view,
                ephemeral=ephemeral
            )

        except Exception as e:
            logger.error(f"Error during remove-sale preview/confirmation setup: {e}", exc_info=True)
            await interaction.followup.send(
                f"❌ An error occurred during setup: {str(e)}",
                ephemeral=ephemeral
            )

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="reset-config", description="Reset all configuration files for this server")
    async def reset_config(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        async def confirm_callback(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=ephemeral, thinking=True)
            results = {}
            results['shift'] = await self.reset_shift(interaction)
            results['period'] = await self.reset_period(interaction)
            results['role'] = await self.reset_role(interaction) # Legacy
            results['bonus'] = await self.reset_bonus_rules(interaction)
            results['models'] = await self.reset_models(interaction)
            results['display'] = await self.reset_display(interaction)
            results['compensation'] = await self.reset_compensation(interaction)

            failed_resets = [k for k, v in results.items() if not v]
            if not failed_resets:
                await interaction.followup.send(content="✅ All configuration data has been reset for this server.", ephemeral=ephemeral)
            else:
                 await interaction.followup.send(content=f"⚠️ Some configurations failed to reset ({', '.join(failed_resets)}). Check logs.", ephemeral=ephemeral)
            # No need to edit original message

        async def cancel_callback(interaction: discord.Interaction):
            await interaction.response.edit_message(content="❌ Reset Canceled.", view=None)

        view = discord.ui.View(timeout=180)
        confirm_button = discord.ui.Button(label="Confirm Reset All Config", style=discord.ButtonStyle.danger)
        cancel_button = discord.ui.Button(label="Cancel", style=discord.ButtonStyle.secondary)

        confirm_button.callback = confirm_callback
        cancel_button.callback = cancel_callback

        view.add_item(confirm_button)
        view.add_item(cancel_button)

        await interaction.response.send_message(
            content="‼️🚨‼ **Permanently reset ALL configuration data?**\n(Shifts, Periods, Roles, Bonuses, Models, Display, Compensation)\nEarnings data will **NOT** be affected (use `/clear-earnings` for that).",
            view=view,
            ephemeral=ephemeral
        )

    # --- Helper for Syncing Local Files to Mongo ---
    async def _sync_local_to_mongo(self, interaction: discord.Interaction, file_path: str) -> bool:
        """Helper to load local file data and save to MongoDB."""
        guild_id = interaction.guild.id
        mongo_success = False
        restored_data = None # Initialize
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                if not content.strip():
                    logger.warning(f"Restored file {file_path} is empty, skipping Mongo sync.")
                    return False # Treat empty file as non-syncable
                restored_data = json.loads(content)

            # Determine if it's config or earnings and call appropriate mongo save
            mongo_client_instance, _ = file_handlers.get_mongo_client()
            if not mongo_client_instance:
                logger.warning(f"MongoDB client not available, skipping sync for {file_path}")
                return None # Indicate sync was not applicable/attempted

            if settings.EARNINGS_FILE in file_path:
                if isinstance(restored_data, dict): # Check type for earnings
                    mongo_success = await file_handlers._save_earnings_mongo(guild_id, restored_data)
                else:
                    logger.error(f"Restored earnings data for {guild_id} from {file_path} is not a dict, skipping Mongo sync.")
                    mongo_success = False
            elif os.path.basename(file_path) in settings.FILENAME_TO_MONGO_KEY:
                config_key = settings.FILENAME_TO_MONGO_KEY[os.path.basename(file_path)]
                mongo_success = await file_handlers._save_guild_config_mongo(guild_id, config_key, restored_data)
            else:
                logger.warning(f"File {file_path} is not a recognized config or earnings file, skipping Mongo sync.")
                mongo_success = None # Indicate not applicable

            if mongo_success:
                 logger.info(f"Successfully synced {os.path.basename(file_path)} (guild {guild_id}) from local restore/copy to MongoDB.")
            elif mongo_success is False: # Only log error if sync attempt failed
                 logger.error(f"Failed to sync {os.path.basename(file_path)} (guild {guild_id}) from local restore/copy to MongoDB.")


        except FileNotFoundError:
             logger.error(f"Local file {file_path} not found for Mongo sync.")
             mongo_success = False
        except json.JSONDecodeError:
             logger.error(f"Restored backup file {file_path} is corrupted (invalid JSON). Cannot sync to DB.")
             mongo_success = False
        except Exception as e:
            logger.error(f"Error syncing restored backup {file_path} to MongoDB: {e}", exc_info=True)
            mongo_success = False

        return mongo_success

    # --- Restore Commands (with DB Sync) ---
    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="restore-latest-backup", description="Restore the latest backup for ALL config/earnings files")
    async def restore_latest_backup(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        async def confirm_callback(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=ephemeral, thinking=True) # Defer early

            guild_id = interaction.guild.id
            config_dir = settings.get_guild_path(guild_id)
            earnings_dir = settings.get_guild_earnings_path_dir(guild_id) # Get dir path

            # Find backup files in both config and earnings directories
            config_backup_files = glob.glob(os.path.join(config_dir, "*.bak"))
            # Construct the expected earnings backup file path
            earnings_backup_file = os.path.join(earnings_dir, settings.EARNINGS_FILE + ".bak")

            restored_count = 0
            failed_local_count = 0
            synced_to_db_count = 0
            failed_db_sync_count = 0
            sync_errors = []
            sync_not_attempted = 0

            all_bak_files = config_backup_files
            if os.path.exists(earnings_backup_file):
                all_bak_files.append(earnings_backup_file)
            else:
                 logger.info(f"No earnings backup file found at {earnings_backup_file}")


            if not all_bak_files:
                await interaction.followup.send(content="❌ No backup files found for this server.", ephemeral=ephemeral)
                return

            logger.info(f"Attempting to restore {len(all_bak_files)} files for guild {guild_id}")

            for bak_file in all_bak_files:
                original_file = bak_file[:-4]  # Remove .bak extension
                sync_status = None
                try:
                    shutil.copy2(bak_file, original_file)
                    logger.info(f"Restored local file: {original_file}")
                    restored_count += 1
                    # Attempt DB Sync
                    sync_status = await self._sync_local_to_mongo(interaction, original_file)
                    if sync_status is True:
                         synced_to_db_count += 1
                    elif sync_status is False:
                         failed_db_sync_count += 1
                         sync_errors.append(os.path.basename(original_file))
                    else: # sync_status is None (not attempted / not applicable)
                        sync_not_attempted += 1

                except Exception as e:
                    logger.error(f"Failed to restore local file {bak_file}: {str(e)}")
                    failed_local_count += 1

            # Prepare the response content
            content = f"**Restore Summary (Guild: {guild_id}):**\n"
            content += f"• Files Found: {len(all_bak_files)}\n"
            content += f"• Files Restored Locally: {restored_count}/{len(all_bak_files)}\n"
            if failed_local_count > 0:
                content += f"• Local Restore Failures: {failed_local_count} ❌\n"

            # Refine DB sync reporting
            attempted_sync_count = restored_count - sync_not_attempted
            if attempted_sync_count > 0: # Only report if sync was attempted
                content += f"• Synced to DB: {synced_to_db_count}/{attempted_sync_count}\n"
                if failed_db_sync_count > 0:
                    content += f"• DB Sync Failures: {failed_db_sync_count} ⚠️\n"
                    content += f"  (Files: {', '.join(sync_errors[:5])}{'...' if len(sync_errors) > 5 else ''})\n"
            elif sync_not_attempted == restored_count and restored_count > 0 :
                 content += "• DB Sync: Not attempted (MongoDB may be unavailable or files not applicable)\n"
            else:
                 content += "• DB Sync: No files eligible for sync\n"


            await interaction.followup.send(content=content, ephemeral=ephemeral)

        async def cancel_callback(interaction: discord.Interaction):
            # Need edit_message here since the view is attached to the original response
            await interaction.response.edit_message(content="❌ Restore cancelled.", view=None)

        view = discord.ui.View(timeout=180) # Use a standard view for confirmation
        confirm_button = discord.ui.Button(label="Confirm Restore All", style=discord.ButtonStyle.danger)
        cancel_button = discord.ui.Button(label="Cancel", style=discord.ButtonStyle.secondary)

        confirm_button.callback = confirm_callback
        cancel_button.callback = cancel_callback

        view.add_item(confirm_button)
        view.add_item(cancel_button)

        await interaction.response.send_message(
            content="‼️🚨‼ **Restore latest backup for ALL configuration and earnings files?**\n(This overwrites current settings and attempts DB sync)",
            view=view,
            ephemeral=ephemeral
        )

    # --- Individual Reset Methods (return bool for success) ---
    async def reset_shift(self, interaction: discord.Interaction) -> bool:
        guild_id = interaction.guild.id
        shift_file = settings.get_guild_shifts_path(guild_id)
        return await file_handlers.save_json(shift_file, [])

    async def reset_period(self, interaction: discord.Interaction) -> bool:
        guild_id = interaction.guild.id
        period_file = settings.get_guild_periods_path(guild_id)
        return await file_handlers.save_json(period_file, [])

    async def reset_role(self, interaction: discord.Interaction) -> bool: # Legacy
        guild_id = interaction.guild.id
        role_file = settings.get_guild_roles_path(guild_id)
        return await file_handlers.save_json(role_file, {})

    async def reset_bonus_rules(self, interaction: discord.Interaction) -> bool:
        guild_id = interaction.guild.id
        bonus_file = settings.get_guild_bonus_rules_path(guild_id)
        return await file_handlers.save_json(bonus_file, [])

    async def reset_earnings(self, interaction: discord.Interaction) -> bool:
        return await file_handlers.save_json(settings.get_guild_earnings_path(interaction.guild.id), {})

    async def reset_models(self, interaction: discord.Interaction) -> bool:
        return await file_handlers.save_json(settings.get_guild_models_path(interaction.guild.id), [])

    async def reset_compensation(self, interaction: discord.Interaction) -> bool:
        return await file_handlers.save_json(
            settings.get_guild_commission_path(interaction.guild.id),
            settings.DEFAULT_COMMISSION_SETTINGS.copy()
        )

    async def reset_display(self, interaction: discord.Interaction) -> bool:
        guild_id = interaction.guild.id
        file_path = settings.get_guild_display_path(guild_id)
        return await file_handlers.save_json(file_path, settings.DEFAULT_DISPLAY_SETTINGS.copy())

    # --- Individual Reset Commands (using ConfirmButton) ---
    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="reset-shift-config", description="Reset shift configuration")
    async def reset_shift_config(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        async def reset_action(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=ephemeral, thinking=True)
            success = await self.reset_shift(interaction)
            await interaction.followup.send(
                content="✅ Shift configuration reset." if success else "❌ Failed to reset shift configuration.",
                ephemeral=ephemeral
            )

        view = ConfirmButton(reset_action, interaction.user.id)
        # Store message for potential timeout edit
        view._interaction_message = await interaction.response.send_message(
            "⚠️ **Permanently reset the shift configuration?**",
            view=view,
            ephemeral=ephemeral
        )

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="reset-period-config", description="Reset period configuration")
    async def reset_period_config(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        async def reset_action(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=ephemeral, thinking=True)
            success = await self.reset_period(interaction)
            await interaction.followup.send(
                content="✅ Period configuration reset." if success else "❌ Failed to reset period configuration.",
                ephemeral=ephemeral
            )

        view = ConfirmButton(reset_action, interaction.user.id)
        view._interaction_message = await interaction.response.send_message(
            "⚠️ **Permanently reset the period configuration?**",
            view=view,
            ephemeral=ephemeral
        )

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="reset-role-config", description="[Legacy] Reset legacy role configuration")
    async def reset_role_config(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        async def reset_action(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=ephemeral, thinking=True)
            success = await self.reset_role(interaction)
            await interaction.followup.send(
                content="✅ Legacy Role configuration reset." if success else "❌ Failed to reset legacy role configuration.",
                ephemeral=ephemeral
            )

        view = ConfirmButton(reset_action, interaction.user.id)
        view._interaction_message = await interaction.response.send_message(
            "⚠️ **Permanently reset the legacy role configuration?**",
            view=view,
            ephemeral=ephemeral
        )

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="reset-bonus-config", description="Reset bonus rules configuration")
    async def reset_bonus_config(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        async def reset_action(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=ephemeral, thinking=True)
            success = await self.reset_bonus_rules(interaction)
            await interaction.followup.send(
                content="✅ Bonus rules configuration reset." if success else "❌ Failed to reset bonus rules configuration.",
                ephemeral=ephemeral
            )

        view = ConfirmButton(reset_action, interaction.user.id)
        view._interaction_message = await interaction.response.send_message(
            "⚠️ **Permanently reset the bonus rules configuration?**",
            view=view,
            ephemeral=ephemeral
        )


    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="reset-models-config", description="Reset models configuration")
    async def reset_models_config(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        async def reset_action(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=ephemeral, thinking=True)
            success = await self.reset_models(interaction)
            await interaction.followup.send(
                content="✅ Model settings reset." if success else "❌ Failed to reset models.",
                ephemeral=ephemeral
            )

        view = ConfirmButton(reset_action, interaction.user.id)
        view._interaction_message = await interaction.response.send_message(
            "⚠️ **Permanently reset the models configuration?**",
            view=view,
            ephemeral=ephemeral
        )

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="reset-compensation-config", description="Reset compensation configuration")
    async def reset_compensation_config(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        async def reset_action(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=ephemeral, thinking=True)
            success = await self.reset_compensation(interaction)
            await interaction.followup.send(
                 content="✅ Compensation configuration reset." if success else "❌ Failed to reset compensation configuration.",
                 ephemeral=ephemeral
            )

        view = ConfirmButton(reset_action, interaction.user.id)
        view._interaction_message = await interaction.response.send_message(
            "⚠️ **Permanently reset the compensation configuration?**",
            view=view,
            ephemeral=ephemeral
        )

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="reset-display-config", description="Reset display configuration")
    async def reset_display_config(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        async def reset_action(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=ephemeral, thinking=True)
            success = await self.reset_display(interaction)
            await interaction.followup.send(
                content="✅ Display configuration reset." if success else "❌ Failed to reset display configuration.",
                ephemeral=ephemeral
            )

        view = ConfirmButton(reset_action, interaction.user.id)
        view._interaction_message = await interaction.response.send_message(
            "⚠️ **Permanently reset the display configuration?**",
            view=view,
            ephemeral=ephemeral
        )


    # --- Individual Restore Commands (using ConfirmButton and DB Sync) ---
    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="restore-shift-config", description="Restore the latest shift configuration backup")
    async def restore_shift_config(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        async def restore_action(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=ephemeral, thinking=True) # Defer early
            file_path = settings.get_guild_shifts_path(interaction.guild.id)
            backup_file = f"{file_path}.bak"
            message = ""
            mongo_synced = None # None = not applicable/attempted, True = success, False = fail

            if os.path.exists(backup_file):
                try:
                    shutil.copy2(backup_file, file_path)
                    message = "✅ Shift configuration backup restored locally."
                    # Attempt to sync to MongoDB
                    mongo_synced = await self._sync_local_to_mongo(interaction, file_path)
                    if mongo_synced is True:
                        message += " Synced to DB."
                    elif mongo_synced is False: # Explicitly check for False (sync failure)
                         message += " ⚠️ DB sync failed."
                    # If mongo_synced is None, no message added for DB sync

                except Exception as e:
                    logger.error(f"Error during local restore of {backup_file}: {e}")
                    message = f"❌ Error restoring local file: {e}"
            else:
                message = "❌ No shift configuration backup found."

            await interaction.followup.send(content=message, ephemeral=ephemeral) # Use followup

        view = ConfirmButton(restore_action, interaction.user.id)
        view._interaction_message = await interaction.response.send_message(
            "⚠️ **Restore the shift configuration backup?**\n(Overwrites current settings & attempts DB sync)",
            view=view,
            ephemeral=ephemeral
        )

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="restore-period-backup", description="Restore the latest period configuration backup")
    async def restore_period_backup(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        async def restore_action(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=ephemeral, thinking=True)
            file_path = settings.get_guild_periods_path(interaction.guild.id)
            backup_file = f"{file_path}.bak"
            message = ""
            mongo_synced = None

            if os.path.exists(backup_file):
                try:
                    shutil.copy2(backup_file, file_path)
                    message = "✅ Period configuration backup restored locally."
                    mongo_synced = await self._sync_local_to_mongo(interaction, file_path)
                    if mongo_synced is True: message += " Synced to DB."
                    elif mongo_synced is False: message += " ⚠️ DB sync failed."
                except Exception as e:
                    logger.error(f"Error during local restore of {backup_file}: {e}")
                    message = f"❌ Error restoring local file: {e}"
            else:
                message = "❌ No period configuration backup found."
            await interaction.followup.send(content=message, ephemeral=ephemeral)

        view = ConfirmButton(restore_action, interaction.user.id)
        view._interaction_message = await interaction.response.send_message(
            "⚠️ **Restore the period configuration backup?**\n(Overwrites current settings & attempts DB sync)",
            view=view,
            ephemeral=ephemeral
        )

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="restore-role-backup", description="[Legacy] Restore the latest legacy role configuration backup")
    async def restore_role_backup(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        async def restore_action(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=ephemeral, thinking=True)
            file_path = settings.get_guild_roles_path(interaction.guild.id)
            backup_file = f"{file_path}.bak"
            message = ""
            mongo_synced = None

            if os.path.exists(backup_file):
                try:
                    shutil.copy2(backup_file, file_path)
                    message = "✅ Legacy Role configuration backup restored locally."
                    mongo_synced = await self._sync_local_to_mongo(interaction, file_path)
                    if mongo_synced is True: message += " Synced to DB."
                    elif mongo_synced is False: message += " ⚠️ DB sync failed."
                except Exception as e:
                    logger.error(f"Error during local restore of {backup_file}: {e}")
                    message = f"❌ Error restoring local file: {e}"
            else:
                message = "❌ No legacy role configuration backup found."
            await interaction.followup.send(content=message, ephemeral=ephemeral)

        view = ConfirmButton(restore_action, interaction.user.id)
        view._interaction_message = await interaction.response.send_message(
            "⚠️ **Restore the legacy role configuration backup?**\n(Overwrites current settings & attempts DB sync)",
            view=view,
            ephemeral=ephemeral
        )

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="restore-bonus-backup", description="Restore the latest bonus rules configuration backup")
    async def restore_bonus_backup(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        async def restore_action(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=ephemeral, thinking=True)
            file_path = settings.get_guild_bonus_rules_path(interaction.guild.id)
            backup_file = f"{file_path}.bak"
            message = ""
            mongo_synced = None

            if os.path.exists(backup_file):
                try:
                    shutil.copy2(backup_file, file_path)
                    message = "✅ Bonus rules configuration backup restored locally."
                    mongo_synced = await self._sync_local_to_mongo(interaction, file_path)
                    if mongo_synced is True: message += " Synced to DB."
                    elif mongo_synced is False: message += " ⚠️ DB sync failed."
                except Exception as e:
                    logger.error(f"Error during local restore of {backup_file}: {e}")
                    message = f"❌ Error restoring local file: {e}"
            else:
                message = "❌ No bonus rules configuration backup found."
            await interaction.followup.send(content=message, ephemeral=ephemeral)

        view = ConfirmButton(restore_action, interaction.user.id)
        view._interaction_message = await interaction.response.send_message(
            "⚠️ **Restore the bonus rules configuration backup?**\n(Overwrites current settings & attempts DB sync)",
            view=view,
            ephemeral=ephemeral
        )

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="restore-earnings-backup", description="Restore the latest earnings configuration backup")
    async def restore_earnings_backup(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        async def restore_action(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=ephemeral, thinking=True)
            file_path = settings.get_guild_earnings_path(interaction.guild.id)
            backup_file = f"{file_path}.bak"
            message = ""
            mongo_synced = None

            if os.path.exists(backup_file):
                try:
                    shutil.copy2(backup_file, file_path)
                    message = "✅ Earnings backup restored locally."
                    mongo_synced = await self._sync_local_to_mongo(interaction, file_path)
                    if mongo_synced is True: message += " Synced to DB."
                    elif mongo_synced is False: message += " ⚠️ DB sync failed."
                except Exception as e:
                    logger.error(f"Error during local restore of {backup_file}: {e}")
                    message = f"❌ Error restoring local file: {e}"
            else:
                message = "❌ No earnings backup found."
            await interaction.followup.send(content=message, ephemeral=ephemeral)

        view = ConfirmButton(restore_action, interaction.user.id)
        view._interaction_message = await interaction.response.send_message(
            "‼️🚨‼ **Restore the earnings backup?**\n(Overwrites current data & attempts DB sync)",
            view=view,
            ephemeral=ephemeral
        )

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="restore-models-backup", description="Restore the latest models configuration backup")
    async def restore_models_backup(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        async def restore_action(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=ephemeral, thinking=True)
            file_path = settings.get_guild_models_path(interaction.guild.id)
            backup_file = f"{file_path}.bak"
            message = ""
            mongo_synced = None

            if os.path.exists(backup_file):
                try:
                    shutil.copy2(backup_file, file_path)
                    message = "✅ Models configuration backup restored locally."
                    mongo_synced = await self._sync_local_to_mongo(interaction, file_path)
                    if mongo_synced is True: message += " Synced to DB."
                    elif mongo_synced is False: message += " ⚠️ DB sync failed."
                except Exception as e:
                    logger.error(f"Error during local restore of {backup_file}: {e}")
                    message = f"❌ Error restoring local file: {e}"
            else:
                message = "❌ No models configuration backup found."
            await interaction.followup.send(content=message, ephemeral=ephemeral)

        view = ConfirmButton(restore_action, interaction.user.id)
        view._interaction_message = await interaction.response.send_message(
            "⚠️ **Restore the models configuration backup?**\n(Overwrites current settings & attempts DB sync)",
            view=view,
            ephemeral=ephemeral
        )

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="restore-compensation-backup", description="Restore the latest compensation configuration backup")
    async def restore_compensation_backup(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        async def restore_action(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=ephemeral, thinking=True)
            file_path = settings.get_guild_commission_path(interaction.guild.id)
            backup_file = f"{file_path}.bak"
            message = ""
            mongo_synced = None

            if os.path.exists(backup_file):
                try:
                    shutil.copy2(backup_file, file_path)
                    message = "✅ Compensation configuration backup restored locally."
                    mongo_synced = await self._sync_local_to_mongo(interaction, file_path)
                    if mongo_synced is True: message += " Synced to DB."
                    elif mongo_synced is False: message += " ⚠️ DB sync failed."
                except Exception as e:
                    logger.error(f"Error during local restore of {backup_file}: {e}")
                    message = f"❌ Error restoring local file: {e}"
            else:
                message = "❌ No compensation configuration backup found."
            await interaction.followup.send(content=message, ephemeral=ephemeral)

        view = ConfirmButton(restore_action, interaction.user.id)
        view._interaction_message = await interaction.response.send_message(
            "⚠️ **Restore the compensation configuration backup?**\n(Overwrites current settings & attempts DB sync)",
            view=view,
            ephemeral=ephemeral
        )

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="restore-display-backup", description="Restore the latest display configuration backup")
    async def restore_display_backup(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        async def restore_action(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=ephemeral, thinking=True)
            file_path = settings.get_guild_display_path(interaction.guild.id)
            backup_file = f"{file_path}.bak"
            message = ""
            mongo_synced = None

            if os.path.exists(backup_file):
                try:
                    shutil.copy2(backup_file, file_path)
                    message = "✅ Display configuration backup restored locally."
                    mongo_synced = await self._sync_local_to_mongo(interaction, file_path)
                    if mongo_synced is True: message += " Synced to DB."
                    elif mongo_synced is False: message += " ⚠️ DB sync failed."
                except Exception as e:
                    logger.error(f"Error during local restore of {backup_file}: {e}")
                    message = f"❌ Error restoring local file: {e}"
            else:
                message = "❌ No display configuration backup found."
            await interaction.followup.send(content=message, ephemeral=ephemeral)

        view = ConfirmButton(restore_action, interaction.user.id)
        view._interaction_message = await interaction.response.send_message(
            "⚠️ **Restore the display configuration backup?**\n(Overwrites current settings & attempts DB sync)",
            view=view,
            ephemeral=ephemeral
        )

    # --- Toggle Ephemeral ---
    @app_commands.command(
        name="toggle-ephemeral",
        description="Toggle whether command responses are ephemeral"
    )
    @app_commands.default_permissions(administrator=True)
    async def toggle_ephemeral(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        file_path = settings.get_guild_display_path(guild_id)

        # Load current settings
        current_settings = await file_handlers.load_json(file_path, settings.DEFAULT_DISPLAY_SETTINGS.copy())

        # Toggle setting
        current_value = current_settings.get('ephemeral_responses', settings.DEFAULT_DISPLAY_SETTINGS['ephemeral_responses'])
        new_setting = not current_value
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
                ephemeral=True # Default to ephemeral for errors
            )

    # --- Copy Config ---
    @app_commands.command(name="copy-config-from-the-server", description="Copy server configuration from another server")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        source_id="Server ID to copy from",
        include_words="Comma-separated words to include in filenames (substring match, case-insensitive)",
        exclude_words="Comma-separated words to exclude from filenames (substring match, case-insensitive)",
        create_backup="Whether to create backup before copying"
    )
    async def copy_config(
        self,
        interaction: discord.Interaction,
        source_id: str,
        include_words: Optional[str] = None,
        exclude_words: Optional[str] = None, # Made optional
        create_backup: bool = True
    ):
        """Copy config files with enhanced safety and feedback, including DB sync"""
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)
        await interaction.response.defer(ephemeral=ephemeral, thinking=True) # Defer early

        target_guild_id = interaction.guild.id # Use interaction.guild.id

        try:
            # Prevent self-copying (keep existing backup logic)
            if str(source_id) == str(target_guild_id):
                target_dir_for_backup = os.path.join("data", "config", str(target_guild_id))

                if not os.path.exists(target_dir_for_backup):
                    await interaction.followup.send( # Use followup after defer
                        "❌ No configuration found to backup",
                        ephemeral=ephemeral
                    )
                    return

                backup_time = datetime.now().strftime("%Y%m%d-%H%M%S")
                backup_path = f"{target_dir_for_backup}_backup_{backup_time}"
                try:
                    shutil.copytree(target_dir_for_backup, backup_path)
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
                    await interaction.followup.send(embed=embed, ephemeral=ephemeral) # Use followup
                except Exception as e:
                    await interaction.followup.send( # Use followup
                        f"❌ Backup failed: {str(e)}",
                        ephemeral=ephemeral
                    )
                return

            source_dir = os.path.join("data", "config", source_id)
            target_dir = os.path.join("data", "config", str(target_guild_id))

            if not os.path.exists(source_dir):
                await interaction.followup.send( # Use followup
                    f"❌ Source server configuration (`{source_id}`) not found locally.",
                    ephemeral=ephemeral
                )
                return

            include_list = [w.strip().lower() for w in include_words.split(',')] if include_words else []
            # Use default excludes only if exclude_words is not provided or is empty
            default_excludes = ['role_percentages', 'commission_settings', 'display_settings']
            exclude_input_list = [w.strip().lower() for w in exclude_words.split(',')] if exclude_words else default_excludes
            exclude_list = list(set(exclude_input_list + [".bak"])) # Always exclude .bak

            copied_files = []
            skipped_files = []
            errors = []

            # Backup handling (keep existing logic)
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

                # Exclusion checks first
                if any(excl in fname for excl in exclude_list if excl): # Check if excl is not empty
                    return False

                # Inclusion filter (only if include_list is provided)
                if include_list and not any(inc in fname for inc in include_list if inc):
                    return False

                return True

            # File operations (keep existing logic)
            try:
                os.makedirs(target_dir, exist_ok=True) # Ensure target dir exists
                for file in os.listdir(source_dir):
                    src_path = os.path.join(source_dir, file)
                    dest_path = os.path.join(target_dir, file)

                    if os.path.isfile(src_path): # Only copy files, not directories
                        if not should_copy(src_path):
                            skipped_files.append(file)
                            continue
                        try:
                            shutil.copy2(src_path, dest_path)
                            copied_files.append(file) # Store filename only
                        except Exception as e:
                            errors.append(f"{file}: {str(e)}")
                    else:
                         skipped_files.append(f"{file} (Directory)") # Mark directories as skipped

            except Exception as e:
                errors.append(f"File listing/copying failed: {str(e)}")


            # --- Sync copied files to MongoDB ---
            sync_errors = []
            synced_count = 0
            files_to_sync = [
                f for f in copied_files # Iterate over successfully copied filenames
                if f in settings.FILENAME_TO_MONGO_KEY # Check if it's a config file we manage in Mongo
            ]

            logger.info(f"Attempting to sync {len(files_to_sync)} copied config files to MongoDB for guild {target_guild_id}...")

            for config_filename in files_to_sync:
                local_path = os.path.join(target_dir, config_filename) # Path in the *target* dir
                sync_result = await self._sync_local_to_mongo(interaction, local_path)
                if sync_result is True:
                     synced_count += 1
                elif sync_result is False:
                     sync_errors.append(f"{config_filename}: Sync failed")
                # If sync_result is None, it wasn't attempted/applicable, don't count as error


            # Build result embed (keep existing logic)
            embed = discord.Embed(
                title="Config Copy Results",
                color=discord.Color.orange() if errors or sync_errors else discord.Color.green()
            )

            if backup_path:
                embed.add_field(
                    name="Backup Created",
                    value=f"`{os.path.basename(backup_path)}`",
                    inline=False
                )

            # Refine stats reporting
            attempted_sync_count = len(files_to_sync)
            result_stats = [
                f"• Copied Locally: {len(copied_files)} files",
                f"• Skipped: {len(skipped_files)} files/dirs",
                f"• Local Copy Errors: {len(errors)}"
            ]
            if attempted_sync_count > 0:
                 result_stats.extend([
                     f"• Synced to DB: {synced_count}/{attempted_sync_count}", # Report sync status
                     f"• DB Sync Errors: {len(sync_errors)}"
                 ])
            else:
                 result_stats.append("• DB Sync: No eligible files copied for sync")

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
                    name="Copied Files (Local)",
                    value=f"```{sample_copied}```",
                    inline=False
                )
            else:
                embed.add_field(
                    name="⚠️ Notice",
                    value="No files were copied locally based on filters",
                    inline=False
                )

            # Error reporting for local copy and DB sync
            all_errors = errors + sync_errors
            if all_errors:
                sample_errors = "\n".join(f"• {e}" for e in all_errors[:5]) # Show combined errors
                if len(all_errors) > 5:
                    sample_errors += f"\n...and {len(all_errors)-5} more"
                embed.add_field(
                    name="Errors (Local Copy / DB Sync)",
                    value=f"```\n{sample_errors}\n```", # Use code block
                    inline=False
                )

            await interaction.followup.send(embed=embed, ephemeral=ephemeral) # Use followup

        except Exception as e:
            logger.error(f"Config copy critical error: {str(e)}", exc_info=True)
            await interaction.followup.send( # Use followup
                f"❌ Critical error during copy: {str(e)}",
                ephemeral=ephemeral
            )

    # --- Copy Earnings ---
    @app_commands.command(name="copy-earnings-from-the-server", description="Copy earnings data from another server (WARNING: Overwrites current data)")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        source_id="The server ID you want to copy earnings from",
        create_backup="Whether to create backup before copying (recommended)"
    )
    async def copy_earnings(self, interaction: discord.Interaction, source_id: str, create_backup: bool = True):
        """Copy earnings data with backup protection and DB sync"""
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        # Defer immediately for potentially long operations
        await interaction.response.defer(ephemeral=ephemeral, thinking=True)

        # --- Confirmation View Definition ---
        class FinalConfirmationView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=180)
                self.confirmed = False
                self._interaction_message = None # Store message for editing

            async def on_timeout(self):
                if self._interaction_message:
                    try: await self._interaction_message.edit(content="Confirmation timed out.", view=None)
                    except discord.NotFound: pass
                self.stop()

            @discord.ui.button(label="CONFIRM OVERWRITE", style=discord.ButtonStyle.danger)
            async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
                self.confirmed = True
                # Just defer here, the main function will handle edits
                await interaction.response.defer()
                self.stop()

            @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
            async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
                # Edit the message the view is attached to
                if self._interaction_message:
                    await self._interaction_message.edit(content="Operation cancelled.", view=None, embed=None)
                else: # Fallback if message somehow wasn't stored
                    await interaction.response.edit_message(content="Operation cancelled.", view=None, embed=None)
                self.stop()


        try:
            target_guild_id = interaction.guild.id # Use interaction.guild.id

            # Self-backup logic (keep as is, but use followup.send)
            if str(source_id) == str(target_guild_id):
                target_dir_for_backup = os.path.join("data", "earnings", str(target_guild_id))
                target_file_for_backup = os.path.join(target_dir_for_backup, settings.EARNINGS_FILE)

                if not os.path.exists(target_file_for_backup):
                    await interaction.followup.send( # Use followup
                        "❌ No earnings data found to backup",
                        ephemeral=ephemeral
                    )
                    return

                backup_time = datetime.now().strftime("%Y%m%d-%H%M%S")
                backup_dir_name = f"{target_guild_id}_earnings_backup_{backup_time}"
                backup_path = os.path.join("data", "earnings", backup_dir_name)

                try:
                    os.makedirs(backup_path, exist_ok=True)
                    shutil.copy2(target_file_for_backup, os.path.join(backup_path, settings.EARNINGS_FILE))

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
                    await interaction.followup.send(embed=embed, ephemeral=ephemeral) # Use followup
                except Exception as e:
                    await interaction.followup.send( # Use followup
                        f"❌ Backup failed: {str(e)}",
                        ephemeral=ephemeral
                    )
                return

            source_path = os.path.join("data", "earnings", source_id, settings.EARNINGS_FILE)
            target_dir = os.path.join("data", "earnings", str(target_guild_id))
            target_path = os.path.join(target_dir, settings.EARNINGS_FILE)
            backup_path = None

            if not os.path.exists(source_path):
                await interaction.followup.send( # Use followup
                    f"❌ No earnings data found in source server `{source_id}`",
                    ephemeral=ephemeral
                )
                return

            # Backup handling (keep existing logic, use followup.send for errors)
            if create_backup and os.path.exists(target_path):
                backup_time = datetime.now().strftime("%Y%m%d-%H%M%S")
                backup_dir_name = f"{target_guild_id}_earnings_backup_{backup_time}"
                backup_path = os.path.join("data", "earnings", backup_dir_name)
                try:
                    os.makedirs(backup_path, exist_ok=True)
                    shutil.copy2(target_path, os.path.join(backup_path, settings.EARNINGS_FILE))
                except Exception as e:
                    await interaction.followup.send( # Use followup
                        f"⚠️ Backup failed: {str(e)}",
                        ephemeral=ephemeral
                    )
                    # Decide if you want to stop here or continue without backup
                    # For safety, let's stop if backup fails
                    return

            # Load source data for confirmation (keep existing logic)
            entry_count = 0
            try:
                async with aiofiles.open(source_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    if not content.strip(): data = {}
                    else: data = json.loads(content)
                entry_count = sum(len(entries) for entries in data.values() if isinstance(entries, list)) if isinstance(data, dict) else 0
            except Exception as e:
                 await interaction.followup.send(f"❌ Error reading source earnings file: {e}", ephemeral=ephemeral)
                 return


            # Initial warning embed (keep existing logic)
            initial_embed = discord.Embed(
                title="⚠️ Earnings Overwrite Warning",
                description=f"This will replace current data with `{entry_count}` entries from server `{source_id}`.",
                color=discord.Color.orange()
            )
            if backup_path:
                initial_embed.add_field(
                    name="Backup Created",
                    value=f"`{os.path.basename(backup_path)}`",
                    inline=False
                )

            view = FinalConfirmationView()
            # Send the confirmation using followup since we deferred
            confirmation_message = await interaction.followup.send(embed=initial_embed, view=view, ephemeral=ephemeral, wait=True)
            view._interaction_message = confirmation_message # Store message in view
            await view.wait() # Wait for user interaction

            if not view.confirmed:
                 # Message edit is handled by the view's cancel callback
                 return

            # --- Perform copy and DB Sync ---
            db_sync_status = "❌ Not Attempted"
            db_sync_color = discord.Color.red()
            copy_success = False
            try:
                os.makedirs(target_dir, exist_ok=True)
                shutil.copyfile(source_path, target_path)
                logger.info(f"Copied earnings locally from {source_id} to {target_guild_id}")
                copy_success = True

                # Sync copied earnings to MongoDB using the helper
                sync_result = await self._sync_local_to_mongo(interaction, target_path)
                if sync_result is True:
                     db_sync_status = "✅ Synced to DB"
                     db_sync_color = discord.Color.green()
                elif sync_result is False:
                     db_sync_status = "⚠️ DB Sync Failed"
                     db_sync_color = discord.Color.orange()
                else: # None
                     db_sync_status = "⚪ DB Sync Not Attempted/Applicable"
                     db_sync_color = discord.Color.light_grey()


            except Exception as copy_sync_error:
                 logger.error(f"Error during earnings copy/sync: {copy_sync_error}", exc_info=True)
                 db_sync_status = f"❌ Error during copy/sync: {copy_sync_error}"
                 db_sync_color = discord.Color.red()


            # Results embed
            final_embed = discord.Embed(
                title="✅ Earnings Copy Complete" if copy_success else "❌ Earnings Copy Failed",
                description=f"Attempted to copy `{entry_count}` entries from `{source_id}`." if copy_success else f"Failed to copy earnings from `{source_id}`.",
                color=db_sync_color # Color reflects sync status mainly
            )
            if backup_path:
                final_embed.add_field(
                    name="Backup Status",
                    value=f"Backup created: `{os.path.basename(backup_path)}`",
                    inline=False
                )
            final_embed.add_field(
                name="Database Sync Status",
                value=db_sync_status,
                inline=False
            )

            # Edit the original confirmation message with the final result
            await confirmation_message.edit(embed=final_embed, view=None)

        except Exception as e:
            logger.error(f"Earnings copy critical error: {str(e)}", exc_info=True)
            # Try to send a followup if the interaction is still valid
            try:
                await interaction.followup.send(
                    f"❌ Critical error during earnings copy: {str(e)}",
                    ephemeral=ephemeral
                )
            except discord.NotFound:
                 logger.error("Interaction expired before sending critical error message.")
            # Ensure any potentially active view is stopped on critical error
            if 'view' in locals() and isinstance(view, discord.ui.View) and not view.is_finished():
                view.stop()


    # --- View Config ---
    @app_commands.command(name="view-config", description="View complete server configuration")
    @app_commands.default_permissions(administrator=True)
    async def view_config(self, interaction: discord.Interaction) -> None:
        """Display all server configurations with interactive pagination"""
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)
        await interaction.response.defer(ephemeral=ephemeral, thinking=True)
        guild_id = interaction.guild.id

        #region Helper Functions
        def create_embed(title: str) -> discord.Embed:
            """Create a styled embed template"""
            return discord.Embed(
                title=title,
                color=0x00ff00, # Changed color slightly
                timestamp=discord.utils.utcnow()
            ).set_footer(text=f"Requested by {interaction.user.display_name} | Guild ID: {guild_id}")

        def chunk_content(content_lines: List[str], title: str, use_code_block: bool = True) -> list[tuple[str, str]]:
            """Split content lines into embed-safe chunks with optional code block"""
            chunks = []
            current_chunk = []
            current_length = 0
            max_chunk_length = 1000 # Keep well below 1024 limit

            code_block_overhead = 7 if use_code_block else 0 # ```\n \n```

            for line in content_lines:
                line_length = len(line) + 1  # +1 for newline

                if current_length + line_length + code_block_overhead > max_chunk_length:
                    # Finalize current chunk
                    chunk_value = "\n".join(current_chunk)
                    if use_code_block and chunk_value.strip():
                        chunk_value = f"```\n{chunk_value}\n```"
                    chunks.append((title, chunk_value if chunk_value.strip() else "`[No entries]`"))

                    # Start new chunk
                    current_chunk = [line]
                    current_length = line_length
                    title = f"{title.replace(' (cont.)', '')} (cont.)" # Ensure title gets (cont.) correctly
                else:
                    current_chunk.append(line)
                    current_length += line_length

            # Add the last chunk
            if current_chunk:
                chunk_value = "\n".join(current_chunk)
                if use_code_block and chunk_value.strip():
                     chunk_value = f"```\n{chunk_value}\n```"
                chunks.append((title, chunk_value if chunk_value.strip() else "`[No entries]`"))

            # Handle case where there's no content at all
            return chunks if chunks else [(title, "`[No entries]`")]


        async def load_config_section(loader, formatter, section_name: str, use_code_block: bool = True):
            """Load and format a config section with code block option"""
            try:
                raw_data = await loader()
                if not raw_data:
                    # Return a single chunk indicating no entries
                    return chunk_content([], f"{section_name}", use_code_block)
                formatted_lines = formatter(raw_data) # Formatter should return a list of strings
                return chunk_content(formatted_lines, section_name, use_code_block)
            except Exception as e:
                logger.error(f"Config error loading/formatting {section_name}: {str(e)}", exc_info=True)
                return chunk_content([], f"{section_name} Error", use_code_block=False) # Show error without code block

        async def format_compensation(data_type: str, interaction: discord.Interaction) -> list[str]:
            """Format compensation data without code blocks (for mentions)"""
            lines = []
            try:
                comp_data = await file_handlers.load_json(
                    settings.get_guild_commission_path(interaction.guild.id), {}
                )
                section_data = comp_data.get(data_type, {})

                if not isinstance(section_data, dict):
                    logger.warning(f"Compensation section '{data_type}' is not a dictionary for guild {interaction.guild.id}. Data: {section_data}")
                    return ["`[Invalid Data Structure]`"]

                sorted_items = sorted(section_data.items(), key=lambda item: item[0]) # Sort by ID

                for entry_id, entry_settings in sorted_items:
                    if not entry_id.isdigit():
                        lines.append(f"• `Invalid ID Format: {entry_id}`")
                        continue
                    if not isinstance(entry_settings, dict):
                         lines.append(f"• `Invalid Settings Format for ID: {entry_id}`")
                         continue

                    target = None
                    display_text = f"`Unknown ID: {entry_id}`"
                    if data_type == "roles":
                        target = interaction.guild.get_role(int(entry_id))
                        if target: display_text = f"**{target.name}** ({target.mention})"
                    else:  # users
                        target = interaction.guild.get_member(int(entry_id))
                        if target: display_text = f"**{target.display_name}** ({target.mention})"


                    commission_raw = entry_settings.get('commission_percentage')
                    hourly_raw = entry_settings.get('hourly_rate')
                    override_role = entry_settings.get('override_role', False) if data_type == "users" else None

                    commission = f"{commission_raw}%" if commission_raw is not None else "N/A"
                    hourly = f"${hourly_raw}/h" if hourly_raw is not None else "N/A"

                    details = f"  • Commission: {commission}\n  • Hourly Rate: {hourly}"
                    if override_role is not None:
                        details += f"\n  • Override Role: {'Yes' if override_role else 'No'}"

                    lines.append(f"◈ {display_text}\n```{details}```")

                return lines if lines else ["`[No entries]`"]

            except Exception as e:
                logger.error(f"Error formatting compensation '{data_type}' for guild {interaction.guild.id}: {str(e)}", exc_info=True)
                return ["`[Error Loading Data]`"]
        #endregion

        #region Configuration Loaders
        config_sections = [] # List to hold (title, content_lines) tuples

        # Legacy Role Cuts
        config_sections.extend(await load_config_section(
            lambda: file_handlers.load_json(settings.get_guild_roles_path(guild_id), {}),
            lambda d: [f"• {(interaction.guild.get_role(int(k)) or f'ID:{k}').name}: {v}%" for k, v in d.items()],
            "Legacy Role Cuts",
            use_code_block=True
        ))

        # Shifts
        config_sections.extend(await load_config_section(
            lambda: file_handlers.load_json(settings.get_guild_shifts_path(guild_id), []),
            lambda d: [f"• {s}" for s in d],
            "Shifts",
            use_code_block=True
        ))

        # Periods
        config_sections.extend(await load_config_section(
            lambda: file_handlers.load_json(settings.get_guild_periods_path(guild_id), []),
            lambda d: [f"• {p}" for p in d],
            "Periods",
            use_code_block=True
        ))

        # Bonus Rules
        config_sections.extend(await load_config_section(
            lambda: file_handlers.load_json(settings.get_guild_bonus_rules_path(guild_id), []),
            lambda d: [f"• ${float(r.get('from',0)):.2f} - ${float(r.get('to',0)):.2f}: Bonus ${float(r.get('amount',0)):.2f}"
                       for r in sorted(d, key=lambda x: float(x.get('from', 0)))],
            "Bonus Rules",
            use_code_block=True
        ))

        # Models
        config_sections.extend(await load_config_section(
            lambda: file_handlers.load_json(settings.get_guild_models_path(guild_id), []),
            lambda d: [f"• {m}" for m in d],
            "Models",
            use_code_block=True
        ))

        # Display Settings
        config_sections.extend(await load_config_section(
            lambda: file_handlers.load_json(settings.get_guild_display_path(guild_id), settings.DEFAULT_DISPLAY_SETTINGS.copy()),
            lambda d: [
                f"• Ephemeral Responses: {d.get('ephemeral_responses', settings.DEFAULT_DISPLAY_SETTINGS['ephemeral_responses'])}",
                f"• Show Averages: {d.get('show_average', settings.DEFAULT_DISPLAY_SETTINGS['show_average'])}",
                f"• Agency Name: {d.get('agency_name', settings.DEFAULT_DISPLAY_SETTINGS['agency_name'])}",
                f"• Show IDs: {d.get('show_ids', settings.DEFAULT_DISPLAY_SETTINGS['show_ids'])}",
                f"• Bot Name: {d.get('bot_name', settings.DEFAULT_DISPLAY_SETTINGS['bot_name'])}"
            ],
            "Display Settings",
            use_code_block=True # Use code block for alignment
        ))

        # Compensation Data (Role)
        config_sections.extend(await load_config_section(
            lambda: format_compensation("roles", interaction),
            lambda lines: lines, # Already formatted as list of strings
            "Role Compensation Settings",
            use_code_block=False  # Mentions need to render
        ))
        # Compensation Data (User)
        config_sections.extend(await load_config_section(
            lambda: format_compensation("users", interaction),
            lambda lines: lines, # Already formatted as list of strings
            "User Compensation Settings",
            use_code_block=False  # Mentions need to render
        ))
        #endregion

        #region Pagination System
        class ConfigView(discord.ui.View):
            def __init__(self, embeds: list[discord.Embed], original_interaction: discord.Interaction, ephemeral: bool):
                super().__init__(timeout=300) # Increased timeout
                self.embeds = embeds
                self.original_interaction = original_interaction
                self.ephemeral = ephemeral
                self.page = 0
                self._message = None # To store the message for editing

                # Initial button state
                self._update_buttons()

            async def send_initial_message(self):
                # Send the first page using followup
                self._message = await self.original_interaction.followup.send(
                    embed=self.embeds[0],
                    view=self,
                    ephemeral=self.ephemeral
                )

            def _update_buttons(self):
                # Disable/enable buttons based on current page
                for item in self.children:
                    if isinstance(item, discord.ui.Button):
                        if item.custom_id == "prev_page":
                            item.disabled = self.page == 0
                        elif item.custom_id == "next_page":
                            item.disabled = self.page >= len(self.embeds) - 1
                        elif item.custom_id == "page_indicator":
                             item.label = f"Page {self.page + 1}/{len(self.embeds)}"

            @discord.ui.button(label="◀", style=discord.ButtonStyle.blurple, custom_id="prev_page")
            async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user.id != self.original_interaction.user.id:
                     await interaction.response.send_message("You cannot interact with this.", ephemeral=True)
                     return
                self.page -= 1
                self._update_buttons()
                await interaction.response.edit_message(embed=self.embeds[self.page], view=self)

            # Add a non-interactive page indicator
            @discord.ui.button(label="Page 1/X", style=discord.ButtonStyle.secondary, disabled=True, custom_id="page_indicator")
            async def page_indicator_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                pass # Does nothing

            @discord.ui.button(label="▶", style=discord.ButtonStyle.blurple, custom_id="next_page")
            async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user.id != self.original_interaction.user.id:
                     await interaction.response.send_message("You cannot interact with this.", ephemeral=True)
                     return
                self.page += 1
                self._update_buttons()
                await interaction.response.edit_message(embed=self.embeds[self.page], view=self)

            @discord.ui.button(label="✖ Close", style=discord.ButtonStyle.red, custom_id="close_config")
            async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                 if interaction.user.id != self.original_interaction.user.id:
                      await interaction.response.send_message("You cannot interact with this.", ephemeral=True)
                      return
                 # Attempt to delete the original response message
                 try:
                      await self.original_interaction.delete_original_response()
                 except discord.NotFound:
                      # If original is gone, try editing the view message (if stored)
                      if self._message:
                           try: await self._message.edit(content="View closed.", embed=None, view=None)
                           except discord.NotFound: pass
                 except discord.HTTPException as e:
                      logger.warning(f"Failed to delete config view message: {e}")
                      # Fallback edit if delete fails
                      if self._message:
                          try: await self._message.edit(content="View closed.", embed=None, view=None)
                          except discord.NotFound: pass
                 self.stop()

            async def on_timeout(self):
                 if self._message:
                      try:
                           # Remove buttons on timeout
                           await self._message.edit(view=None)
                      except discord.NotFound:
                           pass # Message already deleted
                 self.stop()

        # Build embeds from chunks
        embeds = []
        current_embed = None
        field_count_in_current_embed = 0
        max_fields_per_embed = 5 # Reduced limit for safety

        for title, content in config_sections:
            # Ensure content is not empty before adding field
            if not content or content.strip() == '```\n```' or content.strip() == '`[No entries]`':
                 content = "`[No entries]`" # Standardize empty display

            # Start a new embed if needed
            if current_embed is None or field_count_in_current_embed >= max_fields_per_embed or len(current_embed) + len(title) + len(content) > 5900: # Check total length too
                if current_embed: embeds.append(current_embed) # Add previous embed
                current_embed = create_embed("Server Configuration" if not embeds else "Configuration Continued")
                field_count_in_current_embed = 0

            current_embed.add_field(name=title, value=content, inline=False)
            field_count_in_current_embed += 1

        # Add the last embed if it exists
        if current_embed:
            embeds.append(current_embed)
        #endregion

        # Send response
        try:
            if not embeds:
                await interaction.followup.send("No configuration found or error loading configuration.", ephemeral=ephemeral)
                return

            view = ConfigView(embeds, interaction, ephemeral)
            await view.send_initial_message() # Send the first page via followup

        except Exception as e:
            logger.error(f"Config display failed: {str(e)}", exc_info=True)
            # Try to send an error message via followup
            try:
                await interaction.followup.send(
                    "❌ Failed to display configuration - an error occurred.",
                    ephemeral=ephemeral
                )
            except discord.NotFound:
                 logger.error("Interaction expired before sending config display error.")


    # --- Manage Backups ---
    @app_commands.command(name="manage-backups", description="Manage configuration or earnings backups")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        backup_type="Type of backups to manage",
        action="Action to perform",
        backup_ids="Comma-separated backup IDs (YYYYMMDD-HHMMSS format) to remove (for 'remove' action)"
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
        backup_ids: Optional[str] = None # Made optional
    ):
        """Manage server backups with type selection"""
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)
        await interaction.response.defer(ephemeral=ephemeral, thinking=True)
        guild_id = str(interaction.guild.id)

        try:
            # Determine paths based on backup type
            if backup_type == "config":
                base_dir = os.path.join("data", "config")
                pattern = f"{guild_id}_backup_*" # Directory pattern
                backup_name = "Configuration"
                prefix_pattern = f"{guild_id}_backup_"
            else: # earnings
                base_dir = os.path.join("data", "earnings")
                pattern = f"{guild_id}_earnings_backup_*" # Directory pattern
                backup_name = "Earnings"
                prefix_pattern = f"{guild_id}_earnings_backup_"

            if action == "list":
                backup_dirs = [d for d in glob.glob(os.path.join(base_dir, pattern)) if os.path.isdir(d)]
                backups = []

                for dir_path in backup_dirs:
                    dir_name = os.path.basename(dir_path)
                    # Extract timestamp ID (YYYYMMDD-HHMMSS)
                    try:
                        backup_id = dir_name.split("_backup_")[-1]
                        if not re.fullmatch(r"\d{8}-\d{6}", backup_id): continue # Skip invalid formats

                        dt = datetime.strptime(backup_id, "%Y%m%d-%H%M%S")
                        formatted_date = dt.strftime("%Y-%m-%d %H:%M:%S UTC") # More explicit format

                        # Get size (optional, can be slow for many/large backups)
                        # total_size = sum(os.path.getsize(os.path.join(dirpath, filename)) for dirpath, dirnames, filenames in os.walk(dir_path) for filename in filenames)
                        # size_mb = total_size / (1024 * 1024)

                        backups.append((backup_id, dir_name, formatted_date))#, size_mb))
                    except (ValueError, IndexError):
                         logger.warning(f"Could not parse backup ID/date from directory name: {dir_name}")
                         continue # Skip directories with unexpected names

                # Sort by date descending (most recent first)
                backups.sort(key=lambda x: x[0], reverse=True)

                embed = discord.Embed(
                    title=f"{backup_name} Backups List",
                    color=discord.Color.blue()
                )

                if not backups:
                    embed.description = "No backups found matching the criteria."
                else:
                    description_lines = []
                    for bid, dir_name, date in backups[:20]: # Limit display
                         description_lines.append(f"• **ID:** `{bid}`\n  *Created:* {date}") # Size: {size:.2f} MB
                    if len(backups) > 20:
                        description_lines.append(f"\n...and {len(backups)-20} more.")

                    embed.description = "\n\n".join(description_lines)
                    embed.set_footer(text=f"Total {backup_name.lower()} backups found: {len(backups)}")

                await interaction.followup.send(embed=embed, ephemeral=ephemeral)

            elif action == "remove":
                if not backup_ids:
                    await interaction.followup.send(
                        "❌ Please provide backup IDs (YYYYMMDD-HHMMSS format, comma-separated) to remove.",
                        ephemeral=ephemeral
                    )
                    return

                backup_id_list = [bid.strip() for bid in backup_ids.split(',')]
                removed_count = 0
                errors = []
                not_found = []

                for backup_id in backup_id_list:
                    # Validate ID format strictly
                    if not re.fullmatch(r"\d{8}-\d{6}", backup_id):
                        errors.append(f"Invalid ID format: `{backup_id}`")
                        continue

                    # Construct the expected directory name
                    dir_name = f"{prefix_pattern}{backup_id}"
                    backup_path = os.path.join(base_dir, dir_name)

                    if not os.path.isdir(backup_path): # Check if it's a directory
                        not_found.append(f"`{backup_id}`")
                        continue

                    try:
                        shutil.rmtree(backup_path)
                        removed_count += 1
                        logger.info(f"Removed backup directory: {backup_path}")
                    except Exception as e:
                        errors.append(f"Failed to remove `{backup_id}`: {str(e)}")
                        logger.error(f"Error removing backup {backup_path}: {e}", exc_info=True)

                # Build results embed
                embed = discord.Embed(
                    title=f"{backup_name} Backup Removal Report",
                    color=discord.Color.green() if not errors and not not_found else discord.Color.orange()
                )

                summary = f"• Successfully Removed: {removed_count}\n"
                if not_found:
                     summary += f"• Not Found: {len(not_found)} ({', '.join(not_found[:5])}{'...' if len(not_found) > 5 else ''})\n"
                if errors:
                     summary += f"• Errors: {len(errors)} ❌"

                embed.description = summary

                if errors:
                    error_details = "\n".join(f"• {e}" for e in errors[:10]) # Limit details shown
                    if len(errors) > 10: error_details += "\n..."
                    embed.add_field(name="Error Details", value=error_details, inline=False)

                await interaction.followup.send(embed=embed, ephemeral=ephemeral)

        except Exception as e:
            logger.error(f"Backup management error: {str(e)}", exc_info=True)
            await interaction.followup.send(
                f"❌ Critical error during backup management: {str(e)}",
                ephemeral=ephemeral
            )

# --- Confirm Button Class ---
class ConfirmButton(discord.ui.View):
    def __init__(self, action_callback, user_id: int):
        super().__init__(timeout=180) # Add timeout
        self.action_callback = action_callback
        self.user_id = user_id
        self._interaction_message = None # To store the message for editing

    async def on_timeout(self):
        if self._interaction_message:
            try:
                # Edit the message to indicate timeout, remove buttons
                await self._interaction_message.edit(content="Confirmation timed out.", view=None)
            except discord.NotFound:
                pass # Message might have been deleted
            except Exception as e:
                 logger.warning(f"Failed to edit message on timeout: {e}")
        self.stop()

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.red)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ You cannot use this button.", ephemeral=True)
            return

        # Let the callback handle response/deferral/followup
        try:
             await self.action_callback(interaction)
        except Exception as e:
             logger.error(f"Error in ConfirmButton action callback: {e}", exc_info=True)
             # Try to notify user of error if interaction is still valid
             try:
                  # Check if response already sent by callback
                  if not interaction.response.is_done():
                       await interaction.response.send_message("❌ An error occurred executing the confirmed action.", ephemeral=True)
                  else:
                       await interaction.followup.send("❌ An error occurred executing the confirmed action.", ephemeral=True)
             except Exception: # Ignore errors sending error message
                  pass
        finally:
             self.stop() # Stop the view after action attempt

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary) # Changed style
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ You cannot use this button.", ephemeral=True)
            return

        # Edit the original message the view is attached to
        await interaction.response.edit_message(content="❌ Operation Canceled.", view=None)
        self.stop() # Stop the view

# --- Cog Setup ---
async def setup(bot):
    await bot.add_cog(AdminSlashCommands(bot))