import os
import logging
import discord

from config import settings
from decimal import Decimal
from datetime import datetime
from discord.ext import commands
from typing import Optional, List, Dict
from utils import file_handlers, validators, calculations, generator_uuid

logger = logging.getLogger("xof_calculator.calculator")

class CalculatorCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        logger.info("CalculatorCommands cog initialized")

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

    @commands.command(name="calculate")
    async def calculate(self, ctx, period: str = commands.parameter(description="The period to calculate for (e.g., 'weekly')"), shift: str = commands.parameter(description="The shift to calculate for (e.g., 'night')"), role: discord.Role = commands.parameter(description="The role to calculate for (e.g., '@Expert')"), gross_revenue: str = commands.parameter(description="The gross revenue (e.g., '1269.69')"), *, models: str = commands.parameter(description="The models to calculate for (e.g., 'peanut')")):
        """
        Calculate earnings based on revenue, role, and shift
        
        Usage: !calculate weekly night @Expert 1269.69 peanut
        """
        logger.info(f"Calculate command: {ctx.author} - {period}/{shift}/{role.name}/{gross_revenue}")
        guild_id = str(ctx.guild.id)
        
        # Validate period
        period_data = await file_handlers.load_json(settings.get_guild_periods_path(ctx.guild.id), [])
        valid_periods = period_data
        matched_period = validators.validate_period(period, valid_periods)
        
        if matched_period is None:
            logger.warning(f"Invalid period '{period}' for guild {guild_id}")
            await ctx.send(f"❌ Period '{period}' not configured! Admins: use !set-period.")
            return

        period = matched_period
        
        # Validate shift
        shift_data = await file_handlers.load_json(settings.get_guild_shifts_path(ctx.guild.id), [])
        valid_shifts = shift_data
        matched_shift = validators.validate_shift(shift, valid_shifts)
        
        if matched_shift is None:
            logger.warning(f"Invalid shift '{shift}' for guild {guild_id}")
            await ctx.send(f"❌ Shift '{shift}' not configured! Admins: use !set-shift.")
            return
            
        shift = matched_shift
        
        # Validate role
        role_data = await file_handlers.load_json(settings.get_guild_roles_path(ctx.guild.id), {})
        if str(role.id) not in role_data:
            logger.warning(f"Role {role.name} ({role.id}) not configured for guild {guild_id}")
            await ctx.send(f"⚠ {role.name} not configured! Admins: use !set-role.")
            return
        
        # Parse revenue
        gross_revenue_decimal = validators.parse_money(gross_revenue)
        if gross_revenue_decimal is None:
            logger.warning(f"Invalid revenue format: {gross_revenue}")
            await ctx.send("❌ Invalid revenue format. Please use a valid number.")
            return
        
        # Get role percentage
        percentage = Decimal(str(role_data[str(role.id)]))
        
        # Load bonus rules
        bonus_rules = await file_handlers.load_json(settings.get_guild_bonus_rules_path(ctx.guild.id), [])
        guild_bonus_rules = bonus_rules
        
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
            logger.warning(f"Missing permission to delete messages in guild {guild_id}")
        except Exception as e:
            logger.error(f"Error deleting message: {str(e)}")
        
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
        earnings_data = await file_handlers.load_json(settings.get_guild_earnings_path(ctx.guild.id), {})
        if sender not in earnings_data:
            earnings_data[sender] = []

        unique_id = generator_uuid.generate_id()
        
        # Add new entry
        new_entry = {
            "id": unique_id,
            "date": current_date,
            "total_cut": float(results["total_cut"]),
            "gross_revenue": float(results["gross_revenue"]),
            "period": period.lower(),
            "shift": shift,
            "role": role.name,
            "models": models_list,
            "hours_worked": float(0)
        }
        earnings_data[sender].append(new_entry)
        
        # Save updated earnings data
        success = await file_handlers.save_json(settings.get_guild_earnings_path(ctx.guild.id), earnings_data)
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
            ("🎁 Bonus", f"${float(results['bonus']):,.2f}", True),
            ("💰 Total Cut", f"${float(results['total_cut']):,.2f}", True),
            ("🎭 Models", models_list, False)
        ]
        
        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)

        if await self.get_show_ids(ctx.guild.id):
            embed.set_footer(text=f"Sale ID: {unique_id}")
        
        # Send the embed with images
        try:
            await ctx.send(embed=embed, files=valid_images)
            logger.info(f"Earnings calculation completed for {ctx.author}")
        except Exception as e:
            logger.error(f"Error sending calculation results: {str(e)}")
            await ctx.send("⚠ Error sending calculation results. Please try again or contact an admin.")
    
    @commands.command(name="total")
    async def total(self, ctx, period: str = commands.parameter(description="The period to calculate for (e.g., 'weekly')"), from_date: Optional[str] = commands.parameter(description="The start date (e.g., '01/01/2023')"), to_date: Optional[str] = commands.parameter(description="The end date (e.g., '27/02/2025')"), sender: Optional[str] = commands.parameter(description="The sender to calculate for (e.g., '@User')")):
        """
        Calculate total earnings for a period and optional date range

        Usage: !total weekly 01/01/2023 27/02/2025 @User
        """
        logger.info(f"Total command: {ctx.author} - {period} from {from_date} to {to_date} for {sender or 'self'}")
        guild_id = str(ctx.guild.id)
        
        # Validate period
        valid_periods = await file_handlers.load_json(settings.get_guild_periods_path(ctx.guild.id), [])
        matched_period = validators.validate_period(period, valid_periods)
        
        if matched_period is None:
            logger.warning(f"Invalid period '{period}' for guild {guild_id}")
            await ctx.send(f"❌ Period '{period}' not configured! Admins: use !set-period.")
            return
        period = matched_period
        
        # Validate dates if provided
        if from_date and not validators.validate_date_format(from_date, settings.DATE_FORMAT):
            logger.warning(f"Invalid from_date format: {from_date}")
            await ctx.send(f"❌ Invalid from_date format. Please use {settings.DATE_FORMAT}.")
            return
        
        if to_date and not validators.validate_date_format(to_date, settings.DATE_FORMAT):
            logger.warning(f"Invalid to_date format: {to_date}")
            await ctx.send(f"❌ Invalid to_date format. Please use {settings.DATE_FORMAT}.")
            return
        
        # Try to delete the command message
        try:
            await ctx.message.delete()
        except discord.errors.Forbidden:
            logger.warning(f"Missing permission to delete messages in guild {guild_id}")
        except Exception as e:
            logger.error(f"Error deleting message: {str(e)}")
        
        # Determine sender
        if sender is None:
            sender = ctx.author.mention
        
        # Load earnings data
        earnings_data = await file_handlers.load_json(settings.get_guild_earnings_path(ctx.guild.id), {})
        
        if sender not in earnings_data:
            logger.warning(f"No earnings recorded for {sender}")
            await ctx.send(f"No earnings recorded for {sender}.")
            return
        
        # Get sender's earnings for the period
        earnings_list = [
            entry for entry in earnings_data[sender] 
            if entry.get("period", "").lower() == period.lower()
        ]
        
        if not earnings_list:
            logger.warning(f"No {period} earnings recorded for {sender}")
            await ctx.send(f"No earnings recorded for {sender} in {period}.")
            return
        
        # Calculate gross and total
        try:
            gross_revenue, total_earnings = calculations.get_total_earnings(
                earnings_list, 
                period.lower(),
                from_date,
                to_date
            )
        except Exception as e:
            logger.error(f"Error calculating totals: {str(e)}")
            await ctx.send("❌ Error calculating totals. Please check logs.")
            return
        
        # Prepare date range display
        date_range = f"from `{from_date}` to `{to_date}`" if from_date and to_date else "for all time"

        embed = discord.Embed(
            title="💰 Total Earnings",
            description=f"**{sender}**'s total earnings for {period} period {date_range}:",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="Total Gross", 
            value=f"${float(gross_revenue):,.2f}", 
            inline=False
        )

        embed.add_field(
            name="Total Cut", 
            value=f"${float(total_earnings):,.2f}", 
            inline=False
        )
        
        try:
            await ctx.send(embed=embed)
            logger.info(f"Total earnings calculation completed for {sender}")
        except Exception as e:
            logger.error(f"Error sending total results: {str(e)}")
            await ctx.send("⚠ Error sending calculation results. Please try again or contact an admin.")

async def setup(bot):
    await bot.add_cog(CalculatorCommands(bot))
    logger.info("CalculatorCommands cog registered")