# AGT BOT
import discord
import json
import os
from dotenv import load_dotenv
load_dotenv()
from collections import defaultdict
from discord.ext import commands
from discord import app_commands
from typing import Optional
from datetime import datetime, timezone


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                              CONFIGURATION                                   ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

SERVER_ID = discord.Object(id=1455476030931210343)

# Role IDs
COMMENTATOR_ROLE = 1457029603095740591
REFEREE_ROLE     = 1455502932790214747
CASTER_ROLE      = 1455503580827222219

# Channel IDs
TRANSACTION_LOG_CHANNEL = 1460337594339426578
AUDIT_LOG_CHANNEL       = 1484284952253038712

# File paths
TEAMS_FILE         = "teams.json"
SCRIMS_FILE        = "scrims.json"
SCRIM_MESSAGES_FILE = "scrim_messages.json"
INVITES_FILE       = "invites.json"
FORFEITS_FILE      = "forfeits.json"
SEEDING_FILE       = "seeding.json"

# Premium Server ID
PREMIUM_SERVERS = {}


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                            PERSISTENCE HELPERS                               ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

def load_json_file(path: str, default):
    if not os.path.exists(path):
        return default
    with open(path, "r") as f:
        content = f.read().strip()
        if not content:
            return default
        return json.loads(content)

def save_json_file(path: str, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

# Teams
def load_teams() -> dict:
    data = load_json_file(TEAMS_FILE, {})
    return {k.lower(): v for k, v in data.items()}

def save_teams():
    save_json_file(TEAMS_FILE, teams)


# Seeding
def load_seeding() -> dict:
    return load_json_file(SEEDING_FILE, {})

def save_seeding(data: dict):
    save_json_file(SEEDING_FILE, data)


# Scrims
def load_scrims() -> list:
    data = load_json_file(SCRIMS_FILE, [])
    return data if isinstance(data, list) else []

def save_scrims():
    save_json_file(SCRIMS_FILE, scrims_schedule)


# Scrim message IDs
def load_scrim_messages() -> dict:
    return load_json_file(SCRIM_MESSAGES_FILE, {})

def save_scrim_messages():
    save_json_file(SCRIM_MESSAGES_FILE, scrim_message_ids)


# Invites
def load_invites() -> dict:
    data = load_json_file(INVITES_FILE, {})
    return {int(k): v for k, v in data.items()}

def save_invites():
    save_json_file(INVITES_FILE, pending_invites)


# Forfeits
def load_forfeits() -> dict:
    return load_json_file(FORFEITS_FILE, {})

def save_forfeits():
    save_json_file(FORFEITS_FILE, forfeits)


# ── In-memory state ───────────────────────────────────────────────────────────

teams:            dict = load_teams()
seeding:          dict = load_seeding()
scrims_schedule:  list = load_scrims()
scrim_message_ids: dict = load_scrim_messages()
scrim_messages:   dict = {}   # {key: discord.Message} — populated at runtime
pending_invites:  dict = load_invites()
forfeits:         dict = load_forfeits()


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                               BOT CLIENT                                     ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

class Client(commands.Bot):
    async def on_ready(self):
        print(f'Logged on as {self.user}!')
        self.add_view(ScrimView())
        try:
            guild  = discord.Object(id=1455476030931210343)
            synced = await self.tree.sync(guild=guild)
            print(f'Synced {len(synced)} commands to guild {guild.id}')
        except Exception as e:
            print(f'Error syncing commands: {e}')

intents = discord.Intents.default()
intents.members = True

client = Client(command_prefix="!", intents=intents)

 # --- PREMIUM CHECK ---
def is_premium():
    async def paid_premium(interaction: discord.Interaction):
        if interaction.guild and interaction.guild.id in PREMIUM_SERVERS:
            return True

        await interaction.response.send_message(
            "This server does has not paid for premium. If you want access to this command please ask the server owner to contact @had3s.pgc.",
            ephemeral=True)
        return False

    return app_commands.check(paid_premium)


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                               AUDIT LOGGING                                  ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

async def log_command(interaction: discord.Interaction) -> bool:
    if interaction.command is None:
        return True
    if interaction.type == discord.InteractionType.autocomplete:
        return True

    if not interaction.guild or interaction.guild.id not in PREMIUM_SERVERS:
        return True

    channel = interaction.guild.get_channel(AUDIT_LOG_CHANNEL)
    if channel:
        options     = interaction.data.get("options", [])
        parts       = []
        for o in options:
            name  = o["name"]
            value = o["value"]
            if name == "player":
                value = f"<@{value}>"
            parts.append(f"{name}: `{value}`")
        options_str = " ".join(parts)

        embed = discord.Embed(
            description=f"**/{interaction.command.name}**" + (f"\n{options_str}" if options_str else ""),
            color=0xB3B3FC)
        embed.set_author(name=interaction.user.name, icon_url=interaction.user.display_avatar.url)
        embed.set_footer(text=f"#{interaction.channel.name}")
        embed.timestamp = discord.utils.utcnow()
        await channel.send(embed=embed)
    return True

client.tree.interaction_check = log_command


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                            AUTOCOMPLETE HANDLERS                             ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

async def team_autocomplete(interaction: discord.Interaction, current: str):
    return [
        app_commands.Choice(name=name.title(), value=name)
        for name in teams if current.lower() in name.lower()
    ][:25]

async def seeding_team_autocomplete(interaction: discord.Interaction, current: str):
    try:
        order  = seeding.get("order", [])
        points = seeding.get("points", {})
        return [
            app_commands.Choice(name=f"{name.title()} — {points.get(name, 0)} pts", value=name)
            for name in order if current.lower() in name.lower()
        ][:25]
    except Exception:
        return []

async def scrim_autocomplete(interaction: discord.Interaction, current: str):
    return [
        app_commands.Choice(
            name=f"{s['team1']} vs {s['team2']} — {s['date']} at {s['time']}",
            value=f"{s['team1'].lower()}|{s['team2'].lower()}|{s['time']}|{s['date']}"
        )
        for s in scrims_schedule
        if current.lower() in f"{s['team1']} {s['team2']}".lower()
    ][:25]


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                              UTILITY FUNCTIONS                               ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

def get_player_team(player_id: int) -> str | None:
    for key, team in teams.items():
        if player_id in team["players"]:
            return key
    return None

async def log_transaction(interaction: discord.Interaction, message: str):
    channel = interaction.guild.get_channel(TRANSACTION_LOG_CHANNEL)
    if channel:
        await channel.send(message)

async def get_scrim_message(guild: discord.Guild, key: str):
    if key in scrim_messages:
        return scrim_messages[key]
    data = scrim_message_ids.get(key)
    if not data:
        return None
    try:
        channel = guild.get_channel(data["channel_id"])
        if channel is None:
            return None
        msg = await channel.fetch_message(data["message_id"])
        scrim_messages[key] = msg
        return msg
    except (discord.NotFound, discord.Forbidden):
        return None

async def get_seeding_message(guild: discord.Guild):
    channel_id = seeding.get("channel_id")
    message_id = seeding.get("message_id")
    if not channel_id or not message_id:
        return None
    try:
        channel = guild.get_channel(channel_id)
        if channel is None:
            return None
        return await channel.fetch_message(message_id)
    except (discord.NotFound, discord.Forbidden):
        return None

def build_seeding_embed(order: list, footer: str, points: dict, ended: bool = False, qualifiers: int = None) -> discord.Embed:
    if not ended:
        description = "# AGT Season's Seeding 🎯\n**Current seedings based on team scores.**"
    else:
        description = f"# AGT Seeding Results 🏆\n**Top {qualifiers} teams have moved on! Congradulations!**"

    lines = []
    for team, team_key in enumerate(order, start=1):
        team        = teams.get(team_key, {})
        wins        = team.get("wins", 0)
        losses      = team.get("losses", 0)
        draws       = team.get("draws", 0)
        team_points = points.get(team_key, 0)
        prefix      = ("✅" if team <= qualifiers else "❌") if (ended and qualifiers is not None) else ""
        lines.append(
            f"## {prefix} **{team} {team_key.title()}**\n"
            f"> **{wins}W | {losses}L | {draws}D | {team_points}pts**"
        )

    embed = discord.Embed(
        description=description + "\n\n" + "\n\n".join(lines),
        color=0xB3B3FC if not ended else discord.Color.gold())
    embed.set_footer(text=footer)
    return embed

async def _apply_seeding_result(interaction: discord.Interaction, winner: str, loser: str, label: str):
    if not (seeding and seeding.get("order") and not seeding.get("locked")):
        return

    win_pts = seeding.get("win_points", 0)
    loss_pts = seeding.get("loss_points", 0)
    points  = seeding.get("points", {})
    updated = False

    if winner in points:
        points[winner] = points.get(winner, 0) + win_pts
        updated = True
    if loser in points:
        points[loser] = points.get(loser, 0) + loss_pts
        updated = True

    if updated:
        order = sorted(points, key=lambda k: points[k], reverse=True)
        seeding["order"]  = order
        seeding["points"] = points
        save_seeding(seeding)
        seed_embed   = build_seeding_embed(order, footer=label, points=points)
        original_msg = await get_seeding_message(interaction.guild)
        if original_msg:
            await original_msg.edit(embed=seed_embed)


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                               SCRIM VIEW (UI)                                ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

class ScrimView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def has_role(self, interaction: discord.Interaction, *role_ids: int) -> bool:
        if not any(role.id in role_ids for role in interaction.user.roles):
            await interaction.response.send_message("You don't have the required role for this.", ephemeral=True)
            return False
        return True

    def lock_if_full(self, description: str):
        all_filled = (
            "**Commentator:** None"    not in description
            and "**2nd Commentator:** None" not in description
            and "**Referee:** None"    not in description
            and "**Caster:** None"     not in description
        )
        if all_filled:
            for item in self.children:
                if hasattr(item, "custom_id") and item.custom_id != "scrim:leave":
                    item.disabled = True

    @discord.ui.button(label="Be Commentator",     style=discord.ButtonStyle.gray, emoji="🎙️", custom_id="scrim:commentator")
    async def com(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.has_role(interaction, COMMENTATOR_ROLE):
            return
        embed = interaction.message.embeds[0]
        if interaction.user.mention in embed.description:
            await interaction.response.send_message("You have already claimed a role in this scrim.", ephemeral=True)
            return
        if "**Commentator:** None" not in embed.description:
            await interaction.response.send_message("Commentator already taken.", ephemeral=True)
            return
        embed.description = embed.description.replace("**Commentator:** None", f"**Commentator:** {interaction.user.mention}")
        button.disabled = True
        self.lock_if_full(embed.description)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Be 2nd Commentator", style=discord.ButtonStyle.gray, emoji="🎤", custom_id="scrim:commentator2")
    async def com2(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.has_role(interaction, COMMENTATOR_ROLE):
            return
        embed = interaction.message.embeds[0]
        if interaction.user.mention in embed.description:
            await interaction.response.send_message("You have already claimed a role in this scrim.", ephemeral=True)
            return
        if "**2nd Commentator:** None" not in embed.description:
            await interaction.response.send_message("2nd Commentator already taken.", ephemeral=True)
            return
        embed.description = embed.description.replace("**2nd Commentator:** None", f"**2nd Commentator:** {interaction.user.mention}")
        button.disabled = True
        self.lock_if_full(embed.description)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Be Referee",         style=discord.ButtonStyle.gray, emoji="⁉️", custom_id="scrim:referee")
    async def ref(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.has_role(interaction, REFEREE_ROLE):
            return
        embed = interaction.message.embeds[0]
        if interaction.user.mention in embed.description:
            await interaction.response.send_message("You have already claimed a role in this scrim.", ephemeral=True)
            return
        if "**Referee:** None" not in embed.description:
            await interaction.response.send_message("Referee already taken.", ephemeral=True)
            return
        embed.description = embed.description.replace("**Referee:** None", f"**Referee:** {interaction.user.mention}")
        button.disabled = True
        self.lock_if_full(embed.description)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Be Caster",          style=discord.ButtonStyle.gray, emoji="📸", custom_id="scrim:caster")
    async def cast(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.has_role(interaction, CASTER_ROLE):
            return
        embed = interaction.message.embeds[0]
        if interaction.user.mention in embed.description:
            await interaction.response.send_message("You have already claimed a role in this scrim.", ephemeral=True)
            return
        if "**Caster:** None" not in embed.description:
            await interaction.response.send_message("Caster already taken.", ephemeral=True)
            return
        embed.description = embed.description.replace("**Caster:** None", f"**Caster:** {interaction.user.mention}")
        button.disabled = True
        self.lock_if_full(embed.description)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Exit Role",          style=discord.ButtonStyle.gray, emoji="🚫", custom_id="scrim:leave")
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.has_role(interaction, CASTER_ROLE, COMMENTATOR_ROLE, REFEREE_ROLE):
            return
        await interaction.response.defer()
        embed = interaction.message.embeds[0]
        if interaction.user.mention not in embed.description:
            await interaction.followup.send("You do not have any roles in this scrim.", ephemeral=True)
            return
        role_map = {
            "scrim:commentator":  f"**Commentator:** {interaction.user.mention}",
            "scrim:commentator2": f"**2nd Commentator:** {interaction.user.mention}",
            "scrim:referee":      f"**Referee:** {interaction.user.mention}",
            "scrim:caster":       f"**Caster:** {interaction.user.mention}",
        }
        for child in self.children:
            if hasattr(child, "custom_id") and child.custom_id in role_map:
                if role_map[child.custom_id] in embed.description:
                    child.disabled = False
        for value in role_map.values():
            if value in embed.description:
                label = value.split(f": {interaction.user.mention}")[0]
                embed.description = embed.description.replace(value, f"{label}: None")
        await interaction.message.edit(embed=embed, view=self)

    @discord.ui.button(label="Cancel Scrim",       style=discord.ButtonStyle.red,  emoji="❌", custom_id="scrim:cancel")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You do not have permission to cancel scrims.", ephemeral=True)
            return
        embed = interaction.message.embeds[0]
        embed.colour      = discord.Color.red()
        embed.description = "# ❌ Scrim Cancelled\n" + "\n".join(embed.description.split("\n")[1:])
        for child in self.children:
            child.disabled = True
        await interaction.message.edit(embed=embed, view=self)
        await log_transaction(interaction, f"A scrim was cancelled by {interaction.user.mention}.")
        await interaction.response.send_message("Scrim has been cancelled.", ephemeral=True)


# INVITE VIEW

class MyInvitesView(discord.ui.View):
    def __init__(self, player: discord.Member, invites: list):
        super().__init__(timeout=60)
        self.player = player
        for invite in invites:
            self.add_item(InviteButton(invite["team_name"], invite["inviter_id"]))


class InviteButton(discord.ui.Button):
    def __init__(self, team_name: str, inviter_id: int):
        super().__init__(label=team_name.title(), style=discord.ButtonStyle.blurple, emoji="📨")
        self.team_name  = team_name
        self.inviter_id = inviter_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.view.player.id:
            await interaction.response.send_message("These invites are not for you.", ephemeral=True)
            return
        view = InviteActionView(interaction.user, self.team_name, self.inviter_id, self.view)
        await interaction.response.edit_message(
            content=f"You have an invite to **{self.team_name.title()}** from <@{self.inviter_id}>. Accept or decline?",
            view=view)


class InviteActionView(discord.ui.View):
    def __init__(self, player: discord.Member, team_name: str, inviter_id: int, previous_view):
        super().__init__(timeout=60)
        self.player        = player
        self.team_name     = team_name
        self.inviter_id    = inviter_id
        self.previous_view = previous_view

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.gray, emoji="✅")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.player.id:
            await interaction.response.send_message("This invite is not for you.", ephemeral=True)
            return
        key = self.team_name.lower()
        if key not in teams:
            await interaction.response.edit_message(content="This team no longer exists.", view=None)
            return
        team = teams[key]
        if team.get("locked"):
            await interaction.response.edit_message(content="This team's roster is locked. You cannot join right now.", view=None)
            return
        if self.player.id in team["players"]:
            await interaction.response.edit_message(content="You are already on this team.", view=None)
            return
        existing_team = get_player_team(self.player.id)
        if existing_team and existing_team != self.team_name.lower():
            await interaction.response.edit_message(
                content=f"You are already on **{existing_team.title()}**, please leave that team before you join this one.",
                view=None)
            return
        if len(team["players"]) >= 10:
            await interaction.response.edit_message(content="This team is full (10/10 players).", view=None)
            return
        team_role = interaction.guild.get_role(team["team_role"])
        if team_role is None:
            await interaction.response.edit_message(content="Team role not found. It may have been deleted.", view=None)
            return
        await self.player.add_roles(team_role)
        team["players"].append(self.player.id)
        if self.player.id in pending_invites:
            pending_invites[self.player.id] = [
                i for i in pending_invites[self.player.id] if i["team_name"] != self.team_name
            ]
            save_invites()
        save_teams()
        await log_transaction(interaction, f"{self.player.mention} accepted the invite to **{self.team_name.title()}**.")
        await interaction.response.edit_message(content=f"You have joined **{self.team_name.title()}**!", view=None)

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.gray, emoji="❌")
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.player.id:
            await interaction.response.send_message("This invite is not for you.", ephemeral=True)
            return
        if self.player.id in pending_invites:
            pending_invites[self.player.id] = [
                i for i in pending_invites[self.player.id] if i["team_name"] != self.team_name
            ]
            save_invites()
        await interaction.response.edit_message(content=f"You declined the invite to **{self.team_name.title()}**.", view=None)


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                                   EVENTS                                     ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

@client.event
async def on_member_remove(member: discord.Member):
    key = get_player_team(member.id)
    if not key:
        return
    team = teams[key]
    team["players"].remove(member.id)
    if team["captain"] == member.id:
        team["captain"] = None
    if team["co_captain"] == member.id:
        team["co_captain"] = None
    save_teams()
    channel = member.guild.get_channel(TRANSACTION_LOG_CHANNEL)
    if channel:
        await channel.send(
            f"{member.mention} (`{member.name}`) left the server and was automatically removed from **{key.title()}**."
        )


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                            COMMANDS — GENERAL                                ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

@client.tree.command(name="print", description="Print a message", guild=SERVER_ID)
@is_premium()
async def msg(interaction: discord.Interaction, message: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        return
    await interaction.response.send_message("Your message was sent!", ephemeral=True)
    await interaction.channel.send(message)


@client.tree.command(name="info", description="Information about the bot's commands", guild=SERVER_ID)
async def cmd_info(interaction: discord.Interaction):
    embed = discord.Embed(description="# AGT Bot System — Command Guide\n"
            "* What every command does and who is allowed to use it:\n\n"
            ">>> ## Basic commands"
            "**/info**\n"
            "- Who can use it: Anyone\n"
            "- Sends information about the bot's commands.\n\n"
            "**/roster**\n"
            "- Who can use it: Anyone\n"
            "- Shows the roster of a team.\n\n"
            "**/leave_team**\n"
            "- Who can use it: Anyone\n"
            "- Allows a player to leave their current team.\n\n"
            "**/check_invites**\n"
            "- Who can use it: Anyone\n"
            "- Shows a list of invites from teams, allowing you to pick which to join.\n\n"
            "**/schedule**\n"
            "- Who can use it: Anyone\n"
            "- Shows the full upcoming scrim schedule grouped by date.\n\n"
            "**/kick_player**\n"
            "- Who can use it: Captains, Co-Captains, and Administrators\n"
            "- Removes a player from a team.\n\n"
            "**/assign_cocaptain**\n"
            "- Who can use it: Captains and Administrators\n"
            "- Assigns a co-captain to a team.\n\n"
            "**/transfer_captain**\n"
            "- Who can use it: Captains and Administrators\n"
            "- Transfers captaincy to another player on the team.\n\n"
            "**/invite_player**\n"
            "- Who can use it: Captains, Co-Captains, and Administrators\n"
            "- Invites a member in the league to join a team.\n\n"
            "**/create_team**\n"
            "- Who can use it: Administrators\n"
            "- Allows an administrator to enter and setup a team for the league.\n\n"
            "**/disband_team**\n"
            "- Who can use it: Administrators\n"
            "- Disbands an existing team within the league disqualifying them from participating.\n\n"
            "**/lock_rosters**\n"
            "- Who can use it: Administrators\n"
            "- Locks all team rosters preventing changes.\n\n"
            "**/unlock_rosters**\n"
            "- Who can use it: Administrators\n"
            "- Unlocks all team rosters allowing changes.\n\n"
            "**/assign_captain**\n"
            "- Who can use it: Administrators\n"
            "- Assigns a captain to a team.<<<\n\n"

            "## Premium Commands\n"
            "**/print**\n"
            "- Who can use it: Administrators\n"
            "- Prints whatever the user inputs into the command.\n\n"
            "**/disband_all**\n"
            "- Who can use it: Administrators\n"
            "- Disbands all existing teams removing them from the league.\n\n"
            "**/list_teams**\n"
            "- Who can use it: Administrators\n"
            "- Lists all active teams in the league.\n\n"
            "**/add_player**\n"
            "- Who can use it: Administrators\n"
            "- Allows an administrator to manually add a player to a team.\n\n"
            "**/set_scrim**\n"
            "- Who can use it: Administrators\n"
            "- Allows an administrator to set up a time for a scrim.\n\n"
            "**/check_scrims**\n"
            "- Who can use it: Anyone\n"
            "- Shows a quick list of all upcoming scrims.\n\n"
            "**/end_scrim**\n"
            "- Who can use it: Administrators\n"
            "- Ends a scrim and records the final score.\n\n"
            "**/check_scrims**\n"
            "- Who can use it: Anyone\n"
            "- Shows a quick list of all upcoming scrims.\n\n"
            "**/create_scrim_channel**\n"
            "- Who can use it: Administrators\n"
            "- Creates a private channel for two teams to coordinate their scrim.\n\n"
            "**/forfeit_scrim**\n"
            "- Who can use it: Administrators\n"
            "- Marks a team as forfeiting a scrim.\n\n"
            "**/autoforfeit_scrim**\n"
            "- Who can use it: Administrators\n"
            "- Flags a team for auto-forfeit on their next scheduled scrim.\n\n"
            "**/create_seeding**\n"
            "- Who can use it: Administrators\n"
            "- Creates a seeding round and tracks team scores.\n\n"
            "**/edit_seeding**\n"
            "- Who can use it: Administrators\n"
            "- Manually adds or removes points from a team in seeding.\n\n"
            "**/end_seeding**\n"
            "- Who can use it: Administrators\n"
            "- Ends the seeding round and displays which teams have advanced.\n\n"
            "AGT Season Management System - Created by Had3s", color=0xB3B3FC)
# Once you send the embed removed the "await interaction.channel.send(embed=embed)" 
# Also replace the ""Done"" in "await interaction.response.send_message("Done", ephmeral=True)" with "embed=embed"
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                            COMMANDS — TEAMS                                  ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

@client.tree.command(name="create_team", description="Create a new team", guild=SERVER_ID)
async def create_team(interaction: discord.Interaction, team_name: str, captain_name: discord.Member, co_captain_name: Optional[discord.Member] = None):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You don't have permission to create teams.", ephemeral=True)
        return
    if team_name in teams:
        await interaction.response.send_message(f"**{team_name.title()}** already exists.", ephemeral=True)
        return
    existing = get_player_team(captain_name.id)
    if existing:
        await interaction.response.send_message(f"{captain_name.mention} is already on **{existing.title()}**, choose another member.", ephemeral=True)
        return
    if co_captain_name:
        existing = get_player_team(co_captain_name.id)
        if existing:
            await interaction.response.send_message(f"{co_captain_name.mention} is already on **{existing.title()}**, choose another member.", ephemeral=True)
            return

    await interaction.response.defer(ephemeral=True)
    team_role       = await interaction.guild.create_role(name=team_name.title())
    captain_role    = await interaction.guild.create_role(name=f"{team_name.title()} | Captain")
    co_captain_role = await interaction.guild.create_role(name=f"{team_name.title()} | Co-Captain")

    await captain_name.add_roles(team_role, captain_role)
    if co_captain_name:
        await co_captain_name.add_roles(team_role, co_captain_role)

    teams[team_name] = {
        "name":           team_name,
        "captain":        captain_name.id,
        "co_captain":     co_captain_name.id if co_captain_name else None,
        "players":        [captain_name.id] + ([co_captain_name.id] if co_captain_name else []),
        "wins":           0,
        "losses":         0,
        "draws":          0,
        "team_role":      team_role.id,
        "captain_role":   captain_role.id,
        "co_captain_role": co_captain_role.id,
    }
    save_teams()
    await log_transaction(interaction,
        f"# **{team_name.title()}** has been created.\n"
        f">>> ### Captain: {captain_name.mention}\n"
        f"### Co-Captain: {co_captain_name.mention if co_captain_name else 'None'}")

    embed = discord.Embed(
        description=(
            f"**{team_name}** was created.\n"
            f"### Roles created:\n"
            f">>> • {team_role.mention}\n"
            f"• {captain_role.mention}\n"
            f"• {co_captain_role.mention}"
        ), color=0xB3B3FC)
    await interaction.followup.send(embed=embed, ephemeral=True)


@client.tree.command(name="disband_team", description="Disbands an existing team", guild=SERVER_ID)
@app_commands.autocomplete(team_name=team_autocomplete)
async def disband_team(interaction: discord.Interaction, team_name: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You don't have permission to disband teams.", ephemeral=True)
        return
    key = team_name.lower()
    if key not in teams:
        await interaction.response.send_message(f"**{team_name.title()}** does not exist.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    team            = teams[key]
    team_role       = interaction.guild.get_role(team["team_role"])
    captain_role    = interaction.guild.get_role(team["captain_role"])
    co_captain_role = interaction.guild.get_role(team["co_captain_role"])

    for pid in team["players"]:
        member = interaction.guild.get_member(pid)
        if member:
            roles_to_remove = [r for r in [team_role, captain_role, co_captain_role] if r and r in member.roles]
            if roles_to_remove:
                await member.remove_roles(*roles_to_remove)

    for role_key in ["team_role", "captain_role", "co_captain_role"]:
        try:
            role = interaction.guild.get_role(team[role_key]) or discord.utils.get(
                await interaction.guild.fetch_roles(), id=team[role_key])
            if role:
                await role.delete()
        except discord.NotFound:
            pass

    del teams[key]
    save_teams()
    await log_transaction(interaction, f"Team **{team_name.title()}** was disbanded by {interaction.user.mention}.")
    await interaction.followup.send("Team Disbanded.", ephemeral=True)


@client.tree.command(name="disband_all", description="Disbands all teams", guild=SERVER_ID)
@is_premium()
async def disband_all(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You don't have permission to disband all teams.", ephemeral=True)
        return
    if not teams:
        await interaction.response.send_message("No teams currently exist.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    for key in list(teams.keys()):
        team            = teams[key]
        team_role       = interaction.guild.get_role(team["team_role"])
        captain_role    = interaction.guild.get_role(team["captain_role"])
        co_captain_role = interaction.guild.get_role(team["co_captain_role"])
        for pid in team["players"]:
            member = interaction.guild.get_member(pid)
            if member:
                roles_to_remove = [r for r in [team_role, captain_role, co_captain_role] if r and r in member.roles]
                if roles_to_remove:
                    await member.remove_roles(*roles_to_remove)
        for role_key in ["team_role", "captain_role", "co_captain_role"]:
            try:
                role = interaction.guild.get_role(team[role_key]) or discord.utils.get(
                    await interaction.guild.fetch_roles(), id=team[role_key])
                if role:
                    await role.delete()
            except discord.NotFound:
                pass

    teams.clear()
    save_teams()
    await log_transaction(interaction, f"All teams were disbanded by {interaction.user.mention}.")
    await interaction.followup.send("All teams disbanded.", ephemeral=True)


@client.tree.command(name="list_teams", description="List all active teams", guild=SERVER_ID)
@is_premium()
async def list_teams(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You do not have permissions to list teams.")
    if not teams:
        await interaction.response.send_message("No teams currently exist.", ephemeral=True)
        return
    team_list = "\n".join([f"• **(-- {name.title()} --)**" for name in teams])
    embed = discord.Embed(description=f"## 🏆 Current Season Teams:\n>>> {team_list}", color=0xB3B3FC)
    await interaction.response.send_message("Done.", ephemeral=True)
    await interaction.channel.send(embed=embed)


@client.tree.command(name="roster", description="Show the roster of a team", guild=SERVER_ID)
@app_commands.autocomplete(team_name=team_autocomplete)
async def roster(interaction: discord.Interaction, team_name: str):
    key = team_name.lower()
    if key not in teams:
        await interaction.response.send_message(f"**{team_name.title()}** does not exist.", ephemeral=True)
        return
    team       = teams[key]
    captain    = f"<@{team['captain']}>"    if team["captain"]    else "None"
    co_captain = f"<@{team['co_captain']}>" if team["co_captain"] else "None"
    players    = "\n".join([f"<@{p}>" for p in team["players"]]) if team["players"] else "None"
    embed = discord.Embed(description=(
        f"## **{team_name.title()}** Roster:\n\n"
        f">>> **Captain:** {captain}\n"
        f"**Co-Captain:** {co_captain}\n"
        f"**Players:**\n{players}\n"), color=0xB3B3FC)
    await interaction.response.send_message(embed=embed, ephemeral=True)


@client.tree.command(name="lock_rosters", description="Lock all team rosters", guild=SERVER_ID)
async def lock_rosters(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You don't have permission to lock rosters.", ephemeral=True)
        return
    if not teams:
        await interaction.response.send_message("No teams currently exist.", ephemeral=True)
        return
    for key in teams:
        teams[key]["locked"] = True
    save_teams()
    await log_transaction(interaction, f"All rosters were locked by {interaction.user.mention}.")
    await interaction.response.send_message("All Rosters Locked.", ephemeral=True)


@client.tree.command(name="unlock_rosters", description="Unlock all team rosters", guild=SERVER_ID)
async def cmd_unlock_rosters(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You don't have permission to unlock rosters.", ephemeral=True)
        return
    if not teams:
        await interaction.response.send_message("No teams currently exist.", ephemeral=True)
        return
    for key in teams:
        teams[key]["locked"] = False
    save_teams()
    await log_transaction(interaction, f"All rosters were unlocked by {interaction.user.mention}.")
    await interaction.response.send_message("All Rosters Unlocked.", ephemeral=True)


@client.tree.command(name="add_player", description="Manually add a player to a team (Admin only)", guild=SERVER_ID)
@is_premium()
@app_commands.autocomplete(team_name=team_autocomplete)
async def cmd_add_player(interaction: discord.Interaction, team_name: str, player: discord.Member):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You don't have permission to add players.", ephemeral=True)
        return
    key = team_name.lower()
    if key not in teams:
        await interaction.response.send_message(f"Team **{team_name.title()}** does not exist.", ephemeral=True)
        return
    team = teams[key]
    if team.get("locked"):
        await interaction.response.send_message("This team's roster is locked.", ephemeral=True)
        return
    if player.id in team["players"]:
        await interaction.response.send_message(f"{player.mention} is already on this team, choose another player.", ephemeral=True)
        return
    if len(team["players"]) >= 10:
        await interaction.response.send_message(f"**{team_name.title()}** is full (10/10 players).", ephemeral=True)
        return
    existing_team = get_player_team(player.id)
    if existing_team:
        await interaction.response.send_message(f"{player.mention} is already on **{existing_team.title()}**, choose another player.", ephemeral=True)
        return
    team_role = interaction.guild.get_role(team["team_role"])
    if team_role:
        await player.add_roles(team_role)
    team["players"].append(player.id)
    save_teams()
    await log_transaction(interaction, f"{player.mention} was manually added to **{team_name.title()}** by {interaction.user.mention}.")
    await interaction.response.send_message(f"{player.mention} has been added to **{team_name.title()}**.", ephemeral=True)


@client.tree.command(name="kick_player", description="Kick a player from a team", guild=SERVER_ID)
@app_commands.autocomplete(team_name=team_autocomplete)
async def cmd_kick_player(interaction: discord.Interaction, team_name: str, player: discord.Member):
    key = team_name.lower()
    if key not in teams:
        await interaction.response.send_message(f"Team **{team_name.title()}** does not exist.", ephemeral=True)
        return
    team          = teams[key]
    is_captain    = team["captain"]    == interaction.user.id
    is_co_captain = team["co_captain"] == interaction.user.id
    is_admin      = interaction.user.guild_permissions.administrator
    if not (is_captain or is_co_captain or is_admin):
        await interaction.response.send_message("Only the captain, co-captain, or an admin can remove players.", ephemeral=True)
        return
    if not is_admin and interaction.user.id not in team["players"]:
        await interaction.response.send_message("You are not on this team.", ephemeral=True)
        return
    if player.id == interaction.user.id and not is_admin:
        await interaction.response.send_message("You cannot kick yourself. Use /leave_team instead.", ephemeral=True)
        return
    if player.id not in team["players"]:
        await interaction.response.send_message(f"{player.mention} is not on the team.", ephemeral=True)
        return
    if is_co_captain and team["captain"] == player.id:
        await interaction.response.send_message("Co-captains cannot kick the captain.", ephemeral=True)
        return
    for role_key in ["team_role", "captain_role", "co_captain_role"]:
        role = interaction.guild.get_role(team[role_key])
        if role and role in player.roles:
            await player.remove_roles(role)
    team["players"].remove(player.id)
    if team["captain"]    == player.id: team["captain"]    = None
    if team["co_captain"] == player.id: team["co_captain"] = None
    save_teams()
    await log_transaction(interaction, f"{player.mention} was removed from **{team_name.title()}**.")
    await interaction.response.send_message("Done.", ephemeral=True)


@client.tree.command(name="leave_team", description="Leave your current team", guild=SERVER_ID)
async def cmd_leave_team(interaction: discord.Interaction):
    key = get_player_team(interaction.user.id)
    if not key:
        await interaction.response.send_message("You are not on any team.", ephemeral=True)
        return
    team = teams[key]
    if team.get("locked"):
        await interaction.response.send_message("This team's roster is locked. You cannot leave right now.", ephemeral=True)
        return
    for role_key in ["team_role", "captain_role", "co_captain_role"]:
        role = interaction.guild.get_role(team[role_key])
        if role and role in interaction.user.roles:
            await interaction.user.remove_roles(role)
    if team["captain"]    == interaction.user.id: team["captain"]    = None
    if team["co_captain"] == interaction.user.id: team["co_captain"] = None
    team["players"].remove(interaction.user.id)
    save_teams()
    await log_transaction(interaction, f"{interaction.user.mention} left **{key.title()}**.")
    await interaction.response.send_message(f"You have left **{key.title()}**.", ephemeral=True)


@client.tree.command(name="assign_captain", description="Assign a captain to a team", guild=SERVER_ID)
@app_commands.autocomplete(team_name=team_autocomplete)
async def cmd_assign_captain(interaction: discord.Interaction, team_name: str, player: discord.Member):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You don't have permission to assign captains.", ephemeral=True)
        return
    key = team_name.lower()
    if key not in teams:
        await interaction.response.send_message(f"Team **{team_name.title()}** does not exist.", ephemeral=True)
        return
    team = teams[key]
    if team["captain"] == player.id:
        await interaction.response.send_message(f"{player.mention} is already the captain.", ephemeral=True)
        return
    if player.id not in team["players"]:
        await interaction.response.send_message(f"{player.mention} is not in **{team_name.title()}**. Add them to the team first.", ephemeral=True)
        return
    if team["captain"]:
        old_captain      = interaction.guild.get_member(team["captain"])
        old_captain_role = interaction.guild.get_role(team["captain_role"])
        if old_captain and old_captain_role:
            await old_captain.remove_roles(old_captain_role)
    captain_role = interaction.guild.get_role(team["captain_role"])
    if captain_role:
        await player.add_roles(captain_role)
    team["captain"] = player.id
    save_teams()
    await log_transaction(interaction, f"{player.mention} was assigned as captain of **{team_name.title()}**.")
    await interaction.response.send_message("Done.", ephemeral=True)


@client.tree.command(name="assign_cocaptain", description="Assign a co-captain to a team", guild=SERVER_ID)
@app_commands.autocomplete(team_name=team_autocomplete)
async def cmd_assign_cocaptain(interaction: discord.Interaction, team_name: str, player: discord.Member):
    key = team_name.lower()
    if key not in teams:
        await interaction.response.send_message(f"Team **{team_name.title()}** does not exist.", ephemeral=True)
        return
    team       = teams[key]
    is_captain = team["captain"] == interaction.user.id
    is_admin   = interaction.user.guild_permissions.administrator
    if not (is_captain or is_admin):
        await interaction.response.send_message("Only the captain or an admin can assign a co-captain.", ephemeral=True)
        return
    if team["co_captain"] == player.id:
        await interaction.response.send_message(f"{player.mention} is already the co-captain.", ephemeral=True)
        return
    if player.id not in team["players"]:
        await interaction.response.send_message(f"{player.mention} is not in **{team_name.title()}**. Add them to the team first.", ephemeral=True)
        return
    if team["co_captain"]:
        old_co        = interaction.guild.get_member(team["co_captain"])
        old_co_role   = interaction.guild.get_role(team["co_captain_role"])
        if old_co and old_co_role:
            await old_co.remove_roles(old_co_role)
    co_captain_role = interaction.guild.get_role(team["co_captain_role"])
    if co_captain_role:
        await player.add_roles(co_captain_role)
    team["co_captain"] = player.id
    save_teams()
    await log_transaction(interaction, f"{player.mention} was assigned as co-captain of **{team_name.title()}**.")
    await interaction.response.send_message("Done.", ephemeral=True)


@client.tree.command(name="transfer_captain", description="Transfer captaincy to another player", guild=SERVER_ID)
@app_commands.autocomplete(team_name=team_autocomplete)
async def cmd_transfer_captain(interaction: discord.Interaction, team_name: str, player: discord.Member):
    key = team_name.lower()
    if key not in teams:
        await interaction.response.send_message(f"Team **{team_name.title()}** does not exist.", ephemeral=True)
        return
    team       = teams[key]
    is_captain = team["captain"] == interaction.user.id
    is_admin   = interaction.user.guild_permissions.administrator
    if not (is_captain or is_admin):
        await interaction.response.send_message("Only the current captain or an admin can transfer captaincy.", ephemeral=True)
        return
    if player.id == interaction.user.id:
        await interaction.response.send_message("You can't transfer captaincy to yourself.", ephemeral=True)
        return
    if team["captain"] == player.id:
        await interaction.response.send_message(f"{player.mention} is already the captain.", ephemeral=True)
        return
    if player.id not in team["players"]:
        await interaction.response.send_message(f"{player.mention} is not on this team.", ephemeral=True)
        return
    if team["captain"]:
        old_captain  = interaction.guild.get_member(team["captain"])
        captain_role = interaction.guild.get_role(team["captain_role"])
        if old_captain and captain_role:
            await old_captain.remove_roles(captain_role)
    captain_role = interaction.guild.get_role(team["captain_role"])
    if captain_role:
        await player.add_roles(captain_role)
    team["captain"] = player.id
    save_teams()
    await log_transaction(interaction, f"Captaincy of **{team_name.title()}** was transferred to {player.mention}.")
    embed = discord.Embed(
        description=f"Captaincy of **{team_name.title()}** has been transferred to {player.mention}.",
        color=0xB3B3FC)
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                            COMMANDS — INVITES                                ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

@client.tree.command(name="invite_player", description="Invite a player to a team", guild=SERVER_ID)
@app_commands.autocomplete(team_name=team_autocomplete)
async def cmd_invite_player(interaction: discord.Interaction, team_name: str, player: discord.Member):
    key = team_name.lower()
    if key not in teams:
        await interaction.response.send_message(f"**{team_name.title()}** does not exist.", ephemeral=True)
        return
    team          = teams[key]
    is_captain    = team["captain"]    == interaction.user.id
    is_co_captain = team["co_captain"] == interaction.user.id
    is_admin      = interaction.user.guild_permissions.administrator
    if not (is_captain or is_co_captain or is_admin):
        await interaction.response.send_message("Only the captain, co-captain, or an admin can invite players.", ephemeral=True)
        return
    if not is_admin and interaction.user.id not in team["players"]:
        await interaction.response.send_message("You are not on this team.", ephemeral=True)
        return
    if team.get("locked"):
        await interaction.response.send_message("All rosters are locked. Wait until an Administrator unlocks rosters.", ephemeral=True)
        return
    if player.id in team["players"]:
        await interaction.response.send_message(f"{player.mention} is already on the team, choose another player.", ephemeral=True)
        return
    if len(team["players"]) >= 10:
        await interaction.response.send_message(f"**{team_name.title()}** is full.", ephemeral=True)
        return
    team_role = interaction.guild.get_role(team["team_role"])
    if team_role is None:
        await interaction.response.send_message("Team role not found. It may have been deleted manually.", ephemeral=True)
        return
    existing_team = get_player_team(player.id)
    if existing_team:
        await interaction.response.send_message(f"{player.mention} is already on **{existing_team.title()}**, choose another player.", ephemeral=True)
        return
    if player.id in pending_invites:
        for invite in pending_invites[player.id]:
            if invite["team_name"] == key:
                await interaction.response.send_message(f"{player.mention} already has a pending invite to this team.", ephemeral=True)
                return
    if player.id not in pending_invites:
        pending_invites[player.id] = []
    pending_invites[player.id].append({"team_name": key, "inviter_id": interaction.user.id})
    save_invites()
    await interaction.response.send_message(f"Invite sent to {player.mention} for **{team_name.title()}**.", ephemeral=True)


@client.tree.command(name="check_invites", description="View your pending team invites", guild=SERVER_ID)
async def cmd_check_invites(interaction: discord.Interaction):
    invites = pending_invites.get(interaction.user.id, [])
    if not invites:
        await interaction.response.send_message("You have no pending invites.", ephemeral=True)
        return
    await interaction.response.send_message(
        content="## Your pending invites\nClick a team to accept or decline their invite:",
        view=MyInvitesView(interaction.user, invites),
        ephemeral=True)


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                            COMMANDS — SEEDING                                ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

@client.tree.command(name="create_seeding", description="Create a seeding round for teams", guild=SERVER_ID)
@is_premium()
@app_commands.describe(win_points="Points awarded per win", loss_points="Points awarded per loss")
async def cmd_create_seeding(interaction: discord.Interaction, win_points: int, loss_points: int):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You don't have permission to create seeding rounds.", ephemeral=True)
        return
    if not teams:
        await interaction.response.send_message("No teams have been created yet.", ephemeral=True)
        return
    for key in teams:
        teams[key]["wins"] = teams[key]["losses"] = teams[key]["draws"] = 0
    save_teams()
    points = {key: 0 for key in teams}
    order  = sorted(points, key=lambda k: points[k], reverse=True)
    embed  = build_seeding_embed(order, footer=f"Seeding created by {interaction.user.display_name}", points=points)
    await interaction.response.send_message("Done.", ephemeral=True)
    msg = await interaction.channel.send(embed=embed)
    seeding.update({
        "created_by": interaction.user.id,
        "created_at": discord.utils.utcnow().isoformat(),
        "order":       order,
        "points":      points,
        "win_points":  win_points,
        "loss_points": loss_points,
        "channel_id":  interaction.channel.id,
        "message_id":  msg.id,
        "locked":      False,
    })
    save_seeding(seeding)


@client.tree.command(name="edit_seeding", description="Add or remove points from a team", guild=SERVER_ID)
@is_premium()
@app_commands.autocomplete(team_name=seeding_team_autocomplete)
@app_commands.describe(team_name="The team to edit", points="Points to add")
async def cmd_edit_seeding(interaction: discord.Interaction, team_name: str, points: int):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You don't have permission to edit seedings.", ephemeral=True)
        return
    if not seeding or not seeding.get("order"):
        await interaction.response.send_message("No seeding exists yet. Use `/create_seeding` first.", ephemeral=True)
        return
    if seeding.get("locked"):
        await interaction.response.send_message("Seeding is already locked/ended.", ephemeral=True)
        return
    key = team_name.lower()
    if key not in seeding["order"]:
        await interaction.response.send_message(f"**{team_name.title()}** is not in the current seedings.", ephemeral=True)
        return
    current_points      = seeding["points"]
    current_points[key] = current_points.get(key, 0) + points
    order               = sorted(current_points, key=lambda k: current_points[k], reverse=True)
    seeding["order"]    = order
    seeding["points"]   = current_points
    save_seeding(seeding)
    embed        = build_seeding_embed(order, footer=f"Last edited by {interaction.user.display_name}", points=current_points)
    original_msg = await get_seeding_message(interaction.guild)
    if original_msg:
        await original_msg.edit(embed=embed)
        await interaction.response.send_message("Seeding updated.", ephemeral=True)
    else:
        await interaction.response.send_message("Original seeding message not found, posting a new one.", ephemeral=True)
        msg = await interaction.channel.send(embed=embed)
        seeding["channel_id"] = interaction.channel.id
        seeding["message_id"] = msg.id
        save_seeding(seeding)


@client.tree.command(name="end_seeding", description="End the seeding and show qualifying teams", guild=SERVER_ID)
@is_premium()
@app_commands.describe(qualifiers="Number of teams that advance")
async def cmd_end_seeding(interaction: discord.Interaction, qualifiers: int):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You don't have permission to end seedings.", ephemeral=True)
        return
    if not seeding or not seeding.get("order"):
        await interaction.response.send_message("No seeding exists yet. Use `/create_seeding` first.", ephemeral=True)
        return
    if seeding.get("locked"):
        await interaction.response.send_message("Seeding is already locked/ended.", ephemeral=True)
        return
    order = seeding["order"]
    if qualifiers < 1 or qualifiers > len(order):
        await interaction.response.send_message(f"Qualifiers must be between 1 and {len(order)}.", ephemeral=True)
        return
    seeding["locked"]     = True
    seeding["qualifiers"] = qualifiers
    save_seeding(seeding)
    points = seeding.get("points", {})
    embed  = build_seeding_embed(
        order,
        footer=f"Seeding ended by {interaction.user.display_name} — {qualifiers}/{len(order)} teams advanced",
        points=points, ended=True, qualifiers=qualifiers)
    original_msg = await get_seeding_message(interaction.guild)
    if original_msg:
        await original_msg.edit(embed=embed)
        await interaction.response.send_message("Seeding ended and results posted.", ephemeral=True)
    else:
        await interaction.response.send_message("Original seeding message not found, posting a new one.", ephemeral=True)
        msg = await interaction.channel.send(embed=embed)
        seeding["channel_id"] = interaction.channel.id
        seeding["message_id"] = msg.id
        save_seeding(seeding)
    await log_transaction(interaction, f"Seeding ended by {interaction.user.mention}. {qualifiers}/{len(order)} teams advanced.")


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                            COMMANDS — SCRIMS                                 ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

@client.tree.command(name="set_scrim", description="Set a time and date for a scrim", guild=SERVER_ID)
@is_premium()
@app_commands.autocomplete(first_team=team_autocomplete, second_team=team_autocomplete)
async def cmd_set_scrim(interaction: discord.Interaction, time: str, date: str, first_team: str, second_team: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You don't have permission to create scrims.", ephemeral=True)
        return
    if first_team.lower() == second_team.lower():
        await interaction.response.send_message("Both teams cannot be the same.", ephemeral=True)
        return
    embed = discord.Embed(
        description=(
            "# **----------AGT OFFICIAL SCRIM----------**\n"
            ">>> ## Scrim Details:\n\n"
            f"**Time:** {time}\n"
            f"**Day:** {date}\n"
            f"**First Team:** {first_team.title()}\n"
            f"**Second Team:** {second_team.title()}\n\n"
            "**Commentator:** None\n"
            "**2nd Commentator:** None\n"
            "**Referee:** None\n"
            "**Caster:** None"
        ), color=0xB3B3FC)
    await interaction.response.send_message("Scrim created.", ephemeral=True)
    msg = await interaction.channel.send(embed=embed, view=ScrimView())
    key = f"{first_team.lower()}_{second_team.lower()}"
    scrim_messages[key]    = msg
    scrim_message_ids[key] = {"channel_id": interaction.channel.id, "message_id": msg.id}
    save_scrim_messages()
    scrims_schedule.append({"time": time, "date": date, "team1": first_team.title(), "team2": second_team.title()})
    save_scrims()


@client.tree.command(name="end_scrim", description="End and record the score of a scrim", guild=SERVER_ID)
@is_premium()
@app_commands.autocomplete(scrim=scrim_autocomplete)
async def cmd_end_scrim(interaction: discord.Interaction, scrim: str, score1: int, score2: int, notes: str = ""):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You don't have permission to log scrim scores.", ephemeral=True)
        return
    parts = scrim.split("|")
    if len(parts) != 4:
        await interaction.response.send_message("Invalid scrim selection.", ephemeral=True)
        return
    team1, team2, time, date = parts
    if team1 == team2:
        await interaction.response.send_message("Both teams cannot be the same.", ephemeral=True)
        return

    key = f"{team1}_{team2}"
    msg = await get_scrim_message(interaction.guild, key)
    if msg:
        try:
            result_str = (f"{team1.title()} wins" if score1 > score2
                          else f"{team2.title()} wins" if score2 > score1
                          else "Draw")
            completed_embed = discord.Embed(
                description=(
                    "# **----------✅ SCRIM COMPLETED----------**\n"
                    ">>> ## **Official Scrim For AGT:**\n\n"
                    f"**First Team:** {team1.title()}\n"
                    f"**Second Team:** {team2.title()}\n\n"
                    f"**Result:** {result_str} **{score1} - {score2}**"
                ), color=0x57F287)
            await msg.edit(embed=completed_embed, view=None)
        except Exception:
            pass
        scrim_messages.pop(key, None)
        scrim_message_ids.pop(key, None)
        save_scrim_messages()

    global scrims_schedule
    scrims_schedule = [
        s for s in scrims_schedule
        if not (s["team1"].lower() == team1 and s["team2"].lower() == team2)
    ]
    save_scrims()

    if score1 == score2:
        if team1 in teams: teams[team1]["draws"] = teams[team1].get("draws", 0) + 1
        if team2 in teams: teams[team2]["draws"] = teams[team2].get("draws", 0) + 1
        save_teams()
        # Draws award loss_points to both
        if seeding and seeding.get("order") and not seeding.get("locked"):
            loss_pts = seeding.get("loss_points", 0)
            points   = seeding.get("points", {})
            updated  = False
            for t in [team1, team2]:
                if t in points:
                    points[t] = points.get(t, 0) + loss_pts
                    updated   = True
            if updated:
                order             = sorted(points, key=lambda k: points[k], reverse=True)
                seeding["order"]  = order
                seeding["points"] = points
                save_seeding(seeding)
                seed_embed   = build_seeding_embed(order, footer=f"Updated after {team1.title()} vs {team2.title()}", points=points)
                original_msg = await get_seeding_message(interaction.guild)
                if original_msg:
                    await original_msg.edit(embed=seed_embed)
    else:
        winner = team1 if score1 > score2 else team2
        loser  = team2 if score1 > score2 else team1
        if winner in teams: teams[winner]["wins"]   = teams[winner].get("wins", 0) + 1
        if loser  in teams: teams[loser]["losses"]  = teams[loser].get("losses", 0) + 1
        save_teams()
        await _apply_seeding_result(interaction, winner, loser, f"Updated after {team1.title()} vs {team2.title()}")

    outcome      = "🤝 Draw" if score1 == score2 else f"🏆 {team1.title() if score1 > score2 else team2.title()} Wins"
    result_embed = discord.Embed(description="# 🏆 Scrim Result", color=0xB3B3FC)
    result_embed.add_field(name="Match",  value=f"{team1.title()} 🆚 {team2.title()}", inline=False)
    result_embed.add_field(name="Score",  value=f"**{score1} - {score2}**",            inline=True)
    result_embed.add_field(name="Result", value=f"**{outcome}**",                      inline=True)
    if notes:
        result_embed.add_field(name="Notes", value=notes, inline=False)
    result_embed.set_footer(text="Good Game!")
    await interaction.response.send_message("Scrim score logged.", ephemeral=True)
    await interaction.channel.send(embed=result_embed)


@client.tree.command(name="check_scrims", description="View upcoming scrims", guild=SERVER_ID)
@is_premium()
async def cmd_check_scrims(interaction: discord.Interaction):
    if not scrims_schedule:
        await interaction.response.send_message("No scrims are currently scheduled.", ephemeral=True)
        return
    lines = "\n".join([f"• **{s['team1']}** vs **{s['team2']}** — {s['date']} at {s['time']}" for s in scrims_schedule])
    embed = discord.Embed(title="Upcoming Scrims:", description=f">>> {lines}", color=0xB3B3FC)
    await interaction.response.send_message(embed=embed, ephemeral=True)


@client.tree.command(name="schedule", description="View the full upcoming scrim schedule", guild=SERVER_ID)
async def cmd_schedule(interaction: discord.Interaction):
    if not scrims_schedule:
        await interaction.response.send_message("No scrims are currently scheduled.", ephemeral=True)
        return
    by_date = defaultdict(list)
    for s in scrims_schedule:
        by_date[s["date"]].append(s)
    embed = discord.Embed(title="📅 Upcoming Scrim Schedule", color=0xB3B3FC)
    embed.set_footer(text=f"{len(scrims_schedule)} scrim(s) scheduled • Use /check_scrims for a quick list")
    for date, scrims in sorted(by_date.items()):
        lines = []
        for s in scrims:
            t1_key     = s["team1"].lower()
            t2_key     = s["team2"].lower()
            t1_forfeit = forfeits.get(t1_key, {}).get("auto_forfeit", False)
            t2_forfeit = forfeits.get(t2_key, {}).get("auto_forfeit", False)
            t1_display = f"~~{s['team1']}~~ ⚠️" if t1_forfeit else s["team1"]
            t2_display = f"~~{s['team2']}~~ ⚠️" if t2_forfeit else s["team2"]
            lines.append(f"🕐 **{s['time']}** — {t1_display} vs {t2_display}")
        embed.add_field(name=f"📆 {date}", value="\n".join(lines), inline=False)
    await interaction.response.send_message(embed=embed)


@client.tree.command(name="create_scrim_channel", description="Create a private channel for two teams' scrim", guild=SERVER_ID)
@is_premium()
@app_commands.autocomplete(first_team=team_autocomplete, second_team=team_autocomplete)
@app_commands.describe(
    first_team="First team in the scrim",
    second_team="Second team in the scrim",
    category_name="Category to put the channel in (optional, defaults to 'SCRIMS')")
async def cmd_create_scrim_channel(interaction: discord.Interaction, first_team: str, second_team: str, category_name: str = "SCRIMS"):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You don't have permission to create scrim channels.", ephemeral=True)
        return
    t1_key = first_team.lower()
    t2_key = second_team.lower()
    if t1_key == t2_key:
        await interaction.response.send_message("Both teams cannot be the same.", ephemeral=True)
        return
    if t1_key not in teams:
        await interaction.response.send_message(f"**{first_team.title()}** does not exist.", ephemeral=True)
        return
    if t2_key not in teams:
        await interaction.response.send_message(f"**{second_team.title()}** does not exist.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    team1    = teams[t1_key]
    team2    = teams[t2_key]
    category = discord.utils.get(interaction.guild.categories, name=category_name.upper())
    if category is None:
        category = await interaction.guild.create_category(category_name.upper())

    overwrites = {interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False)}
    t1_role = interaction.guild.get_role(team1["team_role"])
    t2_role = interaction.guild.get_role(team2["team_role"])
    if t1_role:
        overwrites[t1_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
    if t2_role:
        overwrites[t2_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
    for role in interaction.guild.roles:
        if role.permissions.administrator:
            overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)

    channel = await interaction.guild.create_text_channel(
        name=f"scrim-{t1_key}-vs-{t2_key}",
        category=category,
        overwrites=overwrites,
        topic=f"Private scrim channel: {first_team.title()} vs {second_team.title()}")

    welcome_embed = discord.Embed(
        description=(
            f"# 🎮 Scrim Channel\n"
            f">>> **{first_team.title()}** vs **{second_team.title()}**\n\n"
            f"This is your private scrim coordination channel.\n"
            f"Only members of both teams and admins can see this.\n\n"
            f"🔒 Channel will remain open until an admin deletes it."
        ), color=0xB3B3FC)
    welcome_embed.set_footer(text="Good luck to both teams!")
    await channel.send(embed=welcome_embed)
    await log_transaction(interaction,
        f"Scrim channel {channel.mention} created for **{first_team.title()}** vs **{second_team.title()}** by {interaction.user.mention}.")
    await interaction.followup.send(f"✅ Scrim channel created: {channel.mention}", ephemeral=True)


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                            COMMANDS — FORFEITS                               ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

@client.tree.command(name="forfeit_scrim", description="Mark a team as forfeiting a scrim (admin only)", guild=SERVER_ID)
@is_premium()
@app_commands.autocomplete(scrim=scrim_autocomplete, forfeiting_team=team_autocomplete)
@app_commands.describe(
    scrim="The scrim to forfeit",
    forfeiting_team="The team that is forfeiting",
    reason="Reason for the forfeit (optional)")
async def cmd_forfeit_scrim(interaction: discord.Interaction, scrim: str, forfeiting_team: str, reason: str = "No reason provided"):
    global scrims_schedule
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You don't have permission to forfeit scrims.", ephemeral=True)
        return
    parts = scrim.split("|")
    if len(parts) != 4:
        await interaction.response.send_message("Invalid scrim selection.", ephemeral=True)
        return
    team1, team2, time, date = parts
    forfeit_key = forfeiting_team.lower()
    if forfeit_key not in [team1.lower(), team2.lower()]:
        await interaction.response.send_message(f"**{forfeiting_team.title()}** is not in this scrim.", ephemeral=True)
        return

    winner = team2 if forfeit_key == team1.lower() else team1
    loser  = forfeit_key
    key    = f"{team1}_{team2}"

    msg = await get_scrim_message(interaction.guild, key)
    if msg:
        try:
            forfeit_embed = discord.Embed(
                description=(
                    f"# **----------🚫 SCRIM FORFEITED----------**\n"
                    f">>> ## **Official Scrim:**\n\n"
                    f"**First Team:** {team1.title()}\n"
                    f"**Second Team:** {team2.title()}\n\n"
                    f"**🏆 Winner:** {winner.title()} (by forfeit)\n"
                    f"**❌ Forfeit:** {loser.title()}\n"
                    f"**Reason:** {reason}"
                ), color=discord.Color.orange())
            await msg.edit(embed=forfeit_embed, view=None)
        except Exception:
            pass
        scrim_messages.pop(key, None)
        scrim_message_ids.pop(key, None)
        save_scrim_messages()

    scrims_schedule = [
        s for s in scrims_schedule
        if not (s["team1"].lower() == team1.lower() and s["team2"].lower() == team2.lower())
    ]
    save_scrims()

    if winner in teams: teams[winner]["wins"]   = teams[winner].get("wins", 0) + 1
    if loser  in teams: teams[loser]["losses"]  = teams[loser].get("losses", 0) + 1
    save_teams()
    await _apply_seeding_result(interaction, winner, loser, f"Updated after {loser.title()} forfeited vs {winner.title()}")

    result_embed = discord.Embed(
        description=(
            f"# 🚫 Scrim Forfeit\n"
            f">>> **{team1.title()}** vs **{team2.title()}**\n\n"
            f"**🏆 Winner:** {winner.title()} *(by forfeit)*\n"
            f"**❌ Forfeited by:** {loser.title()}\n"
            f"**Reason:** {reason}"
        ), color=discord.Color.orange())
    result_embed.set_footer(text=f"Forfeit logged by {interaction.user.display_name}")
    await log_transaction(interaction, f"**{loser.title()}** forfeited their scrim against **{winner.title()}**. Reason: {reason}")
    await interaction.response.send_message("Forfeit logged.", ephemeral=True)
    await interaction.channel.send(embed=result_embed)


@client.tree.command(name="autoforfeit_scrim", description="Flag a team for auto-forfeit on their next scrim (admin only)", guild=SERVER_ID)
@is_premium()
@app_commands.autocomplete(team_name=team_autocomplete)
@app_commands.describe(
    team_name="Team to flag for auto-forfeit",
    confirm="Set True to immediately trigger the forfeit on their next scheduled scrim",
    reason="Reason for the auto-forfeit flag")
async def cmd_autoforfeit_scrim(interaction: discord.Interaction, team_name: str, confirm: bool = False, reason: str = "Team flagged for auto-forfeit"):
    global scrims_schedule
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        return
    key = team_name.lower()
    if key not in teams:
        await interaction.response.send_message(f"**{team_name.title()}** does not exist.", ephemeral=True)
        return

    if confirm:
        next_scrim = next(
            (s for s in scrims_schedule if s["team1"].lower() == key or s["team2"].lower() == key),
            None)
        if next_scrim is None:
            await interaction.response.send_message(f"**{team_name.title()}** has no upcoming scrims to forfeit.", ephemeral=True)
            return

        winner    = next_scrim["team2"].lower() if next_scrim["team1"].lower() == key else next_scrim["team1"].lower()
        loser     = key
        embed_key = f"{next_scrim['team1'].lower()}_{next_scrim['team2'].lower()}"

        msg = await get_scrim_message(interaction.guild, embed_key)
        if msg:
            try:
                auto_embed = discord.Embed(
                    description=(
                        f"# **----------⚠️ AUTO-FORFEIT----------**\n"
                        f">>> **{next_scrim['team1'].title()}** vs **{next_scrim['team2'].title()}**\n\n"
                        f"**🏆 Winner:** {winner.title()} *(auto-forfeit)*\n"
                        f"**❌ Auto-Forfeited:** {loser.title()}\n"
                        f"**Reason:** {reason}"
                    ), color=discord.Color.red())
                await msg.edit(embed=auto_embed, view=None)
            except Exception:
                pass
            scrim_messages.pop(embed_key, None)
            scrim_message_ids.pop(embed_key, None)
            save_scrim_messages()

        scrims_schedule = [
            s for s in scrims_schedule
            if not (s["team1"].lower() == next_scrim["team1"].lower()
                    and s["team2"].lower() == next_scrim["team2"].lower())
        ]
        save_scrims()

        if winner in teams: teams[winner]["wins"]   = teams[winner].get("wins", 0) + 1
        if loser  in teams: teams[loser]["losses"]  = teams[loser].get("losses", 0) + 1
        save_teams()
        await _apply_seeding_result(interaction, winner, loser, f"Updated after {loser.title()} auto-forfeited")

        if key in forfeits:
            del forfeits[key]
            save_forfeits()

        result_embed = discord.Embed(
            description=(
                f"# ⚠️ Auto-Forfeit Applied\n"
                f">>> **{loser.title()}** auto-forfeited their scrim against **{winner.title()}**.\n\n"
                f"**Reason:** {reason}"
            ), color=discord.Color.red())
        result_embed.set_footer(text=f"Auto-forfeit by {interaction.user.display_name}")
        await log_transaction(interaction, f"**{loser.title()}** was auto-forfeited against **{winner.title()}**. Reason: {reason}")
        await interaction.response.send_message("Auto-forfeit applied.", ephemeral=True)
        await interaction.channel.send(embed=result_embed)
        return

    # Toggle the warning flag
    if key in forfeits and forfeits[key].get("auto_forfeit"):
        del forfeits[key]
        save_forfeits()
        embed = discord.Embed(
            description=f"✅ Auto-forfeit flag **removed** from **{team_name.title()}**.",
            color=0xB3B3FC)
        await log_transaction(interaction, f"Auto-forfeit flag removed from **{team_name.title()}** by {interaction.user.mention}.")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        forfeits[key] = {
            "auto_forfeit": True,
            "reason":       reason,
            "flagged_by":   interaction.user.id,
            "flagged_at":   discord.utils.utcnow().isoformat(),
        }
        save_forfeits()
        embed = discord.Embed(
            description=(
                f"⚠️ **{team_name.title()}** has been flagged for auto-forfeit.\n\n"
                f"**Reason:** {reason}\n\n"
                f"They will appear as ~~strikethrough~~ ⚠️ in `/schedule`.\n"
                f"Run this command again to remove the flag, or use `confirm:True` to immediately forfeit their next scrim."
            ), color=discord.Color.orange())
        await log_transaction(interaction, f"**{team_name.title()}** was flagged for auto-forfeit by {interaction.user.mention}. Reason: {reason}")
        await interaction.response.send_message(embed=embed, ephemeral=True)


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                                   ENTRYPOINT                                 ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

client.run(os.getenv('TOKEN'))

