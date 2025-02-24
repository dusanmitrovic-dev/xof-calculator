import discord
import json
from discord.ext import commands
from datetime import datetime, timedelta

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Load configuration files
try:
    with open('role_percentages.json', 'r') as f:
        role_data = json.load(f)
except FileNotFoundError:
    role_data = {}

try:
    with open('shift_config.json', 'r') as f:
        shift_data = json.load(f)
except FileNotFoundError:
    shift_data = {}

try:
    with open('period_config.json', 'r') as f:
        period_data = json.load(f)
except FileNotFoundError:
    period_data = {}

# Load bonus rules
try:
    with open('bonus_rules.json', 'r') as f:
        bonus_rules = json.load(f)
except FileNotFoundError:
    bonus_rules = {}

# Load earnings data
try:
    with open('earnings.json', 'r') as f:
        earnings_by_sender = json.load(f)
except FileNotFoundError:
    earnings_by_sender = {}

@bot.event
async def on_ready():
    print(f'Bot is online as {bot.user}')

@bot.command()
@commands.has_permissions(administrator=True)
async def calculateroleset(ctx, role: discord.Role, percentage: float):
    """Set a role's percentage cut (Admin only)"""
    if percentage < 0 or percentage > 100:
        await ctx.send("Percentage must be between 0 and 100.")
        return
    
    guild_id = str(ctx.guild.id)
    role_id = str(role.id)
    
    if guild_id not in role_data:
        role_data[guild_id] = {}
    role_data[guild_id][role_id] = percentage
    
    with open('role_percentages.json', 'w') as f:
        json.dump(role_data, f, indent=4)
    
    await ctx.send(f"✅ {role.name} now has {percentage}% cut!")

@bot.command()
@commands.has_permissions(administrator=True)
async def calculateshiftset(ctx, *, shift: str):
    """Add a valid shift name (Admin only)"""
    guild_id = str(ctx.guild.id)
    
    existing_shifts = shift_data.get(guild_id, [])
    if any(s.lower() == shift.lower() for s in existing_shifts):
        await ctx.send(f"Shift '{shift}' already exists!")
        return
    
    if guild_id not in shift_data:
        shift_data[guild_id] = []
    shift_data[guild_id].append(shift)
    
    with open('shift_config.json', 'w') as f:
        json.dump(shift_data, f, indent=4)
    
    await ctx.send(f"✅ Shift '{shift}' added!")

@bot.command()
@commands.has_permissions(administrator=True)
async def calculateperiodset(ctx, *, period: str):
    """Add a valid period name (Admin only)"""
    guild_id = str(ctx.guild.id)
    
    existing_periods = period_data.get(guild_id, [])
    if any(p.lower() == period.lower() for p in existing_periods):
        await ctx.send(f"Period '{period}' already exists!")
        return
    
    if guild_id not in period_data:
        period_data[guild_id] = []
    period_data[guild_id].append(period)
    
    with open('period_config.json', 'w') as f:
        json.dump(period_data, f, indent=4)
    
    await ctx.send(f"✅ Period '{period}' added!")

@bot.command()
@commands.has_permissions(administrator=True)
async def calculatebonus(ctx, from_str: str, to_str: str, bonus_str: str):
    """Set a bonus rule for a revenue range (Admin only)"""
    try:
        from_num = float(from_str.replace('$', '').replace(',', ''))
        to_num = float(to_str.replace('$', '').replace(',', ''))
        bonus_amount = float(bonus_str.replace('$', '').replace(',', ''))
    except ValueError:
        await ctx.send("Invalid number format. Please enter numbers without symbols other than decimal points.")
        return

    if from_num > to_num:
        await ctx.send("The 'from' value must be less than or equal to the 'to' value.")
        return

    guild_id = str(ctx.guild.id)
    new_rule = {
        "from": from_num,
        "to": to_num,
        "amount": bonus_amount
    }

    if guild_id not in bonus_rules:
        bonus_rules[guild_id] = []
    bonus_rules[guild_id].append(new_rule)

    with open('bonus_rules.json', 'w') as f:
        json.dump(bonus_rules, f, indent=4)

    await ctx.send(f"✅ Bonus rule added: ${from_num:,.2f} to ${to_num:,.2f} → ${bonus_amount:,.2f} bonus!")

@bot.command()
async def calculate(ctx, period: str, shift: str, role: discord.Role, gross_revenue: float, *models):
    guild_id = str(ctx.guild.id)
    valid_periods = period_data.get(guild_id, [])
    matched_period = next((p for p in valid_periods if p.lower() == period.lower()), None)
    if not matched_period:
        await ctx.send(f"❌ Period '{period}' not configured! Admins: use !calculateperiodset.")
        return
    period = matched_period

    valid_images = []
    for attachment in ctx.message.attachments:
        if attachment.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            valid_images.append(await attachment.to_file())

    try:
        await ctx.message.delete()
    except discord.Forbidden:
        await ctx.send("Missing message delete permissions!")
        return

    valid_shifts = shift_data.get(guild_id, [])
    matched_shift = next((s for s in valid_shifts if s.lower() == shift.lower()), None)
    if not matched_shift:
        await ctx.send(f"❌ Shift '{shift}' not configured! Admins: use !calculateshiftset.")
        return
    shift = matched_shift

    if guild_id not in role_data or str(role.id) not in role_data[guild_id]:
        await ctx.send(f"⚠ {role.name} not configured! Admins: !calculateroleset.")
        return

    percentage = role_data[guild_id][str(role.id)]
    net_revenue = gross_revenue * 0.8
    employee_cut = (percentage / 100) * net_revenue

    # Calculate bonus based on configured rules
    sorted_rules = sorted(bonus_rules.get(guild_id, []), key=lambda x: x['from'], reverse=True)
    bonus = 0
    for rule in sorted_rules:
        if gross_revenue >= rule['from'] and gross_revenue <= rule['to']:
            bonus = rule['amount']
            break

    total_cut = employee_cut + bonus
    models_list = ", ".join(models) if models else "None"
    current_date = datetime.now().strftime("%d/%m/%Y")

    sender = ctx.author.mention
    if sender not in earnings_by_sender:
        earnings_by_sender[sender] = []
    earnings_by_sender[sender].append({
        "date": current_date,
        "total_cut": total_cut,
        "gross_revenue": gross_revenue,
        "period": period.lower()
    })

    with open('earnings.json', 'w') as f:
        json.dump(earnings_by_sender, f, indent=4)

    print(f"DEBUG: Earnings saved for {sender} in period {period}: {earnings_by_sender[sender]}")  # Debug line

    embed = discord.Embed(title="📊 Earnings Calculation", color=0x009933FF)
    fields = [
        ("📅 Date", current_date, True),
        ("✍ Sender", sender, True),
        ("📥 Shift", shift, True),
        ("🎯 Role", role.name, True),
        ("⌛ Period", period.capitalize(), True),
        ("💰 Gross Revenue", f"${gross_revenue:,.2f}", True),
        ("💵 Net Revenue", f"${net_revenue:,.2f} (80%)", True),
        ("🎁 Bonus", f"${bonus:,.2f}", True),
        ("💸 Total Cut", f"${total_cut:,.2f} ({percentage}% + Bonus)", True),
        ("🎭 Models", models_list, False)
    ]
    
    for name, value, inline in fields:
        embed.add_field(name=name, value=value, inline=inline)

    await ctx.send(embed=embed, files=valid_images)

@bot.command()
async def total(ctx, period: str, from_date: str = None, to_date: str = None, sender: str = None):
    guild_id = str(ctx.guild.id)
    valid_periods = period_data.get(guild_id, [])
    matched_period = next((p for p in valid_periods if p.lower() == period.lower()), None)
    if not matched_period:
        await ctx.send(f"❌ Period '{period}' not configured! Admins: use !calculateperiodset.")
        return
    period = matched_period

    try:
        await ctx.message.delete()
    except discord.Forbidden:
        await ctx.send("I don't have permission to delete messages!")
        return
    
    if sender is None:
        sender = ctx.author.mention

    if sender in earnings_by_sender:
        earnings = [e for e in earnings_by_sender[sender] if e["period"] == period.lower()]
        print(f"DEBUG: Earnings for {sender} in period {period}: {earnings}")  # Debug line
        if from_date and to_date:
            try:
                from_date_obj = datetime.strptime(from_date, "%d/%m/%Y")
                to_date_obj = datetime.strptime(to_date, "%d/%m/%Y")
                earnings = [entry for entry in earnings if from_date_obj <= datetime.strptime(entry["date"], "%d/%m/%Y") <= to_date_obj]
                print(f"DEBUG: Filtered earnings for {sender} between {from_date} and {to_date}: {earnings}")  # Debug line
            except ValueError:
                await ctx.send("Invalid date format. Please use DD/MM/YYYY.")
                return

        total_cut = sum(entry["total_cut"] for entry in earnings)
        
        if earnings:
            date_range = f"from {from_date} to {to_date}" if from_date and to_date else "for all time"
            await ctx.send(embed=discord.Embed(
                title="💰 Total Cut",
                description=f"**{sender}**'s total cut for {period} {date_range}:",
                color=discord.Color.green()
            ).add_field(name="💸 Total Cut", value=f"${total_cut:,.2f}", inline=False))
        else:
            await ctx.send(f"No earnings recorded for {sender} in the specified period and date range.")
    else:
        await ctx.send(f"No earnings recorded for {sender}.")
  
bot.run("")