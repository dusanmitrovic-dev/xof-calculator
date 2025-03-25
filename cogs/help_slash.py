import logging
import discord
from discord.ext import commands
from discord import app_commands
from config import settings
from utils import file_handlers

logger = logging.getLogger("xof_calculator.help_slash")

class HelpSlashCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_ephemeral_setting(self, guild_id):
        file_path = settings.get_guild_file(guild_id, settings.DISPLAY_SETTINGS_FILE)
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

    @app_commands.command(name="help", description="Show available commands based on your permissions")
    async def help(self, interaction: discord.Interaction):
        """Show available commands based on user permissions"""
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)

        is_admin = interaction.user.guild_permissions.administrator

        # Create an embed to display the commands
        embed = discord.Embed(title="Available Commands", description=f"Version: {settings.VERSION}", color=discord.Color.blue())

        # General commands (available to everyone)
        general_commands = "\n".join([
            "`/calculate workflow` - Calculate earnings using an interactive wizard"
        ])
        embed.add_field(name="General Commands", value=general_commands, inline=False)

        if is_admin:
            # Configuration Commands
            config_commands = "\n".join([
                "`/set-role` - Set a role's percentage cut",
                "`/remove-role` - Remove a role's percentage configuration",
                "`/set-shift` - Add a valid shift name",
                "`/remove-shift` - Remove a shift configuration",
                "`/set-period` - Add a valid period name",
                "`/remove-period` - Remove a period configuration",
                "`/set-bonus-rule` - Set a bonus rule for a revenue range",
                "`/remove-bonus-rule` - Remove a bonus rule for a revenue range",
                "`/set-model` - Add a valid model name",
                "`/remove-model` - Remove a model configuration",
                "`/set-role-commission` - Set a role's commission percentage",
                "`/set-role-hourly` - Set a role's hourly rate",
                "`/set-user-commission` - Set a user's commission percentage",
                "`/set-user-hourly` - Set a user's hourly rate",
                "`/toggle-user-role-override` - Toggle role override for a specific user"
            ])
            embed.add_field(name="Configuration Commands", value=config_commands, inline=False)

            # List Commands
            list_commands = "\n".join([
                "`/list-roles` - List configured roles and percentages",
                "`/list-shifts` - List configured shifts",
                "`/list-periods` - List configured periods",
                "`/list-bonus-rules` - List configured bonus rules",
                "`/list-models` - List configured models"
            ])
            embed.add_field(name="List Commands", value=list_commands, inline=False)

            # Reset Commands
            reset_commands = "\n".join([
                "`/reset-config` - Reset all configuration files",
                "`/reset-shift-config` - Reset shift configuration",
                "`/reset-period-config` - Reset period configuration",
                "`/reset-role-config` - Reset role configuration",
                "`/reset-bonus-config` - Reset bonus rules configuration",
                "`/reset-models-config` - Reset models configuration",
                "`/reset-compensation-config` - Reset compensation configuration"
            ])
            embed.add_field(name="Reset Commands", value=reset_commands, inline=False)

            # Backup Commands
            backup_commands = "\n".join([
                "`/restore-latest-backup` - Restore the latest backup",
                "`/restore-shift-backup` - Restore the latest shift configuration backup",
                "`/restore-period-backup` - Restore the latest period configuration backup",
                "`/restore-role-backup` - Restore the latest role configuration backup",
                "`/restore-bonus-backup` - Restore the latest bonus rules configuration backup",
                "`/restore-earnings-backup` - Restore the latest earnings configuration backup",
                "`/restore-models-backup` - Restore the latest models configuration backup",
                "`/restore-compensation-backup` - Restore the latest compensation configuration backup",
            ])
            embed.add_field(name="Backup Commands", value=backup_commands, inline=False)

            # Miscellaneous Admin Commands
            misc_admin_commands = "\n".join([
                "`/toggle-ephemeral` - Toggle whether command responses are ephemeral",
                "`/toggle-average` - Toggle performance averages in calculation embeds",
                "`/toggle-id-display` - Toggle display of IDs in reports",
                "`/set-agency-name` - Set the agency name",
                "`/set-bot-name` - Set the bot name",
                "`/clear-earnings` - Clear all earnings data",
                "`/remove-sale` - Remove earnings entries by IDs , Users mentions or combined",
                "`/view-config` - Display all server configurations with interactive pagination",
                "`/copy-config-from-the-server` - Copy config files while preserving existing configurations",
                "`/copy-earnings-from-the-server` - Copy earnings data from another server",
                "`/manage-backups` - Manage server backups with type, action selection and optional ids parameter in case of removal action",

            ])
            embed.add_field(name="Miscellaneous Admin Commands", value=misc_admin_commands, inline=False)

            # Report Commands
            report_commands = "\n".join([
                "`/view-earnings` - View your earnings"
            ])
            embed.add_field(name="Report Commands", value=report_commands, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)


async def setup(bot):
    await bot.add_cog(HelpSlashCommands(bot))

