import discord
from discord import app_commands
from discord.ext import commands
import logging
from datetime import datetime, timezone, timedelta
import uuid
from typing import Optional

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

    async def get_display_settings(self, guild_id):
        file_path = settings.get_guild_file(guild_id, settings.DISPLAY_SETTINGS_FILE)
        return await file_handlers.load_json(file_path, settings.DEFAULT_DISPLAY_SETTINGS)

    async def get_clock_data(self, guild_id: int) -> dict:
        path = settings.get_guild_clock_data_path(guild_id)
        return await file_handlers.load_json(path, settings.DEFAULT_CLOCK_DATA)

    async def save_clock_data(self, guild_id: int, data: dict):
        path = settings.get_guild_clock_data_path(guild_id)
        await file_handlers.save_json(path, data)

    async def get_user_clock_state(self, clock_data: dict, user_id: int) -> dict:
        user_id_str = str(user_id)
        if user_id_str not in clock_data["users"]:
            clock_data["users"][user_id_str] = DEFAULT_USER_CLOCK_STATE.copy()
        return clock_data["users"][user_id_str]

    async def has_bonus_penalty_permission(self, interaction: discord.Interaction) -> bool:
        if interaction.user.guild_permissions.administrator:
            return True
        
        clock_data = await self.get_clock_data(interaction.guild_id)
        manager_roles_ids = clock_data.get("settings", {}).get("bonus_penalty_manager_roles", [])
        
        member = interaction.user
        for role_id in manager_roles_ids:
            if discord.utils.get(member.roles, id=int(role_id)):
                return True
        return False

    async def send_response(self, interaction: discord.Interaction, content: str, embed: Optional[discord.Embed] = None):
        display_settings = await self.get_display_settings(interaction.guild_id)
        ephemeral = display_settings.get('ephemeral_responses', True)
        use_embeds = display_settings.get('use_embeds', True)
        
        if use_embeds and embed:
            await interaction.response.send_message(embed=embed, ephemeral=ephemeral)
        else:
            await interaction.response.send_message(content, ephemeral=ephemeral)

    # Settings Command Group
    clock_settings_group = app_commands.Group(
        name="clock-settings", 
        description="Manage clock-in system settings",
        default_permissions=discord.Permissions(administrator=True)
    )

    @clock_settings_group.command(name="set-max-breaks", description="Set maximum breaks per shift")
    @app_commands.describe(count="Maximum breaks (0 for unlimited)")
    async def set_max_breaks(self, interaction: discord.Interaction, count: app_commands.Range[int, 0, 20]):
        display_settings = await self.get_display_settings(interaction.guild_id)
        ephemeral = display_settings.get('ephemeral_responses', True)
        
        clock_data = await self.get_clock_data(interaction.guild_id)
        clock_data.setdefault("settings", settings.DEFAULT_CLOCK_DATA["settings"].copy())
        clock_data["settings"]["max_breaks_per_shift"] = count
        
        await self.save_clock_data(interaction.guild_id, clock_data)
        await interaction.response.send_message(
            f"Maximum breaks per shift set to {count}.",
            ephemeral=ephemeral
        )

    @clock_settings_group.command(name="add-manager-role", description="Add a bonus/penalty manager role")
    async def add_manager_role(self, interaction: discord.Interaction, role: discord.Role):
        display_settings = await self.get_display_settings(interaction.guild_id)
        ephemeral = display_settings.get('ephemeral_responses', True)
        
        clock_data = await self.get_clock_data(interaction.guild_id)
        clock_data.setdefault("settings", settings.DEFAULT_CLOCK_DATA["settings"].copy())
        manager_roles = clock_data["settings"].setdefault("bonus_penalty_manager_roles", [])
        
        if str(role.id) not in manager_roles:
            manager_roles.append(str(role.id))
            await self.save_clock_data(interaction.guild_id, clock_data)
            await interaction.response.send_message(
                f"Added {role.mention} as manager role.",
                ephemeral=ephemeral
            )
        else:
            await interaction.response.send_message(
                f"{role.mention} is already a manager role.",
                ephemeral=ephemeral
            )

    @clock_settings_group.command(name="remove-manager-role", description="Remove a manager role")
    async def remove_manager_role(self, interaction: discord.Interaction, role: discord.Role):
        display_settings = await self.get_display_settings(interaction.guild_id)
        ephemeral = display_settings.get('ephemeral_responses', True)
        
        clock_data = await self.get_clock_data(interaction.guild_id)
        manager_roles = clock_data.get("settings", {}).get("bonus_penalty_manager_roles", [])

        if str(role.id) in manager_roles:
            manager_roles.remove(str(role.id))
            await self.save_clock_data(interaction.guild_id, clock_data)
            await interaction.response.send_message(
                f"Removed {role.mention} from manager roles.",
                ephemeral=ephemeral
            )
        else:
            await interaction.response.send_message(
                f"{role.mention} is not a manager role.",
                ephemeral=ephemeral
            )

    @clock_settings_group.command(name="view", description="View current settings")
    async def view_clock_settings(self, interaction: discord.Interaction):
        display_settings = await self.get_display_settings(interaction.guild_id)
        ephemeral = display_settings.get('ephemeral_responses', True)
        
        clock_data = await self.get_clock_data(interaction.guild_id)
        settings_data = clock_data.get("settings", settings.DEFAULT_CLOCK_DATA["settings"])

        embed = discord.Embed(title="Clock System Settings", color=discord.Color.blue())
        embed.add_field(
            name="Max Breaks Per Shift",
            value=str(settings_data.get("max_breaks_per_shift", 3)),
            inline=False
        )
        
        manager_roles = []
        for role_id in settings_data.get("bonus_penalty_manager_roles", []):
            role = interaction.guild.get_role(int(role_id))
            if role:
                manager_roles.append(role.mention)
        
        embed.add_field(
            name="Manager Roles",
            value=", ".join(manager_roles) if manager_roles else "None",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)

    # Main Clock Commands
    @app_commands.command(name="clock-in", description="Start your shift")
    async def clock_in(self, interaction: discord.Interaction):
        clock_data = await self.get_clock_data(interaction.guild_id)
        user_state = await self.get_user_clock_state(clock_data, interaction.user.id)
        display_settings = await self.get_display_settings(interaction.guild_id)
        ephemeral = display_settings.get('ephemeral_responses', True)

        if user_state["status"] == "clocked_in":
            await interaction.response.send_message(
                "You are already clocked in.",
                ephemeral=ephemeral
            )
            return
        if user_state["status"] == "on_break":
            await interaction.response.send_message(
                "You are currently on break. Use /back before clocking in again.",
                ephemeral=ephemeral
            )
            return

        user_state["status"] = "clocked_in"
        user_state["clock_in_time"] = datetime.now(timezone.utc).isoformat()
        user_state["breaks_taken_this_shift"] = 0
        user_state["accumulated_break_duration_seconds_this_shift"] = 0.0
        user_state["break_start_time"] = None

        await self.save_clock_data(interaction.guild_id, clock_data)
        
        timestamp = int(datetime.now(timezone.utc).timestamp())
        content = f"You have clocked in at <t:{timestamp}:F>"
        embed = discord.Embed(
            description=f"Clocked in at <t:{timestamp}:F>",
            color=discord.Color.green()
        )
        await self.send_response(interaction, content, embed)

    @app_commands.command(name="clock-out", description="End your shift")
    async def clock_out(self, interaction: discord.Interaction):
        clock_data = await self.get_clock_data(interaction.guild_id)
        user_state = await self.get_user_clock_state(clock_data, interaction.user.id)
        display_settings = await self.get_display_settings(interaction.guild_id)
        ephemeral = display_settings.get('ephemeral_responses', True)

        if user_state["status"] == "clocked_out":
            await interaction.response.send_message(
                "You are not clocked in.",
                ephemeral=ephemeral
            )
            return

        now_utc = datetime.now(timezone.utc)
        
        if user_state["status"] == "on_break" and user_state["break_start_time"]:
            break_start_dt = datetime.fromisoformat(user_state["break_start_time"])
            current_break_duration = now_utc - break_start_dt
            user_state["accumulated_break_duration_seconds_this_shift"] += current_break_duration.total_seconds()
            user_state["break_start_time"] = None

        if not user_state["clock_in_time"]:
            await interaction.response.send_message(
                "Error: Clock-in time not found.",
                ephemeral=ephemeral
            )
            return
            
        clock_in_dt = datetime.fromisoformat(user_state["clock_in_time"])
        total_shift_duration = now_utc - clock_in_dt
        total_work_duration = timedelta(
            seconds=max(0, total_shift_duration.total_seconds() - 
                      user_state["accumulated_break_duration_seconds_this_shift"])
        )

        embed = discord.Embed(
            title="Shift Summary",
            color=discord.Color.green(),
            timestamp=now_utc
        )
        embed.add_field(
            name="Clocked In",
            value=f"<t:{int(clock_in_dt.timestamp())}:F>",
            inline=True
        )
        embed.add_field(
            name="Clocked Out",
            value=f"<t:{int(now_utc.timestamp())}:F>",
            inline=True
        )
        embed.add_field(
            name="Total Time Worked",
            value=f"**{format_timedelta(total_work_duration)}**",
            inline=False
        )

        content = (
            f"Your shift has ended.\n"
            f"**Worked:** {format_timedelta(total_work_duration)}"
        )

        user_state["status"] = "clocked_out"
        user_state["clock_in_time"] = None
        user_state["break_start_time"] = None

        await self.save_clock_data(interaction.guild_id, clock_data)
        await self.send_response(interaction, content, embed)

    @app_commands.command(name="break", description="Start a break")
    async def start_break(self, interaction: discord.Interaction):
        clock_data = await self.get_clock_data(interaction.guild_id)
        user_state = await self.get_user_clock_state(clock_data, interaction.user.id)
        max_breaks = clock_data.get("settings", {}).get("max_breaks_per_shift", 3)
        display_settings = await self.get_display_settings(interaction.guild_id)
        ephemeral = display_settings.get('ephemeral_responses', True)

        if user_state["status"] != "clocked_in":
            await interaction.response.send_message(
                "You must be clocked in to start a break.",
                ephemeral=ephemeral
            )
            return
        if user_state["status"] == "on_break":
            await interaction.response.send_message(
                "You are already on break.",
                ephemeral=ephemeral
            )
            return
        
        if max_breaks > 0 and user_state["breaks_taken_this_shift"] >= max_breaks:
            await interaction.response.send_message(
                f"You have reached the maximum of {max_breaks} breaks.",
                ephemeral=ephemeral
            )
            return

        user_state["status"] = "on_break"
        user_state["break_start_time"] = datetime.now(timezone.utc).isoformat()
        user_state["breaks_taken_this_shift"] += 1

        await self.save_clock_data(interaction.guild_id, clock_data)
        
        timestamp = int(datetime.now(timezone.utc).timestamp())
        content = f"Your break started at <t:{timestamp}:T>"
        embed = discord.Embed(
            description=f"Break started at <t:{timestamp}:T>",
            color=discord.Color.orange()
        )
        await self.send_response(interaction, content, embed)

    @app_commands.command(name="back", description="Return from break")
    async def end_break(self, interaction: discord.Interaction):
        clock_data = await self.get_clock_data(interaction.guild_id)
        user_state = await self.get_user_clock_state(clock_data, interaction.user.id)
        display_settings = await self.get_display_settings(interaction.guild_id)
        ephemeral = display_settings.get('ephemeral_responses', True)

        if user_state["status"] != "on_break":
            await interaction.response.send_message(
                "You are not currently on break.",
                ephemeral=ephemeral
            )
            return
        
        if not user_state["break_start_time"]:
            await interaction.response.send_message(
                "Error: Break start time not found.",
                ephemeral=ephemeral
            )
            return

        now_utc = datetime.now(timezone.utc)
        break_start_dt = datetime.fromisoformat(user_state["break_start_time"])
        current_break_duration = now_utc - break_start_dt
        
        user_state["accumulated_break_duration_seconds_this_shift"] += current_break_duration.total_seconds()
        user_state["status"] = "clocked_in"
        user_state["break_start_time"] = None

        await self.save_clock_data(interaction.guild_id, clock_data)
        
        embed = discord.Embed(
            title="Break Ended",
            color=discord.Color.green(),
            timestamp=now_utc
        )
        embed.add_field(
            name="Duration",
            value=format_timedelta(current_break_duration),
            inline=True
        )
        embed.add_field(
            name="Total Break Time",
            value=format_timedelta(timedelta(
                seconds=user_state["accumulated_break_duration_seconds_this_shift"]
            )),
            inline=True
        )
        
        content = f"You returned from break. Duration: {format_timedelta(current_break_duration)}"
        await self.send_response(interaction, content, embed)

    # Bonus/Penalty Commands
    bonus_group = app_commands.Group(name="bonus", description="Manage bonuses")
    penalty_group = app_commands.Group(name="penalty", description="Manage penalties")

    async def _add_bonus_penalty(self, interaction: discord.Interaction, user: discord.User, 
                               amount: float, item_type: str, reason: Optional[str] = None):
        display_settings = await self.get_display_settings(interaction.guild_id)
        ephemeral = display_settings.get('ephemeral_responses', True)
        if not await self.has_bonus_penalty_permission(interaction):
            await interaction.response.send_message(
                "You don't have permission to manage bonuses/penalties.",
                ephemeral=ephemeral
            )
            return
        
        if amount <= 0:
            await interaction.response.send_message(
                f"Amount must be positive.",
                ephemeral=ephemeral
            )
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
        
        await interaction.response.send_message(
            f"{item_type.capitalize()} of ${amount:.2f} added to {user.mention}. ID: `{item_id[:8]}`",
            ephemeral=ephemeral
        )

    async def _remove_bonus_penalty(self, interaction: discord.Interaction, 
                                   user: discord.User, item_id: str, item_type: str):
        display_settings = await self.get_display_settings(interaction.guild_id)
        ephemeral = display_settings.get('ephemeral_responses', True)
        if not await self.has_bonus_penalty_permission(interaction):
            await interaction.response.send_message(
                "You don't have permission to manage bonuses/penalties.",
                ephemeral=ephemeral
            )
            return

        clock_data = await self.get_clock_data(interaction.guild_id)
        user_bp_list = clock_data["bonuses_penalties"].get(str(user.id), [])
        
        item_to_remove = None
        for item in user_bp_list:
            if item["id"].startswith(item_id) and item["type"] == item_type:
                item_to_remove = item
                break
        
        if item_to_remove:
            user_bp_list.remove(item_to_remove)
            await self.save_clock_data(interaction.guild_id, clock_data)
            await interaction.response.send_message(
                f"Removed {item_type} (ID: `{item_to_remove['id'][:8]}`) from {user.mention}.",
                ephemeral=ephemeral
            )
        else:
            await interaction.response.send_message(
                f"No {item_type} found with ID starting with `{item_id}`.",
                ephemeral=ephemeral
            )

    async def _list_bonus_penalty(self, interaction: discord.Interaction, 
                                target_user: discord.User, item_type: str):
        display_settings = await self.get_display_settings(interaction.guild_id)
        ephemeral = display_settings.get('ephemeral_responses', True)
        if target_user.id != interaction.user.id and not await self.has_bonus_penalty_permission(interaction):
            await interaction.response.send_message(
                f"You can't view other users' {item_type}s.",
                ephemeral=ephemeral
            )
            return

        clock_data = await self.get_clock_data(interaction.guild_id)
        user_bp_list = sorted(
            [item for item in clock_data["bonuses_penalties"].get(str(target_user.id), []) 
            if item["type"] == item_type],
            key=lambda x: x['timestamp'],
            reverse=True
        )

        if not user_bp_list:
            await interaction.response.send_message(
                f"No {item_type}s found.",
                ephemeral=ephemeral
            )
            return

        embed = discord.Embed(
            title=f"{item_type.capitalize()}s for {target_user.display_name}",
            color=discord.Color.blue()
        )
        
        description = []
        for i, item in enumerate(user_bp_list, 1):
            giver = interaction.guild.get_member(int(item["giver_id"]))
            giver_name = giver.display_name if giver else "Unknown"
            reason = item.get('reason', 'No reason provided')
            timestamp = datetime.fromisoformat(item['timestamp']).strftime('%m/%d %H:%M')
            description.append(
                f"**{i}. ${item['amount']:.2f}**\n"
                f"*{reason}*\n"
                f"ID: `{item['id'][:8]}` • By {giver_name} • {timestamp}"
            )
        
        embed.description = "\n\n".join(description)
        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)

    # Bonus Commands
    @bonus_group.command(name="add", description="Add a bonus")
    @app_commands.describe(
        user="User to receive bonus",
        amount="Bonus amount",
        reason="Optional reason"
    )
    async def add_bonus(self, interaction: discord.Interaction, 
                       user: discord.User, amount: app_commands.Range[float, 0.01, 10000.0], 
                       reason: Optional[str] = None):
        await self._add_bonus_penalty(interaction, user, amount, "bonus", reason)

    @bonus_group.command(name="remove", description="Remove a bonus")
    @app_commands.describe(
        user="User to remove bonus from",
        bonus_id="Bonus ID to remove"
    )
    async def remove_bonus(self, interaction: discord.Interaction, 
                          user: discord.User, bonus_id: str):
        await self._remove_bonus_penalty(interaction, user, bonus_id, "bonus")

    @bonus_group.command(name="list", description="List bonuses")
    @app_commands.describe(user="User to list bonuses for")
    async def list_bonuses(self, interaction: discord.Interaction, 
                          user: Optional[discord.User] = None):
        target_user = user or interaction.user
        await self._list_bonus_penalty(interaction, target_user, "bonus")

    # Penalty Commands
    @penalty_group.command(name="add", description="Add a penalty")
    @app_commands.describe(
        user="User to receive penalty",
        amount="Penalty amount",
        reason="Optional reason"
    )
    async def add_penalty(self, interaction: discord.Interaction, 
                         user: discord.User, amount: app_commands.Range[float, 0.01, 10000.0], 
                         reason: Optional[str] = None):
        await self._add_bonus_penalty(interaction, user, amount, "penalty", reason)

    @penalty_group.command(name="remove", description="Remove a penalty")
    @app_commands.describe(
        user="User to remove penalty from",
        penalty_id="Penalty ID to remove"
    )
    async def remove_penalty(self, interaction: discord.Interaction, 
                            user: discord.User, penalty_id: str):
        await self._remove_bonus_penalty(interaction, user, penalty_id, "penalty")

    @penalty_group.command(name="list", description="List penalties")
    @app_commands.describe(user="User to list penalties for")
    async def list_penalties(self, interaction: discord.Interaction, 
                            user: Optional[discord.User] = None):
        target_user = user or interaction.user
        await self._list_bonus_penalty(interaction, target_user, "penalty")

async def setup(bot):
    await bot.add_cog(ClockInTrackerSlash(bot))
    logger.info("ClockInTrackerSlash cog loaded.")