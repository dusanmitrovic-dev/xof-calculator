import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import discord
import asyncio
import zipfile
import logging
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
from discord import ui, app_commands
from discord.ui import Select, View, Button
from discord.ext import commands
from reportlab.lib import colors
from utils import file_handlers
from datetime import datetime
from decimal import Decimal
from config import settings
from pathlib import Path

SUPPORTED_EXPORTS = ["none", "txt", "csv", "json", "xlsx", "pdf", "png", "zip"]
# All available formats
ALL_ZIP_FORMATS = ['csv', 'json', 'xlsx', 'pdf', 'png', 'txt', 'html', 'markdown', 'svg'] # todo: Option to set default zip exports in settings
MAX_ENTRIES = 5000000

logger = logging.getLogger("xof_calculator.calculator")

# class ZipFormatSelector(Select): # todo: remove
#     def __init__(self, formats: List[str]):
#         options = [
#             discord.SelectOption(label="All Formats", value="all", description="Select all available formats"),
#         ]
        
#         for fmt in formats:
#             options.append(
#                 discord.SelectOption(label=fmt.upper(), value=fmt, description=f"Include {fmt.upper()} format")
#             )
        
#         super().__init__(
#             placeholder="Select formats to include in ZIP...",
#             min_values=1,
#             max_values=len(formats) + 1,  # +1 for "All" option
#             options=options
#         )
        
#         self.selected_formats = []
    
#     async def callback(self, interaction: discord.Interaction):
#         self.selected_formats = self.values
        
#         # If "all" is selected, use all formats
#         if "all" in self.selected_formats:
#             self.selected_formats = ALL_ZIP_FORMATS.copy()
        
#         formats_str = ", ".join(self.selected_formats)
#         await interaction.response.send_message(
#             f"Selected formats: {formats_str}",
#             ephemeral=True
#         )

# class FormatSelectorView(View):
#     def __init__(self, timeout: float = 180):
#         super().__init__(timeout=timeout)
#         self.selector = ZipFormatSelector(ALL_ZIP_FORMATS)
#         self.add_item(self.selector)
#         self.confirmed = False

#     @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
#     async def confirm(self, interaction: discord.Interaction, button: Button):
#         self.confirmed = True
#         self.stop()
#         await interaction.response.send_message(
#             f"Formats confirmed: {', '.join(self.selector.selected_formats)}",
#             ephemeral=True
#         )

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
        display_settings = await file_handlers.load_json(settings.DISPLAY_SETTINGS_FILE, settings.DEFAULT_DISPLAY_SETTINGS)
        guild_settings = display_settings.get(str(guild_id), {})
        return guild_settings.get('ephemeral_responses', True)

    # async def generate_export_file(self, user_earnings, user, export_format): # todo: remove
    #     """Generate export file based on format choice"""
    #     sanitized_name = Path(user.display_name).stem[:32].replace(" ", "_")
    #     base_name = f"{sanitized_name}_earnings_{datetime.now().strftime('%d_%m_%Y')}"
        
    #     buffer = io.BytesIO()
        
    #     if export_format == "zip":
    #         with zipfile.ZipFile(buffer, 'w') as zip_file:
    #             formats = ['csv', 'json', 'xlsx', 'pdf', 'png', 'txt']
                
    #             fmt_buffer = None
    #             for fmt in formats:
    #                 fmt_buffer = io.BytesIO()
                    
    #                 try:
    #                     if fmt == "csv":
    #                         df = pd.DataFrame(user_earnings)
    #                         df.to_csv(fmt_buffer, index=False)
                        
    #                     elif fmt == "json":
    #                         fmt_buffer.write(json.dumps(user_earnings, indent=2).encode('utf-8'))
                        
    #                     elif fmt == "xlsx":
    #                         df = pd.DataFrame(user_earnings)
    #                         with pd.ExcelWriter(fmt_buffer, engine='openpyxl') as writer:
    #                             df.to_excel(writer, index=False, sheet_name='Earnings')
                        
    #                     elif fmt == "pdf":
    #                         # FIX: Use fmt_buffer instead of main buffer
    #                         doc = SimpleDocTemplate(fmt_buffer, pagesize=letter)
    #                         data = [["Date", "Role", "Gross", "Total Cut"]]
    #                         data += [[
    #                             entry['date'],
    #                             entry['role'],
    #                             f"${float(entry['gross_revenue']):.2f}",
    #                             f"${float(entry['total_cut']):.2f}"
    #                         ] for entry in user_earnings]
                            
    #                         table = Table(data)
    #                         table.setStyle(TableStyle([
    #                             ('BACKGROUND', (0,0), (-1,0), colors.grey),
    #                             ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
    #                             ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    #                             ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
    #                             ('BOTTOMPADDING', (0,0), (-1,0), 12),
    #                             ('BACKGROUND', (0,1), (-1,-1), colors.beige),
    #                             ('GRID', (0,0), (-1,-1), 1, colors.black)
    #                         ]))
    #                         doc.build([table])
                        
    #                     elif fmt == "png":
    #                         # FIX: Use fmt_buffer instead of main buffer
    #                         plt.figure(figsize=(10, 6))
    #                         dates = [datetime.strptime(entry['date'], '%d/%m/%Y') for entry in user_earnings]
    #                         plt.plot(dates, [float(e['gross_revenue']) for e in user_earnings], label='Gross Revenue')
    #                         plt.plot(dates, [float(e['total_cut']) for e in user_earnings], label='Total Cut')
    #                         plt.legend()
    #                         plt.tight_layout()
    #                         plt.savefig(fmt_buffer, format='png')
    #                         plt.close()
                        
    #                     else:  # txt
    #                         # FIX: Use fmt_buffer instead of main buffer
    #                         text_content = f"Earnings Report for {user.display_name}\n\n"
    #                         text_content += "\n".join(
    #                             f"{entry['date']} | {entry['role']:9} | ${float(entry['gross_revenue']):8.2f} | ${float(entry['total_cut']):8.2f}"
    #                             for entry in user_earnings
    #                         )
    #                         fmt_buffer.write(text_content.encode('utf-8'))
                    
    #                 finally:
    #                     fmt_buffer.seek(0)
    #                     zip_file.writestr(f"{base_name}.{fmt}", fmt_buffer.getvalue())
    #                     fmt_buffer.close()

    #         buffer.seek(0)
    #         return discord.File(buffer, filename=f"{base_name}.zip")
        
    #     # Handle non-zip formats (original code remains unchanged)
    #     elif export_format == "csv":
    #         df = pd.DataFrame(user_earnings)
    #         df.to_csv(buffer, index=False)
        
    #     elif export_format == "json":
    #         buffer.write(json.dumps(user_earnings, indent=2).encode('utf-8'))
        
    #     elif export_format == "xlsx":
    #         df = pd.DataFrame(user_earnings)
    #         with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
    #             df.to_excel(writer, index=False, sheet_name='Earnings')
        
    #     elif export_format == "pdf":
    #         doc = SimpleDocTemplate(buffer, pagesize=letter)
    #         data = [["Date", "Role", "Gross", "Total Cut"]]
    #         data += [[
    #             entry['date'],
    #             entry['role'],
    #             f"${float(entry['gross_revenue']):.2f}",
    #             f"${float(entry['total_cut']):.2f}"
    #         ] for entry in user_earnings]
                            
    #         table = Table(data)
    #         table.setStyle(TableStyle([
    #             ('BACKGROUND', (0,0), (-1,0), colors.grey),
    #             ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
    #             ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    #             ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
    #             ('BOTTOMPADDING', (0,0), (-1,0), 12),
    #             ('BACKGROUND', (0,1), (-1,-1), colors.beige),
    #             ('GRID', (0,0), (-1,-1), 1, colors.black)
    #         ]))
    #         doc.build([table])
        
    #     elif export_format == "png":
    #         plt.figure(figsize=(10, 6))
    #         dates = [datetime.strptime(entry['date'], '%d/%m/%Y') for entry in user_earnings]
    #         plt.plot(dates, [float(e['gross_revenue']) for e in user_earnings], label='Gross Revenue')
    #         plt.plot(dates, [float(e['total_cut']) for e in user_earnings], label='Total Cut')
    #         plt.legend()
    #         plt.tight_layout()
    #         plt.savefig(buffer, format='png')
    #         plt.close()
        
    #     else:  # txt
    #         text_content = f"Earnings Report for {user.display_name}\n\n"
    #         text_content += "\n".join(
    #             f"{entry['date']} | {entry['role']:9} | ${float(entry['gross_revenue']):8.2f} | ${float(entry['total_cut']):8.2f}"
    #             for entry in user_earnings
    #         )
    #         buffer.write(text_content.encode('utf-8'))

    #     buffer.seek(0)
    #     return discord.File(buffer, filename=f"{base_name}.{export_format}")
    
    # def add_footer(self, canvas, doc, username):
    #     canvas.saveState()
    #     styles = getSampleStyleSheet()
        
    #     # Footer text
    #     footer = Paragraph(
    #         f"Generated by YourAppName for {username} | {datetime.now().strftime('%Y-%m-%d %H:%M')}",
    #         styles['Normal']
    #     )
        
    #     # Draw footer at bottom of page
    #     w, h = footer.wrap(doc.width, doc.bottomMargin)
    #     footer.drawOn(canvas, doc.leftMargin, h)
        
    #     canvas.restoreState()

    async def generate_export_file(self, user_earnings, user, export_format, zip_formats=None):
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
                    fmt_buffer = self._generate_format_buffer(df, user, fmt, user_earnings)
                    zip_file.writestr(f"{base_name}.{fmt}", fmt_buffer.getvalue())
                    fmt_buffer.close()
        else:
            # Handle single format export
            buffer = self._generate_format_buffer(df, user, export_format, user_earnings)
        
        buffer.seek(0)
        return discord.File(buffer, filename=f"{base_name}.{export_format}")

    def _generate_format_buffer(self, df, user, format_type, user_earnings):
        """
        Helper method to generate a specific format export buffer.
        
        Args:
            df: DataFrame with earnings data
            user: User object with display_name attribute
            format_type: String indicating the desired export format
            user_earnings: Original list of earnings data
            
        Returns:
            io.BytesIO: Buffer containing the exported data
        """
        buffer = io.BytesIO()
        
        try:
            if format_type == "csv":
                self._generate_csv(df, buffer)
            elif format_type == "json":
                self._generate_json(df, buffer)
            elif format_type == "xlsx":
                self._generate_excel(df, buffer)
            elif format_type == "pdf":
                self._generate_pdf(df, user, buffer, user_earnings)
            elif format_type == "png":
                self._generate_png(df, user, buffer, user_earnings)
            elif format_type == "svg":
                self._generate_svg(df, user, buffer, user_earnings)
            elif format_type == "html":
                self._generate_html(df, user, buffer, user_earnings)
            elif format_type == "markdown":
                self._generate_markdown(df, user, buffer, user_earnings)
            else:  # txt
                self._generate_txt(df, user, buffer, user_earnings)
        except Exception as e:
            # If there's an error, write the error to the buffer
            error_msg = f"Error generating {format_type} format: {str(e)}"
            buffer.write(error_msg.encode('utf-8'))
        
        buffer.seek(0)
        return buffer

    def _generate_csv(self, df, buffer):
        """Generate CSV format export"""
        df.to_csv(buffer, index=False)

    def _generate_json(self, df, buffer):
        """Generate JSON format export"""
        json_data = df.to_json(orient='records', date_format='iso', indent=2)
        buffer.write(json_data.encode('utf-8'))

    def _generate_excel(self, df, buffer):
        """Generate Excel format export with formatting."""
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            # Write the main Earnings sheet
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

    def _generate_pdf(self, df, user, buffer, user_earnings):
        """Generate PDF format export"""
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        
        # Add title
        styles = getSampleStyleSheet()
        title_style = styles["Title"]
        elements.append(Paragraph(f"Earnings Report for {user.display_name}", title_style))
        elements.append(Spacer(1, 12))
        
        # Add summary section
        subtitle_style = styles["Heading2"]
        elements.append(Paragraph("Summary", subtitle_style))
        
        summary_data = [
            ["Metric", "Value"],
            ["Total Gross Revenue", f"${df['gross_revenue'].sum():.2f}"],
            ["Total Earnings", f"${df['total_cut'].sum():.2f}"],
            ["Total Hours Worked", f"{df['hours_worked'].sum():.1f}"],
        ]
        
        summary_table = Table(summary_data, colWidths=[250, 150])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (1,0), colors.grey),
            ('TEXTCOLOR', (0,0), (1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (1,-1), 'LEFT'),
            ('FONTNAME', (0,0), (1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (1,0), 12),
            ('BACKGROUND', (0,1), (1,-1), colors.beige),
            ('GRID', (0,0), (1,-1), 1, colors.black)
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 24))
        
        # Add detailed table
        elements.append(Paragraph("Detailed Earnings", subtitle_style))
        
        # Format data for the table
        data = [["#", "Date", "Role", "Shift", "Hours", "Gross Revenue", "Earnings"]]
        for i, entry in enumerate(user_earnings, 1):
            hourly = float(entry['total_cut']) / float(entry['hours_worked']) if float(entry['hours_worked']) > 0 else 0
            data.append([
                i,
                entry['date'],
                entry['role'],
                entry['shift'].capitalize(),
                f"{float(entry['hours_worked']):.1f}",
                f"${float(entry['gross_revenue']):.2f}",
                f"${float(entry['total_cut']):.2f}"
            ])
        
        # Create the table
        detail_table = Table(data)
        detail_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,0), 12),
            ('BACKGROUND', (0,1), (-1,-1), colors.beige),
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            # Align numeric columns right
            ('ALIGN', (4,1), (7,-1), 'RIGHT'),
        ]))
        elements.append(detail_table)
        elements.append(Spacer(1, 24))
        
        # Add charts on a new page
        elements.append(PageBreak())
        elements.append(Paragraph("Earnings Visualization", subtitle_style))
        elements.append(Spacer(1, 12))
        # Generate and add chart as Image
        chart_buffer = io.BytesIO()
        plt.figure(figsize=(7, 4))
        dates = [datetime.strptime(entry['date'], '%d/%m/%Y') for entry in user_earnings]
        plt.plot(dates, [float(e['gross_revenue']) for e in user_earnings], 'b-', label='Gross Revenue')
        plt.plot(dates, [float(e['total_cut']) for e in user_earnings], 'r-', label='Earnings')
        plt.legend()
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.title("Revenue vs Earnings Over Time")
        plt.tight_layout()
        plt.savefig(chart_buffer, format='png', dpi=150)
        plt.close()
        
        chart_buffer.seek(0)
        elements.append(Image(chart_buffer, width=450, height=250))
        
        # Build the PDF document
        doc.build(elements)

    def _generate_png(self, df, user, buffer, user_earnings):
        """Generate PNG format export"""
        # Create a more sophisticated visualization with multiple charts
        fig, axes = plt.subplots(figsize=(12, 6))
        
        # Plot 1: Line chart of revenue and earnings
        dates = [datetime.strptime(entry['date'], '%d/%m/%Y') for entry in user_earnings]
        axes.plot(dates, [float(e['gross_revenue']) for e in user_earnings], 'b-o', label='Gross Revenue')
        axes.plot(dates, [float(e['total_cut']) for e in user_earnings], 'r-o', label='Earnings')
        axes.set_title('Revenue & Earnings Over Time')
        axes.legend()
        axes.grid(True, linestyle='--', alpha=0.7)
        
        # Add a title to the overall figure
        fig.suptitle(f'Earnings Report for {user.display_name}', fontsize=16)
        fig.tight_layout(rect=[0, 0, 1, 0.95])
        
        plt.savefig(buffer, format='png', dpi=150)
        plt.close(fig)

    def _generate_svg(self, df, user, buffer, user_earnings):
        """Generate SVG format export"""
        # Create SVG visualization
        fig, ax1 = plt.subplots(figsize=(16, 9))
        
        # Plot 1: Line chart
        dates = [datetime.strptime(entry['date'], '%d/%m/%Y') for entry in user_earnings]
        ax1.plot_date(dates, [float(e['gross_revenue']) for e in user_earnings], 'b-o', label='Gross Revenue')
        ax1.plot_date(dates, [float(e['total_cut']) for e in user_earnings], 'r-o', label='Earnings')
        ax1.set_title('Revenue & Earnings Over Time')
        ax1.legend()
        ax1.grid(True, linestyle='--', alpha=0.7)
        
        fig.tight_layout()
        plt.savefig(buffer, format='svg')
        plt.close(fig)

    def _generate_html(self, df, user, buffer, user_earnings):
        """Generate HTML format export"""
        # Create an interactive HTML report with tables and charts
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Earnings Report for {user.display_name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1, h2 {{ color: #ffffff; }}
                table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #333366; color: white; }}
                tr:nth-child(even) {{ background-color: #f2f2f2; }}
                .summary {{ background-color: #f8f8f8; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                .summary-item {{ margin: 5px 0; }}
                .header {{ background-color: #333366; color: white; padding: 10px; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Earnings Report for {user.display_name}</h1>
                <p>Generated on {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
            </div>
            
            <h2>Summary</h2>
            <div class="summary">
                <p class="summary-item"><strong>Total Gross Revenue:</strong> ${df['gross_revenue'].sum():.2f}</p>
                <p class="summary-item"><strong>Total Earnings:</strong> ${df['total_cut'].sum():.2f}</p>
                <p class="summary-item"><strong>Total Hours Worked:</strong> {df['hours_worked'].sum():.1f}</p>
            </div>
            
            <h2>Detailed Earnings</h2>
            <table>
                <tr>
                    <th>#</th>
                    <th>Date</th>
                    <th>Role</th>
                    <th>Shift</th>
                    <th>Hours</th>
                    <th>Gross Revenue</th>
                    <th>Earnings</th>
                </tr>
        """
        
        # Add table rows
        for i, entry in enumerate(user_earnings, 1):
            hourly = float(entry['total_cut']) / float(entry['hours_worked']) if float(entry['hours_worked']) > 0 else 0
            html_content += f"""
                <tr>
                    <td>{i}</td>
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

    def _generate_markdown(self, df, user, buffer, user_earnings):
        """Generate Markdown format export"""
        # Create a markdown report
        md_content = f"""# Earnings Report for {user.display_name}

Generated on {datetime.now().strftime('%d/%m/%Y %H:%M')}

## Summary


* **Total Gross Revenue:** ${df['gross_revenue'].sum():.2f}
* **Total Earnings:** ${df['total_cut'].sum():.2f}
* **Total Hours Worked:** {df['hours_worked'].sum():.1f}

## Detailed Earnings


| # | Date       | Role       | Shift | Hours | Gross Revenue | Earnings |
|---|------------|------------|-------|-------|--------------|----------|
"""
        
        # Add table rows
        for i, entry in enumerate(user_earnings, 1):
            md_content += f"| {i} | {entry['date']} | {entry['role']} | {entry['shift'].capitalize()} | {float(entry['hours_worked']):.1f} | ${float(entry['gross_revenue']):.2f} | ${float(entry['total_cut']):.2f} |\n"
        
        md_content += "\n## Earnings by Role\n\n"
        md_content += "| Role       | Total Earnings | Hours Worked | Percentage of Total |\n"
        md_content += "|------------|---------------|--------------|--------------------|\n"
        
        # Add role summary rows
        role_summary = df.groupby('role').agg({
            'total_cut': 'sum',
            'hours_worked': 'sum'
        }).reset_index()
        
        total_earnings = df['total_cut'].sum()
        
        for _, row in role_summary.iterrows():
            percentage = (row['total_cut'] / total_earnings) * 100
            
            md_content += f"| {row['role']} | ${row['total_cut']:.2f} | {row['hours_worked']:.1f} | {percentage:.1f}% |\n"
        
        buffer.write(md_content.encode('utf-8'))

    def _generate_txt(self, df, user, buffer, user_earnings):
        """Generate TXT format export"""
        # Create an improved text report with ASCII art charts
        text_content = f"============================================\n"
        text_content += f"   EARNINGS REPORT FOR {user.display_name.upper()}\n"
        text_content += f"   Generated on {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
        text_content += f"============================================\n\n"
        
        # Summary section
        text_content += "SUMMARY\n"
        text_content += "-------\n"
        text_content += f"Total Gross Revenue: ${df['gross_revenue'].sum():.2f}\n"
        text_content += f"Total Earnings:      ${df['total_cut'].sum():.2f}\n"
        text_content += f"Total Hours Worked:  {df['hours_worked'].sum():.1f}\n"
        
        # Detailed section
        text_content += "\nDETAILED EARNINGS\n"
        text_content += "------------------\n"
        text_content += f"{'#':3} | {'DATE':10} | {'ROLE':12} | {'SHIFT':8} | {'HOURS':6} | {'GROSS ($)':10} | {'EARNINGS ($)':12}\n"
        text_content += "-" * 80 + "\n"
        
        for i, entry in enumerate(user_earnings, 1):
            text_content += f"{i:3} | {entry['date']:10} | {entry['role']:12} | {entry['shift'].capitalize():8} | {float(entry['hours_worked']):6.1f} | {float(entry['gross_revenue']):10.2f} | {float(entry['total_cut']):12.2f} \n"
        
        text_content += "\n"
        
        # Role summary
        role_summary = df.groupby('role').agg({
            'total_cut': 'sum',
            'hours_worked': 'sum'
        }).reset_index()
        
        text_content += "EARNINGS BY ROLE\n"
        text_content += "-----------------\n"
        text_content += f"{'ROLE':12} | {'EARNINGS ($)':12} | {'HOURS':6} | {'PERCENT':8}\n"
        text_content += "-" * 48 + "\n"
        
        total_earnings = df['total_cut'].sum()
        
        for _, row in role_summary.iterrows():
            percentage = (row['total_cut'] / total_earnings) * 100
            
            text_content += f"{row['role']:12} | {row['total_cut']:12.2f} | {row['hours_worked']:6.1f} | {percentage:7.1f}%\n"
        
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
        percentage = Decimal(str(role_config.get("commission_percentage", 0))) if isinstance(role_config.get("commission_percentage"), (int, float, Decimal, str)) else 0
        
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
                    performance_text = f" (↑ {performance:.1f}% avg.)" if performance > 0 else f" (↓ {abs(performance):.1f}% avg.)"
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
            ("💼 Employee Cut", results.get("employee_cut", "N/A"), True), # todo: maybe add hourly cut display
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

    # async def create_table_embed(self, interaction, user_earnings, embed): # todo: remove old logic        
    #     table_header = "```\n  # |   Date     |   Role    |  Gross   |  Total   \n----|------------|-----------|----------|--------\n"
    #     table_rows = []
    #     total_gross = 0
    #     total_cut_sum = 0
            
    #     for index, entry in enumerate(user_earnings, start=1):
    #         gross_revenue = float(entry['gross_revenue'])
    #         total_cut = float(entry['total_cut'])
    #         total_gross += gross_revenue
    #         total_cut_sum += total_cut
    #         table_rows.append(f"{index:3} | {entry['date']:10} | {entry['role'].capitalize():<9} | {gross_revenue:8.2f} | {total_cut:6.2f}\n")

    #     # Build table chunks with proper overflow handling
    #     current_chunk = table_header
    #     for row in table_rows:
    #         if len(current_chunk) + len(row) + 3 > 1024:
    #             # Add current chunk if it has content beyond header
    #             if current_chunk != table_header:
    #                 embed.add_field(name="", value=current_chunk + "```", inline=False)
    #             # current_chunk = table_header  # Start new chunk # todo: remove
    #             current_chunk = "```\n"  # Start new chunk without table header 
                
    #         current_chunk += row

    #     # Add remaining content
    #     if current_chunk != table_header:
    #         embed.add_field(name="", value=current_chunk + "```", inline=False)
            
    #     # Add totals
    #     embed.add_field(name="Total Gross", value=f"```\n{total_gross:.2f}\n```", inline=True)
    #     embed.add_field(name="Total Cut", value=f"```\n{total_cut_sum:.2f}\n```", inline=True)

    #     return embed

    # async def create_list_embed(self, interaction, user_earnings, embed):
    #     current_chunk = []
    #     for idx, entry in enumerate(user_earnings, start=1):
    #         gross_revenue = float(entry['gross_revenue'])
    #         total_cut_percent = (float(entry['total_cut']) / gross_revenue * 100 if gross_revenue != 0 else 0.0)
    #         entry_text = (
    #                 f"```diff\n"
    #                 f"+ Entry #{idx}\n"
    #                 f"📅 Date:    {entry.get('date', 'N/A')}\n"
    #                 f"🎯 Role:    {entry.get('role', 'N/A').capitalize()}\n"
    #                 f"💰 Gross:   ${float(entry.get('gross_revenue', 0)):.2f}\n"
    #                 f"💸 Cut:     ${float(entry.get('total_cut', 0)):.2f} "
    #                 f"({float(entry.get('total_cut', 0))/float(entry.get('gross_revenue', 1))*100:.1f}%)\n"
    #                 f"```\n"
    #             )

    #         if len("\n".join(current_chunk + [entry_text])) > 1024:
    #             embed.add_field(name="", value="\n".join(current_chunk), inline=False)
    #             current_chunk = [entry_text]
    #         else:
    #             current_chunk.append(entry_text)

    #     if current_chunk:
    #         embed.add_field(name="", value="\n".join(current_chunk), inline=False)

    #     return embed

    async def create_list_embed(self, interaction, user_earnings, embed):
        """Creates properly sized list entries that respect Discord's 1024 character limit per field."""
        embeds = [embed]
        current_embed = embed
        field_count = 0
        MAX_FIELDS_PER_EMBED = 20  # Keep some space for other fields
        
        for idx, entry in enumerate(user_earnings, start=1):
            gross_revenue = float(entry['gross_revenue'])
            total_cut = float(entry['total_cut'])
            total_cut_percent = (total_cut / gross_revenue * 100 if gross_revenue != 0 else 0.0)
            
            # Create a more compact entry that's guaranteed to be under 1024 chars
            entry_text = (
                f"```diff\n"
                f"+ Entry #{idx}\n"
                f"📅 Date:    {entry.get('date', 'N/A')}\n"
                f"🎯 Role:    {entry.get('role', 'N/A').capitalize()}\n"
                f"💰 Gross:   ${gross_revenue:.2f}\n"
                f"💸 Cut:     ${total_cut:.2f} ({total_cut_percent:.1f}%)\n"
                f"```"
            )
            
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
            
            # Add the entry as a single field
            # current_embed.add_field(name=f"Entry #{idx}", value=entry_text, inline=False)
            field_count += 1
        
        return embeds

    async def create_table_embed(self, interaction, user_earnings, embed):
        """Creates a table display that respects Discord's field character limits."""
        # Decrease rows per chunk to ensure we stay within size limits
        rows_per_chunk = 8  # Reduced from 15
        embeds = [embed]
        current_embed = embed
        field_count = 0
        MAX_FIELDS_PER_EMBED = 6  # Reduced from 20 to keep embed size smaller
        
        # Calculate totals first
        total_gross = sum(float(entry['gross_revenue']) for entry in user_earnings)
        total_cut_sum = sum(float(entry['total_cut']) for entry in user_earnings)
        
        # Process entries in chunks
        for i in range(0, len(user_earnings), rows_per_chunk):
            chunk = user_earnings[i:i+rows_per_chunk]
            
            # Create header for each chunk
            table_text = "```\n  # |   Date     |   Role    |  Gross   |  Cut    \n----|------------|-----------|----------|--------\n"
            
            # Add rows to this chunk
            for j, entry in enumerate(chunk, start=i+1):
                gross_revenue = float(entry['gross_revenue'])
                total_cut = float(entry['total_cut'])
                # Make the row more compact
                row = f"{j:3} | {entry['date'][:10]} | {entry['role'].capitalize()[:9]} | {gross_revenue:8.2f} | {total_cut:6.2f}\n"
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
                name=f"Entries {chunk_start}-{chunk_end}", 
                value=table_text, 
                inline=False
            )
            field_count += 1
        
        # Add totals to a new embed always to ensure we don't exceed limits
        summary_embed = discord.Embed(
            title=f"{embed.title} (Summary)",
            color=embed.color,
            timestamp=interaction.created_at
        )
        embeds.append(summary_embed)
        
        summary_embed.add_field(name="Total Gross", value=f"```\n${total_gross:.2f}\n```", inline=True)
        summary_embed.add_field(name="Total Cut", value=f"```\n${total_cut_sum:.2f}\n```", inline=True)
        
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
        send_to="Users/Roles to send report to (mention them)",
        period="Period to view (weekly, monthly, etc)",
        range_from="Starting date (dd/mm/yyyy)",
        range_to="Ending date (dd/mm/yyyy)",
        send_to_message="Message to send to the selected users or roles",
        zip_formats="Available formats: txt, csv, json, xlsx, pdf, png, markdown, html, svg",
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
            app_commands.Choice(name="SVG", value="svg"),
            app_commands.Choice(name="ZIP Archive", value="zip")
        ]
    )
    async def view_earnings(
        self,
        interaction: discord.Interaction,
        user: Optional[discord.User] = None,
        entries: Optional[int] = MAX_ENTRIES,
        export: Optional[str] = "none",
        display_entries: Optional[bool] = False,
        as_table: Optional[bool] = False,
        period: Optional[str] = None,
        send_to: Optional[str] = None,
        range_from: Optional[str] = None,
        range_to: Optional[str] = None,
        send_to_message: Optional[str] = None,
        # zip_formats: Optional[str] = None
        zip_formats: Optional[str] = None,
        all_data: Optional[bool] = False
    ):
        """Command for users to view their earnings with enhanced reporting."""
        ephemeral = await self.get_ephemeral_setting(interaction.guild.id)
        
        try:
            # Permission check
            if not interaction.user.guild_permissions.administrator and user:
                await interaction.response.send_message(
                    "❌ You need administrator permissions to view other users' earnings.",
                    ephemeral=ephemeral
                )
                return

            await interaction.response.defer(ephemeral=ephemeral)

            # Validate entries count
            entries = min(max(entries, 1), MAX_ENTRIES)

            # Load and filter data
            earnings_data = await file_handlers.load_json(settings.EARNINGS_FILE, settings.DEFAULT_EARNINGS)
            user_earnings = None

            if not all_data:
                if user:
                    user_earnings = earnings_data.get(user.mention, [])
                else:
                    user_earnings = earnings_data.get(interaction.user.mention, [])
            else:
                user_earnings = [entry for entries in earnings_data.values() if entries for entry in entries]

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

            # # Create earnings summary embed
            # total_gross = sum(float(entry['gross_revenue']) for entry in user_earnings)
            # total_cut = sum(float(entry['total_cut']) for entry in user_earnings)

            # embed = discord.Embed( # todo: remove
            #     title=f"📊 Earnings Summary - {interaction.user.display_name}",
            #     color=0x2ECC71,
            #     timestamp=interaction.created_at
            # )
            # embed.add_field(name="Total Gross", value=f"```\n{total_gross:.2f}\n```", inline=True)
            # embed.add_field(name="Total Cut", value=f"```\n{total_cut:.2f}\n```", inline=True)

            # # Send to recipients # todo: remove
            # if send_to:
            # note: send to logic
            # else:
            #     if file:
            #         await interaction.followup.send(file=file, ephemeral=ephemeral)
                # await interaction.followup.send(embed=embed, ephemeral=ephemeral) # todo: check if this is needed if not remove

            # Create embed
            embed = discord.Embed(
                title=f"📊 Earnings Summary - {interaction.user.display_name}",
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
            embed.add_field(name="Total Gross", value=f"```\n{total_gross:.2f}\n```", inline=True)
            embed.add_field(name="Total Cut", value=f"```\n{total_cut_sum:.2f}\n```", inline=True)

            await interaction.followup.send(embed=embed, ephemeral=ephemeral)

            if display_entries:
                base_embed = discord.Embed(
                    title=f"📊 Earnings {('Table' if as_table else 'List')} {(' - ' + period.upper() if period else '')}",
                    color=0x2ECC71,
                    timestamp=interaction.created_at
                )

                # embed = await self.create_table_embed(interaction, user_earnings, embed) if as_table \ # todo: remove old logic
                #     else await self.create_list_embed(interaction, user_earnings, embed)
                
                # await interaction.followup.send(embed=embed, ephemeral=ephemeral)

                embeds = await self.create_table_embed(interaction, user_earnings, base_embed) if as_table \
                    else await self.create_list_embed(interaction, user_earnings, base_embed)
                
                await self.send_paginated_embeds(interaction, embeds, ephemeral=ephemeral)
                
            else:
                pass

            if export != "zip" and zip_formats:
                await interaction.followup.send("⚠️ Zip formats are set but the export format is not 'zip'.", ephemeral=ephemeral)
                return

            # Process zip_formats selection
            zip_formats_list = []

            # zip_formats_list = [] # note: deep seek
            # if export == "zip":
            #     # Default to all formats if none selected
            #     if not zip_formats:
            #         zip_formats_list = ALL_ZIP_FORMATS.copy()
            #     else:
            #         # Check if "all" was explicitly chosen
            #         if "all" in zip_formats:
            #             zip_formats_list = ALL_ZIP_FORMATS.copy()
            #         else:
            #             # Filter valid formats (choices enforce validity, but double-check)
            #             zip_formats_list = [fmt for fmt in zip_formats if fmt in ALL_ZIP_FORMATS]
            
            # Handle zip_formats input
            # Process zip_formats selection
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
                    file = await self.generate_export_file(user_earnings, interaction.user, export, zip_formats_list if export == "zip" else None)
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
                    #     try: # todo: remove
                #         await send_to.send(f"{send_to.mention}")

                #         if file:
                #             await send_to.send(file=file)
                #         await send_to.send(embed=embed)
                #         if send_to_message:
                #             report_embed = discord.Embed(
                #                 title="Report message",
                #                 description=f"{send_to_message}"
                #             )
                #             report_embed.add_field(name="Sent by", value=interaction.user.mention, inline=False)
                #             await send_to.send(embed=report_embed)
                #             await interaction.followup.send(f"✅ Report message sent with content: ", embed=report_embed, ephemeral=ephemeral)
                #         await interaction.followup.send(f"✅ Report sent to {send_to.mention}", ephemeral=ephemeral)
                #     except Exception as e:
                #         await interaction.followup.send(f"❌ Failed to send to {send_to.mention}: {str(e)}", ephemeral=ephemeral)
                    try:
                        await recipient.send(f"{recipient.mention}")

                        file = None
                        if export != "none":
                            try:
                                file = await self.generate_export_file(user_earnings, interaction.user, export, zip_formats_list if export == "zip" else None)
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
                        # await interaction.followup.send(f"✅ Report sent to {recipient.mention}", ephemeral=ephemeral) # todo: remove
                        # note: sent success logic
                        successfully_sent_to_content += f"- {recipient.mention} ({recipient.name})\n"
                        success_count += 1
                    except discord.Forbidden:
                        failures.append(f"{recipient.mention} (Blocked DMs)")
                    except Exception as e:
                        # await interaction.followup.send(f"❌ Failed to send to {recipient.mention}: {str(e)}", ephemeral=ephemeral) # todo: remove
                        # note: sent failure logic
                        failures.append(f"{recipient.mention} ({str(e)})")

                    #     content = f"📊 Earnings report from {interaction.user.mention}:" # todo: remove
                    #     if send_to_message:
                    #         content += f"\n\n{send_to_message}"
                        
                    #     await recipient.send(content)
                    #     await recipient.send(embed=embed)
                        
                    #     if file:
                    #         await recipient.send(file=file)
                        
                    #     success_count += 1
                    # except discord.Forbidden:
                    #     failures.append(f"{recipient.mention} (Blocked DMs)")
                    # except Exception as e:
                    #     failures.append(f"{recipient.mention} ({str(e)})")
                
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
                # Send to command user if no recipients specified
                # await interaction.followup.send(embed=embed, ephemeral=ephemeral) # todo: remove
                pass

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