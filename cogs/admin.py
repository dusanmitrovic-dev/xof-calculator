import discord
import logging

from decimal import Decimal
from typing import Optional
from config import settings
from discord.ext import commands
from utils import file_handlers, validators

logger = logging.getLogger("xof_calculator.admin")

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    async def cog_check(self, ctx):
        """Check if user has administrator permissions for all commands in this cog"""
        return ctx.author.guild_permissions.administrator
    
    @commands.command(name="set-role")
    async def role_set(self, ctx, role: discord.Role = commands.parameter(description="The role to set the percentage for"), percentage: str = commands.parameter(description="The percentage cut for the role")):
        """
        Set a role's percentage cut (Admin only)
        
        Usage: !set-role @RoleName 6.5
        """
        # Log command usage
        logger.info(f"User {ctx.author.name} ({ctx.author.id}) used set-role command for role {role.name} with percentage {percentage}")
        
        # Validate percentage
        percentage_decimal = validators.validate_percentage(percentage)
        if percentage_decimal is None:
            logger.warning(f"Invalid percentage '{percentage}' provided by {ctx.author.name}")
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
            # Log successful operation
            logger.info(f"Role {role.name} ({role_id}) percentage set to {percentage_decimal}% by {ctx.author.name}")
            await ctx.send(f"✅ {role.name} now has {percentage_decimal}% cut!")
        else:
            logger.error(f"Failed to save role data for {role.name} ({role_id}) by {ctx.author.name}")
            await ctx.send("❌ Failed to save role data. Please try again later.")

    @commands.command(name="remove-role")
    async def role_remove(self, ctx, role: discord.Role = commands.parameter(description="The role to remove the percentage for")):
        """
        Remove a role's percentage configuration (Admin only)
        
        Usage: !remove-role @Expert
        """
        # Log command usage
        logger.info(f"User {ctx.author.name} ({ctx.author.id}) used remove-role command for role {role.name}")
        
        guild_id = str(ctx.guild.id)
        role_id = str(role.id)
        
        # Load current role data
        role_data = await file_handlers.load_json(settings.ROLE_DATA_FILE, settings.DEFAULT_ROLE_DATA)
        
        # Check if guild and role exist in data
        if guild_id not in role_data or role_id not in role_data[guild_id]:
            logger.warning(f"Role {role.name} ({role_id}) not found in configuration when {ctx.author.name} tried to remove it")
            await ctx.send(f"❌ {role.name} does not have a configured percentage.")
            return
        
        # Remove role
        del role_data[guild_id][role_id]
        
        # Save updated data
        success = await file_handlers.save_json(settings.ROLE_DATA_FILE, role_data)
        
        if success:
            logger.info(f"Role {role.name} ({role_id}) removed from configuration by {ctx.author.name}")
            await ctx.send(f"✅ {role.name} has been removed from percentage configuration!")
        else:
            logger.error(f"Failed to remove role {role.name} ({role_id}) by {ctx.author.name}")
            await ctx.send("❌ Failed to save role data. Please try again later.")
    
    @commands.command(name="set-shift")
    async def shift_set(self, ctx, *, shift: str = commands.parameter(description="The shift name to add")):
        """
        Add a valid shift name (Admin only)
        
        Usage: !set-shift morning
        """
        # Log command usage
        logger.info(f"User {ctx.author.name} ({ctx.author.id}) used set-shift command for shift '{shift}'")
        
        if not shift or len(shift.strip()) == 0:
            logger.warning(f"Empty shift name provided by {ctx.author.name}")
            await ctx.send("❌ Shift name cannot be empty.")
            return
            
        guild_id = str(ctx.guild.id)
        
        # Load current shift data
        shift_data = await file_handlers.load_json(settings.SHIFT_DATA_FILE, settings.DEFAULT_SHIFT_DATA)
        
        # Get existing shifts for this guild
        existing_shifts = shift_data.get(guild_id, [])
        
        # Check if shift already exists (case-insensitive)
        if validators.validate_shift(shift, existing_shifts) is not None:
            logger.warning(f"Shift '{shift}' already exists, attempted to add by {ctx.author.name}")
            await ctx.send(f"❌ Shift '{shift}' already exists!")
            return
        
        # Add new shift
        if guild_id not in shift_data:
            shift_data[guild_id] = []
        shift_data[guild_id].append(shift)
        
        # Save updated data
        success = await file_handlers.save_json(settings.SHIFT_DATA_FILE, shift_data)
        
        if success:
            logger.info(f"Shift '{shift}' added by {ctx.author.name}")
            await ctx.send(f"✅ Shift '{shift}' added!")
        else:
            logger.error(f"Failed to save shift '{shift}' added by {ctx.author.name}")
            await ctx.send("❌ Failed to save shift data. Please try again later.")
    
    @commands.command(name="remove-shift")
    async def shift_remove(self, ctx, *, shift: str = commands.parameter(description="The shift name to remove")):
        """
        Remove a shift configuration (Admin only)
        
        Usage: !remove-shift night
        """
        # Log command usage
        logger.info(f"User {ctx.author.name} ({ctx.author.id}) used remove-shift command for shift '{shift}'")
        
        if not shift or len(shift.strip()) == 0:
            logger.warning(f"Empty shift name provided for removal by {ctx.author.name}")
            await ctx.send("❌ Shift name cannot be empty.")
            return
            
        guild_id = str(ctx.guild.id)
        
        # Load current shift data
        shift_data = await file_handlers.load_json(settings.SHIFT_DATA_FILE, settings.DEFAULT_SHIFT_DATA)
        
        # Get existing shifts for this guild
        existing_shifts = shift_data.get(guild_id, [])
        
        # Validate and get normalized shift name
        normalized_shift = validators.validate_shift(shift, existing_shifts)
        if normalized_shift is None:
            logger.warning(f"Shift '{shift}' doesn't exist, attempted to remove by {ctx.author.name}")
            await ctx.send(f"❌ Shift '{shift}' doesn't exist!")
            return
        
        # Remove shift
        shift_data[guild_id].remove(normalized_shift)
        
        # Save updated data
        success = await file_handlers.save_json(settings.SHIFT_DATA_FILE, shift_data)
        
        if success:
            logger.info(f"Shift '{normalized_shift}' removed by {ctx.author.name}")
            await ctx.send(f"✅ Shift '{normalized_shift}' removed!")
        else:
            logger.error(f"Failed to remove shift '{normalized_shift}' by {ctx.author.name}")
            await ctx.send("❌ Failed to save shift data. Please try again later.")
    
    @commands.command(name="set-period")
    async def period_set(self, ctx, *, period: str = commands.parameter(description="The period name to add")):
        """
        Add a valid period name (Admin only)
        
        Usage: !set-period weekly
        """
        # Log command usage
        logger.info(f"User {ctx.author.name} ({ctx.author.id}) used set-period command for period '{period}'")
        
        if not period or len(period.strip()) == 0:
            logger.warning(f"Empty period name provided by {ctx.author.name}")
            await ctx.send("❌ Period name cannot be empty.")
            return
            
        guild_id = str(ctx.guild.id)
        
        # Load current period data
        period_data = await file_handlers.load_json(settings.PERIOD_DATA_FILE, settings.DEFAULT_PERIOD_DATA)
        
        # Get existing periods for this guild
        existing_periods = period_data.get(guild_id, [])
        
        # Check if period already exists (case-insensitive)
        if validators.validate_period(period, existing_periods) is not None:
            logger.warning(f"Period '{period}' already exists, attempted to add by {ctx.author.name}")
            await ctx.send(f"❌ Period '{period}' already exists!")
            return
        
        # Add new period
        if guild_id not in period_data:
            period_data[guild_id] = []
        period_data[guild_id].append(period)
        
        # Save updated data
        success = await file_handlers.save_json(settings.PERIOD_DATA_FILE, period_data)
        
        if success:
            logger.info(f"Period '{period}' added by {ctx.author.name}")
            await ctx.send(f"✅ Period '{period}' added!")
        else:
            logger.error(f"Failed to add period '{period}' by {ctx.author.name}")
            await ctx.send("❌ Failed to save period data. Please try again later.")
    
    @commands.command(name="remove-period")
    async def period_remove(self, ctx, *, period: str = commands.parameter(description="The period name to remove")):
        """
        Remove a period configuration (Admin only)
        
        Usage: !remove-period weekly
        """
        # Log command usage
        logger.info(f"User {ctx.author.name} ({ctx.author.id}) used remove-period command for period '{period}'")
        
        if not period or len(period.strip()) == 0:
            logger.warning(f"Empty period name provided for removal by {ctx.author.name}")
            await ctx.send("❌ Period name cannot be empty.")
            return
            
        guild_id = str(ctx.guild.id)
        
        # Load current period data
        period_data = await file_handlers.load_json(settings.PERIOD_DATA_FILE, settings.DEFAULT_PERIOD_DATA)
        
        # Get existing periods for this guild
        existing_periods = period_data.get(guild_id, [])
        
        # Validate and get normalized period name
        normalized_period = validators.validate_period(period, existing_periods)
        if normalized_period is None:
            logger.warning(f"Period '{period}' doesn't exist, attempted to remove by {ctx.author.name}")
            await ctx.send(f"❌ Period '{period}' doesn't exist!")
            return
        
        # Remove period
        period_data[guild_id].remove(normalized_period)
        
        # Save updated data
        success = await file_handlers.save_json(settings.PERIOD_DATA_FILE, period_data)
        
        if success:
            logger.info(f"Period '{normalized_period}' removed by {ctx.author.name}")
            await ctx.send(f"✅ Period '{normalized_period}' removed!")
        else:
            logger.error(f"Failed to remove period '{normalized_period}' by {ctx.author.name}")
            await ctx.send("❌ Failed to save period data. Please try again later.")

    @commands.command(name="set-bonus-rule")
    async def bonus_set(self, ctx, from_str: str = commands.parameter(description="The lower bound of the revenue range (e.g., 1000)"), to_str: str = commands.parameter(description="The upper bound of the revenue range (e.g., 2000)"), bonus_str: str = commands.parameter(description="The bonus amount for the range (e.g., 50)")):
        """
        Set a bonus rule for a revenue range (Admin only)
        
        Usage: !set-bonus-rule 1000 2000 50
        """
        # Log command usage
        logger.info(f"User {ctx.author.name} ({ctx.author.id}) used set-bonus-rule command with range {from_str}-{to_str} and bonus {bonus_str}")
        
        guild_id = str(ctx.guild.id)
        
        # Parse monetary values
        from_num = validators.parse_money(from_str)
        to_num = validators.parse_money(to_str)
        bonus_amount = validators.parse_money(bonus_str)
        
        if None in (from_num, to_num, bonus_amount):
            logger.warning(f"Invalid number format in bonus rule creation by {ctx.author.name}: {from_str}, {to_str}, {bonus_str}")
            await ctx.send("❌ Invalid number format. Please enter numbers without symbols other than decimal points.")
            return
            
        if from_num > to_num:
            logger.warning(f"Invalid bonus range (from > to) by {ctx.author.name}: {from_num} > {to_num}")
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
                logger.warning(f"Bonus rule overlap detected in rule created by {ctx.author.name}: {from_num}-{to_num} overlaps with {rule_from}-{rule_to}")
                break
                
        if overlapping:
            await ctx.send("❌ This rule overlaps with an existing bonus rule. Please adjust the range.")
            return
            
        # Add the new rule and save
        bonus_rules[guild_id].append(new_rule)
        success = await file_handlers.save_json(settings.BONUS_RULES_FILE, bonus_rules)
        
        if success:
            logger.info(f"Bonus rule added by {ctx.author.name}: ${float(from_num):,.2f} to ${float(to_num):,.2f} → ${float(bonus_amount):,.2f} bonus")
            await ctx.send(f"✅ Bonus rule added: ${float(from_num):,.2f} to ${float(to_num):,.2f} → ${float(bonus_amount):,.2f} bonus!")
        else:
            logger.error(f"Failed to save bonus rule by {ctx.author.name}: ${float(from_num):,.2f} to ${float(to_num):,.2f} → ${float(bonus_amount):,.2f}")
            await ctx.send("❌ Failed to save bonus rule. Please try again later.")

    @commands.command(name="remove-bonus-rule")
    async def bonus_remove(self, ctx, from_str: str = commands.parameter(description="The lower bound of the revenue range (e.g., 1000)"), to_str: str = commands.parameter(description="The upper bound of the revenue range (e.g., 2000)")):
        """
        Remove a bonus rule for a specific revenue range (Admin only)
        
        Usage: !remove-bonus-rule 1000 2000
        """
        # Log command usage
        logger.info(f"User {ctx.author.name} ({ctx.author.id}) used remove-bonus-rule command for range {from_str}-{to_str}")
        
        guild_id = str(ctx.guild.id)
        
        # Parse monetary values
        from_num = validators.parse_money(from_str)
        to_num = validators.parse_money(to_str)
        
        if None in (from_num, to_num):
            logger.warning(f"Invalid number format in bonus rule removal by {ctx.author.name}: {from_str}, {to_str}")
            await ctx.send("❌ Invalid number format. Please enter numbers without symbols other than decimal points.")
            return
            
        # Load current bonus rules
        bonus_rules = await file_handlers.load_json(settings.BONUS_RULES_FILE, settings.DEFAULT_BONUS_RULES)
        
        # Get guild rules
        guild_rules = bonus_rules.get(guild_id, [])
        if not guild_rules:
            logger.warning(f"No bonus rules configured for guild {guild_id} when {ctx.author.name} tried to remove one")
            await ctx.send("❌ No bonus rules have been configured yet.")
            return
        
        # Find matching rule
        rule_to_remove = None
        for rule in guild_rules:
            rule_from = Decimal(str(rule.get("from", 0)))
            rule_to = Decimal(str(rule.get("to", 0)))
            
            if rule_from == from_num and rule_to == to_num:
                rule_to_remove = rule
                break
                
        if rule_to_remove is None:
            logger.warning(f"Bonus rule not found for range ${float(from_num):,.2f} to ${float(to_num):,.2f} by {ctx.author.name}")
            await ctx.send(f"❌ No bonus rule found for range ${float(from_num):,.2f} to ${float(to_num):,.2f}.")
            return
            
        # Remove the rule and save
        bonus_rules[guild_id].remove(rule_to_remove)
        success = await file_handlers.save_json(settings.BONUS_RULES_FILE, bonus_rules)
        
        if success:
            logger.info(f"Bonus rule removed by {ctx.author.name}: ${float(from_num):,.2f} to ${float(to_num):,.2f}")
            await ctx.send(f"✅ Bonus rule removed: ${float(from_num):,.2f} to ${float(to_num):,.2f}")
        else:
            logger.error(f"Failed to remove bonus rule by {ctx.author.name}: ${float(from_num):,.2f} to ${float(to_num):,.2f}")
            await ctx.send("❌ Failed to save bonus rule changes. Please try again later.")
    
    bonus_remove.help = {
        'from_str': 'The lower bound of the revenue range (e.g., 1000)',
        'to_str': 'The upper bound of the revenue range (e.g., 2000)',
    }
    
    @commands.command(name="list-roles")
    async def roles_list(self, ctx):
        """
        List all configured roles and their percentages (Admin only)
        
        Usage: !list-roles
        """
        # Log command usage
        logger.info(f"User {ctx.author.name} ({ctx.author.id}) used list-roles command")
        
        guild_id = str(ctx.guild.id)
        
        # Load role data
        role_data = await file_handlers.load_json(settings.ROLE_DATA_FILE, settings.DEFAULT_ROLE_DATA)
        guild_roles = role_data.get(guild_id, {})
        
        if not guild_roles:
            logger.info(f"No roles configured for guild {guild_id} when {ctx.author.name} requested list")
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
        
        logger.info(f"Listed {len(guild_roles)} roles for guild {guild_id} requested by {ctx.author.name}")
        await ctx.send(embed=embed)
    
    @commands.command(name="list-shifts")
    async def shifts_list(self, ctx):
        """
        List all configured shifts (Admin only)
        
        Usage: !list-shifts
        """
        # Log command usage
        logger.info(f"User {ctx.author.name} ({ctx.author.id}) used list-shifts command")
        
        guild_id = str(ctx.guild.id)
        
        # Load shift data
        shift_data = await file_handlers.load_json(settings.SHIFT_DATA_FILE, settings.DEFAULT_SHIFT_DATA)
        guild_shifts = shift_data.get(guild_id, [])
        
        if not guild_shifts:
            logger.info(f"No shifts configured for guild {guild_id} when {ctx.author.name} requested list")
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
        
        logger.info(f"Listed {len(guild_shifts)} shifts for guild {guild_id} requested by {ctx.author.name}")
        await ctx.send(embed=embed)
    
    @commands.command(name="list-periods")
    async def periods_list(self, ctx):
        """
        List all configured periods (Admin only)
        
        Usage: !list-periods
        """
        # Log command usage
        logger.info(f"User {ctx.author.name} ({ctx.author.id}) used list-periods command")
        
        guild_id = str(ctx.guild.id)
        
        # Load period data
        period_data = await file_handlers.load_json(settings.PERIOD_DATA_FILE, settings.DEFAULT_PERIOD_DATA)
        guild_periods = period_data.get(guild_id, [])
        
        if not guild_periods:
            logger.info(f"No periods configured for guild {guild_id} when {ctx.author.name} requested list")
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
        
        logger.info(f"Listed {len(guild_periods)} periods for guild {guild_id} requested by {ctx.author.name}")
        await ctx.send(embed=embed)
    
    @commands.command(name="list-bonus-rules")
    async def bonus_list(self, ctx):
        """
        List all configured bonus rules (Admin only)
        
        Usage: !list-bonus-rules
        """
        # Log command usage
        logger.info(f"User {ctx.author.name} ({ctx.author.id}) used list-bonus-rules command")
        
        guild_id = str(ctx.guild.id)
        
        # Load bonus data
        bonus_rules = await file_handlers.load_json(settings.BONUS_RULES_FILE, settings.DEFAULT_BONUS_RULES)
        guild_rules = bonus_rules.get(guild_id, [])
        
        if not guild_rules:
            logger.info(f"No bonus rules configured for guild {guild_id} when {ctx.author.name} requested list")
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

        logger.info(f"Listed {len(guild_rules)} bonus rules for guild {guild_id} requested by {ctx.author.name}")
        await ctx.send(embed=embed)

    @commands.command(name="set-model")
    async def model_set(self, ctx, *, model: str = commands.parameter(description="The model name to add")):
        """
        Add a valid model name (Admin only)
        
        Usage: !set-model peanut
        """
        # Log command usage
        logger.info(f"User {ctx.author.name} ({ctx.author.id}) used set-model command for model '{model}'")
        
        if not model or len(model.strip()) == 0:
            logger.warning(f"Empty model name provided by {ctx.author.name}")
            await ctx.send("❌ Model name cannot be empty.")
            return
            
        guild_id = str(ctx.guild.id)
        
        # Load current model data
        model_data = await file_handlers.load_json(settings.MODELS_DATA_FILE, settings.DEFAULT_MODELS_DATA)
        
        # Get existing models for this guild
        existing_models = model_data.get(guild_id, [])
        
        # Check if model already exists (case-insensitive)
        if model.lower() in [m.lower() for m in existing_models]:
            logger.warning(f"Model '{model}' already exists, attempted to add by {ctx.author.name}")
            await ctx.send(f"❌ Model '{model}' already exists!")
            return
        
        # Add new model
        if guild_id not in model_data:
            model_data[guild_id] = []
        model_data[guild_id].append(model)
        
        # Save updated data
        success = await file_handlers.save_json(settings.MODELS_DATA_FILE, model_data)
        
        if success:
            logger.info(f"Model '{model}' added by {ctx.author.name}")
            await ctx.send(f"✅ Model '{model}' added!")
        else:
            logger.error(f"Failed to add model '{model}' by {ctx.author.name}")
            await ctx.send("❌ Failed to save model data. Please try again later.")
    
    @commands.command(name="remove-model")
    async def model_remove(self, ctx, *, model: str = commands.parameter(description="The model name to remove")):
        """
        Remove a model configuration (Admin only)
        
        Usage: !remove-model peanut
        """
        # Log command usage
        logger.info(f"User {ctx.author.name} ({ctx.author.id}) used remove-model command for model '{model}'")
        
        if not model or len(model.strip()) == 0:
            logger.warning(f"Empty model name provided for removal by {ctx.author.name}")
            await ctx.send("❌ Model name cannot be empty.")
            return
            
        guild_id = str(ctx.guild.id)
        
        # Load current model data
        model_data = await file_handlers.load_json(settings.MODELS_DATA_FILE, settings.DEFAULT_MODELS_DATA)
        
        # Get existing models for this guild
        existing_models = model_data.get(guild_id, [])
        
        # Find the model with case-insensitive matching
        normalized_model = None
        for m in existing_models:
            if m.lower() == model.lower():
                normalized_model = m
                break
                
        if normalized_model is None:
            logger.warning(f"Model '{model}' doesn't exist, attempted to remove by {ctx.author.name}")
            await ctx.send(f"❌ Model '{model}' doesn't exist!")
            return
        
        # Remove model
        model_data[guild_id].remove(normalized_model)
        
        # Save updated data
        success = await file_handlers.save_json(settings.MODELS_DATA_FILE, model_data)
        
        if success:
            logger.info(f"Model '{normalized_model}' removed by {ctx.author.name}")
            await ctx.send(f"✅ Model '{normalized_model}' removed!")
        else:
            logger.error(f"Failed to remove model '{normalized_model}' by {ctx.author.name}")
            await ctx.send("❌ Failed to save model data. Please try again later.")

    @commands.command(name="list-models")
    async def models_list(self, ctx):
        """
        List all configured models (Admin only)
        
        Usage: !list-models
        """
        # Log command usage
        logger.info(f"User {ctx.author.name} ({ctx.author.id}) used list-models command")
        
        guild_id = str(ctx.guild.id)
        
        # Load model data
        model_data = await file_handlers.load_json(settings.MODELS_DATA_FILE, settings.DEFAULT_MODELS_DATA)
        guild_models = model_data.get(guild_id, [])
        
        if not guild_models:
            logger.info(f"No models configured for guild {guild_id} when {ctx.author.name} requested list")
            await ctx.send("❌ No models have been configured yet.")
            return
            
        # Create embed
        embed = discord.Embed(
            title="📋 Configured Models",
            description="List of available models",
            color=discord.Color.blue()
        )
        
        # Add models to embed
        embed.add_field(
            name="Available Models",
            value="\n".join(f"• {model}" for model in guild_models),
            inline=False
        )
        
        logger.info(f"Listed {len(guild_models)} models for guild {guild_id} requested by {ctx.author.name}")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))