import os
import discord
import logging

from config import settings
from typing import Optional
from datetime import datetime
from discord.ext import commands
from utils import file_handlers, validators, calculations

logger = logging.getLogger("xof_calculator.reports")

class ReportCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="summary")
    async def summary(self, ctx, period: str = commands.parameter(description="The period to calculate for (e.g., 'weekly')"), from_date: Optional[str] = commands.parameter(description="The start date (e.g., '01/01/2023')"), to_date: Optional[str] = commands.parameter(description="The end date (e.g., '02/03/2025')")):
        """
        Generate a summary report for all earnings in a period

        Usage: !summary weekly 01/01/2023 31/01/2023
        """
        # Log command usage
        logger.info(f"User {ctx.author.name} ({ctx.author.id}) used summary command with period={period}, from_date={from_date}, to_date={to_date}")
        
        guild_id = str(ctx.guild.id)
        
        # Validate period
        valid_periods = await file_handlers.load_json(settings.get_guild_periods_path(ctx.guild.id), [])
        matched_period = validators.validate_period(period, valid_periods)
        
        if matched_period is None:
            logger.warning(f"Invalid period '{period}' provided by {ctx.author.name}")
            await ctx.send(f"❌ Period '{period}' not configured! Admins: use !set-period.")
            return
            
        period = matched_period
        
        # Validate dates if provided
        if from_date and not validators.validate_date_format(from_date, settings.DATE_FORMAT):
            logger.warning(f"Invalid from_date format '{from_date}' provided by {ctx.author.name}")
            await ctx.send(f"❌ Invalid from_date format. Please use {settings.DATE_FORMAT}.")
            return
        
        if to_date and not validators.validate_date_format(to_date, settings.DATE_FORMAT):
            logger.warning(f"Invalid to_date format '{to_date}' provided by {ctx.author.name}")
            await ctx.send(f"❌ Invalid to_date format. Please use {settings.DATE_FORMAT}.")
            return
        
        # Load earnings data
        earnings_data = await file_handlers.load_json(settings.get_guild_earnings_path(ctx.guild.id), {})
        
        # Collect all entries for the period
        all_entries = []
        for sender, entries in earnings_data.items():
            for entry in entries:
                if entry.get("period", "").lower() == period.lower():
                    # Add sender to entry
                    entry_with_sender = entry.copy()
                    entry_with_sender["sender"] = sender
                    all_entries.append(entry_with_sender)
        
        if not all_entries:
            logger.info(f"No earnings found for period '{period}' in guild {guild_id}")
            await ctx.send(f"No earnings recorded for {period}.")
            return
        
        # Filter by date range if provided
        if from_date and to_date:
            from_date_obj = datetime.strptime(from_date, settings.DATE_FORMAT)
            to_date_obj = datetime.strptime(to_date, settings.DATE_FORMAT)
            
            all_entries = [
                entry for entry in all_entries
                if from_date_obj <= datetime.strptime(entry.get("date", "01/01/1970"), settings.DATE_FORMAT) <= to_date_obj
            ]
        
        if not all_entries:
            logger.info(f"No earnings found for period '{period}' in date range {from_date} - {to_date}")
            await ctx.send(f"No earnings recorded for {period} in the specified date range.")
            return
        
        # Prepare summary data
        total_gross = sum(entry.get("gross_revenue", 0) for entry in all_entries)
        total_paid = sum(entry.get("total_cut", 0) for entry in all_entries)
        user_count = len(set(entry.get("sender") for entry in all_entries))
        entry_count = len(all_entries)
        
        # Log summary results
        logger.info(f"Summary report for period '{period}': {entry_count} entries, {user_count} users, ${total_gross} gross, ${total_paid} total cut")
        
        # Date range display
        date_range = f"from {from_date} to {to_date}" if from_date and to_date else "for all time"
        
        # Create embed
        embed = discord.Embed(
            title=f"📊 {period} Summary Report",
            description=f"Earnings summary {date_range}",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="Total Entries", value=str(entry_count), inline=False)
        embed.add_field(name="Total Users", value=str(user_count), inline=False)
        embed.add_field(name="Platform Fee", value=f"${(total_gross * 0.2):,.2f}", inline=False)
        embed.add_field(name="Gross Revenue", value=f"${total_gross:,.2f}", inline=False)
        embed.add_field(name="Total Chatter Cut", value=f"${total_paid:,.2f}", inline=False)
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(ReportCommands(bot))