import discord
import logging

from discord import app_commands
from discord.ext import commands
from typing import Optional
from config import settings
from utils import file_handlers, validators

logger = logging.getLogger("xof_calculator.admin_slash")

class AdminSlashCommands(commands.Cog, name="admin"):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(
        name="admin-export-earnings-csv",
        description="[Admin] Export all earnings data as CSV"
    )
    async def export_earnings(self, interaction: discord.Interaction):  # Add self parameter
        """
        Admin-only command to export earnings data
        
        Usage: /admin-export-earnings-csv
        """
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ This command is restricted to administrators.", ephemeral=True)
            return
        
        try:
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
                "📊 Full earnings export:",
                file=csv_file,
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Export error: {str(e)}")
            await interaction.response.send_message("❌ Failed to generate export. Check logs.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AdminSlashCommands(bot))

