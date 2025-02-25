import os
import logging
import discord
from discord.ext import commands
from decimal import Decimal
from datetime import datetime
from typing import Optional, List, Dict

from config import settings
from utils import file_handlers, validators, calculations

logger = logging.getLogger("fox_calculator.calculator")

class CalculatorCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="calculate")
    async def calculate(self, ctx, period: str, shift: str, role: discord.Role, gross_revenue: str, *, models: str = "None"):
        """
        Calculate earnings based on revenue, role, and shift
        Usage: !calculate "January 2023" "Morning Shift" @ModelRole $1000 Model1, Model2
        """
        guild_id = str(ctx.guild.id)
        
        # Validate period
        period_data = await file_handlers.load_json(settings.PERIOD_DATA_FILE, settings.DEFAULT_PERIOD_DATA)
        valid_periods = period_data.get(guild_id, [])
        matched_period = validators.validate_period(period, valid_periods)
        
        if matched_period is None:
            await ctx.send(f"❌ Period '{period}' not configured! Admins: use !calculateperiodset.")
            return
        period = matched_period
        
        # Validate shift
        shift_data = await file_handlers.load_json(settings.SHIFT_DATA_FILE, settings.DEFAULT_SHIFT_DATA)
        valid_shifts = shift_data.get(guild_id, [])
        matched_shift = validators.validate_shift(shift, valid_shifts)
        
        if matched_shift is None:
            await ctx.send(f"❌ Shift '{shift}' not configured! Admins: use !calculateshiftset.")
            return
        shift = matched_shift
        
        # Validate role
        role_data = await file_handlers.load_json(settings.ROLE_DATA_FILE, settings.DEFAULT_ROLE_DATA)
        if guild_id not in role_data or str(role.id) not in role_data[guild_id]:
            await ctx.send(f"⚠ {role.name} not configured! Admins: use !calculateroleset.")
            return
        
        # Parse revenue
        gross_revenue_decimal = validators.parse_money(gross_revenue)
        if gross_revenue_decimal is None:
            await ctx.send("❌ Invalid revenue format. Please use a valid number.")
            return
        
        # Get role percentage
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
        
        # Process image attachments
        valid_images = []
        for attachment in ctx.message.attachments:
            if attachment.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                valid_images.append(await attachment.to_file())
        
        # Try to delete the command message for privacy
        try:
            await ctx.message.delete()
        except discord.errors.Forbidden:
            logger.warning(f"Missing permission to delete messages in {ctx.guild.name}")
        except Exception as e:
            logger.error(f"Error deleting message: {e}")
        
        # Calculate earnings
        results = calculations.calculate_earnings(
            gross_revenue_decimal,
            percentage,
            bonus_rule_objects
        )
        
        # Save earnings data
        sender = ctx.author.mention
        current_date = datetime.now().strftime(settings.DATE_FORMAT)
        
        # Process models
        models_list = models if models != "None" else ""
        
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
            await ctx.send("⚠ Calculation completed but failed to save data. Please try again.")
            return
        
        # Create embed
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
            ("💸 Employee Cut", f"${float(results['employee_cut']):,.2f} ({float(percentage)}%)", True),
            ("🎁 Bonus", f"${float(results['bonus']):,.2f}", True),
            ("💰 Total Cut", f"${float(results['total_cut']):,.2f}", True),
            ("🎭 Models", models_list, False)
        ]
        
        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)
        
        # Send the embed with images
        await ctx.send(embed=embed, files=valid_images)
    
    @commands.command(name="total")
    async def total(self, ctx, period: str, from_date: Optional[str] = None, to_date: Optional[str] = None, sender: Optional[str] = None):
        """
        Calculate total earnings for a period and optional date range
        Usage: !total "January 2023" 01/01/2023 31/01/2023 @User
        """
        guild_id = str(ctx.guild.id)
        
        # Validate period
        period_data = await file_handlers.load_json(settings.PERIOD_DATA_FILE, settings.DEFAULT_PERIOD_DATA)
        valid_periods = period_data.get(guild_id, [])
        matched_period = validators.validate_period(period, valid_periods)
        
        if matched_period is None:
            await ctx.send(f"❌ Period '{period}' not configured! Admins: use !calculateperiodset.")
            return
        period = matched_period
        
        # Validate dates if provided
        if from_date and not validators.validate_date_format(from_date, settings.DATE_FORMAT):
            await ctx.send(f"❌ Invalid from_date format. Please use {settings.DATE_FORMAT}.")
            return
        
        if to_date and not validators.validate_date_format(to_date, settings.DATE_FORMAT):
            await ctx.send(f"❌ Invalid to_date format. Please use {settings.DATE_FORMAT}.")
            return
        
        # Try to delete the command message
        try:
            await ctx.message.delete()
        except discord.errors.Forbidden:
            logger.warning(f"Missing permission to delete messages in {ctx.guild.name}")
        except Exception as e:
            logger.error(f"Error deleting message: {e}")
        
        # Determine sender
        if sender is None:
            sender = ctx.author.mention
        
        # Load earnings data
        earnings_data = await file_handlers.load_json(settings.EARNINGS_FILE, settings.DEFAULT_EARNINGS)
        
        if sender not in earnings_data:
            await ctx.send(f"No earnings recorded for {sender}.")
            return
        
        # Get sender's earnings for the period
        earnings_list = [
            entry for entry in earnings_data[sender] 
            if entry.get("period", "").lower() == period.lower()
        ]
        
        if not earnings_list:
            await ctx.send(f"No earnings recorded for {sender} in {period}.")
            return
        
        # Calculate total
        total_earnings = calculations.get_total_earnings(
            earnings_list, 
            period.lower(),
            from_date,
            to_date
        )
        
        # Prepare date range display
        date_range = f"from {from_date} to {to_date}" if from_date and to_date else "for all time"
        
        # Create and send embed
        embed = discord.Embed(
            title="💰 Total Earnings",
            description=f"**{sender}**'s total earnings for {period} {date_range}:",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="💸 Total Cut", 
            value=f"${float(total_earnings):,.2f}", 
            inline=False
        )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(CalculatorCommands(bot))