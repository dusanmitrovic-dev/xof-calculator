import logging
import discord
from discord.ext import commands
from discord import app_commands
from config import settings

logger = logging.getLogger("xof_calculator.help_slash")

class HelpSlashCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Show available commands based on your permissions")
    async def help(self, interaction: discord.Interaction):
        """Show available commands based on user permissions"""
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
                "`/remove-model` - Remove a model configuration"
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
                "`/reset-earnings-config` - Reset earnings configuration",
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
                "`/export-earnings-csv` - Export earnings data as CSV",
                "`/export-earnings-json` - Export earnings data as JSON",
                "`/clear-earnings` - Clear all earnings data"
            ])
            embed.add_field(name="Miscellaneous Admin Commands", value=misc_admin_commands, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(HelpSlashCommands(bot))

