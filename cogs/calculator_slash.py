import os
import io
import logging
import discord
import asyncio

from discord import ui, app_commands
from config import settings
from decimal import Decimal
import zipfile
from datetime import datetime
from pathlib import Path
from discord.ext import commands
from typing import Optional, List, Dict
from utils import file_handlers, validators, calculations
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
import matplotlib.pyplot as plt

SUPPORTED_EXPORTS = ["none", "txt", "csv", "json", "xlsx", "pdf", "png", "zip"]
MAX_ENTRIES = 50

logger = logging.getLogger("xof_calculator.calculator")

class HoursWorkedModal(ui.Modal, title="Enter Hours Worked"):
    def __init__(self, cog, period, shift, role, gross_revenue, compensation_type):
        super().__init__()
        self.cog = cog
        self.period = period
        self.shift = shift
        self.role = role
        self.gross_revenue = gross_revenue
        self.compensation_type = compensation_type
        
        self.hours_input = ui.TextInput(
            label="Hours Worked (e.g. 8)",
            placeholder="Enter number of hours...",
            required=True
        )
        self.add_item(self.hours_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        # Parse hours input
        hours_str = self.hours_input.value
        try:
            hours_worked = Decimal(hours_str)
            if hours_worked <= 0:
                raise ValueError("Hours worked must be positive")
        except (ValueError, InvalidOperation):
            logger.warning(f"User {interaction.user.name} ({interaction.user.id}) entered invalid hours format: {hours_str}")
            await interaction.response.send_message("❌ Invalid hours format. Please use a valid positive number.", ephemeral=True)
            return
        
        # Proceed to period selection with the hours worked
        await self.cog.start_period_selection_with_hours(interaction, self.compensation_type, hours_worked)

class CompensationTypeSelectionView(ui.View):
    def __init__(self, cog):
        super().__init__(timeout=180)
        self.cog = cog
        
        # Add buttons for each compensation type
        commission_button = ui.Button(label="Commission (%)", style=discord.ButtonStyle.primary)
        commission_button.callback = lambda i: self.on_compensation_selected(i, "commission")
        self.add_item(commission_button)
        
        hourly_button = ui.Button(label="Hourly ($/h)", style=discord.ButtonStyle.primary)
        hourly_button.callback = lambda i: self.on_compensation_selected(i, "hourly")
        self.add_item(hourly_button)
        
        both_button = ui.Button(label="Both (% + $/h)", style=discord.ButtonStyle.primary)
        both_button.callback = lambda i: self.on_compensation_selected(i, "both")
        self.add_item(both_button)
    
    async def on_compensation_selected(self, interaction: discord.Interaction, compensation_type: str):
        # Log compensation type selection
        logger.info(f"User {interaction.user.name} ({interaction.user.id}) selected compensation type: {compensation_type}")
        
        # Proceed to period selection with the selected compensation type
        await self.cog.start_period_selection(interaction, compensation_type)

class CalculatorSlashCommands(commands.GroupCog, name="calculate"):
    def __init__(self, bot):
        self.bot = bot
        super().__init__()

    async def generate_export_file(self, user_earnings, user, export_format):
        """Generate export file based on format choice"""
        sanitized_name = Path(user.name).stem[:32].replace(" ", "_")
        timestamp = datetime.now().strftime('%Y%m%d')
        base_name = f"earnings_{sanitized_name}_{timestamp}"
        
        buffer = io.BytesIO()
        
        if export_format == "csv":
            df = pd.DataFrame(user_earnings)
            df.to_csv(buffer, index=False)
            buffer.seek(0)
            return discord.File(buffer, filename=f"{base_name}.csv")
        
        elif export_format == "json":
            import json
            buffer.write(json.dumps(user_earnings, indent=2).encode('utf-8'))
            buffer.seek(0)
            return discord.File(buffer, filename=f"{base_name}.json")
        
        elif export_format == "xlsx":
            df = pd.DataFrame(user_earnings)
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Earnings')
            buffer.seek(0)
            return discord.File(buffer, filename=f"{base_name}.xlsx")
        
        elif export_format == "pdf":
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            elements = []
            
            # Create data table
            data = [["Date", "Role", "Gross", "Total Cut"]]
            for entry in user_earnings:
                data.append([
                    entry['date'],
                    entry['role'],
                    f"${float(entry['gross_revenue']):.2f}",
                    f"${float(entry['total_cut']):.2f}"
                ])
            
            table = Table(data)
            style = TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.grey),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,0), 14),
                ('BOTTOMPADDING', (0,0), (-1,0), 12),
                ('BACKGROUND', (0,1), (-1,-1), colors.beige),
                ('GRID', (0,0), (-1,-1), 1, colors.black)
            ])
            table.setStyle(style)
            elements.append(table)
            
            doc.build(elements)
            buffer.seek(0)
            return discord.File(buffer, filename=f"{base_name}.pdf")
        
        elif export_format == "png":
            plt.figure(figsize=(10, 6))
            dates = [datetime.strptime(entry['date'], '%Y-%m-%d') for entry in user_earnings]
            gross = [float(entry['gross_revenue']) for entry in user_earnings]
            cuts = [float(entry['total_cut']) for entry in user_earnings]
            
            plt.plot(dates, gross, label='Gross Revenue', marker='o')
            plt.plot(dates, cuts, label='Total Cut', marker='x')
            plt.title(f'Earnings Trend for {user.display_name}')
            plt.xlabel('Date')
            plt.ylabel('Amount ($)')
            plt.legend()
            plt.grid(True)
            plt.tight_layout()
            
            plt.savefig(buffer, format='png')
            plt.close()
            buffer.seek(0)
            return discord.File(buffer, filename=f"{base_name}.png")
        
        elif export_format == "zip":
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
                # Add CSV
                csv_file = await generate_export_file(user_earnings, user, "csv")
                zip_file.writestr(f"{base_name}.csv", csv_file.fp.getvalue())
                
                # Add PDF
                pdf_file = await generate_export_file(user_earnings, user, "pdf")
                zip_file.writestr(f"{base_name}.pdf", pdf_file.fp.getvalue())
            
            zip_buffer.seek(0)
            return discord.File(zip_buffer, filename=f"{base_name}.zip")
        
        else:  # txt format
            text_content = f"Earnings Report for {user.display_name}\n\n"
            text_content += "Date       | Role       | Gross     | Total Cut\n"
            text_content += "-"*40 + "\n"
            for entry in user_earnings:
                text_content += (
                    f"{entry['date']} | {entry['role'].ljust(10)} | "
                    f"${float(entry['gross_revenue']):>8.2f} | "
                    f"${float(entry['total_cut']):>9.2f}\n"
                )
            buffer.write(text_content.encode('utf-8'))
            buffer.seek(0)
            return discord.File(buffer, filename=f"{base_name}.txt")
    
    # New interactive slash command
    @app_commands.command(
        name="workflow",
        description="Calculate earnings using an interactive wizard"
    )
    async def calculate_slash(self, interaction: discord.Interaction):
        """Interactive workflow to calculate earnings"""
        # Log command usage
        logger.info(f"User {interaction.user.name} ({interaction.user.id}) started calculate workflow")
        
        # Start the interactive workflow with compensation type selection
        view = CompensationTypeSelectionView(self)
        await interaction.response.send_message("Select a compensation type:", view=view, ephemeral=True)

    async def start_period_selection(self, interaction: discord.Interaction, compensation_type: str):
        """First step: Period selection"""
        # Open the HoursWorkedModal to collect hours worked
        if compensation_type == "commission":
            await self.start_period_selection_with_hours(interaction, compensation_type, Decimal(0))
        else:
            modal = HoursWorkedModal(self, None, None, None, None, compensation_type)
            await interaction.response.send_modal(modal)

    async def start_period_selection_with_hours(self, interaction: discord.Interaction, compensation_type: str, hours_worked: Decimal):
        """First step: Period selection with hours worked"""
        guild_id = str(interaction.guild_id)
        
        # Load period data
        period_data = await file_handlers.load_json(settings.PERIOD_DATA_FILE, settings.DEFAULT_PERIOD_DATA)
        valid_periods = period_data.get(guild_id, [])
        
        if not valid_periods:
            logger.warning(f"No periods configured for guild {guild_id}")
            await interaction.response.send_message("❌ No periods configured! Admins: use /set-period.", ephemeral=True)
            return
        
        # Create period selection view, passing the compensation type and hours worked
        view = PeriodSelectionView(self, valid_periods, compensation_type, hours_worked)
        await interaction.response.edit_message(content="Select a period:", view=view)
    
    async def show_shift_selection(self, interaction: discord.Interaction, period: str, compensation_type: str, hours_worked: Decimal):
        """Second step: Shift selection"""

        # Log period selection
        logger.info(f"User {interaction.user.name} ({interaction.user.id}) selected period: {period}")
        
        guild_id = str(interaction.guild_id)
        
        # Load shift data
        shift_data = await file_handlers.load_json(settings.SHIFT_DATA_FILE, settings.DEFAULT_SHIFT_DATA)
        valid_shifts = shift_data.get(guild_id, [])
        
        if not valid_shifts:
            logger.warning(f"No shifts configured for guild {guild_id}")
            await interaction.response.send_message("❌ No shifts configured! Admins: use !set-shift.", ephemeral=True)
            return
        
        # Create shift selection view, passing the compensation type
        view = ShiftSelectionView(self, valid_shifts, period, compensation_type, hours_worked)
        await interaction.response.edit_message(content="Select a shift:", view=view)
    
    async def show_role_selection(self, interaction: discord.Interaction, period: str, shift: str, compensation_type: str, hours_worked: Decimal):
        """Third step: Role selection"""
        # Log shift selection
        logger.info(f"User {interaction.user.name} ({interaction.user.id}) selected shift: {shift}")
        
        guild_id = str(interaction.guild_id)
        
        # Load role data
        role_data = await file_handlers.load_json(settings.COMMISSION_SETTINGS_FILE, settings.DEFAULT_COMMISSION_SETTINGS)
        
        if guild_id not in role_data or not role_data[guild_id]:
            logger.warning(f"No roles configured for guild {guild_id}")
            await interaction.response.edit_message(content="❌ No roles configured! Admins: use /set-role-commission.", view=None)
            return
        
        # Get roles for this guild that are in the configuration
        guild_roles = interaction.guild.roles
        configured_roles = []
        
        for role in guild_roles:
            if str(role.id) in role_data[guild_id]["roles"] and role in interaction.user.roles:
                configured_roles.append(role)
        
        if not configured_roles:
            logger.warning(f"No configured roles found in guild {guild_id}")
            await interaction.response.edit_message(content="❌ No roles configured! Admins: use /set-role-commission.", view=None)
            return
        
        # Create role selection view
        view = RoleSelectionView(self, configured_roles, period, shift, compensation_type, hours_worked)
        await interaction.response.edit_message(content="Select a role:", view=view)
    
    async def show_revenue_input(self, interaction: discord.Interaction, period: str, shift: str, role: discord.Role, compensation_type: str, hours_worked: Decimal):
        """Fourth step: Revenue input"""
        # Log role selection
        logger.info(f"User {interaction.user.name} ({interaction.user.id}) selected role: {role.name} ({role.id})")
        
        # Create revenue input modal
        modal = RevenueInputModal(self, period, shift, role, compensation_type, hours_worked)
        await interaction.response.send_modal(modal)
    
    async def show_model_selection(self, interaction: discord.Interaction, period: str, shift: str, role: discord.Role, gross_revenue: Decimal, compensation_type: str, hours_worked: Decimal):
        """Fifth step: Model selection"""
        # Log revenue input
        logger.info(f"User {interaction.user.name} ({interaction.user.id}) entered gross revenue: ${gross_revenue}")
        
        guild_id = str(interaction.guild_id)
        # Load models data
        models_data = await file_handlers.load_json(settings.MODELS_DATA_FILE, settings.DEFAULT_MODELS_DATA)

        valid_models = models_data.get(guild_id, [])
        
        if not valid_models:
            logger.warning(f"No models configured for guild {guild_id}")
            await interaction.response.send_message("❌ No models configured! Admins: use !set-model.", ephemeral=True)
            return
        
        # Create model selection view
        view = ModelSelectionView(self, valid_models, period, shift, role, gross_revenue, compensation_type, hours_worked)
        await interaction.response.edit_message(content="Select models (optional, you can select multiple):", view=view)

    async def preview_calculation(self, interaction: discord.Interaction, period: str, shift: str, role: discord.Role, 
                         gross_revenue: Decimal, selected_models: List[str], compensation_type: str, hours_worked: Decimal):
        """Preview calculation and show confirmation options"""
        
        guild_id = str(interaction.guild_id)
        logger.info(f"guild_id: {guild_id}")
        
        # Get role percentage from configuration
        role_data = await file_handlers.load_json(settings.COMMISSION_SETTINGS_FILE, settings.DEFAULT_COMMISSION_SETTINGS)
        
        # Check if guild_id exists in role_data
        if guild_id not in role_data:
            logger.error(f"Guild ID {guild_id} not found in role_data")
            await interaction.edit_original_response(content="Guild configuration not found. Please contact an administrator.")
            return
        
        guild_config = role_data[guild_id]
        
        # Check if role exists in the guild's roles configuration
        if str(role.id) not in guild_config.get("roles", {}):
            logger.error(f"Role ID {role.id} not found in guild {guild_id} configuration")
            await interaction.edit_original_response(content="Role configuration not found. Please contact an administrator.")
            return
        
        role_config = guild_config["roles"][str(role.id)]
        percentage = Decimal(str(role_config.get("commission_percentage", 0)))
        
        # Check if the user has an override
        user_config = guild_config.get("users", {}).get(str(interaction.user.id), {})
        if user_config.get("override_role", False):
            percentage = Decimal(str(user_config.get("commission_percentage", percentage)))
        
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
        
        hourly_rate = 0.0
        hours = hours_worked  

        # Calculate earnings based on compensation type
        if compensation_type == "commission":
            results = calculations.calculate_earnings(
                gross_revenue,
                percentage,
                bonus_rule_objects
            )
        elif compensation_type == "hourly":
            # Calculate hourly earnings
            hourly_rate = Decimal(str(role_config.get("hourly_rate", 0))) if role_config.get("hourly_rate") else 0
            if user_config.get("override_role", False):
                hourly_rate = Decimal(str(user_config.get("hourly_rate", hourly_rate)))
            
            results = calculations.calculate_hourly_earnings(
                gross_revenue,
                hours, # example hours
                hourly_rate,
                bonus_rule_objects
            )
        elif compensation_type == "both":
            # Calculate both commission and hourly earnings
            hourly_rate = Decimal(str(role_config.get("hourly_rate", 0))) if role_config.get("hourly_rate") else 0
            if user_config.get("override_role", False):
                hourly_rate = Decimal(str(user_config.get("hourly_rate", hourly_rate)))
            
            results = calculations.calculate_combined_earnings(
                gross_revenue,
                percentage,
                hours,
                hourly_rate,
                bonus_rule_objects
            )
        
        # Log calculation preview
        logger.info(f"Calculation preview for {interaction.user.name}: Gross=${results['gross_revenue']}, Net=${results['net_revenue']}, Total Cut=${results['total_cut']}")
        
        # Process models
        models_list = ", ".join(selected_models) if selected_models else ""
        
        # Create embed for preview
        embed = discord.Embed(title="📊 Earnings Calculation (PREVIEW)", color=0x009933)
        current_date = datetime.now().strftime(settings.DATE_FORMAT)
        sender = interaction.user.mention
        
        # Build fields dynamically based on compensation type
        fields = []
        
        # Compensation field
        compensation_value = {
            "commission": f"{percentage:.2f}%",
            "hourly": f"${hourly_rate:,.2f}/h",
            "both": f"{percentage:.2f}% + ${hourly_rate:,.2f}/h"
        }[compensation_type]
        
        # Common fields
        fields.extend([
            ("📅 Date", current_date, True),
            ("✍ Sender", sender, True),
            ("💸 Compensation", compensation_value, True),
        ])

        # Hours Worked (only show if not commission)
        if compensation_type != "commission":
            fields.append(("⏰ Hours Worked", f"{hours_worked:.2f}h", True))

        fields.extend([
            ("📥 Shift", shift, True),
            ("🎯 Role", role.name, True),
            ("⌛ Period", period, True),
            ("💰 Gross Revenue", f"${float(results['gross_revenue']):,.2f}", True),
        ])
        
        # Net Revenue (only show if not hourly)
        if compensation_type != "hourly":
            fields.append(("💵 Net Revenue", f"${float(results['net_revenue']):,.2f} (80%)", True))
        
        # Remaining fields
        fields.extend([
            ("🎁 Bonus", f"${float(results['bonus']):,.2f}", True),
            ("💼 Employee Cut", f"${float(results['employee_cut']):,.2f}", True),
            ("💰 Total Cut", f"${float(results['total_cut']):,.2f}", True),
            (" ", "" if results.get("compensation_type") == "hourly" else "", True),
            ("🎭 Models", models_list, False)
        ])
        
        # Store compensation type for finalization
        results["compensation_type"] = compensation_type
        # Add fields to embed
        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)
        
        # Add compensation result to results dictionary
        results["compensation"] = {
            "commission": f"{percentage:.2f}%",
            "hourly": f"${hourly_rate:,.2f}/h",
            "both": f"{percentage:.2f}% + ${hourly_rate:,.2f}/h"
        }[compensation_type]
        
        # Only add hours worked if using hourly or both
        if compensation_type in ["hourly", "both"]:
            results["hours_worked"] = f"{hours:.2f}h"
        
        results["date"] = current_date
        results["sender"] = sender
        results["shift"] = shift
        results["role"] = role.name
        results["period"] = period
        results["gross_revenue"] = f"${float(results['gross_revenue']):,.2f}"
        
        # Only add net revenue if using commission or both
        if compensation_type in ["commission", "both"]:
            results["net_revenue"] = f"${float(results['net_revenue']):,.2f} (80%)"
        
        results["bonus"] = f"${float(results['bonus']):,.2f}"
        results["employee_cut"] = f"${float(results['employee_cut']):,.2f}"
        results["total_cut"] = f"${float(results['total_cut']):,.2f}"
        results["models"] = models_list
        
        # Create confirmation view
        view = ConfirmationView(
            self, 
            results
        )
        
        await interaction.edit_original_response(
            content="Please review your calculation and confirm:", 
            embed=embed, 
            view=view
        )

    async def finalize_calculation(self, interaction: discord.Interaction, results: Dict):
        """Final step: Save and display results to everyone"""
        guild_id = str(interaction.guild_id)
        
        # Save earnings data
        sender = results["sender"]
        current_date = results["date"]
        
        # Process models
        models_list = results["models"]
        
        # Load earnings data
        earnings_data = await file_handlers.load_json(settings.EARNINGS_FILE, settings.DEFAULT_EARNINGS)
        if sender not in earnings_data:
            earnings_data[sender] = []
        
        # Add new entry - handle potential missing hours_worked key
        hours_worked = 0.0
        if "hours_worked" in results:
            hours_worked = float(results["hours_worked"].replace('h', ''))
        
        # Add new entry
        new_entry = {
            "date": results["date"],
            "total_cut": float(results["total_cut"].replace('$', '').replace(',', '')),
            "gross_revenue": float(results["gross_revenue"].replace('$', '').replace(',', '')),
            "period": results["period"].lower(),
            "shift": results["shift"].lower(),
            "role": results["role"],
            "models": models_list,
            "hours_worked": hours_worked
        }
        
        earnings_data[sender].append(new_entry)
        
        # Log final calculation
        hours_worked_text = f", Hours Worked={results.get('hours_worked', 'N/A')}" if "hours_worked" in results else ""
        logger.info(f"Final calculation for {interaction.user.name} ({interaction.user.id}): Gross=${results['gross_revenue']}, Total Cut=${results['total_cut']}, Period={results['period']}, Shift={results['shift']}, Role={results['role']}{hours_worked_text}")
        
        # Save updated earnings data
        success = await file_handlers.save_json(settings.EARNINGS_FILE, earnings_data)
        if not success:
            logger.error(f"Failed to save earnings data for {sender}")
            await interaction.followup.send("⚠ Calculation failed to save data. Please try again.", ephemeral=True)
            return
        
        # Check if average display is enabled
        display_settings = await file_handlers.load_json(settings.DISPLAY_SETTINGS_FILE, settings.DEFAULT_DISPLAY_SETTINGS)
        show_average = display_settings.get(guild_id, {}).get("show_average", False)
        
        # Create embed for public announcement
        embed = discord.Embed(title="📊 Earnings Calculation", color=0x009933)
        
        # Calculate performance comparison if enabled
        performance_text = ""
        if show_average:
            try:
                period = results["period"].lower()
                all_entries = [e for e in earnings_data[sender] if e["period"] == period]
                if len(all_entries) > 1:  # Current entry is already added
                    avg_gross = sum(e["gross_revenue"] for e in all_entries[:-1]) / len(all_entries[:-1])
                    current_gross = float(results["gross_revenue"].replace('$', '').replace(',', ''))
                    performance = (current_gross / avg_gross) * 100 - 100
                    performance_text = f" (↑ {performance:.1f}% above average)" if performance > 0 else f" (↓ {abs(performance):.1f}% below average)"
                else:
                    performance_text = " (First entry for this period type)"
            except Exception as e:
                logger.error(f"Performance calculation error: {str(e)}")
                performance_text = " (Historical data unavailable)"

        fields = []
        
        # Common fields
        fields.extend([
            ("📅 Date", results.get("date", "N/A"), True),
            ("✍ Sender", results.get("sender", "N/A"), True),
            ("💸 Compensation", results.get("compensation", "N/A"), True),
        ])

        # Hours Worked (only show if not commission)
        if results.get("compensation_type") != "commission":
            fields.append(("⏰ Hours Worked", results.get("hours_worked", "N/A"), True))

        fields.extend([
            ("📥 Shift", results.get("shift", "N/A"), True),
            ("🎯 Role", results.get("role", "N/A"), True),
            ("⌛ Period", results.get("period", "N/A"), True),
            ("💰 Gross Revenue", f"{results.get('gross_revenue', 'N/A')}{performance_text}", True),
        ])
        
        # Net Revenue (only show if not hourly)
        if results.get("compensation_type") != "hourly":
            fields.append(("💵 Net Revenue", results.get("net_revenue", "N/A"), True))
        
        # Remaining fields
        fields.extend([
            ("🎁 Bonus", results.get("bonus", "N/A"), True),
            ("💼 Employee Cut", results.get("employee_cut", "N/A"), True),
            ("💰 Total Cut", results.get("total_cut", "N/A"), True),
            (" ", "" if results.get("compensation_type") == "hourly" else "", True),
            ("🎭 Models", results.get("models", "N/A"), False)
        ])
        
        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)
        
        # Send the final result to everyone
        await interaction.channel.send(embed=embed)
        
        # Confirm to the user
        await interaction.response.edit_message(
            content="✅ Calculation confirmed and posted! Check the channel for results.",
            embed=None,
            view=None
        )

    # Admin command
    @app_commands.command(
        name="view-earnings-admin-table",
        description="Admin command to view earnings for a specified user"
    )
    @app_commands.describe(
        user="The user whose earnings you want to view",
        entries="Number of entries to return (max 50)",
        export="Export format (csv, txt, or none)"
    )
    @app_commands.choices(
        export=[
            app_commands.Choice(name="Text File", value="txt"),
            app_commands.Choice(name="CSV File", value="csv")
        ]
    )
    @app_commands.default_permissions(administrator=True)
    async def view_earnings_admin(
        self,
        interaction: discord.Interaction,
        user: discord.User,
        entries: Optional[int] = 50,
        export: Optional[str] = "none"
    ):
        """Admin command to view earnings for a specified user"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need administrator permissions to use this command.", ephemeral=True)
            return

        entries = min(max(entries, 1), 50)
        earnings_data = await file_handlers.load_json(settings.EARNINGS_FILE, settings.DEFAULT_EARNINGS)
        user_earnings = earnings_data.get(user.mention, [])[::-1][:entries]
        user_earnings = sorted(user_earnings, key=lambda x: x['date'], reverse=True)[:entries]

        if not user_earnings:
            await interaction.response.send_message(f"❌ No earnings data found for {user.mention}.", ephemeral=True)
            return

        embed = discord.Embed(title=f"📊 Earnings for {user.display_name} ({len(user_earnings)} entries)", color=0x009933)
        total_gross = 0
        total_cut_sum = 0
        
        table_header = "```\n  # |   Date    |   Role    |  Gross  |  Total   \n----|------------|-----------|---------|--------\n"
        table_rows = []
        
        for index, entry in enumerate(user_earnings, start=1):
            gross_revenue = float(entry['gross_revenue'])
            total_cut = float(entry['total_cut'])
            total_gross += gross_revenue
            total_cut_sum += total_cut
            table_rows.append(f"{index:3} | {entry['date']:10} | {entry['role'].capitalize():<9} | {gross_revenue:7.2f} | {total_cut:6.2f}\n")

        current_chunk = table_header
        for row in table_rows:
            if len(current_chunk) + len(row) + 3 > 1024:
                embed.add_field(name="", value=current_chunk + "```", inline=False)
                current_chunk = "```\n"
            current_chunk += row
        
        if current_chunk != table_header:
            embed.add_field(name="", value=current_chunk + "```", inline=False)
        
        embed.add_field(name="Total Gross", value=f"```\n{total_gross:.2f}\n```", inline=True)
        embed.add_field(name="Total Cut", value=f"```\n{total_cut_sum:.2f}\n```", inline=True)

        if export != "none":
            file_data = ""
            file_name = f"earnings_{user.name}_{datetime.now().strftime('%Y%m%d')}"  # Fixed
            
            if export == "csv":
                file_data = "Index,Date,Role,Gross,Total Cut\n"
                for index, entry in enumerate(user_earnings, start=1):
                    file_data += f"{index},{entry['date']},{entry['role']},{entry['gross_revenue']},{entry['total_cut']}\n"
                file_name += ".csv"
            else:
                file_data = f"Earnings for {user.display_name} - Generated on {datetime.now().strftime('%Y-%m-%d')}\n\n"  # Fixed
                file_data += "Index | Date       | Role      | Gross    | Total Cut\n--------------------------------------------------\n"
                for index, entry in enumerate(user_earnings, start=1):
                    file_data += f"{index:5} | {entry['date']:10} | {entry['role']:<9} | {float(entry['gross_revenue']):8.2f} | {float(entry['total_cut']):9.2f}\n"
                file_data += f"\nTotal Gross: {total_gross:.2f}\nTotal Cut:   {total_cut_sum:.2f}\n"
                file_name += ".txt"
            
            file = discord.File(io.BytesIO(file_data.encode('utf-8')), filename=file_name)
            await interaction.response.send_message(embed=embed, file=file)
        else:
            await interaction.response.send_message(embed=embed)

    # Modified command implementation
    @app_commands.command(
        name="view-earnings",
        description="View your earnings with various export options"
    )
    @app_commands.describe(
        entries=f"Number of entries to return (max {MAX_ENTRIES})",
        export="Export format"
    )
    @app_commands.choices(
        export=[
            app_commands.Choice(name="None", value="none"),
            app_commands.Choice(name="Text File", value="txt"),
            app_commands.Choice(name="CSV", value="csv"),
            app_commands.Choice(name="JSON", value="json"),
            app_commands.Choice(name="Excel", value="xlsx"),
            app_commands.Choice(name="PDF", value="pdf"),
            app_commands.Choice(name="PNG Chart", value="png"),
            app_commands.Choice(name="ZIP Archive", value="zip")
        ]
    )
    async def view_earnings(
        self,
        interaction: discord.Interaction,
        entries: Optional[int] = 50,
        export: Optional[str] = "none"
    ):
        """Command for users to view their own earnings"""
        try:
            # Defer response for large exports
            await interaction.response.defer(ephemeral=export != "none")
            
            # Validate entries
            entries = min(max(entries, 1), MAX_ENTRIES)
            
            # Load data
            earnings_data = await file_handlers.load_json(settings.EARNINGS_FILE, settings.DEFAULT_EARNINGS)
            user_earnings = sorted(
                earnings_data.get(interaction.user.mention, []),
                key=lambda x: x['date'],
                reverse=True
            )[:entries]
            
            if not user_earnings:
                await interaction.followup.send(f"❌ No earnings data found.", ephemeral=True)
                return
            
            # Generate embed
            embed = discord.Embed(
                title=f"📊 Earnings Summary ({len(user_earnings)} entries)",
                color=0x009933
            )
            
            # Add totals
            total_gross = sum(float(entry['gross_revenue']) for entry in user_earnings)
            total_cut = sum(float(entry['total_cut']) for entry in user_earnings)
            embed.add_field(name="Total Gross", value=f"${total_gross:.2f}", inline=True)
            embed.add_field(name="Total Cut", value=f"${total_cut:.2f}", inline=True)
            
            # Generate file if needed
            file = None
            if export != "none":
                try:
                    file = await self.generate_export_file(user_earnings, interaction.user, export)
                except Exception as e:
                    await interaction.followup.send(
                        f"❌ Failed to generate export: {str(e)}",
                        ephemeral=True
                    )
                    return
            
            # Send response
            await interaction.followup.send(
                embed=embed,
                file=file,
                ephemeral=False != "none"
            )
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )

    # User command
    @app_commands.command(
        name="view-earnings-table",
        description="View your earnings in a table format with various export options"
    )
    @app_commands.describe(
        entries="Number of entries to return (max 50)",
        export="Export format (csv, txt, or none)"
    )
    @app_commands.choices(
        export=[
            app_commands.Choice(name="Text File", value="txt"),
            app_commands.Choice(name="CSV File", value="csv")
        ]
    )
    async def view_earnings(
        self,
        interaction: discord.Interaction,
        entries: Optional[int] = 50,
        export: Optional[str] = "none"
    ):
        """Command for users to view their own earnings"""
        entries = min(max(entries, 1), 50)
        target_user = interaction.user
        earnings_data = await file_handlers.load_json(settings.EARNINGS_FILE, settings.DEFAULT_EARNINGS)
        user_earnings = earnings_data.get(target_user.mention, [])[::-1][:entries]
        user_earnings = sorted(user_earnings, key=lambda x: x['date'], reverse=True)[:entries]

        if not user_earnings:
            await interaction.response.send_message(f"❌ No earnings data found for {target_user.mention}.", ephemeral=True)
            return

        embed = discord.Embed(title=f"📊 Earnings for {target_user.display_name} ({len(user_earnings)} entries)", color=0x009933)
        total_gross = 0
        total_cut_sum = 0
        
        table_header = "```\n  # |   Date     |   Role    |  Gross   |  Total   \n----|------------|-----------|----------|--------\n"
        table_rows = []
        
        for index, entry in enumerate(user_earnings, start=1):
            gross_revenue = float(entry['gross_revenue'])
            total_cut = float(entry['total_cut'])
            total_gross += gross_revenue
            total_cut_sum += total_cut
            table_rows.append(f"{index:3} | {entry['date']:10} | {entry['role'].capitalize():<9} | {gross_revenue:8.2f} | {total_cut:6.2f}\n")

        current_chunk = table_header
        for row in table_rows:
            if len(current_chunk) + len(row) + 3 > 1024:
                embed.add_field(name="", value=current_chunk + "```", inline=False)
                current_chunk = "```\n"
            current_chunk += row
        
        if current_chunk != table_header:
            embed.add_field(name="", value=current_chunk + "```", inline=False)
        
        embed.add_field(name="Total Gross", value=f"```\n{total_gross:.2f}\n```", inline=True)
        embed.add_field(name="Total Cut", value=f"```\n{total_cut_sum:.2f}\n```", inline=True)

        if export != "none":
            file_data = ""
            file_name = f"earnings_{target_user.name}_{datetime.now().strftime('%Y%m%d')}"  # Fixed
            
            if export == "csv":
                file_data = "Index,Date,Role,Gross,Total Cut\n"
                for index, entry in enumerate(user_earnings, start=1):
                    file_data += f"{index},{entry['date']},{entry['role']},{entry['gross_revenue']},{entry['total_cut']}\n"
                file_name += ".csv"
            else:
                file_data = f"Earnings for {target_user.display_name} - Generated on {datetime.now().strftime('%Y-%m-%d')}\n\n"  # Fixed
                file_data += "Index | Date       | Role      | Gross    | Total Cut\n--------------------------------------------------\n"
                for index, entry in enumerate(user_earnings, start=1):
                    file_data += f"{index:5} | {entry['date']:10} | {entry['role']:<9} | {float(entry['gross_revenue']):8.2f} | {float(entry['total_cut']):9.2f}\n"
                file_data += f"\nTotal Gross: {total_gross:.2f}\nTotal Cut:   {total_cut_sum:.2f}\n"
                file_name += ".txt"
            
            file = discord.File(io.BytesIO(file_data.encode('utf-8')), filename=file_name)
            await interaction.response.send_message(embed=embed, file=file)
        else:
            await interaction.response.send_message(embed=embed)

# View classes remain unchanged
class PeriodSelectionView(ui.View):
    def __init__(self, cog, periods, compensation_type, hours_worked):
        super().__init__(timeout=180)
        self.cog = cog
        self.compensation_type = compensation_type
        self.hours_worked = hours_worked
        
        # Add a button for each period (limit to 25 due to Discord UI limitations)
        for period in periods[:25]:
            button = ui.Button(label=period, style=discord.ButtonStyle.primary)
            button.callback = lambda i, p=period: self.on_period_selected(i, p)
            self.add_item(button)
    
    async def on_period_selected(self, interaction: discord.Interaction, period: str):
        await self.cog.show_shift_selection(interaction, period, self.compensation_type, self.hours_worked)

class ShiftSelectionView(ui.View):
    def __init__(self, cog, shifts, period, compensation_type, hours_worked):
        super().__init__(timeout=180)
        self.cog = cog
        self.period = period
        self.compensation_type = compensation_type
        self.hours_worked = hours_worked
        
        # Add a button for each shift
        for shift in shifts[:25]:
            button = ui.Button(label=shift, style=discord.ButtonStyle.primary)
            button.callback = lambda i, s=shift: self.on_shift_selected(i, s)
            self.add_item(button)
    
    async def on_shift_selected(self, interaction: discord.Interaction, shift: str):
        await self.cog.show_role_selection(interaction, self.period, shift, self.compensation_type, self.hours_worked)

class RoleSelectionView(ui.View):
    def __init__(self, cog, roles, period, shift, compensation_type, hours_worked):
        super().__init__(timeout=180)
        self.cog = cog
        self.period = period
        self.shift = shift
        self.compensation_type = compensation_type
        self.hours_worked = hours_worked
        
        # Add a button for each role
        for role in roles[:25]:
            button = ui.Button(label=role.name, style=discord.ButtonStyle.primary)
            button.callback = lambda i, r=role: self.on_role_selected(i, r)
            self.add_item(button)
    
    async def on_role_selected(self, interaction: discord.Interaction, role: discord.Role):
        await self.cog.show_revenue_input(interaction, self.period, self.shift, role, self.compensation_type, self.hours_worked)

class RevenueInputModal(ui.Modal, title="Enter Gross Revenue"):
    def __init__(self, cog, period, shift, role, compensation_type, hours_worked):
        super().__init__()
        self.cog = cog
        self.period = period
        self.shift = shift
        self.role = role
        self.compensation_type = compensation_type
        self.hours_worked = hours_worked
        
        self.revenue_input = ui.TextInput(
            label="Gross Revenue (e.g. 1269.69)",
            placeholder="Enter amount...",
            required=True
        )
        self.add_item(self.revenue_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        # Parse revenue input
        revenue_str = self.revenue_input.value
        gross_revenue = validators.parse_money(revenue_str)
        
        if gross_revenue is None:
            logger.warning(f"User {interaction.user.name} ({interaction.user.id}) entered invalid revenue format: {revenue_str}")
            await interaction.response.send_message("❌ Invalid revenue format. Please use a valid number.", ephemeral=True)
            return
        
        await self.cog.show_model_selection(interaction, self.period, self.shift, self.role, gross_revenue, self.compensation_type, self.hours_worked)

class ModelSelectionView(ui.View):
    def __init__(self, cog, models, period, shift, role, gross_revenue, compensation_type, hours_worked):
        super().__init__(timeout=180)
        self.cog = cog
        self.period = period
        self.shift = shift
        self.role = role
        self.gross_revenue = gross_revenue
        self.compensation_type = compensation_type
        self.selected_models = []
        self.all_models = models
        self.current_page = 0
        self.models_per_page = 15  # Show 15 model buttons per page
        self.hours_worked = hours_worked
        
        # Calculate total pages
        self.total_pages = max(1, (len(self.all_models) + self.models_per_page - 1) // self.models_per_page)
        
        # Update the view with current page buttons
        self.update_view()
    
    def update_view(self):
        # Clear current buttons
        self.clear_items()
        
        # Calculate page range
        start_idx = self.current_page * self.models_per_page
        end_idx = min(start_idx + self.models_per_page, len(self.all_models))
        current_page_models = self.all_models[start_idx:end_idx]
        
        # Add buttons for current page models
        for model in current_page_models:
            button = ui.Button(
                label=model, 
                style=discord.ButtonStyle.primary if model in self.selected_models else discord.ButtonStyle.secondary,
                row=min(3, (current_page_models.index(model) // 5))  # Organize into rows of 5 buttons
            )
            button.callback = lambda i, m=model: self.on_model_toggled(i, m)
            self.add_item(button)
        
        if self.total_pages > 1:
            # Previous page button
            prev_button = ui.Button(
                label="◀️ Previous", 
                style=discord.ButtonStyle.secondary,
                disabled=(self.current_page == 0),
                row=4
            )
            prev_button.callback = self.previous_page
            self.add_item(prev_button)
            
            # Page indicator button (non-functional, just shows current page)
            page_indicator = ui.Button(
                label=f"Page {self.current_page + 1}/{self.total_pages}",
                style=discord.ButtonStyle.secondary,
                disabled=True,
                row=4
            )
            self.add_item(page_indicator)
            
            # Next page button
            next_button = ui.Button(
                label="Next ▶️", 
                style=discord.ButtonStyle.secondary,
                disabled=(self.current_page >= self.total_pages - 1),
                row=4
            )
            next_button.callback = self.next_page
            self.add_item(next_button)
        
        continue_button = ui.Button(label="Continue", style=discord.ButtonStyle.success, row=4)
        continue_button.callback = self.on_finish
        self.add_item(continue_button)
        
        clear_button = ui.Button(label="Clear Selections", style=discord.ButtonStyle.danger, row=4)
        clear_button.callback = self.on_clear
        self.add_item(clear_button)
    
    async def previous_page(self, interaction: discord.Interaction):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_view()
            
            selected_text = ", ".join(self.selected_models) if self.selected_models else "None"
            await interaction.response.edit_message(
                content=f"Select models (optional, you can select multiple):\nSelected: {selected_text}\nPage {self.current_page + 1}/{self.total_pages}",
                view=self
            )
    
    async def next_page(self, interaction: discord.Interaction):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_view()
            
            selected_text = ", ".join(self.selected_models) if self.selected_models else "None"
            await interaction.response.edit_message(
                content=f"Select models (optional, you can select multiple):\nSelected: {selected_text}\nPage {self.current_page + 1}/{self.total_pages}",
                view=self
            )
    
    async def on_model_toggled(self, interaction: discord.Interaction, model: str):
        # Toggle model selection
        if model in self.selected_models:
            self.selected_models.remove(model)
        else:
            self.selected_models.append(model)
        
        # Update the view to reflect changes
        self.update_view()
        
        selected_text = ", ".join(self.selected_models) if self.selected_models else "None"
        await interaction.response.edit_message(
            content=f"Select models (optional, you can select multiple):\nSelected: {selected_text}\nPage {self.current_page + 1}/{self.total_pages}", 
            view=self
        )
    
    async def on_clear(self, interaction: discord.Interaction):
        # Clear all selections
        self.selected_models = []
        
        # Update the view to reflect changes
        self.update_view()
        
        await interaction.response.edit_message(
            content=f"Select models (optional, you can select multiple):\nSelected: None\nPage {self.current_page + 1}/{self.total_pages}", 
            view=self
        )
    
    async def on_finish(self, interaction: discord.Interaction):
        await interaction.response.defer()
        # Instead of finalizing, show preview with confirmation options
        await self.cog.preview_calculation(
            interaction, 
            self.period, 
            self.shift, 
            self.role, 
            self.gross_revenue, 
            self.selected_models,
            self.compensation_type,
            self.hours_worked
        )

class ConfirmationView(ui.View):
    def __init__(self, cog, results):
        super().__init__(timeout=180)
        self.cog = cog
        self.results = results

        # Add confirm button
        confirm_button = ui.Button(label="Confirm & Post", style=discord.ButtonStyle.success)
        confirm_button.callback = self.on_confirm
        self.add_item(confirm_button)
        
        # Add cancel button
        cancel_button = ui.Button(label="Cancel", style=discord.ButtonStyle.danger)
        cancel_button.callback = self.on_cancel
        self.add_item(cancel_button)
    
    async def on_confirm(self, interaction: discord.Interaction):
        # Log confirmation decision
        logger.info(f"User {interaction.user.name} ({interaction.user.id}) confirmed calculation")
        
        # Finalize and post the calculation to everyone
        await self.cog.finalize_calculation(
            interaction,
            self.results,
        )
    
    async def on_cancel(self, interaction: discord.Interaction):
        # Log cancellation
        logger.info(f"User {interaction.user.name} ({interaction.user.id}) cancelled calculation")
        
        # Just cancel the workflow
        await interaction.response.edit_message(content="Calculation cancelled.", embed=None, view=None)

async def setup(bot):
    await bot.add_cog(CalculatorSlashCommands(bot))