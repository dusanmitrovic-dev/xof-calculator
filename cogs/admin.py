import discord
import logging

from decimal import Decimal
from typing import Optional
from config import settings
from discord import app_commands
from discord.ext import commands
from utils import file_handlers, validators

logger = logging.getLogger("xof_calculator.admin")

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    async def cog_check(self, ctx):
        """Check if user has administrator permissions for all commands in this cog"""
        return ctx.author.guild_permissions.administrator
    
    @commands.command(name="calculateroleset")
    async def role_set(self, ctx, role: discord.Role, percentage: str):
        """
        Set a role's percentage cut (Admin only)
        
        Usage: !calculateroleset @RoleName 25.5
        """
        # Validate percentage
        percentage_decimal = validators.validate_percentage(percentage)
        if percentage_decimal is None:
            await ctx.send("❌ Percentage must be a valid number between 0 and 100.")
            return
        
        guild_id = str(ctx.guild.id)
        role_id = str(role.id)
        
        # Load current role data
        role_data = await file_handlers.load_json(settings.ROLE_DATA_FILE, settings.DEFAULT_ROLE_DATA)
        
        # Update role data
        if guild_id not in role_data:
            role_data[guild_id] = {}
        role_data[guild_id][role_id] = float(percentage_decimal)
        
        # Save updated data
        success = await file_handlers.save_json(settings.ROLE_DATA_FILE, role_data)
        
        if success:
            await ctx.send(f"✅ {role.name} now has {percentage_decimal}% cut!")
        else:
            await ctx.send("❌ Failed to save role data. Please try again later.")
    
    @commands.command(name="calculateshiftset")
    async def shift_set(self, ctx, *, shift: str):
        """
        Add a valid shift name (Admin only)
        
        Usage: !calculateshiftset Morning Shift
        """
        if not shift or len(shift.strip()) == 0:
            await ctx.send("❌ Shift name cannot be empty.")
            return
            
        guild_id = str(ctx.guild.id)
        
        # Load current shift data
        shift_data = await file_handlers.load_json(settings.SHIFT_DATA_FILE, settings.DEFAULT_SHIFT_DATA)
        
        # Get existing shifts for this guild
        existing_shifts = shift_data.get(guild_id, [])
        
        # Check if shift already exists (case-insensitive)
        if validators.validate_shift(shift, existing_shifts) is not None:
            await ctx.send(f"❌ Shift '{shift}' already exists!")
            return
        
        # Add new shift
        if guild_id not in shift_data:
            shift_data[guild_id] = []
        shift_data[guild_id].append(shift)
        
        # Save updated data
        success = await file_handlers.save_json(settings.SHIFT_DATA_FILE, shift_data)
        
        if success:
            await ctx.send(f"✅ Shift '{shift}' added!")
        else:
            await ctx.send("❌ Failed to save shift data. Please try again later.")
    
    @commands.command(name="calculateperiodset")
    async def period_set(self, ctx, *, period: str):
        """
        Add a valid period name (Admin only)
        
        Usage: !calculateperiodset January 2025
        """
        if not period or len(period.strip()) == 0:
            await ctx.send("❌ Period name cannot be empty.")
            return
            
        guild_id = str(ctx.guild.id)
        
        # Load current period data
        period_data = await file_handlers.load_json(settings.PERIOD_DATA_FILE, settings.DEFAULT_PERIOD_DATA)
        
        # Get existing periods for this guild
        existing_periods = period_data.get(guild_id, [])
        
        # Check if period already exists (case-insensitive)
        if validators.validate_period(period, existing_periods) is not None:
            await ctx.send(f"❌ Period '{period}' already exists!")
            return
        
        # Add new period
        if guild_id not in period_data:
            period_data[guild_id] = []
        period_data[guild_id].append(period)
        
        # Save updated data
        success = await file_handlers.save_json(settings.PERIOD_DATA_FILE, period_data)
        
        if success:
            await ctx.send(f"✅ Period '{period}' added!")
        else:
            await ctx.send("❌ Failed to save period data. Please try again later.")
    
    @commands.command(name="calculatebonus")
    async def bonus_set(self, ctx, from_str: str, to_str: str, bonus_str: str):
        """
        Set a bonus rule for a revenue range (Admin only)
        
        Usage: !calculatebonus $1000 $2000 $50
        """
        guild_id = str(ctx.guild.id)
        
        # Parse monetary values
        from_num = validators.parse_money(from_str)
        to_num = validators.parse_money(to_str)
        bonus_amount = validators.parse_money(bonus_str)
        
        if None in (from_num, to_num, bonus_amount):
            await ctx.send("❌ Invalid number format. Please enter numbers without symbols other than decimal points.")
            return
            
        if from_num > to_num:
            await ctx.send("❌ The 'from' value must be less than or equal to the 'to' value.")
            return
            
        # Load current bonus rules
        bonus_rules = await file_handlers.load_json(settings.BONUS_RULES_FILE, settings.DEFAULT_BONUS_RULES)
        
        # Initialize guild entry if needed
        if guild_id not in bonus_rules:
            bonus_rules[guild_id] = []
            
        # Add new rule
        new_rule = {
            "from": float(from_num),
            "to": float(to_num),
            "amount": float(bonus_amount)
        }
        
        # Check for overlaps with existing rules
        current_rules = bonus_rules[guild_id]
        overlapping = False
        
        for rule in current_rules:
            rule_from = Decimal(str(rule.get("from", 0)))
            rule_to = Decimal(str(rule.get("to", 0)))
            
            # Check for overlap
            if (from_num <= rule_to and to_num >= rule_from):
                overlapping = True
                break
                
        if overlapping:
            await ctx.send("❌ This rule overlaps with an existing bonus rule. Please adjust the range.")
            return
            
        # Add the new rule and save
        bonus_rules[guild_id].append(new_rule)
        success = await file_handlers.save_json(settings.BONUS_RULES_FILE, bonus_rules)
        
        if success:
            await ctx.send(f"✅ Bonus rule added: ${float(from_num):,.2f} to ${float(to_num):,.2f} → ${float(bonus_amount):,.2f} bonus!")
        else:
            await ctx.send("❌ Failed to save bonus rule. Please try again later.")
    
    @commands.command(name="calculateroleslist")
    async def roles_list(self, ctx):
        """List all configured roles and their percentages (Admin only)"""
        guild_id = str(ctx.guild.id)
        
        # Load role data
        role_data = await file_handlers.load_json(settings.ROLE_DATA_FILE, settings.DEFAULT_ROLE_DATA)
        guild_roles = role_data.get(guild_id, {})
        
        if not guild_roles:
            await ctx.send("❌ No roles have been configured yet.")
            return
            
        # Create embed
        embed = discord.Embed(
            title="📋 Configured Roles",
            description="List of roles and their percentage cuts",
            color=discord.Color.blue()
        )
        
        # Add roles to embed
        for role_id, percentage in guild_roles.items():
            role = ctx.guild.get_role(int(role_id))
            role_name = role.name if role else f"Unknown Role ({role_id})"
            embed.add_field(
                name=role_name,
                value=f"{percentage}%",
                inline=True
            )
            
        await ctx.send(embed=embed)
    
    @commands.command(name="calculateshiftslist")
    async def shifts_list(self, ctx):
        """List all configured shifts (Admin only)"""
        guild_id = str(ctx.guild.id)
        
        # Load shift data
        shift_data = await file_handlers.load_json(settings.SHIFT_DATA_FILE, settings.DEFAULT_SHIFT_DATA)
        guild_shifts = shift_data.get(guild_id, [])
        
        if not guild_shifts:
            await ctx.send("❌ No shifts have been configured yet.")
            return
            
        # Create embed
        embed = discord.Embed(
            title="📋 Configured Shifts",
            description="List of available shifts",
            color=discord.Color.blue()
        )
        
        # Add shifts to embed
        embed.add_field(
            name="Available Shifts",
            value="\n".join(f"• {shift}" for shift in guild_shifts),
            inline=False
        )
            
        await ctx.send(embed=embed)
    
    @commands.command(name="calculateperiodslist")
    async def periods_list(self, ctx):
        """List all configured periods (Admin only)"""
        guild_id = str(ctx.guild.id)
        
        # Load period data
        period_data = await file_handlers.load_json(settings.PERIOD_DATA_FILE, settings.DEFAULT_PERIOD_DATA)
        guild_periods = period_data.get(guild_id, [])
        
        if not guild_periods:
            await ctx.send("❌ No periods have been configured yet.")
            return
            
        # Create embed
        embed = discord.Embed(
            title="📋 Configured Periods",
            description="List of available periods",
            color=discord.Color.blue()
        )
        
        # Add periods to embed
        embed.add_field(
            name="Available Periods",
            value="\n".join(f"• {period}" for period in guild_periods),
            inline=False
        )
            
        await ctx.send(embed=embed)
    
    @commands.command(name="calculatebonuslist")
    async def bonus_list(self, ctx):
        """List all configured bonus rules (Admin only)"""
        guild_id = str(ctx.guild.id)
        
        # Load bonus data
        bonus_rules = await file_handlers.load_json(settings.BONUS_RULES_FILE, settings.DEFAULT_BONUS_RULES)
        guild_rules = bonus_rules.get(guild_id, [])
        
        if not guild_rules:
            await ctx.send("❌ No bonus rules have been configured yet.")
            return
        
        # Sort rules by revenue range
        sorted_rules = sorted(guild_rules, key=lambda x: x.get("from", 0))
        
        # Create embed
        embed = discord.Embed(
            title="📋 Bonus Rules",
            description="List of revenue-based bonus rules",
            color=discord.Color.green()
        )
        
        # Add bonus rules to embed
        for rule in sorted_rules:
            from_val = rule.get("from", 0)
            to_val = rule.get("to", 0)
            amount = rule.get("amount", 0)
            embed.add_field(
                name=f"${from_val} - ${to_val}",
                value=f"Bonus: ${amount}",
                inline=False
            )

        await ctx.send(embed=embed)
    
    @app_commands.command(name="hello", description="Says hello only to the person who asked")
    async def hello(self, interaction: discord.Interaction):
        await interaction.response.send_message("Hello! How can I help you today?", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))