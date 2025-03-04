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

     @app_commands.command(
        name="toggle-average",
        description="Toggle whether to show performance averages in calculation embeds"
    )
    @app_commands.default_permissions(administrator=True)
    async def toggle_average(self, interaction: discord.Interaction):
        """Toggle the display of performance averages in calculation embeds"""
        # Only admins can use this command
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need administrator permissions to use this command.", ephemeral=True)
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
            await interaction.response.send_message(f"✅ Performance average display is now **{status}**.", ephemeral=True)
        else:
            logger.error(f"Failed to save display settings for guild {guild_id}")
            await interaction.response.send_message("❌ Failed to update settings. Please try again.", ephemeral=True)

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(
        name="export-earnings-csv",
        description="[Admin] Export all earnings data as CSV"
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
        description="[Admin] Export all earnings data as JSON"
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
    @app_commands.command(name="set-role", description="[Admin] Set a role's percentage cut")
    @app_commands.describe(role="The role to configure", percentage="The percentage cut (e.g., 6.5)")
    async def set_role(self, interaction: discord.Interaction, role: discord.Role, percentage: str):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ This command is restricted to administrators.", ephemeral=True)
            return
        
        logger.info(f"User {interaction.user.name} ({interaction.user.id}) used set-role command for role {role.name} with percentage {percentage}")
        
        percentage_decimal = validators.validate_percentage(percentage)
        if percentage_decimal is None:
            logger.warning(f"Invalid percentage '{percentage}' provided by {interaction.user.name}")
            await interaction.response.send_message("❌ Percentage must be a valid number between 0 and 100.")
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
            await interaction.response.send_message(f"✅ {role.name} now has {percentage_decimal}% cut!")
        else:
            logger.error(f"Failed to save role data for {role.name} ({role_id}) by {interaction.user.name}")
            await interaction.response.send_message("❌ Failed to save role data. Please try again later.")

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="remove-role", description="[Admin] Remove a role's percentage configuration")
    @app_commands.describe(role="The role to remove")
    async def remove_role(self, interaction: discord.Interaction, role: discord.Role):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ This command is restricted to administrators.", ephemeral=True)
            return
        
        logger.info(f"User {interaction.user.name} ({interaction.user.id}) used remove-role command for role {role.name}")
        
        guild_id = str(interaction.guild.id)
        role_id = str(role.id)
        
        role_data = await file_handlers.load_json(settings.ROLE_DATA_FILE, settings.DEFAULT_ROLE_DATA)
        
        if guild_id not in role_data or role_id not in role_data[guild_id]:
            logger.warning(f"Role {role.name} ({role_id}) not found in configuration")
            await interaction.response.send_message(f"❌ {role.name} does not have a configured percentage.")
            return
        
        del role_data[guild_id][role_id]
        success = await file_handlers.save_json(settings.ROLE_DATA_FILE, role_data)
        
        if success:
            logger.info(f"Role {role.name} ({role_id}) removed from configuration")
            await interaction.response.send_message(f"✅ {role.name} has been removed from percentage configuration!")
        else:
            logger.error(f"Failed to remove role {role.name} ({role_id})")
            await interaction.response.send_message("❌ Failed to save role data. Please try again later.")

    # Shift Management
    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="set-shift", description="[Admin] Add a valid shift name")
    @app_commands.describe(shift="The name of the shift to add")
    async def set_shift(self, interaction: discord.Interaction, shift: str):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ This command is restricted to administrators.", ephemeral=True)
            return
        
        logger.info(f"User {interaction.user.name} used set-shift command for shift '{shift}'")
        
        if not shift.strip():
            await interaction.response.send_message("❌ Shift name cannot be empty.")
            return
            
        guild_id = str(interaction.guild.id)
        shift_data = await file_handlers.load_json(settings.SHIFT_DATA_FILE, settings.DEFAULT_SHIFT_DATA)
        existing_shifts = shift_data.get(guild_id, [])
        
        if validators.validate_shift(shift, existing_shifts) is not None:
            await interaction.response.send_message(f"❌ Shift '{shift}' already exists!")
            return
        
        shift_data.setdefault(guild_id, []).append(shift)
        success = await file_handlers.save_json(settings.SHIFT_DATA_FILE, shift_data)
        
        if success:
            await interaction.response.send_message(f"✅ Shift '{shift}' added!")
        else:
            await interaction.response.send_message("❌ Failed to save shift data. Please try again later.")

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="remove-shift", description="[Admin] Remove a shift configuration")
    @app_commands.describe(shift="The name of the shift to remove")
    async def remove_shift(self, interaction: discord.Interaction, shift: str):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ This command is restricted to administrators.", ephemeral=True)
            return
        
        guild_id = str(interaction.guild.id)
        shift_data = await file_handlers.load_json(settings.SHIFT_DATA_FILE, settings.DEFAULT_SHIFT_DATA)
        existing_shifts = shift_data.get(guild_id, [])
        
        normalized_shift = validators.validate_shift(shift, existing_shifts)
        if normalized_shift is None:
            await interaction.response.send_message(f"❌ Shift '{shift}' doesn't exist!")
            return
        
        shift_data[guild_id].remove(normalized_shift)
        success = await file_handlers.save_json(settings.SHIFT_DATA_FILE, shift_data)
        
        if success:
            await interaction.response.send_message(f"✅ Shift '{normalized_shift}' removed!")
        else:
            await interaction.response.send_message("❌ Failed to save shift data. Please try again later.")

    # Period Management
    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="set-period", description="[Admin] Add a valid period name")
    @app_commands.describe(period="The name of the period to add")
    async def set_period(self, interaction: discord.Interaction, period: str):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ This command is restricted to administrators.", ephemeral=True)
            return
        
        if not period.strip():
            await interaction.response.send_message("❌ Period name cannot be empty.")
            return
            
        guild_id = str(interaction.guild.id)
        period_data = await file_handlers.load_json(settings.PERIOD_DATA_FILE, settings.DEFAULT_PERIOD_DATA)
        existing_periods = period_data.get(guild_id, [])
        
        if validators.validate_period(period, existing_periods) is not None:
            await interaction.response.send_message(f"❌ Period '{period}' already exists!")
            return
        
        period_data.setdefault(guild_id, []).append(period)
        success = await file_handlers.save_json(settings.PERIOD_DATA_FILE, period_data)
        
        if success:
            await interaction.response.send_message(f"✅ Period '{period}' added!")
        else:
            await interaction.response.send_message("❌ Failed to save period data. Please try again later.")

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="remove-period", description="[Admin] Remove a period configuration")
    @app_commands.describe(period="The name of the period to remove")
    async def remove_period(self, interaction: discord.Interaction, period: str):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ This command is restricted to administrators.", ephemeral=True)
            return
        
        guild_id = str(interaction.guild.id)
        period_data = await file_handlers.load_json(settings.PERIOD_DATA_FILE, settings.DEFAULT_PERIOD_DATA)
        existing_periods = period_data.get(guild_id, [])
        
        normalized_period = validators.validate_period(period, existing_periods)
        if normalized_period is None:
            await interaction.response.send_message(f"❌ Period '{period}' doesn't exist!")
            return
        
        period_data[guild_id].remove(normalized_period)
        success = await file_handlers.save_json(settings.PERIOD_DATA_FILE, period_data)
        
        if success:
            await interaction.response.send_message(f"✅ Period '{normalized_period}' removed!")
        else:
            await interaction.response.send_message("❌ Failed to save period data. Please try again later.")

    # Bonus Rules Management
    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="set-bonus-rule", description="[Admin] Set a bonus rule for a revenue range")
    @app_commands.describe(
        from_range="Lower bound of revenue (e.g., 1000)",
        to_range="Upper bound of revenue (e.g., 2000)",
        bonus="Bonus amount (e.g., 50)"
    )
    async def set_bonus_rule(self, interaction: discord.Interaction, from_range: str, to_range: str, bonus: str):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ This command is restricted to administrators.", ephemeral=True)
            return
        
        from_num = validators.parse_money(from_range)
        to_num = validators.parse_money(to_range)
        bonus_amount = validators.parse_money(bonus)
        
        if None in (from_num, to_num, bonus_amount):
            await interaction.response.send_message("❌ Invalid number format.")
            return
            
        if from_num > to_num:
            await interaction.response.send_message("❌ The 'from' value must be less than or equal to the 'to' value.")
            return
            
        guild_id = str(interaction.guild.id)
        bonus_rules = await file_handlers.load_json(settings.BONUS_RULES_FILE, settings.DEFAULT_BONUS_RULES)
        
        new_rule = {"from": float(from_num), "to": float(to_num), "amount": float(bonus_amount)}
        current_rules = bonus_rules.setdefault(guild_id, [])
        
        if any((from_num <= rule["to"] and to_num >= rule["from"]) for rule in current_rules):
            await interaction.response.send_message("❌ This rule overlaps with an existing bonus rule.")
            return
            
        current_rules.append(new_rule)
        success = await file_handlers.save_json(settings.BONUS_RULES_FILE, bonus_rules)
        
        if success:
            await interaction.response.send_message(f"✅ Bonus rule added: ${float(from_num):,.2f}-${float(to_num):,.2f} → ${float(bonus_amount):,.2f}!")
        else:
            await interaction.response.send_message("❌ Failed to save bonus rule.")

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="remove-bonus-rule", description="[Admin] Remove a bonus rule for a revenue range")
    @app_commands.describe(
        from_range="Lower bound of revenue",
        to_range="Upper bound of revenue"
    )
    async def remove_bonus_rule(self, interaction: discord.Interaction, from_range: str, to_range: str):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ This command is restricted to administrators.", ephemeral=True)
            return
        
        from_num = validators.parse_money(from_range)
        to_num = validators.parse_money(to_range)
        
        if None in (from_num, to_num):
            await interaction.response.send_message("❌ Invalid number format.")
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
            await interaction.response.send_message(f"❌ No bonus rule found for ${from_num}-${to_num}.")
            return
            
        bonus_rules[guild_id].remove(rule_to_remove)
        success = await file_handlers.save_json(settings.BONUS_RULES_FILE, bonus_rules)
        
        if success:
            await interaction.response.send_message(f"✅ Bonus rule removed: ${float(from_num):,.2f}-${float(to_num):,.2f}")
        else:
            await interaction.response.send_message("❌ Failed to remove bonus rule.")

    # List Commands
    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="list-roles", description="[Admin] List configured roles and percentages")
    async def list_roles(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        role_data = await file_handlers.load_json(settings.ROLE_DATA_FILE, settings.DEFAULT_ROLE_DATA)
        guild_roles = role_data.get(guild_id, {})
        
        if not guild_roles:
            await interaction.response.send_message("❌ No roles configured.")
            return
            
        embed = discord.Embed(title="Configured Roles", color=discord.Color.blue())
        for role_id, percentage in guild_roles.items():
            role = interaction.guild.get_role(int(role_id))
            role_name = role.name if role else f"Unknown Role ({role_id})"
            embed.add_field(name=role_name, value=f"{percentage}%", inline=True)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="list-shifts", description="[Admin] List configured shifts")
    async def list_shifts(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        shift_data = await file_handlers.load_json(settings.SHIFT_DATA_FILE, settings.DEFAULT_SHIFT_DATA)
        guild_shifts = shift_data.get(guild_id, [])
        
        if not guild_shifts:
            await interaction.response.send_message("❌ No shifts configured.")
            return
            
        embed = discord.Embed(title="Configured Shifts", color=discord.Color.blue())
        embed.add_field(name="Shifts", value="\n".join(f"• {shift}" for shift in guild_shifts))
        await interaction.response.send_message(embed=embed)

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="list-periods", description="[Admin] List configured periods")
    async def list_periods(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        period_data = await file_handlers.load_json(settings.PERIOD_DATA_FILE, settings.DEFAULT_PERIOD_DATA)
        guild_periods = period_data.get(guild_id, [])
        
        if not guild_periods:
            await interaction.response.send_message("❌ No periods configured.")
            return
            
        embed = discord.Embed(title="Configured Periods", color=discord.Color.blue())
        embed.add_field(name="Periods", value="\n".join(f"• {period}" for period in guild_periods))
        await interaction.response.send_message(embed=embed)

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="list-bonus-rules", description="[Admin] List configured bonus rules")
    async def list_bonus_rules(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        bonus_rules = await file_handlers.load_json(settings.BONUS_RULES_FILE, settings.DEFAULT_BONUS_RULES)
        guild_rules = bonus_rules.get(guild_id, [])
        
        if not guild_rules:
            await interaction.response.send_message("❌ No bonus rules configured.")
            return
            
        embed = discord.Embed(title="Bonus Rules", color=discord.Color.green())
        
        for rule in sorted(guild_rules, key=lambda x: x["from"]):
            embed.add_field(
                name=f"${rule['from']} - ${rule['to']}",
                value=f"Bonus: ${rule['amount']}",
                inline=False
            )

        await interaction.response.send_message(embed=embed)

    # Model Management
    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="set-model", description="[Admin] Add a valid model name")
    @app_commands.describe(model="The name of the model to add")
    async def set_model(self, interaction: discord.Interaction, model: str):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ This command is restricted to administrators.", ephemeral=True)
            return
        
        logger.info(f"User {interaction.user.name} used set-model command for model '{model}'")
        
        if not model.strip():
            await interaction.response.send_message("❌ Model name cannot be empty.")
            return
            
        guild_id = str(interaction.guild.id)
        model_data = await file_handlers.load_json(settings.MODELS_DATA_FILE, settings.DEFAULT_MODELS_DATA)
        existing_models = model_data.get(guild_id, [])
        
        if model.lower() in [m.lower() for m in existing_models]:
            await interaction.response.send_message(f"❌ Model '{model}' already exists!")
            return
        
        model_data.setdefault(guild_id, []).append(model)
        success = await file_handlers.save_json(settings.MODELS_DATA_FILE, model_data)
        
        if success:
            await interaction.response.send_message(f"✅ Model '{model}' added!")
        else:
            await interaction.response.send_message("❌ Failed to save model data. Please try again later.")

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="remove-model", description="[Admin] Remove a model configuration")
    @app_commands.describe(model="The name of the model to remove")
    async def remove_model(self, interaction: discord.Interaction, model: str):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ This command is restricted to administrators.", ephemeral=True)
            return
        
        guild_id = str(interaction.guild.id)
        model_data = await file_handlers.load_json(settings.MODELS_DATA_FILE, settings.DEFAULT_MODELS_DATA)
        existing_models = model_data.get(guild_id, [])
        
        normalized_model = next((m for m in existing_models if m.lower() == model.lower()), None)
        if normalized_model is None:
            await interaction.response.send_message(f"❌ Model '{model}' doesn't exist!")
            return
        
        model_data[guild_id].remove(normalized_model)
        success = await file_handlers.save_json(settings.MODELS_DATA_FILE, model_data)
        
        if success:
            await interaction.response.send_message(f"✅ Model '{normalized_model}' removed!")
        else:
            await interaction.response.send_message("❌ Failed to save model data. Please try again later.")

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="list-models", description="[Admin] List configured models")
    async def list_models(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        model_data = await file_handlers.load_json(settings.MODELS_DATA_FILE, settings.DEFAULT_MODELS_DATA)
        guild_models = model_data.get(guild_id, [])
        
        if not guild_models:
            await interaction.response.send_message("❌ No models configured.")
            return
            
        embed = discord.Embed(title="Configured Models", color=discord.Color.blue())
        embed.add_field(name="Models", value="\n".join(f"• {model}" for model in guild_models))
        await interaction.response.send_message(embed=embed)

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="clear-earnings", description="[Admin] Clear all earnings data")
    async def clear_earnings(self, interaction: discord.Interaction):
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Confirm", style=discord.ButtonStyle.danger, custom_id="confirm_clear_earnings"))

        async def button_callback(interaction):
            guild_id = str(interaction.guild.id)
            earnings_data = await file_handlers.load_json(settings.EARNINGS_FILE, settings.DEFAULT_EARNINGS)
            earnings_data[guild_id] = {}
            await file_handlers.save_json(settings.EARNINGS_FILE, earnings_data)
            await interaction.response.send_message(f"✅ All earnings data for the guild with ID ({guild_id}) has been successfully cleared.", ephemeral=True)

        view.children[0].callback = button_callback
        await interaction.response.send_message("⚠️ Are you sure you want to clear all earnings data?", view=view, ephemeral=True)

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="reset-config", description="[Admin] Reset all configuration files")
    async def reset_config(self, interaction: discord.Interaction):
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Confirm", style=discord.ButtonStyle.danger, custom_id="confirm_reset_config"))

        async def button_callback(interaction):
            await file_handlers.save_json(settings.SHIFT_DATA_FILE, settings.DEFAULT_SHIFT_DATA)
            await file_handlers.save_json(settings.PERIOD_DATA_FILE, settings.DEFAULT_PERIOD_DATA)
            await file_handlers.save_json(settings.ROLE_DATA_FILE, settings.DEFAULT_ROLE_DATA)
            await file_handlers.save_json(settings.BONUS_RULES_FILE, settings.DEFAULT_BONUS_RULES)
            await file_handlers.save_json(settings.EARNINGS_FILE, settings.DEFAULT_EARNINGS)
            await interaction.response.send_message("✅ Configuration files reset.", ephemeral=True)

        view.children[0].callback = button_callback
        await interaction.response.send_message("⚠️ Are you sure you want to reset all configuration files? This will delete all existing data.", view=view, ephemeral=True)

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="restore-latest-backup", description="[Admin] Restore the latest backup")
    async def restore_latest_backup(self, interaction: discord.Interaction):
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Confirm", style=discord.ButtonStyle.danger, custom_id="confirm_restore_backup"))
        
        async def button_callback(interaction):
            await interaction.response.defer(ephemeral=True)
            
            # Path to data directory (parallel to cogs directory)
            cogs_dir = os.path.dirname(os.path.abspath(__file__))  # Current file's directory (cogs folder)
            parent_dir = os.path.dirname(cogs_dir)  # Parent directory of cogs
            data_dir = os.path.join(parent_dir, "data")  # data folder is parallel to cogs
            
            # Find all .bak files
            backup_files = glob.glob(os.path.join(data_dir, "*.bak"))
            
            if not backup_files:
                await interaction.followup.send("❌ No backup files found!", ephemeral=True)
                return
            
            restored_count = 0
            failed_count = 0
            
            for bak_file in backup_files:
                try:
                    # Get the original filename by removing .bak extension
                    original_file = bak_file[:-4]  # Remove ".bak"
                    
                    # Copy the backup file to the original location
                    shutil.copy2(bak_file, original_file)
                    restored_count += 1
                except Exception as e:
                    print(f"Failed to restore {bak_file}: {str(e)}")
                    failed_count += 1
            
            if failed_count == 0:
                await interaction.followup.send(f"✅ Successfully restored {restored_count} backup files.", ephemeral=True)
            else:
                await interaction.followup.send(f"⚠️ Restored {restored_count} files, but {failed_count} failed. Check console for details.", ephemeral=True)
        
        view.children[0].callback = button_callback
        await interaction.response.send_message("⚠️ Are you sure you want to restore the latest backup? This will overwrite current data.", view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(AdminSlashCommands(bot))