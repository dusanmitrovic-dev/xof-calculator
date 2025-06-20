import discord
from discord import app_commands, ui
from discord.ext import commands
import logging
from datetime import datetime, timezone, timedelta
import uuid # For bonus/penalty IDs
from typing import Optional, List, Dict, Any

from config import settings # Now settings.py has DEFAULT_CLOCK_DATA and get_guild_clock_data_path
from utils import file_handlers

logger = logging.getLogger("xof_calculator.clock_in_tracker_slash")

DEFAULT_USER_CLOCK_STATE = {
    "status": "clocked_out", # "clocked_in", "on_break"
    "clock_in_time": None, # ISO string
    "break_start_time": None, # ISO string
    "breaks_taken_this_shift": 0,
    "accumulated_break_duration_seconds_this_shift": 0.0
}

def format_timedelta(td: timedelta) -> str:
    total_seconds = int(td.total_seconds())
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = []
    if days > 0: parts.append(f"{days}d")
    if hours > 0: parts.append(f"{hours}h")
    if minutes > 0: parts.append(f"{minutes}m")
    if seconds > 0 or not parts: parts.append(f"{seconds}s")
    
    return " ".join(parts) if parts else "0s"

class ClockInTrackerSlash(commands.Cog, name="clock_in_tracker"):
    def __init__(self, bot):
        self.bot = bot

    async def get_ephemeral_setting(self, guild_id):
        file_path = settings.get_guild_file(guild_id, settings.DISPLAY_SETTINGS_FILE)
        display_settings = await file_handlers.load_json(file_path, {
                "ephemeral_responses": True,
                "show_average": True,
                "agency_name": "Agency",
                "show_ids": True,
                "bot_name": "Shift Calculator"
        })
        guild_settings = display_settings
        return guild_settings.get('ephemeral_responses', 
            settings.DEFAULT_DISPLAY_SETTINGS['ephemeral_responses'])

    async def get_clock_data(self, guild_id: int) -> Dict[str, Any]:
        path = settings.get_guild_clock_data_path(guild_id)
        return await file_handlers.load_json(path, settings.DEFAULT_CLOCK_DATA)

    async def save_clock_data(self, guild_id: int, data: Dict[str, Any]):
        path = settings.get_guild_clock_data_path(guild_id)
        await file_handlers.save_json(path, data)

    async def get_user_clock_state(self, clock_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        user_id_str = str(user_id)
        if user_id_str not in clock_data["users"]:
            # clock_data["users"][user_id_str] = DEFAULT_USER_CLOCK_STATE.copy()
            clock_data["users"][user_id_str] = {
                "status": "clocked_out", # "clocked_in", "on_break"
                "clock_in_time": None, # ISO string
                "break_start_time": None, # ISO string
                "breaks_taken_this_shift": 0,
                "accumulated_break_duration_seconds_this_shift": 0.0
            }
        return clock_data["users"][user_id_str]

    async def has_bonus_penalty_permission(self, interaction: discord.Interaction) -> bool:
        if interaction.user.guild_permissions.administrator:
            return True
        
        clock_data = await self.get_clock_data(interaction.guild_id)
        manager_roles_ids = clock_data.get("settings", {}).get("bonus_penalty_manager_roles", [])
        
        member: discord.Member = interaction.user
        for role_id in manager_roles_ids:
            if discord.utils.get(member.roles, id=int(role_id)):
                return True
        return False

    # --- Settings Command Group ---
    clock_settings_group = app_commands.Group(name="clock-settings", description="Manage clock-in system settings.", default_permissions=discord.Permissions(administrator=True))

    @clock_settings_group.command(name="set-max-breaks", description="Set the maximum number of breaks allowed per shift.")
    @app_commands.describe(count="Maximum breaks (0 for unlimited).")
    async def set_max_breaks(self, interaction: discord.Interaction, count: app_commands.Range[int, 0, 20]):
        ephemeral = await self.get_ephemeral_setting(interaction.guild_id)
        clock_data = await self.get_clock_data(interaction.guild_id)
        
        clock_data.setdefault("settings", settings.DEFAULT_CLOCK_DATA["settings"].copy())
        clock_data["settings"]["max_breaks_per_shift"] = count
        
        await self.save_clock_data(interaction.guild_id, clock_data)
        await interaction.response.send_message(f"✅ Maximum breaks per shift set to {count}.", ephemeral=ephemeral)

    @clock_settings_group.command(name="add-manager-role", description="Add a role that can manage bonuses and penalties.")
    async def add_manager_role(self, interaction: discord.Interaction, role: discord.Role):
        ephemeral = await self.get_ephemeral_setting(interaction.guild_id)
        clock_data = await self.get_clock_data(interaction.guild_id)
        
        clock_data.setdefault("settings", settings.DEFAULT_CLOCK_DATA["settings"].copy())
        manager_roles = clock_data["settings"].setdefault("bonus_penalty_manager_roles", [])
        
        if str(role.id) not in manager_roles:
            manager_roles.append(str(role.id))
            await self.save_clock_data(interaction.guild_id, clock_data)
            await interaction.response.send_message(f"✅ Role {role.mention} can now manage bonuses/penalties.", ephemeral=ephemeral)
        else:
            await interaction.response.send_message(f"⚠️ Role {role.mention} is already a manager role.", ephemeral=ephemeral)

    @clock_settings_group.command(name="remove-manager-role", description="Remove a bonus/penalty manager role.")
    async def remove_manager_role(self, interaction: discord.Interaction, role: discord.Role):
        ephemeral = await self.get_ephemeral_setting(interaction.guild_id)
        clock_data = await self.get_clock_data(interaction.guild_id)

        manager_roles = clock_data.get("settings", {}).get("bonus_penalty_manager_roles", [])
        role_id_str = str(role.id)

        if role_id_str in manager_roles:
            manager_roles.remove(role_id_str)
            await self.save_clock_data(interaction.guild_id, clock_data)
            await interaction.response.send_message(f"✅ Role {role.mention} can no longer manage bonuses/penalties.", ephemeral=ephemeral)
        else:
            await interaction.response.send_message(f"⚠️ Role {role.mention} was not a manager role.", ephemeral=ephemeral)

    @clock_settings_group.command(name="view", description="View current clock-in system settings.")
    async def view_clock_settings(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild_id)
        clock_data = await self.get_clock_data(interaction.guild_id)
        settings_data = clock_data.get("settings", settings.DEFAULT_CLOCK_DATA["settings"])

        max_breaks = settings_data.get("max_breaks_per_shift", 3)
        manager_role_ids = settings_data.get("bonus_penalty_manager_roles", [])
        
        manager_roles_mentions = []
        for role_id_str in manager_role_ids:
            role = interaction.guild.get_role(int(role_id_str))
            if role:
                manager_roles_mentions.append(role.mention)
        
        manager_roles_display = ", ".join(manager_roles_mentions) if manager_roles_mentions else "None"

        embed = discord.Embed(title="🕒 Clock System Settings", color=discord.Color.blue())
        embed.add_field(name="Max Breaks Per Shift", value=str(max_breaks), inline=False)
        embed.add_field(name="Bonus/Penalty Manager Roles", value=manager_roles_display, inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)

    # --- Main Clocking Commands ---
    @app_commands.command(name="clock-in", description="Clock in to start your shift.")
    async def clock_in(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild_id)
        clock_data = await self.get_clock_data(interaction.guild_id)
        user_state = await self.get_user_clock_state(clock_data, interaction.user.id)

        if user_state["status"] == "clocked_in":
            await interaction.response.send_message("❌ You are already clocked in.", ephemeral=ephemeral)
            return
        if user_state["status"] == "on_break":
            await interaction.response.send_message("❌ You are currently on break. Use `/back` before clocking in again (or clock out).", ephemeral=ephemeral)
            return

        user_state["status"] = "clocked_in"
        user_state["clock_in_time"] = datetime.now(timezone.utc).isoformat()
        user_state["breaks_taken_this_shift"] = 0
        user_state["accumulated_break_duration_seconds_this_shift"] = 0.0
        user_state["break_start_time"] = None

        await self.save_clock_data(interaction.guild_id, clock_data)
        await interaction.response.send_message(f"✅ {interaction.user.mention}, you have clocked in at <t:{int(datetime.now(timezone.utc).timestamp())}:F>.", ephemeral=ephemeral)

    @app_commands.command(name="clock-out", description="Clock out to end your shift.")
    async def clock_out(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild_id)
        clock_data = await self.get_clock_data(interaction.guild_id)
        user_state = await self.get_user_clock_state(clock_data, interaction.user.id)

        if user_state["status"] == "clocked_out":
            await interaction.response.send_message("❌ You are not clocked in.", ephemeral=ephemeral)
            return

        now_utc = datetime.now(timezone.utc)
        
        # If user is on break, end the break first
        if user_state["status"] == "on_break" and user_state["break_start_time"]:
            break_start_dt = datetime.fromisoformat(user_state["break_start_time"])
            current_break_duration = now_utc - break_start_dt
            user_state["accumulated_break_duration_seconds_this_shift"] += current_break_duration.total_seconds()
            user_state["break_start_time"] = None # End the break
            logger.info(f"User {interaction.user.id} was on break, auto-ended break of {format_timedelta(current_break_duration)} during clock-out.")

        if not user_state["clock_in_time"]:
            await interaction.response.send_message("❌ Error: Clock-in time not found. Please contact an admin.", ephemeral=ephemeral)
            logger.error(f"User {interaction.user.id} tried to clock out but clock_in_time was null. State: {user_state}")
            return
            
        clock_in_dt = datetime.fromisoformat(user_state["clock_in_time"])
        total_shift_duration = now_utc - clock_in_dt
        total_work_duration_seconds = total_shift_duration.total_seconds() - user_state["accumulated_break_duration_seconds_this_shift"]
        total_work_duration = timedelta(seconds=max(0, total_work_duration_seconds)) # Ensure non-negative

        embed = discord.Embed(title="🕒 Shift Ended", color=discord.Color.green(), timestamp=now_utc)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        embed.add_field(name="Clocked In At", value=f"<t:{int(clock_in_dt.timestamp())}:F>", inline=False)
        embed.add_field(name="Clocked Out At", value=f"<t:{int(now_utc.timestamp())}:F>", inline=False)
        embed.add_field(name="Total Shift Duration", value=format_timedelta(total_shift_duration), inline=True)
        embed.add_field(name="Breaks Taken", value=str(user_state["breaks_taken_this_shift"]), inline=True)
        embed.add_field(name="Total Break Time", value=format_timedelta(timedelta(seconds=user_state["accumulated_break_duration_seconds_this_shift"])), inline=True)
        embed.add_field(name="⏱️ Total Time Worked", value=f"**{format_timedelta(total_work_duration)}**", inline=False)

        # Reset user state for next shift
        user_state["status"] = "clocked_out"
        user_state["clock_in_time"] = None
        user_state["break_start_time"] = None
        # Keep break counts and duration for historical record if needed, or reset them:
        # user_state["breaks_taken_this_shift"] = 0 
        # user_state["accumulated_break_duration_seconds_this_shift"] = 0.0

        await self.save_clock_data(interaction.guild_id, clock_data)
        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)

    @app_commands.command(name="break", description="Start a break.")
    async def start_break(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild_id)
        clock_data = await self.get_clock_data(interaction.guild_id)
        user_state = await self.get_user_clock_state(clock_data, interaction.user.id)
        max_breaks = clock_data.get("settings", {}).get("max_breaks_per_shift", 3)

        if user_state["status"] != "clocked_in":
            await interaction.response.send_message("❌ You must be clocked in to start a break.", ephemeral=ephemeral)
            return
        if user_state["status"] == "on_break":
            await interaction.response.send_message("❌ You are already on break.", ephemeral=ephemeral)
            return
        
        if max_breaks > 0 and user_state["breaks_taken_this_shift"] >= max_breaks:
            await interaction.response.send_message(f"❌ You have reached the maximum of {max_breaks} breaks for this shift.", ephemeral=ephemeral)
            return

        user_state["status"] = "on_break"
        user_state["break_start_time"] = datetime.now(timezone.utc).isoformat()
        user_state["breaks_taken_this_shift"] += 1

        await self.save_clock_data(interaction.guild_id, clock_data)
        await interaction.response.send_message(f"休憩 {interaction.user.mention}, your break has started at <t:{int(datetime.now(timezone.utc).timestamp())}:T>. Enjoy!", ephemeral=ephemeral) # 休憩 is "break" in Japanese, for fun

    @app_commands.command(name="back", description="Return from your break.")
    async def end_break(self, interaction: discord.Interaction):
        ephemeral = await self.get_ephemeral_setting(interaction.guild_id)
        clock_data = await self.get_clock_data(interaction.guild_id)
        user_state = await self.get_user_clock_state(clock_data, interaction.user.id)

        if user_state["status"] != "on_break":
            await interaction.response.send_message("❌ You are not currently on a break.", ephemeral=ephemeral)
            return
        
        if not user_state["break_start_time"]:
            await interaction.response.send_message("❌ Error: Break start time not found. Please contact an admin.", ephemeral=ephemeral)
            logger.error(f"User {interaction.user.id} tried to end break but break_start_time was null. State: {user_state}")
            return

        now_utc = datetime.now(timezone.utc)
        break_start_dt = datetime.fromisoformat(user_state["break_start_time"])
        current_break_duration = now_utc - break_start_dt
        
        user_state["accumulated_break_duration_seconds_this_shift"] += current_break_duration.total_seconds()
        user_state["status"] = "clocked_in"
        user_state["break_start_time"] = None

        await self.save_clock_data(interaction.guild_id, clock_data)
        
        embed = discord.Embed(title="🧘 Break Ended", color=discord.Color.orange(), timestamp=now_utc)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        embed.description = f"Welcome back, {interaction.user.mention}!"
        embed.add_field(name="Break Duration", value=format_timedelta(current_break_duration), inline=False)
        embed.add_field(name="Total Breaks This Shift", value=str(user_state["breaks_taken_this_shift"]), inline=True)
        embed.add_field(name="Total Break Time This Shift", value=format_timedelta(timedelta(seconds=user_state["accumulated_break_duration_seconds_this_shift"])), inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)

    # --- Bonus/Penalty Command Groups ---
    bonus_group = app_commands.Group(name="bonus", description="Manage bonuses.")
    penalty_group = app_commands.Group(name="penalty", description="Manage penalties.")

    async def _add_bonus_penalty(self, interaction: discord.Interaction, user: discord.User, amount: float, item_type: str, reason: Optional[str] = None):
        ephemeral = await self.get_ephemeral_setting(interaction.guild_id)
        if not await self.has_bonus_penalty_permission(interaction):
            await interaction.response.send_message("❌ You do not have permission to manage bonuses/penalties.", ephemeral=True)
            return
        
        if amount <= 0:
            await interaction.response.send_message(f"❌ Amount for {item_type} must be positive.", ephemeral=ephemeral)
            return

        clock_data = await self.get_clock_data(interaction.guild_id)
        user_bp_list = clock_data["bonuses_penalties"].setdefault(str(user.id), [])
        
        item_id = str(uuid.uuid4())
        new_item = {
            "id": item_id,
            "type": item_type,
            "amount": round(amount, 2),
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "giver_id": str(interaction.user.id)
        }
        user_bp_list.append(new_item)
        
        await self.save_clock_data(interaction.guild_id, clock_data)
        
        action_verb = "added" if item_type == "bonus" else "applied"
        reason_text = f" for '{reason}'" if reason else ""
        await interaction.response.send_message(f"✅ {item_type.capitalize()} of ${amount:.2f} {action_verb} to {user.mention}{reason_text}. (ID: `{item_id[:8]}`)", ephemeral=ephemeral)

    async def _remove_bonus_penalty(self, interaction: discord.Interaction, user: discord.User, item_id: str, item_type: str):
        ephemeral = await self.get_ephemeral_setting(interaction.guild_id)
        if not await self.has_bonus_penalty_permission(interaction):
            await interaction.response.send_message("❌ You do not have permission to manage bonuses/penalties.", ephemeral=True)
            return

        clock_data = await self.get_clock_data(interaction.guild_id)
        user_bp_list = clock_data["bonuses_penalties"].get(str(user.id), [])
        
        item_to_remove = None
        for item in user_bp_list:
            if item["id"].startswith(item_id) and item["type"] == item_type: # Allow partial ID match for convenience
                item_to_remove = item
                break
        
        if item_to_remove:
            user_bp_list.remove(item_to_remove)
            await self.save_clock_data(interaction.guild_id, clock_data)
            await interaction.response.send_message(f"✅ {item_type.capitalize()} (ID: `{item_to_remove['id'][:8]}`) of ${item_to_remove['amount']:.2f} removed from {user.mention}.", ephemeral=ephemeral)
        else:
            await interaction.response.send_message(f"❌ No active {item_type} found for {user.mention} with ID starting with `{item_id}`.", ephemeral=ephemeral)

    async def _list_bonus_penalty(self, interaction: discord.Interaction, target_user: discord.User, item_type: str):
        ephemeral = await self.get_ephemeral_setting(interaction.guild_id)
        
        # If listing for another user, check permission
        if target_user.id != interaction.user.id and not await self.has_bonus_penalty_permission(interaction):
            await interaction.response.send_message(f"❌ You do not have permission to view other users' {item_type}s.", ephemeral=True)
            return

        clock_data = await self.get_clock_data(interaction.guild_id)
        user_bp_list = [item for item in clock_data["bonuses_penalties"].get(str(target_user.id), []) if item["type"] == item_type]

        if not user_bp_list:
            await interaction.response.send_message(f"ℹ️ {target_user.mention} has no active {item_type}s.", ephemeral=ephemeral)
            return

        embed = discord.Embed(title=f"Active {item_type.capitalize()}s for {target_user.display_name}", color=discord.Color.blue())
        description_parts = []
        for item in user_bp_list:
            giver = interaction.guild.get_member(int(item["giver_id"]))
            giver_name = giver.display_name if giver else "Unknown Giver"
            reason_text = f"Reason: {item['reason']}" if item.get('reason') else "No reason provided"
            added_at = f"<t:{int(datetime.fromisoformat(item['timestamp']).timestamp())}:R>"
            description_parts.append(
                f"💰 **${item['amount']:.2f}** - {reason_text}\n"
                f"🆔 `ID: {item['id'][:8]}` | 🤵 Given by: {giver_name} | ⏳ Added: {added_at}"
            )
        embed.description = "\n\n".join(description_parts)
        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)

    # Bonus Commands
    @bonus_group.command(name="add", description="Add a bonus to a user.")
    @app_commands.describe(user="The user to receive the bonus", amount="The bonus amount (e.g., 10.50)", reason="Optional reason for the bonus")
    async def add_bonus(self, interaction: discord.Interaction, user: discord.User, amount: app_commands.Range[float, 0.01, 10000.0], reason: Optional[str] = None):
        await self._add_bonus_penalty(interaction, user, amount, "bonus", reason)

    @bonus_group.command(name="remove", description="Remove an active bonus from a user.")
    @app_commands.describe(user="The user whose bonus to remove", bonus_id="The ID (or start of ID) of the bonus to remove")
    async def remove_bonus(self, interaction: discord.Interaction, user: discord.User, bonus_id: str):
        await self._remove_bonus_penalty(interaction, user, bonus_id, "bonus")

    @bonus_group.command(name="list", description="List active bonuses for a user.")
    @app_commands.describe(user="The user whose bonuses to list (optional, defaults to yourself)")
    async def list_bonuses(self, interaction: discord.Interaction, user: Optional[discord.User] = None):
        target_user = user or interaction.user
        await self._list_bonus_penalty(interaction, target_user, "bonus")

    # Penalty Commands
    @penalty_group.command(name="add", description="Add a penalty to a user.")
    @app_commands.describe(user="The user to receive the penalty", amount="The penalty amount (e.g., 5.00)", reason="Optional reason for the penalty")
    async def add_penalty(self, interaction: discord.Interaction, user: discord.User, amount: app_commands.Range[float, 0.01, 10000.0], reason: Optional[str] = None):
        await self._add_bonus_penalty(interaction, user, amount, "penalty", reason)

    @penalty_group.command(name="remove", description="Remove an active penalty from a user.")
    @app_commands.describe(user="The user whose penalty to remove", penalty_id="The ID (or start of ID) of the penalty to remove")
    async def remove_penalty(self, interaction: discord.Interaction, user: discord.User, penalty_id: str):
        await self._remove_bonus_penalty(interaction, user, penalty_id, "penalty")

    @penalty_group.command(name="list", description="List active penalties for a user.")
    @app_commands.describe(user="The user whose penalties to list (optional, defaults to yourself)")
    async def list_penalties(self, interaction: discord.Interaction, user: Optional[discord.User] = None):
        target_user = user or interaction.user
        await self._list_bonus_penalty(interaction, target_user, "penalty")

async def setup(bot):
    await bot.add_cog(ClockInTrackerSlash(bot))
    logger.info("ClockInTrackerSlash cog loaded.")