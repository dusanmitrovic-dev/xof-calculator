import discord
from discord import app_commands, ui
from discord.ext import commands
import logging
from datetime import datetime, timezone, timedelta
import uuid
from typing import Optional, List, Dict, Any

from config import settings
from utils import file_handlers

logger = logging.getLogger("xof_calculator.clock_in_tracker_slash")

DEFAULT_USER_CLOCK_STATE = {
    "status": "clocked_out",
    "clock_in_time": None,
    "break_start_time": None,
    "breaks_taken_this_shift": 0,
    "accumulated_break_duration_seconds_this_shift": 0.0
}

def format_timedelta(td: timedelta, show_seconds=True) -> str:
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = []
    if hours > 0: parts.append(f"{hours}h")
    if minutes > 0: parts.append(f"{minutes}m")
    if show_seconds and (seconds > 0 or not parts):
        parts.append(f"{seconds}s")
    
    return " ".join(parts) if parts else ("0s" if show_seconds else "0m")


class ClockInTrackerSlash(commands.Cog, name="clock_in_tracker"):
    def __init__(self, bot):
        self.bot = bot

    async def get_guild_display_settings(self, guild_id: int) -> Dict[str, Any]:
        file_path = settings.get_guild_display_path(guild_id)
        return await file_handlers.load_json(file_path, settings.DEFAULT_DISPLAY_SETTINGS)

    async def get_clock_data(self, guild_id: int) -> Dict[str, Any]:
        path = settings.get_guild_clock_data_path(guild_id)
        return await file_handlers.load_json(path, settings.DEFAULT_CLOCK_DATA)

    async def save_clock_data(self, guild_id: int, data: Dict[str, Any]):
        path = settings.get_guild_clock_data_path(guild_id)
        await file_handlers.save_json(path, data)

    async def get_user_clock_state(self, clock_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        user_id_str = str(user_id)
        if user_id_str not in clock_data["users"]:
            clock_data["users"][user_id_str] = DEFAULT_USER_CLOCK_STATE.copy()
        return clock_data["users"][user_id_str]

    async def has_bonus_penalty_permission(self, interaction: discord.Interaction) -> bool:
        if interaction.user.guild_permissions.administrator:
            return True
        clock_data = await self.get_clock_data(interaction.guild_id)
        manager_roles_ids = clock_data.get("settings", {}).get("bonus_penalty_manager_roles", [])
        member: discord.Member = interaction.user
        for role_id_str in manager_roles_ids:
            try:
                if discord.utils.get(member.roles, id=int(role_id_str)):
                    return True
            except ValueError:
                logger.warning(f"Invalid role ID '{role_id_str}' in manager roles for guild {interaction.guild_id}")
        return False

    async def should_display_public_clock_event(self, guild_id: int) -> bool:
        clock_data = await self.get_clock_data(guild_id)
        return clock_data.get("settings", {}).get("display_public_clock_embeds", True)

    async def send_response(
        self, interaction: discord.Interaction, message: Optional[str] = None, 
        embed: Optional[discord.Embed] = None, ephemeral: Optional[bool] = None,
        is_public_event: bool = False, is_error: bool = False
    ):
        display_settings = await self.get_guild_display_settings(interaction.guild_id)
        ephemeral = display_settings.get('ephemeral_responses', True)
        # Determine the final ephemeral status
        final_ephemeral: bool
        if ephemeral is not None: # Explicit ephemeral override
            final_ephemeral = ephemeral
        elif is_error: # Errors are always ephemeral
            final_ephemeral = True
        elif is_public_event: # Public events are never ephemeral
            final_ephemeral = False
        else: # General command responses respect guild setting
            display_settings = await self.get_guild_display_settings(interaction.guild_id)
            final_ephemeral = display_settings.get('ephemeral_responses', True)
        
        if not message and not embed:
            logger.warning("send_response called with no message or embed.")
            # Send an ephemeral error message if possible, otherwise log
            try:
                await interaction.response.send_message("An internal error occurred.", ephemeral=ephemeral)
            except discord.errors.InteractionResponded:
                await interaction.followup.send("An internal error occurred.", ephemeral=ephemeral)
            except Exception as e:
                logger.error(f"Failed to send internal error message: {e}")
            return

        try:
            if interaction.response.is_done():
                if embed:
                    await interaction.followup.send(embed=embed, ephemeral=final_ephemeral)
                else:
                    await interaction.followup.send(content=message, ephemeral=final_ephemeral)
            else:
                if embed:
                    await interaction.response.send_message(embed=embed, ephemeral=final_ephemeral)
                else:
                    await interaction.response.send_message(content=message, ephemeral=final_ephemeral)
        except Exception as e:
            logger.error(f"Error sending response in send_response: {e}")
            # Fallback if initial response failed
            try:
                await interaction.followup.send("There was an issue sending the response.", ephemeral=ephemeral)
            except Exception as followup_e:
                 logger.error(f"Error sending followup in send_response: {followup_e}")


    # --- Settings Command Group ---
    clock_settings_group = app_commands.Group(
        name="clock-settings", description="Manage clock-in system settings.",
        default_permissions=discord.Permissions(administrator=True)
    )

    @clock_settings_group.command(name="set-max-breaks", description="Set the maximum number of breaks allowed per shift.")
    @app_commands.describe(count="Maximum breaks (0 for unlimited).")
    async def set_max_breaks(self, interaction: discord.Interaction, count: app_commands.Range[int, 0, 20]):
        clock_data = await self.get_clock_data(interaction.guild_id)
        clock_data.setdefault("settings", settings.DEFAULT_CLOCK_DATA["settings"].copy())
        clock_data["settings"]["max_breaks_per_shift"] = count
        await self.save_clock_data(interaction.guild_id, clock_data)
        await self.send_response(interaction, message=f"🛠️ Maximum breaks per shift updated to **{count}**.")

    @clock_settings_group.command(name="set-max-break-duration", description="Set max allowed duration for a single break (in minutes).")
    @app_commands.describe(minutes="Max duration in minutes (0 for unlimited).")
    async def set_max_break_duration(self, interaction: discord.Interaction, minutes: app_commands.Range[int, 0, 1440]):
        clock_data = await self.get_clock_data(interaction.guild_id)
        clock_data.setdefault("settings", settings.DEFAULT_CLOCK_DATA["settings"].copy())
        clock_data["settings"]["max_break_duration_minutes"] = minutes
        await self.save_clock_data(interaction.guild_id, clock_data)
        duration_text = f"**{minutes} minutes**" if minutes > 0 else "**unlimited**"
        await self.send_response(interaction, message=f"🛠️ Maximum break duration set to {duration_text}.")

    @clock_settings_group.command(name="add-manager-role", description="Allow a role to manage bonuses and penalties.")
    @app_commands.describe(role="The role to grant manager permissions.")
    async def add_manager_role(self, interaction: discord.Interaction, role: discord.Role):
        clock_data = await self.get_clock_data(interaction.guild_id)
        clock_data.setdefault("settings", settings.DEFAULT_CLOCK_DATA["settings"].copy())
        manager_roles = clock_data["settings"].setdefault("bonus_penalty_manager_roles", [])
        if str(role.id) not in manager_roles:
            manager_roles.append(str(role.id))
            await self.save_clock_data(interaction.guild_id, clock_data)
            await self.send_response(interaction, message=f"🛠️ Role {role.mention} can now manage bonuses/penalties.")
        else:
            await self.send_response(interaction, message=f"⚠️ Role {role.mention} is already a manager.", is_error=True)

    @clock_settings_group.command(name="remove-manager-role", description="Revoke manager permissions for bonuses/penalties.")
    @app_commands.describe(role="The role to remove manager permissions from.")
    async def remove_manager_role(self, interaction: discord.Interaction, role: discord.Role):
        clock_data = await self.get_clock_data(interaction.guild_id)
        manager_roles = clock_data.get("settings", {}).get("bonus_penalty_manager_roles", [])
        if str(role.id) in manager_roles:
            manager_roles.remove(str(role.id))
            await self.save_clock_data(interaction.guild_id, clock_data)
            await self.send_response(interaction, message=f"🛠️ Role {role.mention} can no longer manage bonuses/penalties.")
        else:
            await self.send_response(interaction, message=f"⚠️ Role {role.mention} was not a manager.", is_error=True)
            
    @clock_settings_group.command(name="toggle-public-clock-events", description="Toggle public display of clock-in/out/break embeds.")
    async def toggle_public_clock_events(self, interaction: discord.Interaction):
        clock_data = await self.get_clock_data(interaction.guild_id)
        clock_data.setdefault("settings", settings.DEFAULT_CLOCK_DATA["settings"].copy())
        current_setting = clock_data["settings"].get("display_public_clock_embeds", True)
        new_setting = not current_setting
        clock_data["settings"]["display_public_clock_embeds"] = new_setting
        await self.save_clock_data(interaction.guild_id, clock_data)
        status_text = "ENABLED" if new_setting else "DISABLED"
        await self.send_response(interaction, message=f"🛠️ Public clock event announcements are now **{status_text}**.")

    @clock_settings_group.command(name="view", description="View current clock system configuration.")
    async def view_clock_settings(self, interaction: discord.Interaction):
        clock_data = await self.get_clock_data(interaction.guild_id)
        settings_data = clock_data.get("settings", settings.DEFAULT_CLOCK_DATA["settings"].copy())

        max_breaks = settings_data.get("max_breaks_per_shift", 3)
        max_break_duration_min = settings_data.get("max_break_duration_minutes", 0)
        display_public_events = settings_data.get("display_public_clock_embeds", True)
        manager_role_ids = settings_data.get("bonus_penalty_manager_roles", [])
        
        manager_roles_mentions = [
            role.mention for role_id_str in manager_role_ids 
            if (role := interaction.guild.get_role(int(role_id_str)))
        ]
        manager_roles_display = ", ".join(manager_roles_mentions) if manager_roles_mentions else "None"
        display_events_status = "Enabled" if display_public_events else "Disabled"
        max_break_duration_display = f"{max_break_duration_min} minutes" if max_break_duration_min > 0 else "Unlimited"

        embed = discord.Embed(title="Clock System Configuration", color=discord.Color.blue(), timestamp=datetime.now(timezone.utc))
        embed.add_field(name="Max Breaks / Shift", value=f"`{max_breaks}`", inline=True)
        embed.add_field(name="Max Break Duration", value=f"`{max_break_duration_display}`", inline=True)
        embed.add_field(name="Public Clock Events", value=f"`{display_events_status}`", inline=True)
        embed.add_field(name="Bonus/Penalty Managers", value=manager_roles_display, inline=False)
        
        await self.send_response(interaction, embed=embed) # Uses guild ephemeral by default

    # --- Main Clocking Commands ---
    @app_commands.command(name="clock-in", description="Clock in to start your shift.")
    async def clock_in(self, interaction: discord.Interaction):
        clock_data = await self.get_clock_data(interaction.guild_id)
        user_state = await self.get_user_clock_state(clock_data, interaction.user.id)

        if user_state["status"] == "clocked_in":
            await self.send_response(interaction, message="❌ You are already clocked in.", is_error=True)
            return
        if user_state["status"] == "on_break":
            await self.send_response(interaction, message="❌ You are on break. Use `/back` first.", is_error=True)
            return

        user_state["status"] = "clocked_in"
        current_time_utc = datetime.now(timezone.utc)
        user_state["clock_in_time"] = current_time_utc.isoformat()
        user_state["breaks_taken_this_shift"] = 0
        user_state["accumulated_break_duration_seconds_this_shift"] = 0.0
        user_state["break_start_time"] = None
        await self.save_clock_data(interaction.guild_id, clock_data)
        
        if await self.should_display_public_clock_event(interaction.guild_id):
            embed = discord.Embed(
                description=f"✅ {interaction.user.mention} has **clocked in**.",
                color=discord.Color.green(), timestamp=current_time_utc
            )
            await self.send_response(interaction, embed=embed, is_public_event=True)
        else:
            await self.send_response(interaction, message=f"✅ Clocked in at <t:{int(current_time_utc.timestamp())}:T>.")

    @app_commands.command(name="clock-out", description="Clock out to end your shift.")
    async def clock_out(self, interaction: discord.Interaction):
        clock_data = await self.get_clock_data(interaction.guild_id)
        user_state = await self.get_user_clock_state(clock_data, interaction.user.id)

        if user_state["status"] == "clocked_out":
            await self.send_response(interaction, message="❌ You are not clocked in.", is_error=True)
            return

        now_utc = datetime.now(timezone.utc)
        if user_state["status"] == "on_break" and user_state["break_start_time"]:
            break_start_dt = datetime.fromisoformat(user_state["break_start_time"])
            current_break_duration = now_utc - break_start_dt
            user_state["accumulated_break_duration_seconds_this_shift"] += current_break_duration.total_seconds()
            user_state["break_start_time"] = None
            logger.info(f"User {interaction.user.id} auto-ended break of {format_timedelta(current_break_duration)} during clock-out.")

        if not user_state["clock_in_time"]:
            await self.send_response(interaction, message="❌ Error: Clock-in time missing.", is_error=True)
            logger.error(f"User {interaction.user.id} clock_out error: clock_in_time missing. State: {user_state}")
            return
            
        clock_in_dt = datetime.fromisoformat(user_state["clock_in_time"])
        total_shift_duration_td = now_utc - clock_in_dt
        total_work_duration_seconds = total_shift_duration_td.total_seconds() - user_state["accumulated_break_duration_seconds_this_shift"]
        total_work_duration_td = timedelta(seconds=max(0, total_work_duration_seconds))

        user_state["status"] = "clocked_out"
        user_state["clock_in_time"] = None
        await self.save_clock_data(interaction.guild_id, clock_data)

        max_breaks_config = clock_data.get("settings", {}).get("max_breaks_per_shift", 3)
        breaks_display = f"{user_state['breaks_taken_this_shift']}"
        if max_breaks_config > 0:
            breaks_display += f"/{max_breaks_config}"

        if await self.should_display_public_clock_event(interaction.guild_id):
            embed = discord.Embed(
                title=f"Shift Ended: {interaction.user.display_name}",
                color=discord.Color.gold(), timestamp=now_utc
            )
            embed.set_thumbnail(url=interaction.user.display_avatar.url if interaction.user.display_avatar else None)
            embed.add_field(name="Total Time Worked", value=f"**{format_timedelta(total_work_duration_td)}**", inline=False)
            embed.add_field(name="Shift Duration", value=format_timedelta(total_shift_duration_td), inline=True)
            embed.add_field(name="Breaks Taken", value=breaks_display, inline=True)
            embed.add_field(name="Total Break Time", value=format_timedelta(timedelta(seconds=user_state["accumulated_break_duration_seconds_this_shift"])), inline=True)
            await self.send_response(interaction, embed=embed, is_public_event=True)
        else:
            await self.send_response(
                interaction, 
                message=f"✅ Clocked out. Time worked: **{format_timedelta(total_work_duration_td)}**. Breaks: {breaks_display}."
            )

    @app_commands.command(name="break", description="Start a break (must be clocked in).")
    async def start_break(self, interaction: discord.Interaction):
        clock_data = await self.get_clock_data(interaction.guild_id)
        user_state = await self.get_user_clock_state(clock_data, interaction.user.id)
        max_breaks_config = clock_data.get("settings", {}).get("max_breaks_per_shift", 3)

        if user_state["status"] == "on_break":
            await self.send_response(interaction, message="❌ You are already on break.", is_error=True)
            return
        if user_state["status"] != "clocked_in":
            await self.send_response(interaction, message="❌ You must be clocked in to start a break.", is_error=True)
            return
        
        if max_breaks_config > 0 and user_state["breaks_taken_this_shift"] >= max_breaks_config:
            await self.send_response(interaction, message=f"❌ Max breaks ({max_breaks_config}) reached.", is_error=True)
            return

        user_state["status"] = "on_break"
        current_time_utc = datetime.now(timezone.utc)
        user_state["break_start_time"] = current_time_utc.isoformat()
        user_state["breaks_taken_this_shift"] += 1
        await self.save_clock_data(interaction.guild_id, clock_data)

        if await self.should_display_public_clock_event(interaction.guild_id):
            embed = discord.Embed(
                description=f"⏸️ {interaction.user.mention} is now **on break**.",
                color=discord.Color.from_rgb(170, 170, 170), 
                timestamp=current_time_utc
            )
            await self.send_response(interaction, embed=embed, is_public_event=True)
        else:
            await self.send_response(interaction, message=f"✅ Break started at <t:{int(current_time_utc.timestamp())}:T>.")

    @app_commands.command(name="back", description="Return from your break.")
    async def end_break(self, interaction: discord.Interaction):
        clock_data = await self.get_clock_data(interaction.guild_id)
        user_state = await self.get_user_clock_state(clock_data, interaction.user.id)
        settings_data = clock_data.get("settings", {})
        max_break_duration_minutes = settings_data.get("max_break_duration_minutes", 0)

        if user_state["status"] != "on_break":
            await self.send_response(interaction, message="❌ You are not currently on a break.", is_error=True)
            return
        if not user_state["break_start_time"]:
            await self.send_response(interaction, message="❌ Error: Break start time missing.", is_error=True)
            logger.error(f"User {interaction.user.id} end_break error: break_start_time missing. State: {user_state}")
            return

        now_utc = datetime.now(timezone.utc)
        break_start_dt = datetime.fromisoformat(user_state["break_start_time"])
        current_break_duration_td = now_utc - break_start_dt
        
        user_state["accumulated_break_duration_seconds_this_shift"] += current_break_duration_td.total_seconds()
        user_state["status"] = "clocked_in"
        user_state["break_start_time"] = None
        await self.save_clock_data(interaction.guild_id, clock_data)
        
        overstayed_message = ""
        if max_break_duration_minutes > 0:
            allowed_duration_seconds = max_break_duration_minutes * 60
            if current_break_duration_td.total_seconds() > allowed_duration_seconds:
                overstayed_seconds = current_break_duration_td.total_seconds() - allowed_duration_seconds
                overstayed_td = timedelta(seconds=overstayed_seconds)
                overstayed_message = f"\n🔴 Overstayed by: {format_timedelta(overstayed_td, show_seconds=False)}"

        max_breaks_config = clock_data.get("settings", {}).get("max_breaks_per_shift", 3)
        breaks_display = f"{user_state['breaks_taken_this_shift']}"
        if max_breaks_config > 0:
            breaks_display += f"/{max_breaks_config}"

        if await self.should_display_public_clock_event(interaction.guild_id):
            embed = discord.Embed(
                description=f"▶️ {interaction.user.mention} is **back from break**.{overstayed_message}",
                color=discord.Color.from_rgb(100,100,100),
                timestamp=now_utc
            )
            embed.add_field(name="Break Duration", value=format_timedelta(current_break_duration_td), inline=True)
            embed.add_field(name="Breaks Taken", value=breaks_display, inline=True)
            await self.send_response(interaction, embed=embed, is_public_event=True)
        else:
            await self.send_response(
                interaction, 
                message=f"✅ Welcome back! Break duration: {format_timedelta(current_break_duration_td)}.{overstayed_message}"
            )

    # --- Bonus/Penalty Command Groups ---
    bonus_group = app_commands.Group(name="bonus", description="Manage bonuses for users.")
    penalty_group = app_commands.Group(name="penalty", description="Manage penalties for users.")

    async def _add_bonus_penalty(self, interaction: discord.Interaction, user: discord.User, amount: float, item_type: str, reason: Optional[str] = None):
        if not await self.has_bonus_penalty_permission(interaction):
            await self.send_response(interaction, message="❌ Permission denied.", is_error=True)
            return
        if amount <= 0:
            await self.send_response(interaction, message=f"❌ Amount must be positive.", is_error=True)
            return

        clock_data = await self.get_clock_data(interaction.guild_id)
        user_bp_list = clock_data["bonuses_penalties"].setdefault(str(user.id), [])
        item_id = str(uuid.uuid4())
        new_item = {
            "id": item_id, "type": item_type, "amount": round(amount, 2),
            "reason": reason, "timestamp": datetime.now(timezone.utc).isoformat(),
            "giver_id": str(interaction.user.id)
        }
        user_bp_list.append(new_item)
        await self.save_clock_data(interaction.guild_id, clock_data)
        
        action_verb = "Added" if item_type == "bonus" else "Applied"
        embed_color = discord.Color.green() if item_type == "bonus" else discord.Color.red()
        reason_display = f"\nReason: _{reason}_" if reason else ""
        
        embed = discord.Embed(
            title=f"{item_type.capitalize()} {action_verb}",
            description=f"**${amount:.2f}** {item_type} {action_verb.lower()} to {user.mention}.{reason_display}",
            color=embed_color, timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="ID", value=f"`{item_id[:8]}`", inline=False)
        embed.set_footer(text=f"By: {interaction.user.display_name}")
        await self.send_response(interaction, embed=embed) # Respects guild ephemeral for admin actions

    async def _remove_bonus_penalty(self, interaction: discord.Interaction, user: discord.User, item_id_prefix: str, item_type: str):
        if not await self.has_bonus_penalty_permission(interaction):
            await self.send_response(interaction, message="❌ Permission denied.", is_error=True)
            return

        clock_data = await self.get_clock_data(interaction.guild_id)
        user_bp_list = clock_data["bonuses_penalties"].get(str(user.id), [])
        item_to_remove = next((item for item in user_bp_list if item["id"].startswith(item_id_prefix) and item["type"] == item_type), None)
        
        if item_to_remove:
            user_bp_list.remove(item_to_remove)
            await self.save_clock_data(interaction.guild_id, clock_data)
            embed = discord.Embed(
                title=f"{item_type.capitalize()} Removed",
                description=f"Removed **${item_to_remove['amount']:.2f}** {item_type} (ID: `{item_to_remove['id'][:8]}`) from {user.mention}.",
                color=discord.Color.dark_grey(), timestamp=datetime.now(timezone.utc)
            )
            embed.set_footer(text=f"By: {interaction.user.display_name}")
            await self.send_response(interaction, embed=embed) # Respects guild ephemeral
        else:
            await self.send_response(interaction, message=f"❌ No {item_type} for {user.mention} with ID starting `{item_id_prefix}`.", is_error=True)

    async def _list_bonus_penalty(self, interaction: discord.Interaction, target_user: discord.User, item_type: str):
        if target_user.id != interaction.user.id and not await self.has_bonus_penalty_permission(interaction):
            await self.send_response(interaction, message=f"❌ Permission to view others' {item_type}s denied.", is_error=True)
            return

        clock_data = await self.get_clock_data(interaction.guild_id)
        user_bp_list = sorted(
            [item for item in clock_data["bonuses_penalties"].get(str(target_user.id), []) if item["type"] == item_type],
            key=lambda x: x['timestamp'], reverse=True
        )

        # Determine ephemeral for the list itself (not errors)
        display_settings = await self.get_guild_display_settings(interaction.guild_id)
        list_ephemeral = display_settings.get('ephemeral_responses', True)

        if not user_bp_list:
            await self.send_response(interaction, message=f"ℹ️ {target_user.mention} has no active {item_type}s.", ephemeral=list_ephemeral)
            return

        embed_color = discord.Color.green() if item_type == "bonus" else discord.Color.red()
        title_text = f"Active {item_type.capitalize()}s: {target_user.display_name}"
        if target_user.name and target_user.name.lower() != target_user.display_name.lower():
            title_text += f" ({target_user.name})"
        
        embed = discord.Embed(title=title_text, color=embed_color, timestamp=datetime.now(timezone.utc))
        
        description_lines = []
        for i, item in enumerate(user_bp_list[:10], 1):
            giver_member = interaction.guild.get_member(int(item["giver_id"]))
            giver_display_name = giver_member.display_name if giver_member else "Unknown"
            giver_username = giver_member.name if giver_member else ""
            giver_text = giver_display_name
            if giver_member and giver_username and giver_username.lower() != giver_display_name.lower():
                giver_text += f" ({giver_username})"

            reason_text = f"_{item['reason']}_" if item.get('reason') else "_No reason_"
            added_at = f"<t:{int(datetime.fromisoformat(item['timestamp']).timestamp())}:R>"
            line = f"**{i}. ${item['amount']:.2f}** - {reason_text}\n   ID: `{item['id'][:8]}` | By: {giver_text} | {added_at}"
            description_lines.append(line)
        
        embed.description = "\n\n".join(description_lines)
        if len(user_bp_list) > 10:
            embed.set_footer(text=f"Showing {len(description_lines)} of {len(user_bp_list)}.")
            
        await self.send_response(interaction, embed=embed, ephemeral=list_ephemeral)

    # Bonus Commands
    @bonus_group.command(name="add", description="Add a bonus to a user.")
    @app_commands.describe(user="User", amount="Amount", reason="Optional reason.")
    async def add_bonus(self, interaction: discord.Interaction, user: discord.User, amount: app_commands.Range[float, 0.01, 100000.0], reason: Optional[str] = None):
        await self._add_bonus_penalty(interaction, user, amount, "bonus", reason)

    @bonus_group.command(name="remove", description="Remove an active bonus.")
    @app_commands.describe(user="User", bonus_id_prefix="ID (or start of ID) to remove.")
    async def remove_bonus(self, interaction: discord.Interaction, user: discord.User, bonus_id_prefix: str):
        await self._remove_bonus_penalty(interaction, user, bonus_id_prefix, "bonus")

    @bonus_group.command(name="list", description="List active bonuses (defaults to self).")
    @app_commands.describe(user="User whose bonuses to list.")
    async def list_bonuses(self, interaction: discord.Interaction, user: Optional[discord.User] = None):
        await self._list_bonus_penalty(interaction, user or interaction.user, "bonus")

    # Penalty Commands
    @penalty_group.command(name="add", description="Apply a penalty to a user.")
    @app_commands.describe(user="User", amount="Amount", reason="Optional reason.")
    async def add_penalty(self, interaction: discord.Interaction, user: discord.User, amount: app_commands.Range[float, 0.01, 100000.0], reason: Optional[str] = None):
        await self._add_bonus_penalty(interaction, user, amount, "penalty", reason)

    @penalty_group.command(name="remove", description="Remove an active penalty.")
    @app_commands.describe(user="User", penalty_id_prefix="ID (or start of ID) to remove.")
    async def remove_penalty(self, interaction: discord.Interaction, user: discord.User, penalty_id_prefix: str):
        await self._remove_bonus_penalty(interaction, user, penalty_id_prefix, "penalty")

    @penalty_group.command(name="list", description="List active penalties (defaults to self).")
    @app_commands.describe(user="User whose penalties to list.")
    async def list_penalties(self, interaction: discord.Interaction, user: Optional[discord.User] = None):
        await self._list_bonus_penalty(interaction, user or interaction.user, "penalty")

async def setup(bot):
    await bot.add_cog(ClockInTrackerSlash(bot))
    logger.info("ClockInTrackerSlash cog loaded with corrected ephemeral handling.")