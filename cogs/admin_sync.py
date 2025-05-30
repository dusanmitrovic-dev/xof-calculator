import logging
from typing import Any, Dict, List
import discord
from discord import Interaction, app_commands
from discord.ext import commands
from utils import file_handlers
from config import settings
from utils.db import get_current_mongo_client

logger = logging.getLogger("xof_calculator.admin_sync")

class SyncCommands(commands.Cog, name="sync"):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="sync-members-and-roles", description="Sync all roles and members to the database")
    @app_commands.default_permissions(administrator=True)
    async def sync(
        self,
        interaction: discord.Interaction
    ):
        """
        Sync all roles and members from the guild to the database.
        """
        ephemeral = True  # Assuming ephemeral responses are enabled by default
        guild_id = str(interaction.guild.id)

        try:
            # Fetch roles and members
            roles, members = await get_roles_and_members_from_interaction(interaction)

            # Sync to the database
            success = await sync_guild_members_and_roles(guild_id, members, roles)

            if success:
                await interaction.response.send_message("✅ Roles and members successfully synced to the database.", ephemeral=ephemeral)
            else:
                await interaction.response.send_message("❌ Failed to sync roles and members to the database.", ephemeral=ephemeral)

        except Exception as e:
            logger.error(f"Error during sync operation: {e}")
            await interaction.response.send_message(f"❌ An error occurred: {e}", ephemeral=ephemeral)

    @app_commands.command(name="sync-config", description="Push or pull configuration data to/from the database")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        action="Choose whether to push or pull configuration data"
    )
    @app_commands.choices(
        action=[
            app_commands.Choice(name="Push to Database", value="push"),
            app_commands.Choice(name="Pull from Database", value="pull")
        ]
    )
    async def sync_config(
        self,
        interaction: discord.Interaction,
        action: app_commands.Choice[str]
    ):
        """Push or pull configuration data to/from the database."""
        ephemeral = True  # Assuming ephemeral responses are enabled by default
        guild_id = str(interaction.guild.id)

        try:
            if action.value == "push":
                await push_config(guild_id)
                await interaction.response.send_message("✅ Configuration data pushed to the database.", ephemeral=ephemeral)
            elif action.value == "pull":
                await pull_config(guild_id)
                await interaction.response.send_message("✅ Configuration data pulled from the database.", ephemeral=ephemeral)
        except Exception as e:
            logger.error(f"Error during sync operation: {e}")
            await interaction.response.send_message(f"❌ An error occurred: {e}", ephemeral=ephemeral)

    @app_commands.command(name="sync-earnings", description="Push or pull earnings data to/from the database")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        action="Choose whether to push or pull earnings data"
    )
    @app_commands.choices(
        action=[
            app_commands.Choice(name="Push to Database", value="push"),
            app_commands.Choice(name="Pull from Database", value="pull")
        ]
    )
    async def sync_earnings(
        self,
        interaction: discord.Interaction,
        action: app_commands.Choice[str]
    ):
        """Push or pull earnings data to/from the database."""
        ephemeral = True  # Assuming ephemeral responses are enabled by default
        guild_id = str(interaction.guild.id)

        try:
            if action.value == "push":
                await push_earnings(guild_id)
                await interaction.response.send_message("✅ Earnings data pushed to the database.", ephemeral=ephemeral)
            elif action.value == "pull":
                await pull_earnings(guild_id)
                await interaction.response.send_message("✅ Earnings data pulled from the database.", ephemeral=ephemeral)
        except Exception as e:
            logger.error(f"Error during sync operation: {e}")
            await interaction.response.send_message(f"❌ An error occurred: {e}", ephemeral=ephemeral)
    
async def sync_guild_members_and_roles(guild_id: str, members: List[Dict[str, Any]], roles: List[Dict[str, Any]]) -> bool:
    """
    Sync all current guild members and their IDs, as well as all roles and their IDs, to the database.
    Ensure that only existing members and roles remain in the database.

    Args:
        guild_id: The ID of the guild.
        members: A list of dictionaries containing member information (e.g., {"id": "123", "name": "John"}).
        roles: A list of dictionaries containing role information (e.g., {"id": "456", "name": "Admin"}).

    Returns:
        True if the sync was successful, False otherwise.
    """
    try:
        client = get_current_mongo_client()
        db = client.get_database()

        # Sync members
        member_ids = [member["id"] for member in members]
        for member in members:
            db["guild_members"].update_one(
                {"id": member["id"], "guild_id": guild_id},
                {"$set": {"name": member["name"], "display_name": member.get("display_name", ""), "guild_id": guild_id}},
                upsert=True
            )
        # Remove members that no longer exist in the guild
        db["guild_members"].delete_many({"guild_id": guild_id, "id": {"$nin": member_ids}})

        # Sync roles
        role_ids = [role["id"] for role in roles]
        for role in roles:
            db["guild_roles"].update_one(
                {"id": role["id"], "guild_id": guild_id},
                {"$set": {"name": role["name"], "guild_id": guild_id}},
                upsert=True
            )
        # Remove roles that no longer exist in the guild
        db["guild_roles"].delete_many({"guild_id": guild_id, "id": {"$nin": role_ids}})

        logger.info(f"Successfully synced members and roles for guild_id: {guild_id}")
        return True

    except Exception as e:
        logger.error(f"Error syncing members and roles for guild_id {guild_id}: {e}")
        return False

async def push_config(guild_id: str):
    """Push configuration data to the database."""
    config_files = [
        settings.get_guild_roles_path(guild_id),
        settings.get_guild_shifts_path(guild_id),
        settings.get_guild_periods_path(guild_id),
        settings.get_guild_bonus_rules_path(guild_id),
        settings.get_guild_models_path(guild_id),
        settings.get_guild_display_path(guild_id),
        settings.get_guild_commission_path(guild_id)
    ]

    for file_path in config_files:
        collection_name = settings.MONGO_COLLECTION_MAPPING.get(file_path.split("/")[-1])
        if collection_name in ["roles", "display_settings", "commission_settings"]:
            data = await file_handlers.load_json_from_file(file_path, default={})
        else: 
            data = await file_handlers.load_json_from_file(file_path, default=[])
        
        if data:
            await file_handlers.save_json(file_path, data)  # Save to MongoDB

async def pull_config(guild_id: str):
    """Pull configuration data from the database."""
    config_files = [
        settings.get_guild_roles_path(guild_id),
        settings.get_guild_shifts_path(guild_id),
        settings.get_guild_periods_path(guild_id),
        settings.get_guild_bonus_rules_path(guild_id),
        settings.get_guild_models_path(guild_id),
        settings.get_guild_display_path(guild_id),
        settings.get_guild_commission_path(guild_id)
    ]

    for file_path in config_files:
        collection_name = settings.MONGO_COLLECTION_MAPPING.get(file_path.split("/")[-1])
        data = None
        if collection_name in ["roles", "display_settings", "commission_settings"]:
            data = await file_handlers.load_json(file_path, default={})
        else: 
            data = await file_handlers.load_json(file_path, default=[])
        
        if data:
            await file_handlers.save_json(file_path, data)  # Save to MongoDB

async def push_earnings(guild_id: str):
    """Push earnings data to the database."""
    file_path = settings.get_guild_earnings_path(guild_id)
    data = await file_handlers.load_json_from_file(file_path, default={})

    if not isinstance(data, dict):
        logger.error("Invalid earnings data format. Expected a dictionary grouped by user_mention.")
        return

    try:
        client = get_current_mongo_client()
        db = client.get_database()

        if not data:  # If data is empty, remove all entries for the guild_id
            result = db["earnings"].delete_many({"guild_id": str(guild_id)})
            logger.info(f"Removed {result.deleted_count} earnings entries for guild_id: {guild_id}")
            return

        for user_mention, entries in data.items():
            for entry in entries:
                entry["user_mention"] = user_mention
                entry["guild_id"] = str(guild_id)
                entry["models"] = entry["models"] if isinstance(entry["models"], list) else [entry["models"]]

                db["earnings"].update_one(
                    {"id": entry["id"], "guild_id": str(guild_id)},
                    {"$set": entry},
                    upsert=True
                )
        logger.info("Earnings data successfully pushed to the database.")
    except Exception as e:
        logger.error(f"Error pushing earnings data to the database: {e}")

async def pull_earnings(guild_id: str):
    """Pull earnings data from the database."""
    file_path = settings.get_guild_earnings_path(guild_id)

    try:
        client = get_current_mongo_client()
        db = client.get_database()

        data = list(db["earnings"].find({"guild_id": str(guild_id)}))
        for entry in data:
            entry.pop("_id", None)
            entry["models"] = entry["models"] if isinstance(entry["models"], list) else [entry["models"]]
            try:
                entry["date"] = file_handlers.normalize_date_format(entry["date"])
            except ValueError as e:
                logger.error(f"Skipping entry with invalid date: {entry}. Error: {e}")
                continue

        earnings_dict = {}
        for entry in data:
            user_mention = entry.get("user_mention", "unknown_sender")
            if user_mention not in earnings_dict:
                earnings_dict[user_mention] = []
            earnings_dict[user_mention].append(entry)

        if earnings_dict:
            await file_handlers.save_json_to_file(file_path, earnings_dict)
            logger.info("Earnings data successfully pulled from the database.")
        else:
            logger.warning("No earnings data found in the database.")
    except Exception as e:
        logger.error(f"Error pulling earnings data from the database: {e}")

async def get_roles_and_members_from_interaction(interaction: Interaction):
    """
    Fetch all roles and members from the guild associated with the interaction.

    Args:
        interaction: The interaction object from a Discord command or event.

    Returns:
        A tuple containing:
            - roles: A list of dictionaries with role IDs and names.
            - members: A list of dictionaries with member IDs and names.
    """
    guild = interaction.guild

    if not guild:
        raise ValueError("Interaction does not belong to a guild.")

    # Fetch roles
    roles = [{"id": role.id, "name": role.name} for role in guild.roles]

    # Fetch members
    members = [{"id": member.id, "name": member.name, "display_name": member.display_name} async for member in guild.fetch_members(limit=None)]

    return roles, members

async def setup(bot):
    await bot.add_cog(SyncCommands(bot))