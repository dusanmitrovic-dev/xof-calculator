import discord
from discord import app_commands, ui
from discord.ext import commands, tasks
import logging
from datetime import datetime, timezone, timedelta
import uuid
from typing import Optional, List, Dict, Any

from config import settings # Assuming this exists and has DEFAULT_DISPLAY_SETTINGS, DEFAULT_CLOCK_DATA
from utils import file_handlers # Assuming this exists for load/save JSON

logger = logging.getLogger("xof_calculator.clock_in_tracker_slash")

DEFAULT_USER_CLOCK_STATE = {
    "status": "clocked_out",
    "clock_in_time": None,
    "break_start_time": None,
    "breaks_taken_this_shift": 0,
    "accumulated_break_duration_seconds_this_shift": 0.0,
    "expected_break_end_time_iso": None, # For overstay alert
    "overstay_alert_message_id": None,   # For overstay alert
    "break_interaction_channel_id": None # For overstay alert, channel where /break was used
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
        self.check_break_overstays.start()

    def cog_unload(self):
        self.check_break_overstays.cancel()

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
        # Ensure all keys from default exist for older user data
        for key, default_value in DEFAULT_USER_CLOCK_STATE.items():
            if key not in clock_data["users"][user_id_str]:
                clock_data["users"][user_id_str][key] = default_value
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
        embed: Optional[discord.Embed] = None, ephemeral: Optional[bool] = None
    ):
        actual_ephemeral: bool
        if ephemeral is not None:
            actual_ephemeral = ephemeral
        else:
            display_settings = await self.get_guild_display_settings(interaction.guild_id)
            actual_ephemeral = display_settings.get('ephemeral_responses', True)
        
        if not message and not embed:
            logger.warning(f"send_response called for interaction {interaction.id} with no message or embed.")
            try:
                # Always send this kind of internal error ephemerally
                if interaction.response.is_done():
                    await interaction.followup.send("An internal error occurred.", ephemeral=True) # Forced ephemeral
                else:
                    await interaction.response.send_message("An internal error occurred.", ephemeral=True) # Forced ephemeral
            except Exception as e:
                logger.error(f"Failed to send internal error message in send_response for interaction {interaction.id}: {e}", exc_info=True)
            return

        try:
            if interaction.response.is_done():
                await interaction.followup.send(content=message, embed=embed, ephemeral=actual_ephemeral)
            else:
                await interaction.response.send_message(content=message, embed=embed, ephemeral=actual_ephemeral)
        except Exception as e:
            logger.error(f"Error sending response in send_response for interaction {interaction.id}: {e}", exc_info=True)
            try:
                # Fallback error message, always ephemeral
                await interaction.followup.send("There was an issue processing your request and sending the response.", ephemeral=True) # Forced ephemeral
            except Exception as followup_e:
                 logger.error(f"Error sending fallback followup in send_response for interaction {interaction.id}: {followup_e}", exc_info=True)


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
        await self.send_response(interaction, message=f"🛠️ Maximum breaks per shift updated to **{count if count > 0 else 'unlimited'}**.")

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
        # display_settings = await self.get_guild_display_settings(interaction.guild_id) # Not used for ephemeral here, admin command
        # ephemeral = display_settings.get('ephemeral_responses', True)
        clock_data = await self.get_clock_data(interaction.guild_id)
        clock_data.setdefault("settings", settings.DEFAULT_CLOCK_DATA["settings"].copy())
        manager_roles = clock_data["settings"].setdefault("bonus_penalty_manager_roles", [])
        if str(role.id) not in manager_roles:
            manager_roles.append(str(role.id))
            await self.save_clock_data(interaction.guild_id, clock_data)
            await self.send_response(interaction, message=f"🛠️ Role {role.mention} can now manage bonuses/penalties.")
        else:
            await self.send_response(interaction, message=f"⚠️ Role {role.mention} is already a manager.", ephemeral=True) # Explicit ephemeral for warning

    @clock_settings_group.command(name="remove-manager-role", description="Revoke manager permissions for bonuses/penalties.")
    @app_commands.describe(role="The role to remove manager permissions from.")
    async def remove_manager_role(self, interaction: discord.Interaction, role: discord.Role):
        # display_settings = await self.get_guild_display_settings(interaction.guild_id) # Not used for ephemeral here, admin command
        # ephemeral = display_settings.get('ephemeral_responses', True)
        clock_data = await self.get_clock_data(interaction.guild_id)
        manager_roles = clock_data.get("settings", {}).get("bonus_penalty_manager_roles", [])
        if str(role.id) in manager_roles:
            manager_roles.remove(str(role.id))
            await self.save_clock_data(interaction.guild_id, clock_data)
            await self.send_response(interaction, message=f"🛠️ Role {role.mention} can no longer manage bonuses/penalties.")
        else:
            await self.send_response(interaction, message=f"⚠️ Role {role.mention} was not a manager.", ephemeral=True) # Explicit ephemeral for warning
            
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

        max_breaks_val = settings_data.get("max_breaks_per_shift", 3)
        max_breaks_display = str(max_breaks_val) if max_breaks_val > 0 else "Unlimited"
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

        embed = discord.Embed(
            title="⚙️ Clock System Configuration",
            color=discord.Color.blue(),
            timestamp=datetime.now(timezone.utc)
        )

        embed.add_field(
            name="📋 Settings Overview",
            value=(
                "```text\n"
                f"{'Max Breaks Per Shift:':<22} {max_breaks_display}\n"
                f"{'Max Break Duration:':<22} {max_break_duration_display}\n"
                f"{'Public Clock Embeds:':<22} {display_events_status}"
                "\n```"
            ),
            inline=False
        )

        embed.add_field(
            name="🛠️ Bonus / Penalty Managers",
            value=manager_roles_display or "`No manager roles assigned.`",
            inline=False
        )

        
        await self.send_response(interaction, embed=embed) # Uses default ephemeral setting for this info embed

    # --- Main Clocking Commands ---
    @app_commands.command(name="clock-in", description="Clock in to start your shift.")
    async def clock_in(self, interaction: discord.Interaction):
        display_settings = await self.get_guild_display_settings(interaction.guild_id)
        ephemeral_default = display_settings.get('ephemeral_responses', True) # For private messages
        clock_data = await self.get_clock_data(interaction.guild_id)
        user_state = await self.get_user_clock_state(clock_data, interaction.user.id)

        if user_state["status"] == "clocked_in":
            await self.send_response(interaction, message="❌ You are already clocked in.", ephemeral=ephemeral_default)
            return
        if user_state["status"] == "on_break":
            await self.send_response(interaction, message="❌ You are on break. Use `/back` first.", ephemeral=ephemeral_default)
            return

        user_state["status"] = "clocked_in"
        current_time_utc = datetime.now(timezone.utc)
        user_state["clock_in_time"] = current_time_utc.isoformat()
        user_state["breaks_taken_this_shift"] = 0
        user_state["accumulated_break_duration_seconds_this_shift"] = 0.0
        user_state["break_start_time"] = None
        # Clear break-specific alert fields
        user_state["expected_break_end_time_iso"] = None
        user_state["overstay_alert_message_id"] = None
        user_state["break_interaction_channel_id"] = None
        await self.save_clock_data(interaction.guild_id, clock_data)
        
        if await self.should_display_public_clock_event(interaction.guild_id):
            embed = discord.Embed(
                description=f"✅ {interaction.user.mention} has **clocked in**.",
                color=discord.Color.green(), timestamp=current_time_utc
            )
            await self.send_response(interaction, embed=embed, ephemeral=False) # Public event
        else:
            await self.send_response(interaction, message=f"✅ Clocked in at <t:{int(current_time_utc.timestamp())}:T>.", ephemeral=ephemeral_default)

    @app_commands.command(name="clock-out", description="Clock out to end your shift.")
    async def clock_out(self, interaction: discord.Interaction):
        display_settings = await self.get_guild_display_settings(interaction.guild_id)
        ephemeral_default = display_settings.get('ephemeral_responses', True) # For private messages
        clock_data = await self.get_clock_data(interaction.guild_id)
        user_state = await self.get_user_clock_state(clock_data, interaction.user.id)

        if user_state["status"] == "clocked_out":
            await self.send_response(interaction, message="❌ You are not clocked in.", ephemeral=ephemeral_default)
            return

        now_utc = datetime.now(timezone.utc)
        # Handle ending break if clocking out while on break
        if user_state["status"] == "on_break" and user_state["break_start_time"]:
            break_start_dt = datetime.fromisoformat(user_state["break_start_time"])
            current_break_duration = now_utc - break_start_dt
            user_state["accumulated_break_duration_seconds_this_shift"] += current_break_duration.total_seconds()
            logger.info(f"User {interaction.user.id} auto-ended break of {format_timedelta(current_break_duration)} during clock-out.")
            # Attempt to clean up overstay alert message if any
            await self._cleanup_overstay_alert(interaction.guild_id, interaction.user.id, user_state, clock_data)

        if not user_state["clock_in_time"]:
            await self.send_response(interaction, message="❌ Error: Clock-in time missing. Please contact an admin.", ephemeral=True) # Error, likely ephemeral
            logger.error(f"User {interaction.user.id} clock_out error: clock_in_time missing. State: {user_state}")
            user_state.update(DEFAULT_USER_CLOCK_STATE.copy())
            await self.save_clock_data(interaction.guild_id, clock_data)
            return
            
        clock_in_dt = datetime.fromisoformat(user_state["clock_in_time"])
        total_shift_duration_td = now_utc - clock_in_dt
        # Capture the final break/shift values after any on-break logic
        original_breaks_taken = user_state.get("breaks_taken_this_shift", 0)
        original_accumulated_break_duration = user_state.get("accumulated_break_duration_seconds_this_shift", 0.0)
        total_work_duration_seconds = total_shift_duration_td.total_seconds() - original_accumulated_break_duration
        total_work_duration_td = timedelta(seconds=max(0, total_work_duration_seconds))

        user_state.update(DEFAULT_USER_CLOCK_STATE.copy()) 
        await self.save_clock_data(interaction.guild_id, clock_data)

        max_breaks_config = clock_data.get("settings", {}).get("max_breaks_per_shift", 3)
        breaks_display = f"{original_breaks_taken}"
        if max_breaks_config > 0:
            breaks_display += f"/{max_breaks_config}"
        else: # Unlimited breaks
             breaks_display += " (Unlimited)"


        if await self.should_display_public_clock_event(interaction.guild_id):
            embed = discord.Embed(
                title=f"",
                color=discord.Color.from_rgb(0, 150, 255), # Professional Blue
                timestamp=now_utc
            )
            # embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url if interaction.user.display_avatar else None)
            
            embed.add_field(name="", value=(
                "```text\n"
                f"{'Total Shift Duration:':<22} {format_timedelta(total_shift_duration_td)}\n"
                f"{'Time Worked:':<22} {format_timedelta(total_work_duration_td)}\n"
                f"{'Total Break Time:':<22} {format_timedelta(timedelta(seconds=original_accumulated_break_duration))}\n"
                f"{'Breaks Taken:':<22} {breaks_display}"
                "\n```"
            ), inline=False)
            
            if interaction.user.display_avatar:
                embed.set_thumbnail(url=interaction.user.display_avatar.url)

            await self.send_response(interaction, embed=embed, ephemeral=False) # Public event
        else:
            await self.send_response(
                interaction, 
                message=f"✅ Clocked out. Time worked: **{format_timedelta(total_work_duration_td)}**. Breaks: {breaks_display}.",
                ephemeral=ephemeral_default
            )

    @app_commands.command(name="break", description="Start a break (must be clocked in).")
    async def start_break(self, interaction: discord.Interaction):
        display_settings = await self.get_guild_display_settings(interaction.guild_id)
        ephemeral_default = display_settings.get('ephemeral_responses', True)
        clock_data = await self.get_clock_data(interaction.guild_id)
        user_state = await self.get_user_clock_state(clock_data, interaction.user.id)
        guild_settings = clock_data.get("settings", {})
        max_breaks_config = guild_settings.get("max_breaks_per_shift", 3)
        max_break_duration_minutes = guild_settings.get("max_break_duration_minutes", 0)

        if user_state["status"] == "on_break":
            await self.send_response(interaction, message="❌ You are already on break.", ephemeral=ephemeral_default)
            return
        if user_state["status"] != "clocked_in":
            await self.send_response(interaction, message="❌ You must be clocked in to start a break.", ephemeral=ephemeral_default)
            return
        
        if max_breaks_config > 0 and user_state["breaks_taken_this_shift"] >= max_breaks_config:
            await self.send_response(interaction, message=f"❌ Max breaks ({max_breaks_config}) reached for this shift.", ephemeral=ephemeral_default)
            return

        user_state["status"] = "on_break"
        current_time_utc = datetime.now(timezone.utc)
        user_state["break_start_time"] = current_time_utc.isoformat()
        user_state["breaks_taken_this_shift"] += 1
        user_state["break_interaction_channel_id"] = interaction.channel_id 

        if max_break_duration_minutes > 0:
            user_state["expected_break_end_time_iso"] = (current_time_utc + timedelta(minutes=max_break_duration_minutes)).isoformat()
        else:
            user_state["expected_break_end_time_iso"] = None 
        user_state["overstay_alert_message_id"] = None 

        await self.save_clock_data(interaction.guild_id, clock_data)

        if await self.should_display_public_clock_event(interaction.guild_id):
            embed = discord.Embed(
                description=f"⏸️ {interaction.user.mention} is now **on break**.",
                color=discord.Color.from_rgb(170, 170, 170), # Grey
                timestamp=current_time_utc
            )
            await self.send_response(interaction, embed=embed, ephemeral=False) # Public event
        else:
            await self.send_response(interaction, message=f"⏸️ Break started at <t:{int(current_time_utc.timestamp())}:T>.", ephemeral=ephemeral_default)

    async def _cleanup_overstay_alert(self, guild_id: int, user_id: int, user_state: Dict[str, Any], clock_data: Dict[str, Any], save_data: bool = True):
        updated = False
        if user_state.get("overstay_alert_message_id") and user_state.get("break_interaction_channel_id"):
            guild = self.bot.get_guild(guild_id)
            if guild:
                # Ensure channel is fetchable and of correct type
                channel_id = user_state["break_interaction_channel_id"]
                try:
                    channel = await guild.fetch_channel(channel_id) # fetch_channel can get any type
                    if not isinstance(channel, discord.TextChannel): # Explicitly check for TextChannel
                         logger.warning(f"Break interaction channel {channel_id} for user {user_id} is not a TextChannel. Type: {type(channel)}")
                         channel = None # Invalidate channel if not TextChannel
                except (discord.NotFound, discord.Forbidden): # Channel not found or no permissions
                    logger.warning(f"Could not fetch break interaction channel {channel_id} for user {user_id} during overstay cleanup.")
                    channel = None # Invalidate channel
                
                if channel and isinstance(channel, discord.TextChannel):
                    try:
                        msg_to_delete = await channel.fetch_message(user_state["overstay_alert_message_id"])
                        await msg_to_delete.delete()
                        logger.info(f"Deleted overstay alert message {user_state['overstay_alert_message_id']} for user {user_id}")
                    except discord.NotFound:
                        logger.info(f"Overstay alert message {user_state['overstay_alert_message_id']} for user {user_id} not found during cleanup.")
                    except discord.Forbidden:
                        logger.warning(f"Bot lacks permissions to delete overstay alert message {user_state['overstay_alert_message_id']} in channel {channel.id} for user {user_id}.")
                    except Exception as e:
                        logger.error(f"Error deleting overstay alert message for user {user_id}: {e}", exc_info=True)
            user_state["overstay_alert_message_id"] = None
            updated = True
        
        if user_state.get("expected_break_end_time_iso") is not None:
            user_state["expected_break_end_time_iso"] = None
            updated = True
        # break_interaction_channel_id is cleared on clock_out or new clock_in. 
        # Not clearing it here allows alerts to be re-sent to the same channel if the user goes on break again quickly.
            
        if updated and save_data:
            await self.save_clock_data(guild_id, clock_data)
        return updated


    @app_commands.command(name="back", description="Return from your break.")
    async def end_break(self, interaction: discord.Interaction):
        display_settings = await self.get_guild_display_settings(interaction.guild_id)
        ephemeral_default = display_settings.get('ephemeral_responses', True)
        clock_data = await self.get_clock_data(interaction.guild_id)
        user_state = await self.get_user_clock_state(clock_data, interaction.user.id)
        settings_data = clock_data.get("settings", {})
        max_break_duration_minutes = settings_data.get("max_break_duration_minutes", 0)

        if user_state["status"] != "on_break":
            await self.send_response(interaction, message="❌ You are not currently on a break.", ephemeral=ephemeral_default)
            return
        if not user_state["break_start_time"]:
            await self.send_response(interaction, message="❌ Error: Break start time missing. Please contact an admin.", ephemeral=True) # Error, likely ephemeral
            logger.error(f"User {interaction.user.id} end_break error: break_start_time missing. State: {user_state}")
            user_state["status"] = "clocked_in" 
            await self.save_clock_data(interaction.guild_id, clock_data)
            return

        now_utc = datetime.now(timezone.utc)
        break_start_dt = datetime.fromisoformat(user_state["break_start_time"])
        current_break_duration_td = now_utc - break_start_dt
        
        user_state["accumulated_break_duration_seconds_this_shift"] += current_break_duration_td.total_seconds()
        user_state["status"] = "clocked_in"
        user_state["break_start_time"] = None
        
        await self._cleanup_overstay_alert(interaction.guild_id, interaction.user.id, user_state, clock_data, save_data=False)
        
        await self.save_clock_data(interaction.guild_id, clock_data)
        
        overstayed_message = ""
        if max_break_duration_minutes > 0 and user_state.get("expected_break_end_time_iso"): # Check if expected_break_end_time_iso was set
            # It was cleaned up by _cleanup_overstay_alert, so re-calculate if needed from original break start
            expected_end_dt_for_calc = break_start_dt + timedelta(minutes=max_break_duration_minutes)
            if now_utc > expected_end_dt_for_calc:
                overstayed_seconds = (now_utc - expected_end_dt_for_calc).total_seconds()
                overstayed_td = timedelta(seconds=overstayed_seconds)
                overstayed_message = f"\n\n🔴 Overstayed by: {format_timedelta(overstayed_td, show_seconds=True)}"
        elif max_break_duration_minutes > 0: # Fallback if expected_break_end_time_iso wasn't set (should not happen if logic is correct)
            allowed_duration_seconds = max_break_duration_minutes * 60
            if current_break_duration_td.total_seconds() > allowed_duration_seconds:
                overstayed_seconds = current_break_duration_td.total_seconds() - allowed_duration_seconds
                overstayed_td = timedelta(seconds=overstayed_seconds)
                overstayed_message = f"\n\n🔴 Overstayed by: {format_timedelta(overstayed_td, show_seconds=True)}"


        max_breaks_config = clock_data.get("settings", {}).get("max_breaks_per_shift", 3)
        breaks_display = f"{user_state['breaks_taken_this_shift']}"
        if max_breaks_config > 0:
            breaks_display += f"/{max_breaks_config}"
        else:
            breaks_display += " (Unlimited)"

        if await self.should_display_public_clock_event(interaction.guild_id):
            embed = discord.Embed(
                title="",
                description=f"▶️ {interaction.user.mention} is **back from break**.{overstayed_message}",
                color=discord.Color.from_rgb(100, 100, 255),  # Slightly vibrant purple-blue
                timestamp=now_utc
            )

            embed.add_field(name="", value=(
                "```text\n"
                f"{'Break Duration:':<16} {format_timedelta(current_break_duration_td)}\n"
                f"{'Breaks Taken:':<16} {breaks_display}"
                "\n```"
            ), inline=False)

            if overstayed_message:
                embed.description = overstayed_message.strip()

            await self.send_response(interaction, embed=embed, ephemeral=False)
        else:
            await self.send_response(
                interaction,
                message=f"▶️ Welcome back! Break duration: {format_timedelta(current_break_duration_td)}.{overstayed_message}",
                ephemeral=ephemeral_default
            )


    # --- Bonus/Penalty Command Groups ---
    bonus_group = app_commands.Group(name="bonus", description="Manage bonuses for users.")
    penalty_group = app_commands.Group(name="penalty", description="Manage penalties for users.")

    async def _add_bonus_penalty(self, interaction: discord.Interaction, user: discord.User, amount: float, item_type: str, reason: Optional[str] = None):
        # Admin commands usually are not ephemeral by default, but this one's response is an embed that might be better public
        # display_settings = await self.get_guild_display_settings(interaction.guild_id)
        # ephemeral = display_settings.get('ephemeral_responses', True)
        if not await self.has_bonus_penalty_permission(interaction):
            await self.send_response(interaction, message="❌ You do not have permission to manage bonuses/penalties.", ephemeral=True) # Permission error, ephemeral
            return
        if amount <= 0:
            await self.send_response(interaction, message=f"❌ Amount must be positive.", ephemeral=True) # Input error, ephemeral
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
        reason_display = reason or "No reason provided"
        reason_display = discord.utils.escape_markdown(reason_display)
        display_name = user.display_name
        username = user.name
        embed = discord.Embed(
            title=f"{display_name} ({username}) — {'✅ Bonus' if item_type == 'bonus' else '❌ Penalty'} [`{item_id[:8]}`]",
            color=embed_color,
            timestamp=datetime.now(timezone.utc)
        )
        if user.display_avatar:
            embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="Amount", value=f"${amount:.2f}", inline=False)
        embed.add_field(name="Reason", value=reason_display, inline=False)
        embed.set_footer(text=f"By: {interaction.user.display_name}")
        await self.send_response(interaction, embed=embed)
        return

    async def _remove_bonus_penalty(self, interaction: discord.Interaction, user: discord.User, item_id_prefix: str, item_type: str):
        # display_settings = await self.get_guild_display_settings(interaction.guild_id)
        # ephemeral = display_settings.get('ephemeral_responses', True)
        if not await self.has_bonus_penalty_permission(interaction):
            await self.send_response(interaction, message="❌ You do not have permission to manage bonuses/penalties.", ephemeral=True) # Permission error, ephemeral
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
            await self.send_response(interaction, embed=embed) # Uses guild default ephemeral
        else:
            await self.send_response(interaction, message=f"❌ No {item_type} found for {user.mention} with ID starting with `{item_id_prefix}`.", ephemeral=True) # Error, ephemeral

    async def _list_bonus_penalty(self, interaction: discord.Interaction, target_user: Optional[discord.User], item_type: str):
        # If no user is provided, show a summary for all users with at least one bonus/penalty
        clock_data = await self.get_clock_data(interaction.guild_id)
        display_settings = await self.get_guild_display_settings(interaction.guild_id) # For ephemeral setting
        ephemeral = display_settings.get('ephemeral_responses', True)

        if target_user is None:
            # Build a detailed list for all users with at least one bonus/penalty
            user_items = clock_data["bonuses_penalties"]
            summary = []
            for user_id_str, items in user_items.items():
                filtered = [item for item in items if item["type"] == item_type]
                if filtered:
                    user_id = int(user_id_str)
                    member = interaction.guild.get_member(user_id)
                    if member:
                        display_name = member.display_name
                        username = member.name
                        mention = member.mention
                    else:
                        try:
                            user_obj = await self.bot.fetch_user(user_id)
                            display_name = user_obj.display_name
                            username = user_obj.name
                            mention = user_obj.mention
                        except Exception:
                            display_name = f"User {user_id_str}"
                            username = f"{user_id_str}"
                            mention = f"<@{user_id_str}>"
                    total = sum(item["amount"] for item in filtered)
                    summary.append((display_name, username, mention, filtered, total))
            if not summary:
                await self.send_response(interaction, message=f"ℹ️ No users have any active {item_type}.", ephemeral=ephemeral)
                return
            summary.sort(key=lambda x: len(x[3]), reverse=True)  # Sort by count desc
            embed_color = discord.Color.green() if item_type == "bonus" else discord.Color.red()
            embed = discord.Embed(
                title=f"All Users with Active {'Bonuses' if item_type == 'bonus' else 'Penalties'}",
                color=embed_color,
                timestamp=datetime.now(timezone.utc)
            )
            lines = []
            for display_name, username, mention, filtered, total in summary[:10]:
                user_header = f"{display_name} ({username})"
                user_lines = [f"{user_header}:"]
                # Sort filtered items by timestamp descending (newest first)
                filtered_sorted = sorted(filtered, key=lambda x: x['timestamp'], reverse=True)
                for idx, item in enumerate(filtered_sorted, 1):
                    reason = item.get("reason") or "No reason provided"
                    reason = discord.utils.escape_markdown(reason)
                    id_value = item.get("id", "")[:8]
                    user_lines.append(f"{idx}. `{id_value}` ${item['amount']:.2f} - {reason}")
                user_lines.append(f"\n`Total: ${total:.2f} ({len(filtered)} items)`")
                lines.append("\n".join(user_lines))
            embed.description = "\n\n".join(lines)
            if len(summary) > 10:
                embed.set_footer(text=f"Showing 10 of {len(summary)} users. Top by count.")
            else:
                embed.set_footer(text=f"Total users: {len(summary)}.")
            await self.send_response(interaction, embed=embed, ephemeral=ephemeral)
            return

        # Single user detailed list (same style as all-users, with avatar)
        user_bp_list = sorted(
            [item for item in clock_data["bonuses_penalties"].get(str(target_user.id), []) if item["type"] == item_type],
            key=lambda x: x['timestamp'], reverse=True # Newest first
        )
        if not user_bp_list:
            await self.send_response(interaction, message=f"ℹ️ {target_user.mention} has no active {item_type}.", ephemeral=ephemeral)
            return
        display_name = target_user.display_name
        username = target_user.name
        total = sum(item["amount"] for item in user_bp_list)
        embed_color = discord.Color.green() if item_type == "bonus" else discord.Color.red()
        embed = discord.Embed(
            title=f"{display_name} ({username}) — {'Bonuses' if item_type == 'bonus' else 'Penalties'}",
            color=embed_color,
            timestamp=datetime.now(timezone.utc)
        )
        if target_user.display_avatar:
            embed.set_thumbnail(url=target_user.display_avatar.url)
        user_lines = []
        for idx, item in enumerate(user_bp_list[:20], 1):
            reason = item.get("reason") or "No reason provided"
            reason = discord.utils.escape_markdown(reason)
            id_value = item.get("id", "")[:8]
            user_lines.append(f"{idx}. `{id_value}` ${item['amount']:.2f} - {reason}")
        user_lines.append(f"\n`Total: ${total:.2f} ({len(user_bp_list)} items)`")
        embed.description = "\n".join(user_lines)
        if len(user_bp_list) > 20:
            embed.set_footer(text=f"Showing 20 of {len(user_bp_list)} total. Newest first.")
        else:
            embed.set_footer(text=f"Newest listed first.")
        await self.send_response(interaction, embed=embed, ephemeral=ephemeral) # Respects guild ephemeral for list views

    # Bonus Commands
    @bonus_group.command(name="add", description="Add a bonus to a user.")
    @app_commands.describe(user="User", amount="Amount", reason="Optional reason.")
    async def add_bonus(self, interaction: discord.Interaction, user: discord.User, amount: app_commands.Range[float, 0.01, 100000.0], reason: Optional[str] = None):
        await self._add_bonus_penalty(interaction, user, amount, "bonus", reason)

    @bonus_group.command(name="remove", description="Remove an active bonus.")
    @app_commands.describe(user="User", bonus_id_prefix="ID (or start of ID) to remove.")
    async def remove_bonus(self, interaction: discord.Interaction, user: discord.User, bonus_id_prefix: str):
        await self._remove_bonus_penalty(interaction, user, bonus_id_prefix, "bonus")

    @bonus_group.command(name="list", description="List active bonuses (defaults to all if no user).")
    @app_commands.describe(user="User whose bonuses to list.")
    async def list_bonuses(self, interaction: discord.Interaction, user: Optional[discord.User] = None):
        await self._list_bonus_penalty(interaction, user, "bonus")

    # Penalty Commands
    @penalty_group.command(name="add", description="Apply a penalty to a user.")
    @app_commands.describe(user="User", amount="Amount", reason="Optional reason.")
    async def add_penalty(self, interaction: discord.Interaction, user: discord.User, amount: app_commands.Range[float, 0.01, 100000.0], reason: Optional[str] = None):
        await self._add_bonus_penalty(interaction, user, amount, "penalty", reason)

    @penalty_group.command(name="remove", description="Remove an active penalty.")
    @app_commands.describe(user="User", penalty_id_prefix="ID (or start of ID) to remove.")
    async def remove_penalty(self, interaction: discord.Interaction, user: discord.User, penalty_id_prefix: str):
        await self._remove_bonus_penalty(interaction, user, penalty_id_prefix, "penalty")

    @penalty_group.command(name="list", description="List active penalties (defaults to all if no user).")
    @app_commands.describe(user="User whose penalties to list.")
    async def list_penalties(self, interaction: discord.Interaction, user: Optional[discord.User] = None):
        await self._list_bonus_penalty(interaction, user, "penalty")

    # --- Background Task for Break Overstays ---
    @tasks.loop(seconds=15.0)
    async def check_break_overstays(self):
        if not self.bot.is_ready():
            return

        now_utc = datetime.now(timezone.utc)

        for guild in self.bot.guilds:
            try:
                clock_data = await self.get_clock_data(guild.id)
                guild_settings = clock_data.get("settings", {})
                max_break_min_config = guild_settings.get("max_break_duration_minutes", 0)

                if max_break_min_config <= 0: 
                    continue

                users_data = clock_data.get("users", {})
                guild_data_modified = False

                for user_id_str, user_state in users_data.items():
                    user_id = int(user_id_str)
                    if user_state.get("status") == "on_break" and \
                       user_state.get("break_start_time") and \
                       user_state.get("expected_break_end_time_iso") and \
                       user_state.get("break_interaction_channel_id"):
                        
                        expected_end_dt = datetime.fromisoformat(user_state["expected_break_end_time_iso"])
                        
                        if now_utc > expected_end_dt:
                            member = guild.get_member(user_id) 
                            user_obj = None
                            if member:
                                user_obj = member
                            else:
                                try:
                                    user_obj = await self.bot.fetch_user(user_id)
                                except discord.NotFound:
                                    logger.warning(f"Could not find user {user_id} for overstay alert in guild {guild.id}.")
                                    continue # Skip if user cannot be found for mention
                            
                            alert_channel_id = user_state["break_interaction_channel_id"]
                            alert_channel = None
                            try:
                                # Fetch channel to ensure it's up-to-date and exists
                                fetched_ch = await guild.fetch_channel(alert_channel_id)
                                if isinstance(fetched_ch, discord.TextChannel):
                                    alert_channel = fetched_ch
                                else:
                                    logger.warning(f"Break overstay alert channel {alert_channel_id} is not a TextChannel for user {user_id} in guild {guild.id}. Type: {type(fetched_ch)}")
                            except (discord.NotFound, discord.Forbidden):
                                logger.warning(f"Break overstay alert channel {alert_channel_id} not found or no permission for user {user_id} in guild {guild.id}.")
                                # Potentially clear user_state["break_interaction_channel_id"] here if it's persistently bad?
                                # For now, just skip sending the alert for this cycle.
                                continue

                            if not alert_channel:
                                continue # Already logged

                            overstay_duration = now_utc - expected_end_dt
                            formatted_overstay = format_timedelta(overstay_duration, show_seconds=True)
                            
                            embed_title = "⚠️ Break Overstay Alert"
                            embed_desc = f"{user_obj.mention}, you have exceeded your allowed break time of **{max_break_min_config} minutes**."
                            embed_color = discord.Color.orange()

                            alert_embed = discord.Embed(title=embed_title, description=embed_desc, color=embed_color, timestamp=now_utc)
                            alert_embed.add_field(name="Currently Overstayed By", value=f"**{formatted_overstay}**")
                            alert_embed.set_footer(text=f"User: {user_obj.display_name} ({user_obj.name})")

                            try:
                                if user_state.get("overstay_alert_message_id"):
                                    msg = await alert_channel.fetch_message(user_state["overstay_alert_message_id"])
                                    await msg.edit(embed=alert_embed) 
                                else: 
                                    msg = await alert_channel.send(content=user_obj.mention, embed=alert_embed)
                                    user_state["overstay_alert_message_id"] = msg.id
                                    guild_data_modified = True
                            except discord.NotFound:
                                logger.info(f"Overstay alert message {user_state.get('overstay_alert_message_id')} for user {user_id} not found. Sending a new one.")
                                msg = await alert_channel.send(content=user_obj.mention, embed=alert_embed)
                                user_state["overstay_alert_message_id"] = msg.id
                                guild_data_modified = True
                            except discord.Forbidden:
                                logger.warning(f"Bot lacks permission to send/edit overstay alert in channel {alert_channel.id} for user {user_id}.")
                            except Exception as e:
                                logger.error(f"Error handling overstay alert for user {user_id} in guild {guild.id}: {e}", exc_info=True)
                
                if guild_data_modified:
                    await self.save_clock_data(guild.id, clock_data)

            except Exception as e:
                logger.error(f"Error in check_break_overstays task for guild {guild.id}: {e}", exc_info=True)

    @check_break_overstays.before_loop
    async def before_check_break_overstays(self):
        await self.bot.wait_until_ready()
        logger.info("Break overstay checker task is now ready and running.")


async def setup(bot):
    if not hasattr(settings, 'get_guild_display_path') or \
       not hasattr(settings, 'DEFAULT_DISPLAY_SETTINGS') or \
       not hasattr(settings, 'get_guild_clock_data_path') or \
       not hasattr(settings, 'DEFAULT_CLOCK_DATA'):
        logger.error("Config 'settings' module is missing required attributes for ClockInTrackerSlash. Cog not loaded.")
        raise ImportError("Missing required settings attributes for ClockInTrackerSlash.")
    
    if not hasattr(file_handlers, 'load_json') or not hasattr(file_handlers, 'save_json'):
        logger.error("Utils 'file_handlers' module is missing required functions for ClockInTrackerSlash. Cog not loaded.")
        raise ImportError("Missing required file_handlers functions for ClockInTrackerSlash.")

    await bot.add_cog(ClockInTrackerSlash(bot))
    logger.info("ClockInTrackerSlash cog loaded.")