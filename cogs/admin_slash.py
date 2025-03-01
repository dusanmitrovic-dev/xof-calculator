import io
import json
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
    async def export_earnings_csv(self, interaction: discord.Interaction):
        """
        Admin-only command to export earnings data as CSV
        
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
                "📊 Full earnings export (CSV):",
                file=csv_file,
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Export CSV error: {str(e)}")
            await interaction.response.send_message("❌ Failed to generate CSV export. Check logs.", ephemeral=True)

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(
        name="admin-export-earnings-json",
        description="[Admin] Export all earnings data as JSON"
    )
    async def export_earnings_json(self, interaction: discord.Interaction):
        """
        Admin-only command to export earnings data as JSON
        
        Usage: /admin-export-earnings-json
        """
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ This command is restricted to administrators.", ephemeral=True)
            return
        
        try:
            earnings_data = await file_handlers.load_json(settings.EARNINGS_FILE, settings.DEFAULT_EARNINGS)
            
            # Create JSON content
            json_content = json.dumps(earnings_data, indent=4)
            
            # Create file object
            json_file = discord.File(
                io.BytesIO(json_content.encode('utf-8')),
                filename="full_earnings_export.json"
            )
            
            await interaction.response.send_message(
                "📊 Full earnings export (JSON):",
                file=json_file,
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Export JSON error: {str(e)}")
            await interaction.response.send_message("❌ Failed to generate JSON export. Check logs.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AdminSlashCommands(bot))

