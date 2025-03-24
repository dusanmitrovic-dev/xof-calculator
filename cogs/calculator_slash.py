import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import discord
import asyncio
import zipfile
import logging
import random
import time
import json
import io
import re
import os

from reportlab.platypus import PageBreak, SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from openpyxl.chart import LineChart, BarChart, PieChart, Reference
from utils import file_handlers, validators, calculations
from reportlab.lib.styles import getSampleStyleSheet
from openpyxl.chart.label import DataLabelList
from typing import Union, Optional, List, Dict
from reportlab.lib.pagesizes import letter
from babel.numbers import format_currency
from discord import ui, app_commands
from discord.ui import Select, View, Button
from discord.ext import commands
from reportlab.lib import colors
from utils import file_handlers
from utils import generator_uuid
from datetime import datetime
from decimal import Decimal, InvalidOperation
from config import settings
from pathlib import Path

SUPPORTED_EXPORTS = ["none", "txt", "csv", "json", "xlsx", "pdf", "png", "zip"]
# All available formats
# ALL_ZIP_FORMATS = ['csv', 'json', 'xlsx', 'pdf', 'png', 'txt', 'html', 'markdown', 'svg'] # TODO: remove
ALL_ZIP_FORMATS = ['csv', 'json', 'xlsx', 'pdf', 'png', 'txt', 'html', 'markdown'] # TODO: Option to set default zip exports in settings
MAX_ENTRIES = 5000000

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

    async def get_ephemeral_setting(self, guild_id):
        file_path = settings.get_guild_file(guild_id, settings.DISPLAY_SETTINGS_FILE)  # NOTE: Added
        # display_settings = await file_handlers.load_json(settings.DISPLAY_SETTINGS_FILE, settings.DEFAULT_DISPLAY_SETTINGS) # TODO: remove
        display_settings = await file_handlers.load_json(file_path, {
                "ephemeral_responses": True,
                "show_average": True,
                "agency_name": "Agency",
                "show_ids": True,
                "bot_name": "Shift Calculator"
        })
        # guild_settings = display_settings.get(str(guild_id), settings.DEFAULT_DISPLAY_SETTINGS['defaults']) # TODO: remove
        # guild_settings = display_settings.get(str(guild_id), settings.DEFAULT_DISPLAY_SETTINGS) # TODO: remove
        guild_settings = display_settings
        return guild_settings.get('ephemeral_responses', 
            settings.DEFAULT_DISPLAY_SETTINGS['ephemeral_responses'])
            # settings.DEFAULT_DISPLAY_SETTINGS['defaults']['ephemeral_responses']) # TODO: remove
    
    async def get_average_setting(self, guild_id):
        guild_settings_file = settings.get_guild_display_path(guild_id)
        guild_settings = await file_handlers.load_json(guild_settings_file, {
            "ephemeral_responses": True,
            "show_average": True,
            "agency_name": "Agency",
            "show_ids": True,
            "bot_name": "Shift Calculator"
        })
        return guild_settings.get("show_average", True)

    async def get_agency_name(self, guild_id):
        file_path = settings.get_guild_display_path(guild_id)
        settings_data = await file_handlers.load_json(file_path, {
            "ephemeral_responses": True,
            "show_average": True,
            "agency_name": "Agency",
            "show_ids": True,
            "bot_name": "Shift Calculator"
        })
        return settings_data.get("agency_name", "Agency")

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

    async def get_bot_name(self, guild_id):
        file_path = settings.get_guild_display_path(guild_id)
        settings_data = await file_handlers.load_json(file_path, {
            "ephemeral_responses": True,
            "show_average": True,
            "agency_name": "Agency",
            "show_ids": True,
            "bot_name": "Shift Calculator"
        })
        return settings_data.get("bot_name", "Shift Calculator")

    async def generate_export_file(self, user_earnings, interaction, user, export_format, zip_formats=None, all_data=False):
        """
        Generate export file based on format choice with improved visualizations.
        
        Args:
            user_earnings: List of dictionaries containing earnings data
            user: User object with display_name attribute
            export_format: String indicating the desired export format
            zip_formats: List of formats to include when export_format is "zip" (default: all available formats)
                
        Returns:
            discord.File: File object ready for Discord attachment
        """
        if all_data:
            base_name = f"full_earnings_report_{datetime.now().strftime('%d_%m_%Y')}"
        else:
            sanitized_name = Path(user.display_name).stem[:32].replace(" ", "_")
            base_name = f"{sanitized_name}_earnings_{datetime.now().strftime('%d_%m_%Y')}"
        
        # Convert earnings to DataFrame for easier manipulation
        df = pd.DataFrame(user_earnings)
        
        # If zip_formats not specified, use all formats
        if zip_formats is None:
            zip_formats = ALL_ZIP_FORMATS
        
        buffer = io.BytesIO()
        
        if export_format == "zip":
            with zipfile.ZipFile(buffer, 'w') as zip_file:
                for fmt in zip_formats:
                    fmt_buffer = await self._generate_format_buffer(df, interaction, user, fmt, user_earnings, all_data)
                    zip_file.writestr(f"{base_name}.{fmt}", fmt_buffer.getvalue())
                    fmt_buffer.close()
        else:
            # Handle single format export
            buffer = await self._generate_format_buffer(df, interaction, user, export_format, user_earnings, all_data)
        
        buffer.seek(0)
        return discord.File(buffer, filename=f"{base_name}.{export_format}")

    async def _generate_format_buffer(self, df, interaction, user, format_type, user_earnings, all_data=False):
        """
        Helper method to generate a specific format export buffer.
        
        Args:
            df: DataFrame with earnings data
            user: User object with display_name attribute
            format_type: String indicating the desired export format
            user_earnings: Original list of earnings data
            all_data: Boolean indicating if this is a full report with multiple users
            
        Returns:
            io.BytesIO: Buffer containing the exported data
        """
        buffer = io.BytesIO()
        
        try:
            if format_type == "csv":
                await self._generate_csv(df, buffer, all_data)
            elif format_type == "json":
                await self._generate_json(df, buffer, all_data)
            elif format_type == "xlsx":
                await self._generate_excel(df, buffer, all_data)
            elif format_type == "pdf":
                await self._generate_pdf(df, interaction, user, buffer, user_earnings, all_data)
            elif format_type == "png":
                await self._generate_png(df, user, buffer, user_earnings, all_data)
            # elif format_type == "svg": # TODO: remove
            #     self._generate_svg(df, user, buffer, user_earnings, all_data) # TODO: It displays User earnings instead of Full for Zip? # WARN: DOUBLE CHECK!!
            elif format_type == "html":
                await self._generate_html(df, interaction, user, buffer, user_earnings, all_data)
            elif format_type == "markdown":
                await self._generate_markdown(df, interaction, user, buffer, user_earnings, all_data)
            else:  # txt
                await self._generate_txt(df, interaction, user, buffer, user_earnings, all_data)
        except Exception as e:
            # If there's an error, write the error to the buffer
            error_msg = f"Error generating {format_type} format: {str(e)}"
            buffer.write(error_msg.encode('utf-8'))
        
        buffer.seek(0)
        return buffer

    async def _generate_csv(self, df, buffer, all_data=False): 
        """Generate CSV format export"""
        if all_data and 'display_name' in df.columns:
            df = df[['display_name', 'username', 'date', 'role', 'shift', 
                    'hours_worked', 'gross_revenue', 'total_cut']].copy()
        df.fillna('null', inplace=True)
        df.to_csv(buffer, index=False)

    async def _generate_json(self, df, buffer, all_data=False):
        """Generate JSON format export"""
            # Add user info to JSON output if needed
        if all_data and 'display_name' not in df.columns:
            df['display_name'] = ''
            df['username'] = ''
        
        json_data = df.to_json(orient='records', date_format='iso', indent=2)
        buffer.write(json_data.encode('utf-8'))

    async def _generate_excel(self, df, buffer, all_data=False):
        """Generate Excel format export with formatting."""
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            # Reorder columns if showing user data
            if all_data and 'display_name' in df.columns:
                df = df[['user', 'date', 'role', 
                        'hours_worked', 'gross_revenue', 'total_cut']]
            else:
                df = df[['date', 'role', 
                        'hours_worked', 'gross_revenue', 'total_cut']]

            if 'models' in df.columns:
                df = df.drop(columns=['models', 'shift']).copy()
                
            # Main Earnings sheet
            df.fillna('null', inplace=True)
            df.to_excel(writer, index=False, sheet_name='Earnings')
                
            # Add a summary sheet with numeric values
            total_gross = df['gross_revenue'].sum()
            total_earnings = df['total_cut'].sum()
            total_hours = df['hours_worked'].sum()
            summary = pd.DataFrame({
                'Metric': ['Total Gross Revenue', 'Total Earnings', 'Total Hours Worked'],
                'Value': [total_gross, total_earnings, total_hours]
            })
            summary.to_excel(writer, index=False, sheet_name='Summary')
            
            # Add a pivot table by role
            if 'role' in df.columns:
                pivot = pd.pivot_table(df, 
                                    values=['gross_revenue', 'total_cut', 'hours_worked'],
                                    index=['role'],
                                    aggfunc='sum')
                pivot.to_excel(writer, sheet_name='By Role')
            
            # Access the workbook and sheets for formatting
            workbook = writer.book
            summary_sheet = writer.sheets['Summary']
            
            # Apply number formatting to Summary sheet
            for row in summary_sheet.iter_rows(min_row=2, max_row=3, min_col=2, max_col=2):
                for cell in row:
                    cell.number_format = '"$"#,##0.00'  # Currency format for revenue and earnings
            summary_sheet.cell(row=4, column=2).number_format = '0.0'  # Decimal format for hours
            
            # Apply styling and formatting to all sheets
            for worksheet in writer.sheets.values():
                for col in worksheet.columns:
                    max_length = 0
                    column = col[0].column_letter
                    for cell in col:
                        if cell.value is not None:
                            max_length = max(max_length, len(str(cell.value)))
                    worksheet.column_dimensions[column].width = max_length + 2

    async def _generate_pdf(self, df, interaction, user, buffer, user_earnings, all_data=False):
        """Generate complete PDF report with aggregated charts and individual breakdowns"""
        try:
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            elements = []
            styles = getSampleStyleSheet()
            PAGE_WIDTH = 468  # Standard letter width in points

            # ======================
            # 1. Title Section
            # ======================
            title_style = styles["Title"]
            agency_name = await self.get_agency_name(interaction.guild.id)
            report_title = f"{agency_name} Full Earnings Report" if all_data else f"{agency_name} Earnings Report for {user.display_name}"
            elements.append(Paragraph(report_title, title_style))
            elements.append(Spacer(1, 12))

            # ======================
            # 2. Summary Section
            # ======================
            elements.append(Paragraph("Summary", styles["Heading2"]))
            elements.append(Spacer(1, 6))

            summary_data = [
                ["Metric", "Value"],
                ["Total Gross Revenue", f"${df['gross_revenue'].sum():.2f}"],
                ["Total Earnings", f"${df['total_cut'].sum():.2f}"],
                ["Total Hours Worked", f"{df['hours_worked'].sum():.1f}"],
            ]
            
            if all_data:
                summary_data.insert(1, ["Total Users", f"{len(df['user_id'].unique())}"])
            
            # Full-width summary table
            summary_table = Table(summary_data, colWidths=[PAGE_WIDTH*0.75, PAGE_WIDTH*0.25])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.grey),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0,0), (-1,0), 12),
                ('BACKGROUND', (0,1), (-1,-1), colors.beige),
                ('GRID', (0,0), (-1,-1), 1, colors.black),
                ('FONTSIZE', (0,1), (-1,-1), 9),  # More readable body text
                ('PADDING', (0,0), (-1,-1), 3),    # Cell padding
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), # Vertical alignment
                # For summary table add:
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.whitesmoke, colors.beige])
            ]))
            elements.append(summary_table)
            elements.append(Spacer(1, 24))

            # ======================
            # 3. Detailed Table (Original Version)
            # ======================
            elements.append(Paragraph("Detailed Earnings", styles["Heading2"]))
            elements.append(Spacer(1, 12))
            headers = ["#", "User", "Date", "Role", "Shift", "Hours", "Gross Revenue", "Earnings"] if all_data else ["#", "Date", "Role", "Shift", "Hours", "Gross Revenue", "Earnings"]
            data = [headers]
            
            # col_widths = [30, 120, 80, 60, 50, 70, 70] if all_data else [30, 80, 60, 50, 70, 70]
            
            for i, entry in enumerate(user_earnings, 1):
                row = [
                    str(i),
                    f"{entry.get('display_name', '')} (@{entry.get('username', '')})",
                    entry['date'],
                    entry['role'],
                    entry['shift'].capitalize(),
                    f"{float(entry['hours_worked']):.1f}",
                    f"${float(entry['gross_revenue']):.2f}",
                    f"{format_currency(float(entry['total_cut']), 'USD', locale='en_US')}"
                ] if all_data else [
                    str(i),
                    entry['date'],
                    entry['role'],
                    entry['shift'].capitalize(),
                    f"{float(entry['hours_worked']):.1f}",
                    f"${float(entry['gross_revenue']):.2f}",
                    f"${float(entry['total_cut']):.2f}"
                ]
                data.append(row)

            # Original table formatting
            detail_table = Table(data, colWidths=([40] + [None]*len(headers[1:])) if all_data else None)
            detail_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.grey),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0,0), (-1,0), 12),
                ('BACKGROUND', (0,1), (-1,-1), colors.beige),
                ('GRID', (0,0), (-1,-1), 1, colors.black),
                ('ALIGN', (4,1), (-1,-1), 'CENTER'),
                ('FONTSIZE', (0,1), (-1,-1), 9),
                ('FONTSIZE', (0,1), (-1,-1), 9),  # More readable body text
                ('PADDING', (0,0), (-1,-1), 3),    # Cell padding
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), # Vertical alignment
            ]))
            elements.append(detail_table)
            elements.append(Spacer(1, 24))

            # ======================
            # 4. Charts Section
            # ======================
            elements.append(PageBreak())
            elements.append(Paragraph("Earnings Analysis", styles["Heading2"]))
            elements.append(Spacer(1, 12))

            if all_data:
                processed_df = pd.DataFrame(user_earnings)
                processed_df['user_id'] = processed_df['user_id'].astype(str)
                processed_df['user_id'] = processed_df['user_id'].str.extract(r'(\d+)').fillna('0').astype(np.int64)
                processed_df['date'] = pd.to_datetime(processed_df['date'], dayfirst=True)
                processed_df['member'] = processed_df['user_id'].apply(
                    lambda x: interaction.guild.get_member(int(x)) if interaction and x != 0 else None
                )

                # 4a. Aggregated Timeline Chart
                chart_buffer1 = io.BytesIO()
                with plt.rc_context():
                    fig1, ax1 = plt.subplots(figsize=(7, 3.5))
                    agg_df = processed_df.groupby('date').agg({
                        'gross_revenue': 'sum',
                        'total_cut': 'sum'
                    }).reset_index()
                    
                    ax1.plot(agg_df['date'], agg_df['gross_revenue'], 'o-', label='Total Gross')
                    ax1.plot(agg_df['date'], agg_df['total_cut'], 'o-', label='Total Earnings')
                    ax1.set_title("Aggregated Earnings Timeline")
                    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m/%y'))
                    plt.xticks(rotation=45)
                    ax1.legend()
                    ax1.grid(True, linestyle='--', alpha=0.7)
                    plt.tight_layout()
                    plt.savefig(chart_buffer1, format='png', dpi=150, bbox_inches='tight')
                    plt.close(fig1)
                
                # 4b. User Comparison Chart with internal legend
                chart_buffer2 = io.BytesIO()
                with plt.rc_context():
                    fig2, ax2 = plt.subplots(figsize=(7, 4))  # Slightly taller for legend
                    valid_members = processed_df[processed_df['member'].notnull()]
                    sorted_members = sorted(
                        valid_members['member'].unique(),
                        key=lambda m: m.display_name.lower()
                    )
                    
                    for member in sorted_members:
                        group = valid_members[valid_members['member'] == member]
                        group = group.sort_values('date')
                        ax2.plot(group['date'], group['gross_revenue'], 'o-', label=f"{member.display_name} (@{member.name})")
                    
                    ax2.set_title("Users Revenue Comparison")
                    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m/%y'))
                    plt.xticks(rotation=45)
                    # Legend inside plot
                    ax2.legend(loc='upper center', bbox_to_anchor=(0.5, -0.45),
                        ncol=3, frameon=True, shadow=True)
                    ax2.grid(True, linestyle='--', alpha=0.7)
                    plt.tight_layout()
                    plt.savefig(chart_buffer2, format='png', dpi=150, bbox_inches='tight')
                    plt.close(fig2)

                elements.append(Image(chart_buffer1, width=450, height=200))
                elements.append(Spacer(1, 12))
                elements.append(Image(chart_buffer2, width=450, height=250))
            
            else:
                chart_buffer = io.BytesIO()
                with plt.rc_context():
                    fig, ax = plt.subplots(figsize=(7, 4))
                    dates = [datetime.strptime(e['date'], '%d/%m/%Y') for e in user_earnings]
                    gross = [float(e['gross_revenue']) for e in user_earnings]
                    earnings = [float(e['total_cut']) for e in user_earnings]
                    ax.plot(dates, gross, 'o-', label='Gross Revenue')
                    ax.plot(dates, earnings, 'o-', label='Earnings')
                    ax.set_title(f'{user.display_name}\'s Earnings')
                    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m/%y'))
                    plt.xticks(rotation=45)
                    ax.legend()
                    ax.grid(True, linestyle='--', alpha=0.7)
                    plt.tight_layout()
                    plt.savefig(chart_buffer, format='png', dpi=150, bbox_inches='tight')
                    plt.close(fig)
                
                elements.append(Image(chart_buffer, width=450, height=250))

            # ======================
            # 5. Individual Breakdowns
            # ======================
            if all_data:
                elements.append(PageBreak())
                elements.append(Paragraph("Individual User Breakdowns", styles["Heading2"]))
                
                valid_members = [m for m in processed_df['member'].unique() if m is not None]
                
                for member in valid_members:
                    elements.append(Paragraph(f"{member.display_name} (@{member.name})", styles["Heading3"]))
                    
                    user_data = processed_df[processed_df['member'] == member]
                    dates = user_data['date'].dt.to_pydatetime()
                    gross = user_data['gross_revenue'].astype(float)
                    earnings = user_data['total_cut'].astype(float)

                    fig, ax = plt.subplots(figsize=(7, 4))
                    ax.plot(dates, gross, 'o-', label='Gross Revenue')
                    ax.plot(dates, earnings, 'o-', label='Earnings')
                    ax.set_title(f'{member.display_name}\'s Earnings')
                    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m/%y'))
                    plt.xticks(rotation=45)
                    ax.legend()
                    ax.grid(True, linestyle='--', alpha=0.7)
                    plt.tight_layout()
                    
                    user_buffer = io.BytesIO()
                    plt.savefig(user_buffer, format='png', dpi=150)
                    plt.close(fig)
                    
                    elements.append(Image(user_buffer, width=450, height=250))
                    elements.append(Spacer(1, 12))

            doc.build(elements)

        except Exception as e:
            error_buffer = io.BytesIO()
            doc = SimpleDocTemplate(error_buffer, pagesize=letter)
            elements = [
                Paragraph("Error Generating PDF", styles["Title"]),
                Spacer(1, 12),
                Paragraph(f"Failed to generate report: {str(e)}", styles["BodyText"])
            ]
            doc.build(elements)
            error_buffer.seek(0)
            buffer.write(error_buffer.read())
            buffer.seek(0)

    async def _generate_png(self, df, user, buffer, user_earnings, all_data=False):
        """Generate PNG format export"""
        try:
            with plt.rc_context():  # Isolate plot settings
                fig, ax = plt.subplots(figsize=(12, 6))
                
                # Validate and sort data
                if not user_earnings:
                    raise ValueError("No earnings data to plot")
                    
                # Sort entries by date ascending
                sorted_earnings = sorted(
                    [e for e in user_earnings if 'date' in e],
                    key=lambda x: datetime.strptime(x['date'], '%d/%m/%Y')
                )

                # Create date objects
                dates = [datetime.strptime(e['date'], '%d/%m/%Y') for e in sorted_earnings]
                
                if all_data:
                    # Group by user if showing all data
                    for user_id, group in df.groupby('user'):
                        user_dates = [datetime.strptime(d, '%d/%m/%Y') for d in group['date']]
                        ax.plot(user_dates, group['gross_revenue'], 'o-', label=user_id)
                    ax.set_title('Gross Revenue by User Over Time')
                    ax.legend(loc='upper left')
                else:
                    # Plot individual user data
                    ax.plot(dates, 
                            [float(e['gross_revenue']) for e in sorted_earnings], 
                            'b-o', label='Gross Revenue')
                    ax.plot(dates, 
                            [float(e['total_cut']) for e in sorted_earnings], 
                            'r-o', label='Earnings')
                    ax.set_title(f'Earnings for {user.display_name}')

                # Format dates with 2-digit year (e.g., 2025 → 25)
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m/%y'))  # %y for 2-digit year
                fig.autofmt_xdate(rotation=45)  # Auto-rotate and space labels
                
                # Add legend and grid
                ax.legend()
                ax.grid(True, linestyle='--', alpha=0.7)
                plt.tight_layout()
                
                # Save to buffer
                plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
                plt.close(fig)
                
        except Exception as e:
            # Create error plot as fallback
            plt.figure(figsize=(12, 6))
            plt.text(0.5, 0.5, f"Error generating plot: {str(e)}", 
                    ha='center', va='center')
            plt.savefig(buffer, format='png')
            plt.close()
            buffer.seek(0)

    # def _generate_svg(self, df, user, buffer, user_earnings, all_data=False): # TODO: remove
    #     """Generate SVG format export"""
    #     fig, ax = plt.subplots(figsize=(16, 9))

    #     if all_data:
    #         # Line chart for multiple users
    #         pivot = df.pivot_table(index='date', columns='display_name', values='total_cut', aggfunc='sum')
    #         for user in pivot.columns:
    #             ax.plot(pivot.index, pivot[user], marker='o', linestyle='-', label=user)
    #         ax.set_title('Daily Gross Revenue by User')
    #     else:
    #         # Line chart for individual user
    #         dates = [datetime.strptime(entry['date'], '%d/%m/%Y') for entry in user_earnings]
    #         ax.plot_date(dates, [float(e['gross_revenue']) for e in user_earnings], 'b-o', label='Gross Revenue')
    #         ax.plot_date(dates, [float(e['total_cut']) for e in user_earnings], 'r-o', label='Earnings')
    #         ax.set_title('Revenue & Earnings Over Time')

    #     ax.legend()
    #     ax.grid(True, linestyle='--', alpha=0.7)
    #     plt.xticks(rotation=45)
    #     plt.savefig(buffer, format='svg')
    #     plt.close(fig)

    async def _generate_html(self, df, interaction, user, buffer, user_earnings, all_data=False):
        """Generate HTML format export"""
        agency_name = await self.get_agency_name(interaction.guild.id)
        report_title = f"{agency_name} Full Earnings Report" if all_data else f"{agency_name} Earnings Report for {user.display_name}"
        user_column = ""
        
        if all_data:
            user_column = "<th>User</th>"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{report_title}</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background-color: #f4f4f4;
                    color: #333;
                    margin: 0;
                    padding: 20px;
                }}
                .header {{
                    background: #343a40;
                    color: white;
                    padding: 15px;
                    text-align: center;
                    border-radius: 5px;
                }}
                .summary, table {{
                    background: white;
                    padding: 15px;
                    margin: 20px 0;
                    border-radius: 5px;
                    box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
                }}
                .summary-item {{
                    margin: 5px 0;
                    font-size: 16px;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                }}
                th, td {{
                    padding: 12px;
                    text-align: left;
                    border-bottom: 1px solid #ddd;
                }}
                th {{
                    background: #343a40;
                    color: white;
                }}
                tr:nth-child(even) {{
                    background: #f9f9f9;
                }}
                tr:hover {{
                    background: #f1f1f1;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{report_title}</h1>
                <p>Generated on {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
            </div>
            
            <h2>Summary</h2>
            <div class="summary">
                {'<p class="summary-item"><strong>Total Users:</strong> ' + str(len(df["user_id"].unique())) + "</p>" if all_data else ""}
                <p class="summary-item"><strong>Total Gross Revenue:</strong> ${df['gross_revenue'].sum():.2f}</p>
                <p class="summary-item"><strong>Total Earnings:</strong> ${df['total_cut'].sum():.2f}</p>
                <p class="summary-item"><strong>Total Hours Worked:</strong> {df['hours_worked'].sum():.1f}</p>
            </div>
            
            <h2>Detailed Earnings</h2>
            <table>
                <tr>
                    <th>#</th>
                    {user_column}
                    <th>Date</th>
                    <th>Role</th>
                    <th>Shift</th>
                    <th>Hours</th>
                    <th>Gross Revenue</th>
                    <th>Earnings</th>
                </tr>
        """
        
        for i, entry in enumerate(user_earnings, 1):
            html_content += f"""
                <tr>
                    <td>{i}</td>
                    {"<td>" + f"{entry.get('display_name', '')} (@{entry.get('username', '')})" + "</td>" if all_data else ""}
                    <td>{entry['date']}</td>
                    <td>{entry['role']}</td>
                    <td>{entry['shift'].capitalize()}</td>
                    <td>{float(entry['hours_worked']):.1f}</td>
                    <td>${float(entry['gross_revenue']):.2f}</td>
                    <td>${float(entry['total_cut']):.2f}</td>
                </tr>
            """
        
        html_content += """
            </table>
            
            <h2>Earnings by Role</h2>
            <table>
                <tr>
                    <th>Role</th>
                    <th>Total Earnings</th>
                    <th>Hours Worked</th>
                    <th>Percentage of Total</th>
                </tr>
        """
        
        # Add role summary rows
        role_summary = df.groupby('role').agg({
            'total_cut': 'sum',
            'hours_worked': 'sum'
        }).reset_index()
        
        total_earnings = df['total_cut'].sum()
        
        for _, row in role_summary.iterrows():
            percentage = (row['total_cut'] / total_earnings) * 100
            
            html_content += f"""
                <tr>
                    <td>{row['role']}</td>
                    <td>${row['total_cut']:.2f}</td>
                    <td>{row['hours_worked']:.1f}</td>
                    <td>{percentage:.1f}%</td>
                </tr>
            """
        
        html_content += """
            </table>
        </body>
        </html>
        """
        
        buffer.write(html_content.encode('utf-8'))


    async def _generate_markdown(self, df, interaction, user, buffer, user_earnings, all_data):
        """Generate Markdown format export

        Args:
            df: DataFrame containing earnings data
            user: User object for individual reports
            buffer: Output buffer to write markdown content
            user_earnings: List of user earnings entries
            all_data: Boolean indicating if this is a full report or user-specific
        """
        agency_name = await self.get_agency_name(interaction.guild.id)
        report_title = f"{agency_name} Full Earnings Report" if all_data else f"{agency_name} Earnings Report for {user.display_name}"
        current_date = datetime.now()

        # Filter out future dates
        valid_earnings = [
            entry for entry in user_earnings 
            if datetime.strptime(entry['date'], '%d/%m/%Y') <= current_date
        ]

        valid_df = df[df['date'].apply(lambda x: datetime.strptime(x, '%d/%m/%Y') <= current_date)]

        # Markdown Content Initialization
        md_content = f"# {report_title}\n\nGenerated on {current_date.strftime('%d/%m/%Y %H:%M')}\n\n## Summary\n\n"

        if all_data:
            unique_users = valid_df['user_id'].nunique()
            md_content += f"""
* **Total Users:** {unique_users}
* **Total Gross Revenue:** ${valid_df['gross_revenue'].sum():.2f}
* **Total Earnings:** ${valid_df['total_cut'].sum():.2f}
* **Total Hours Worked:** {valid_df['hours_worked'].sum():.1f}

## Detailed Earnings

| # | User | Date | Role | Shift | Hours | Gross Revenue | Earnings |
|---|------|------|------|-------|-------|--------------|----------|
"""
        else:
            # Summary for a single user
            total_hours = sum(float(entry.get('hours_worked', 0)) for entry in valid_earnings)
            total_gross = sum(float(entry.get('gross_revenue', 0)) for entry in valid_earnings)
            total_earnings = sum(float(entry.get('total_cut', 0)) for entry in valid_earnings)

            md_content += f"""
* **User:** {user.display_name}
* **Total Hours Worked:** {total_hours:.1f}
* **Total Gross Revenue:** ${total_gross:.2f}
* **Total Earnings:** ${total_earnings:.2f}

## Detailed Earnings

| # | Date | Role | Shift | Hours | Gross Revenue | Earnings |
|---|------|------|-------|-------|--------------|----------|
"""

        # Append Earnings Data
        for i, entry in enumerate(valid_earnings, 1):
            hours = max(0, float(entry.get('hours_worked', 0)))
            gross_revenue = float(entry.get('gross_revenue', 0))
            total_cut = float(entry.get('total_cut', 0))

            if all_data:
                display_name = entry.get('display_name', 'Unknown') or 'Unknown'
                username = entry.get('username', 'unknown') or 'unknown'
                user_col = f"{display_name} (@{username})"
                md_content += f"| {i} | {user_col} | {entry['date']} | {entry['role']} | {entry['shift'].capitalize()} | {hours:.1f} | ${gross_revenue:.2f} | ${total_cut:.2f} |\n"
            else:
                md_content += f"| {i} | {entry['date']} | {entry['role']} | {entry['shift'].capitalize()} | {hours:.1f} | ${gross_revenue:.2f} | ${total_cut:.2f} |\n"

        # Role Summary Table (for both cases)
        md_content += "\n## Earnings by Role\n\n"
        md_content += "| Role | Total Earnings | Hours Worked | Percentage of Total |\n"
        md_content += "|------|---------------|--------------|--------------------|\n"

        role_summary = valid_df.groupby('role').agg({
            'total_cut': 'sum',
            'hours_worked': 'sum'
        }).reset_index()

        total_earnings = valid_df['total_cut'].sum()

        for _, row in role_summary.iterrows():
            percentage = (row['total_cut'] / total_earnings) * 100 if total_earnings > 0 else 0
            md_content += f"| {row['role']} | ${row['total_cut']:.2f} | {row['hours_worked']:.1f} | {percentage:.1f}% |\n"

        buffer.write(md_content.encode('utf-8'))


    async def _generate_txt(self, df, interaction, user, buffer, user_earnings, all_data=False):
        """Generate TXT format export
        
        Args:
            df: DataFrame containing earnings data
            interaction: Discord interaction object
            user: User object for individual reports
            buffer: Output buffer to write TXT content
            user_earnings: List of user earnings entries
            all_data: Boolean indicating if this is a full report or user-specific
        """
        agency_name = await self.get_agency_name(interaction.guild.id)
        report_title = f"{agency_name} Full Earnings Report" if all_data else f"{agency_name} Earnings Report for {user.display_name}"

        # Validate dates - filter out future dates
        current_date = datetime.now()
        valid_earnings = []
        for entry in user_earnings:
            entry_date = datetime.strptime(entry['date'], '%d/%m/%Y')
            if entry_date <= current_date:
                valid_earnings.append(entry)
        
        # Recalculate totals based on valid entries
        valid_df = df[df['date'].apply(lambda x: datetime.strptime(x, '%d/%m/%Y') <= current_date)]

        text_content = f"============================================\n"
        text_content += f"   {report_title}\n"
        text_content += f"   Generated on {current_date.strftime('%d/%m/%Y %H:%M')}\n"
        text_content += f"============================================\n\n"
        
        if all_data:
            # Count only valid users
            unique_users = set(entry.get('user_id') for entry in valid_earnings if entry.get('user_id'))
            text_content += f"Total Users:         {len(unique_users)}\n"
        
        text_content += f"Total Gross Revenue: ${valid_df['gross_revenue'].sum():.2f}\n"
        text_content += f"Total Earnings:      ${valid_df['total_cut'].sum():.2f}\n"
        text_content += f"Total Hours Worked:  {valid_df['hours_worked'].sum():.1f}\n"
        
        # Table headers
        if all_data:
            text_content += "\n#   User                Date       Role        Shift     Hours  Gross ($)  Earnings ($)\n"
            text_content += "-" * 88 + "\n"  # Separator length for full report
        else:
            text_content += "\n#   Date       Role        Shift     Hours  Gross ($)  Earnings ($)\n"
            text_content += "-" * 67 + "\n"  # Separator length for user-specific report
        
        for i, entry in enumerate(valid_earnings, 1):
            # Format hours and monetary values
            hours = max(0, float(entry.get('hours_worked', 0)))
            gross = float(entry.get('gross_revenue', 0))
            earnings = float(entry.get('total_cut', 0))
            
            if all_data:
                # Handle user display
                user_id = entry.get('user_id')
                username = entry.get('username', '')
                display_name = entry.get('display_name', '')
                
                if display_name and display_name.lower() != 'none':
                    user_info = f"{display_name[:18]} (@{username[:8]})"
                elif username and username.lower() != 'none':
                    user_info = f"@{username[:20]}"
                else:
                    user_info = "Unknown User"
                
                user_info = user_info.ljust(20)
                
                text_content += f"{i:3} {user_info} {entry['date']:10} {entry['role']:10} {entry['shift'].capitalize():8} {hours:6.1f} {gross:10.2f} {earnings:12.2f}\n"
            else:
                text_content += f"{i:3} {entry['date']:10} {entry['role']:10} {entry['shift'].capitalize():8} {hours:6.1f} {gross:10.2f} {earnings:12.2f}\n"
        
        # Add role summary table
        text_content += "\n============================================\n"
        text_content += "EARNINGS BY ROLE\n"
        text_content += "============================================\n\n"
        text_content += "Role        Total Earnings    Hours Worked    % of Total\n"
        text_content += "-" * 60 + "\n"
        
        role_summary = valid_df.groupby('role').agg({
            'total_cut': 'sum',
            'hours_worked': 'sum'
        }).reset_index()
        
        total_earnings = valid_df['total_cut'].sum()
        
        for _, row in role_summary.iterrows():
            # Avoid division by zero
            percentage = (row['total_cut'] / total_earnings) * 100 if total_earnings > 0 else 0
            text_content += f"{row['role']:10} ${row['total_cut']:15.2f} {row['hours_worked']:15.1f} {percentage:10.1f}%\n"
        
        buffer.write(text_content.encode('utf-8'))
    def add_footer(self, canvas, doc, username):
        """Add footer to the PDF pages"""
        canvas.saveState()
        
        footer_text = f"Earnings Report for {username} - Generated on {datetime.now().strftime('%d/%m/%Y')}"
        canvas.setFont('Helvetica', 8)
        
        # Draw line above footer
        canvas.line(30, 40, doc.width + 30, 40)
        
        # Add page number and footer text
        canvas.drawString(30, 30, footer_text)
        canvas.drawRightString(doc.width + 30, 30, f"Page {canvas._pageNumber}")
        
        canvas.restoreState()

    # New interactive slash command
    @app_commands.command(
        name="workflow",
        description="Calculate earnings using an interactive wizard"
    )
    async def calculate_slash(self, interaction: discord.Interaction):
        """Interactive workflow to calculate earnings"""
        ephemeral = await self.get_ephemeral_setting(interaction.guild_id)

        # Log command usage
        logger.info(f"User {interaction.user.name} ({interaction.user.id}) started calculate workflow")
        
        # Start the interactive workflow with compensation type selection
        view = CompensationTypeSelectionView(self)
        await interaction.response.send_message("Select a compensation type:", view=view, ephemeral=ephemeral)

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

        if not role_config:
            await interaction.followup.send("❌ Role configuration not found.", ephemeral=ephemeral)

            return
        
        commission_percentage = role_config.get("commission_percentage", 0)
        percentage = None

        try:
            percentage = Decimal(str(commission_percentage))
        except (ValueError, TypeError):
            percentage = Decimal("0")

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
                "from": Decimal(rule.get("from", "0")),
                "to": Decimal(rule.get("to", "0")),
                "amount": Decimal(rule.get("amount", "0"))
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
            hourly_rate = Decimal(str(role_config.get("hourly_rate", "0")))
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
            hourly_rate = Decimal(str(role_config.get("hourly_rate", "0")))
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
        logger.info(f"Calculation preview for {interaction.user.name}: Gross=${results['gross_revenue']}, Net=${results.get('net_revenue', 0)}, Total Cut=${results['total_cut']}")
        
        # Process models
        models_list = ", ".join(selected_models) if selected_models else ""
        
        # Create embed for preview
        embed = discord.Embed(title="📊 Earnings Calculation (PREVIEW)", color=0x009933)
        current_date = datetime.now().strftime(settings.DATE_FORMAT)
        sender = interaction.user.mention
        
        # Build fields dynamically based on compensation type
        fields = []

        def format_currency(value, decimal_places=False, thousands_separator=False):
            if decimal_places:
                formatted_value = f"{float(value):,.{settings.DECIMAL_PLACES}f}"
            else:
                formatted_value = f"{float(value):,}{settings.DECIMAL_PLACES}" if thousands_separator else f"{float(value)}"
            
            return f"${formatted_value}"
        
        # Compensation field
        compensation_value = {
            "commission": format_currency(percentage, decimal_places=True) + "%",
            "hourly": format_currency(hourly_rate, decimal_places=True, thousands_separator=True) + "/h",
            "both": f"{format_currency(percentage, decimal_places=True)}% + {format_currency(hourly_rate, decimal_places=True, thousands_separator=True)}/h"
        }[compensation_type]
        
        # Common fields
        fields.extend([
            ("📅 Date", current_date, True),
            ("✍ Sender", sender, True),
            ("💸 Compensation", compensation_value, True),
        ])

        # Hours Worked (only show if not commission)
        if compensation_type != "commission":
            fields.append(("⏰ Hours Worked", format_currency(hours_worked, decimal_places=True) + "h", True))

        fields.extend([
            ("📥 Shift", shift, True),
            ("🎯 Role", role.name, True),
            ("⌛ Period", period, True),
            ("💰 Gross Revenue", format_currency(results['gross_revenue'], decimal_places=True, thousands_separator=True), True),
        ])
        
        # Net Revenue (only show if not hourly)
        if compensation_type != "hourly":
            fields.append(("💵 Net Revenue", f"{format_currency(results['net_revenue'], decimal_places=True, thousands_separator=True)} (80%)", True))
        
        # Remaining fields
        fields.extend([
            ("🎁 Bonus", format_currency(results['bonus'], decimal_places=True, thousands_separator=True), True),
            ("💼 Employee Cut", format_currency(results['employee_cut'], decimal_places=True, thousands_separator=True), True),
            ("💰 Total Cut", format_currency(results['total_cut'], decimal_places=True, thousands_separator=True), True),
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
            "commission": format_currency(percentage, decimal_places=True) + "%",
            "hourly": f"{format_currency(hourly_rate, decimal_places=True, thousands_separator=True)}/h",
            "both": f"{format_currency(percentage, decimal_places=True)}% + {format_currency(hourly_rate, decimal_places=True, thousands_separator=True)}/h"
        }[compensation_type]
        
        # Only add hours worked if using hourly or both
        if compensation_type in ["hourly", "both"]:
            results["hours_worked"] = format_currency(hours_worked, decimal_places=True, thousands_separator=False)
        
        # results["date"] = current_date # TODO: remove
        # results["sender"] = sender
        # results["shift"] = shift
        # results["role"] = role.name
        # results["period"] = period
        # results["gross_revenue"] = f"${float(results['gross_revenue']):,.2f}"
        
        # # Only add net revenue if using commission or both
        # if compensation_type in ["commission", "both"]:
        #     results["net_revenue"] = f"${float(results['net_revenue']):,.2f} (80%)"
        
        # results["bonus"] = f"${float(results['bonus']):,.2f}"
        # results["employee_cut"] = f"${float(results['employee_cut']):,.2f}"
        # results["total_cut"] = f"${float(results['total_cut']):,.2f}"
        # results["models"] = models_list

        results.update({
            "date": current_date,
            "sender": sender,
            "shift": shift,
            "role": role.name,
            "period": period,
            "gross_revenue": format_currency(results["gross_revenue"]),
            "net_revenue": format_currency(results.get("net_revenue", 0)) if compensation_type in ["commission", "both"] else None,
            "bonus": format_currency(results["bonus"]),
            "employee_cut": format_currency(results["employee_cut"]),
            "total_cut": format_currency(results["total_cut"]),
            "models": models_list
        })
        
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
        # earnings_data = await file_handlers.load_json(settings.EARNINGS_FILE, settings.DEFAULT_EARNINGS) # TODO: remove
        earnings_data = await file_handlers.load_json(settings.get_earnings_file_for_guild(interaction.guild.id), settings.DEFAULT_EARNINGS)
        if sender not in earnings_data:
            earnings_data[sender] = []
        
        # Add new entry - handle potential missing hours_worked key
        hours_worked = 0.0
        if "hours_worked" in results:
            hours_worked = float(results["hours_worked"].replace('h', ''). replace('$', '').replace(',', ''))

        unique_id = generator_uuid.generate_id() # NOTE: uuid generation

        # Add new entry
        new_entry = {
            "id": unique_id, # NOTE: Added entry ID # WARN: think about possible combination between uuid and timestamp
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
        # success = await file_handlers.save_json(settings.EARNINGS_FILE, earnings_data) # TODO: remove
        success = await file_handlers.save_json(settings.get_earnings_file_for_guild(interaction.guild.id), earnings_data)
        if not success:
            logger.error(f"Failed to save earnings data for {sender}")
            await interaction.followup.send("⚠ Calculation failed to save data. Please try again.", ephemeral=True)
            return
        
        # Check if average display is enabled
        display_settings = await file_handlers.load_json(settings.DISPLAY_SETTINGS_FILE, settings.DEFAULT_DISPLAY_SETTINGS)
        show_average = display_settings.get(guild_id, {}).get("show_average", settings.DEFAULT_DISPLAY_SETTINGS['defaults'])
        
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
                    performance_text = f" (↑ {performance:.1f}% avg.)" if performance > 0 else f" (↓ {abs(performance):.1f}% avg.)"
                else:
                    performance_text = "" # NOTE: No historical data
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
            fields.append(("💵 Net Revenue", f"{results.get('net_revenue', 'N/A')} (80%)", True))
        
        # Remaining fields
        fields.extend([
            ("🎁 Bonus", results.get("bonus", "N/A"), True),
            ("💼 Employee Cut", results.get("employee_cut", "N/A"), True), # todo: maybe add hourly cut display
            ("💰 Total Cut", results.get("total_cut", "N/A"), True),
            (" ", "" if results.get("compensation_type") == "hourly" else "", True),
            ("🎭 Models", results.get("models", "N/A"), False)
        ])
        
        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)

        if await self.get_show_ids(interaction.guild.id):
            embed.set_footer(text=f"Sale ID: {unique_id}")
        
        # Send the final result to everyone
        await interaction.channel.send(embed=embed)
        
        # Confirm to the user
        await interaction.response.edit_message(
            content="✅ Calculation confirmed and posted! Check the channel for results.",
            embed=None,
            view=None
        )

    async def create_list_embed(self, interaction, user_earnings, embed, all_data=False, period=False):
        """Creates properly sized list entries that respect Discord's 1024 character limit per field."""
        embeds = [embed]
        current_embed = embed
        field_count = 0
        MAX_FIELDS_PER_EMBED = 8  # Reduced from 20 to stay within limits
        
        for idx, entry in enumerate(user_earnings, start=1):
            gross_revenue = float(entry['gross_revenue'])
            total_cut = float(entry['total_cut'])
            entry_id = entry['id']
            
            # Create entry text
            entry_text = f"```diff\n+ Entry #{idx}\n"

            if interaction.user.guild_permissions.administrator and await self.get_show_ids(interaction.guild.id):
                entry_text += f"🔑 Sale ID: {entry_id}\n"
            
            # Add username if all_data is True and user_id is available
            if all_data and 'user_id' in entry:
                # user_id = entry['user_id'].strip('<@>')
                # user = interaction.guild.get_member(int(user_id))
                user = interaction.guild.get_member(entry['user_id'])
                entry_text += f"👤 User:    {f'{user.display_name} (@{user.name})' if user else 'Unknown'}\n"
            
            entry_text += f"📅 Date:    {entry.get('date', 'N/A')}\n"
            if period:
                entry_text += f"⌛ Period:  {entry.get('period', 'N/A')}\n"
            entry_text += f"🎯 Role:    {entry.get('role', 'N/A').capitalize()}\n"
            entry_text += f"💰 Gross:   ${gross_revenue:.2f}\n"
            entry_text += f"💸 Cut:     ${total_cut:.2f}\n"
            entry_text += "```"
            
            # Check if we need a new embed due to field limits
            if field_count >= MAX_FIELDS_PER_EMBED:
                # Create new embed
                current_embed = discord.Embed(
                    title=f"{embed.title} (continued)",
                    color=embed.color,
                    timestamp=interaction.created_at
                )
                embeds.append(current_embed)
                field_count = 0
            
            current_embed.add_field(name=f"", value=entry_text, inline=False)
            field_count += 1
        
        # Add totals to last embed
        total_gross = sum(float(entry['gross_revenue']) for entry in user_earnings)
        total_cut_sum = sum(float(entry['total_cut']) for entry in user_earnings)
        
        # Add totals field to the last embed
        if field_count >= MAX_FIELDS_PER_EMBED - 2:
            # Create a new embed if we're close to the limit
            summary_embed = discord.Embed(
                title=f"{embed.title} (Summary)",
                color=embed.color,
                timestamp=interaction.created_at
            )
            embeds.append(summary_embed)
            last_embed = summary_embed
        else:
            last_embed = embeds[-1]
        
        last_embed.add_field(name="Total Gross", value=f"```\n${total_gross:.2f}\n```", inline=True)
        last_embed.add_field(name="Total Cut", value=f"```\n${total_cut_sum:.2f}\n```", inline=True)
        
        return embeds

    async def create_table_embed(self, interaction, user_earnings, embed, all_data=False):
        """Creates a table display that respects Discord's field character limits."""
        rows_per_chunk = 6  # Further reduced to ensure we stay within limits
        embeds = [embed]
        current_embed = embed
        field_count = 0
        MAX_FIELDS_PER_EMBED = 5  # Further reduced to keep embed size smaller
        
        # Calculate totals first
        total_gross = sum(float(entry['gross_revenue']) for entry in user_earnings)
        total_cut_sum = sum(float(entry['total_cut']) for entry in user_earnings)
        
        # Process entries in chunks
        for i in range(0, len(user_earnings), rows_per_chunk):
            chunk = user_earnings[i:i+rows_per_chunk]
            
            if i == 0:
                table_text = "```\n  # |   Date     |   Role    |  Gross   |   Cut    \n----|------------|-----------|----------|----------\n"
            else:
                table_text = "```"
            
            # Add rows to this chunk
            for j, entry in enumerate(chunk, start=i+1):
                gross_revenue = float(entry['gross_revenue'])
                total_cut = float(entry['total_cut'])
                
                # Get the date safely
                date_str = str(entry.get('date', 'N/A'))
                date_display = date_str[:10] if len(date_str) >= 10 else date_str
                
                # Get the role safely
                role_str = str(entry.get('role', 'N/A')).capitalize()
                role_display = role_str[:9] if len(role_str) >= 9 else role_str.ljust(9)
                
                # Use fixed width formatting to align columns properly
                row = f"{j:3} | {date_display} | {role_display} |  {gross_revenue:7.2f} |  {total_cut:7.2f}\n"
                
                table_text += row
            
            table_text += "```"
            
            # Check if we need a new embed
            if field_count >= MAX_FIELDS_PER_EMBED:
                # Create new embed
                current_embed = discord.Embed(
                    title=f"{embed.title} (continued)",
                    color=embed.color,
                    timestamp=interaction.created_at
                )
                embeds.append(current_embed)
                field_count = 0
            
            # Add the chunk as a field
            chunk_start = i + 1
            chunk_end = min(i + rows_per_chunk, len(user_earnings))
            current_embed.add_field(
                name=f"", 
                # name=f"Entries {chunk_start}-{chunk_end}", 
                value=table_text, 
                inline=False
            )
            field_count += 1
        
        # Always add totals to a new embed to ensure we don't exceed limits
        summary_embed = discord.Embed(
            title=f"{embed.title} (Summary)",
            color=embed.color,
            timestamp=interaction.created_at
        )
        embeds.append(summary_embed)
        
        summary_embed.add_field(name="Total Gross", value=f"```\n {total_gross:.2f}\n```", inline=True)
        summary_embed.add_field(name="Total Cut", value=f"```\n {total_cut_sum:.2f}\n```", inline=True)
        
        return embeds

    async def send_paginated_embeds(self, interaction, embeds, ephemeral=True):
        """Sends multiple embeds as separate messages with page numbering."""
        if not embeds:
            await interaction.followup.send("No data to display.", ephemeral=ephemeral)
            return
        
        total_pages = len(embeds)
        
        for i, embed in enumerate(embeds, start=1):
            # Add page number to footer
            embed.set_footer(text=f"Page {i}/{total_pages} • Today at {datetime.now().strftime('%I:%M %p')}")
            
            # Send the embed
            await interaction.followup.send(embed=embed, ephemeral=ephemeral)

    def parse_mentions(self, send_to_str: str, guild: discord.Guild) -> tuple[list[discord.Member], list[discord.Role]]:
        """Parse user and role mentions from a string"""
        user_mentions = []
        role_mentions = []
            
        # Find user mentions
        user_ids = re.findall(r'<@!?(\d+)>', send_to_str)
        for user_id in user_ids:
            member = guild.get_member(int(user_id))
            if member:
                user_mentions.append(member)
            
        # Find role mentions
        role_ids = re.findall(r'<@&(\d+)>', send_to_str)
        for role_id in role_ids:
            role = guild.get_role(int(role_id))
            if role:
                role_mentions.append(role)
            
        return user_mentions, role_mentions

    async def generate_report_embed(
        self,
        interaction: discord.Interaction,
        mentioned_users: List[discord.User],
        mentioned_roles: List[discord.Role],
        recipients: List[discord.User],
        success_count: int,
        failures: List[str],
        file: Optional[discord.File],
        successfully_sent_to_content: Optional[str] = None
    ) -> discord.Embed:
        """Generate a rich embed for delivery reports."""
        embed = discord.Embed(
            title="📬 Earnings Report Delivery Summary",
            color=discord.Color.green() if success_count > 0 else discord.Color.red(),
            timestamp=interaction.created_at
        )
        
        # Targets Section
        targets = []
        if mentioned_users:
            users_display = "\n".join(f"- {user.mention} ({user.name})" for user in mentioned_users[:3])
            if len(mentioned_users) > 3:
                users_display += f"\n*(+ {len(mentioned_users)-3} more users)*"
            targets.append(f"**Direct Mentions**\n{users_display}")
        
        if mentioned_roles:
            roles_info = []
            for role in mentioned_roles[:2]:
                reached = sum(1 for m in role.members if m in recipients)
                roles_info.append(
                    f"- {role.mention} ({reached}/{len(role.members)} members "
                    f"{'🟢' if reached > 0 else '🔴'})"
                )
            if len(mentioned_roles) > 2:
                roles_info.append(f"*(+ {len(mentioned_roles)-2} more roles)*")
            targets.append("**Role Targets**\n" + "\n".join(roles_info))
        
        embed.add_field(
            name="🎯 Targeted Recipients",
            value="\n\n".join(targets) if targets else "No valid targets specified",
            inline=False
        )

        # Successfully Sent To
        if successfully_sent_to_content:
            embed.add_field(
                name="📨 Successfully Sent To",
                value=successfully_sent_to_content,
                inline=False
            )
        
        # Statistics
        stats = [
            f"• **Total Attempted:** {len(recipients)}",
            f"• **Successful Deliveries:** {success_count} 🟢",
            f"• **Failed Attempts:** {len(failures)} 🔴",
            f"• **File Attached:** {'✅' if file else '❌'}"
        ]
        embed.add_field(name="📊 Statistics", value="\n".join(stats), inline=False)
        
        # Failure Details
        if failures:
            failure_list = "\n".join(
                f"{i}. {failure.split(' (')[0]} `({failure.split(' (')[1][:-1]})`"
                for i, failure in enumerate(failures[:3], 1)
            )
            if len(failures) > 3:
                failure_list += f"\n... *(+{len(failures)-3} more)*"
            
            embed.add_field(name="❌ Top Failures", value=failure_list, inline=False)
        
        # Footer with context
        embed.set_footer(
            text=f"Requested by {interaction.user.display_name} ({interaction.user.name})\n",
            icon_url=interaction.user.display_avatar.url
        )
        
        return embed

    @app_commands.command(
        name="view-earnings",
        description="View your earnings"
    )
    @app_commands.describe(
        user="[Admin] The user whose earnings you want to view",
        entries=f"Number of entries to return (max {MAX_ENTRIES})",
        export="Export format",
        display_entries="Whether entries will be displayed or not",
        as_table="Display earnings in a table format",
        send_to="[Admin] Users/Roles to send report to (mention them)",
        period="Period to view (weekly, monthly, etc)",
        range_from="Starting date (dd/mm/yyyy)",
        range_to="Ending date (dd/mm/yyyy)",
        send_to_message="[Admin] Message to send to the selected users or roles",
        # zip_formats="Available formats: txt, csv, json, xlsx, pdf, png, markdown, html, svg", # TODO: remove
        zip_formats="Available formats: txt, csv, json, xlsx, pdf, png, markdown, html", 
        all_data="[Admin] Use all earnings data, not just specific user's"
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
            app_commands.Choice(name="Markdown", value="markdown"),
            app_commands.Choice(name="HTML", value="html"),
            # app_commands.Choice(name="SVG", value="svg"), # TODO: remove
            app_commands.Choice(name="ZIP Archive", value="zip")
        ]
    )
    async def view_earnings(
        self,
        interaction: discord.Interaction,
        user: Optional[discord.User] = None,
        entries: Optional[int] = MAX_ENTRIES,
        export: Optional[str] = "none",
        display_entries: Optional[bool] = True,
        as_table: Optional[bool] = False,
        period: Optional[str] = None,
        send_to: Optional[str] = None,
        range_from: Optional[str] = None,
        range_to: Optional[str] = None,
        send_to_message: Optional[str] = None,
        zip_formats: Optional[str] = None,
        all_data: Optional[bool] = False
    ):
        """Command for users to view their earnings with enhanced reporting."""
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)
        
        try:
            if (send_to or send_to_message) and not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("❌ Administrator permissions required to send reports.", ephemeral=ephemeral)
                return

            # Permission check
            if user and not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message(
                    f"❌ You need administrator permissions to view {user.mention}'s earnings.",
                    ephemeral=ephemeral
                )
                return
            elif all_data and not interaction.user.guild_permissions.administrator:
                if export != 'png':
                    await interaction.response.send_message(
                        "❌ You need administrator permissions to view all earnings data unless exporting as `PNG Chart`.",
                        ephemeral=ephemeral
                    )
                    return

            await interaction.response.defer(ephemeral=ephemeral)

            # Validate entries count
            entries = min(max(entries, 1), MAX_ENTRIES)

            # Load and filter data
            # earnings_data = await file_handlers.load_json(settings.EARNINGS_FILE, settings.DEFAULT_EARNINGS) # TODO: remove
            earnings_data = await file_handlers.load_json(settings.get_earnings_file_for_guild(interaction.guild.id), settings.DEFAULT_EARNINGS) 
            user_earnings = None

            if not all_data:
                if user:
                    user_earnings = earnings_data.get(user.mention, [])
                else:
                    user_earnings = earnings_data.get(interaction.user.mention, [])
            else:
                # When all_data is True, add user_id to each entry
                user_earnings = [
                    {
                        **entry, 
                        'user_id': int(user_id.strip('<@>')),
                        'display_name': (
                            interaction.guild.get_member(int(user_id.strip('<@>'))).display_name
                            if interaction.guild.get_member(int(user_id.strip('<@>')))
                            else None
                        ),
                        'username': (
                            interaction.guild.get_member(int(user_id.strip('<@>'))).name
                            if interaction.guild.get_member(int(user_id.strip('<@>')))
                            else None
                        ),
                        'user': (
                            f"{interaction.guild.get_member(int(user_id.strip('<@>'))).display_name} (@{interaction.guild.get_member(int(user_id.strip('<@>'))).name})"
                            if interaction.guild.get_member(int(user_id.strip('<@>')))
                            else None
                        ),
                    } 
                    for user_id, entries in earnings_data.items() 
                    for entry in entries
                ]

            # Date filtering
            if range_from or range_to:
                try:
                    from_date = datetime.strptime(range_from, "%d/%m/%Y") if range_from else datetime.min
                    to_date = datetime.now() if range_to == "~" else (
                        datetime.strptime(range_to, "%d/%m/%Y") if range_to else datetime.max
                    )
                    to_date = to_date.replace(hour=23, minute=59, second=59)

                    user_earnings = [
                        entry for entry in user_earnings
                        if from_date <= datetime.strptime(entry['date'], "%d/%m/%Y") <= to_date
                    ]
                except ValueError:
                    return await interaction.followup.send(
                        "❌ Invalid date format. Use dd/mm/yyyy.",
                        ephemeral=ephemeral
                    )

            # Sort and truncate entries
            user_earnings = sorted(
                user_earnings,
                key=lambda x: datetime.strptime(x['date'], "%d/%m/%Y"),
                reverse=True
            )[:entries]

            user_earnings.sort(key=lambda x: int(x['id'].split('-')[0]), reverse=True)

            if not user_earnings:
                return await interaction.followup.send(
                    "❌ No earnings data found.",
                    ephemeral=ephemeral
                )

            if period:
                user_earnings = [
                    entry for entry in user_earnings
                    if entry['period'].lower() == period.lower()
                ]

            if not user_earnings:
                return await interaction.followup.send(
                    "❌ No earnings data found for the period: " + period,
                    ephemeral=ephemeral
                )

            summary_for_text = None
            if not all_data:
                summary_for_text = f"{interaction.user.display_name}"
            else:
                summary_for_text = f"(All Users)"

            # Create embed
            embed = discord.Embed(
                title=f"📊 Earnings Summary - {summary_for_text}",
                color=0x2ECC71,
                timestamp=interaction.created_at
            )

            if user and user.avatar:
                embed.set_thumbnail(url=user.avatar.url)
            elif interaction.user.avatar:
                    embed.set_thumbnail(url=interaction.user.avatar.url)


            total_gross = 0
            total_cut_sum = 0
            for index, entry in enumerate(user_earnings, start=1):
                gross_revenue = float(entry['gross_revenue'])
                total_cut = float(entry['total_cut'])
                total_gross += gross_revenue
                total_cut_sum += total_cut
            embed.add_field(name="Total Gross", value=f"```\n${total_gross:.2f}\n```", inline=True)
            embed.add_field(name="Total Cut", value=f"```\n${total_cut_sum:.2f}\n```", inline=True)

            # if not all_data: # TODO: remove
            await interaction.followup.send(embed=embed, ephemeral=ephemeral)

            if display_entries:
                base_embed = discord.Embed(
                    title=f"📊 Earnings {('Table' if as_table else 'List')} {(' - ' + period.upper() if period else '')}",
                    color=0x2ECC71,
                    timestamp=interaction.created_at
                )

                embeds = await self.create_table_embed(interaction, user_earnings, base_embed, all_data) if as_table \
                    else await self.create_list_embed(interaction, user_earnings, base_embed, all_data, period is None)
                
                if all_data and not interaction.user.guild_permissions.administrator:
                    await interaction.followup.send(
                        "🔍 You are comparing your revenue with others. 🔓 Admin exception granted.",
                        ephemeral=ephemeral
                    )
                else:
                    await self.send_paginated_embeds(interaction, embeds, ephemeral=ephemeral)
                # await self.send_paginated_embeds(interaction, embeds, ephemeral=ephemeral)
                
            else:
                pass

            if export != "zip" and zip_formats:
                await interaction.followup.send("⚠️ Zip formats are set but the export format is not 'zip'.", ephemeral=ephemeral)
                return

            zip_formats_list = []
            
            # Handle zip_formats input
            if export == "zip":
                if zip_formats:
                    formats = re.split(r'[ ,\.\-_\s]+', zip_formats)
                    for fmt in formats:
                        fmt = fmt.lower().strip()
                        if fmt and fmt in ALL_ZIP_FORMATS:
                            zip_formats_list.append(fmt)
                        elif fmt == "all":
                            zip_formats_list = ALL_ZIP_FORMATS.copy()
                            break
                
                # If export is zip but no formats specified, use all formats
                if not zip_formats_list:
                    zip_formats_list = ALL_ZIP_FORMATS.copy()
                
                # Validate formats
                if not zip_formats_list:
                    await interaction.followup.send(
                        "❌ No valid export formats specified for ZIP archive.",
                        ephemeral=ephemeral
                    )
                    return

            file = None
            if export != "none":
                try:
                    file = await self.generate_export_file(user_earnings, interaction, interaction.user, export, zip_formats_list if export == "zip" else None, all_data)
                except Exception as e:
                    return await interaction.followup.send(f"❌ Export failed: {str(e)}", ephemeral=ephemeral)

            if file:
                await interaction.followup.send(file=file, ephemeral=ephemeral)

            if send_to:
                mentioned_users, mentioned_roles = self.parse_mentions(send_to, interaction.guild)
                
                # Collect unique recipients
                recipients = []
                seen = set()
                for user in mentioned_users:
                    if user.id not in seen:
                        recipients.append(user)
                        seen.add(user.id)
                for role in mentioned_roles:
                    for member in role.members:
                        if member.id not in seen:
                            recipients.append(member)
                            seen.add(member.id)
                
                # Send attempts
                success_count = 0
                failures = []
                report__message_embed = None
                successfully_sent_to_content = f"\n"
                for recipient in recipients:
                    try:
                        await recipient.send(f"{recipient.mention}")

                        file = None
                        if export != "none":
                            try:
                                file = await self.generate_export_file(user_earnings, interaction, interaction.user, export, zip_formats_list if export == "zip" else None, all_data)
                            except Exception as e:
                                return await interaction.followup.send(f"❌ Export failed: {str(e)}", ephemeral=ephemeral)
                        
                        await recipient.send(embed=embed)

                        if file:
                            await recipient.send(file=file)

                        if send_to_message:
                            report__message_embed = discord.Embed(
                                title="Report message",
                                description=f"{send_to_message}"
                            )
                            report__message_embed.add_field(name="Sent by", value=interaction.user.mention, inline=False)
                            await recipient.send(embed=report__message_embed)
                        # note: sent success logic
                        successfully_sent_to_content += f"- {recipient.mention} ({recipient.name})\n"
                        success_count += 1
                    except discord.Forbidden:
                        failures.append(f"{recipient.mention} (Blocked DMs)")
                    except Exception as e:
                        # note: sent failure logic
                        failures.append(f"{recipient.mention} ({str(e)})")
                
                # Generate and send report
                report_embed = await self.generate_report_embed(
                    interaction=interaction,
                    mentioned_users=mentioned_users,
                    mentioned_roles=mentioned_roles,
                    recipients=recipients,
                    success_count=success_count,
                    failures=failures,
                    file=file,
                    successfully_sent_to_content=successfully_sent_to_content
                )
                
                if report__message_embed:
                    await interaction.followup.send(f"✅ Report message sent with content: ", embed=report__message_embed, ephemeral=ephemeral)
                await interaction.followup.send(embed=report_embed, ephemeral=ephemeral)
            else:
                pass
        
        except ValueError:
            await interaction.followup.send("❌ Invalid date format. Use dd/mm/yyyy.", ephemeral=ephemeral)
        except Exception as e:
            logger.error(f"Earnings command error: {str(e)}")
            await interaction.followup.send(
                f"❌ Command failed: {str(e)}", 
                ephemeral=ephemeral
            )

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
                row=min(3, (current_page_models.index(model) // 5))
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