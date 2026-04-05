#PGC BOT
import discord
import json
import os
from discord.ext import commands
from discord import app_commands


class Client(commands.Bot):
    async def on_ready(self):
        print(f'Logged on as {self.user}!')
        await client.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name="gtag fr"))
        self.add_view(View())
        try:
            guild = discord.Object(id=1455476030931210343)
            synced = await self.tree.sync(guild=guild)
            print(f'Synced {len(synced)} commands to guild {guild.id}')
        except Exception as e:
            print(f'Error syncing commands: {e}')

    async def on_message(self, message):
        if message.author == self.user:
            return
        if message.content.startswith(self.user.mention):
            await message.channel.send(f"Don't ping me or else I'll find your IP adress bucko 😡")
        print(f'Message from {message.author}: {message.content}')
intents = discord.Intents.default()
intents.message_content = True
client = Client(command_prefix="!", intents=intents)

# audit log
#AUDIT_LOG_CHANNEL = 1484284952253038712
#
#async def log_command(interaction: discord.Interaction) -> bool:
#    channel = interaction.guild.get_channel(AUDIT_LOG_CHANNEL)
#    if channel:
#        options = " ".join(
#            f"{k}: `{v}`" for k, v in
#            {o["name"]: o["value"] for o in interaction.data.get("options", [])}.items()
#        )
#        await channel.send(
#            f"**{interaction.user.name}** used the command **/{interaction.command.name}** in **{interaction.channel.name}**"
#            + (f" — {options}" if options else "")
#        )
#    return True 

#client.tree.interaction_check = log_command

GUILD_ID = discord.Object(id=1455476030931210343)

COMMENTATOR_ROLE = 1457029603095740591
REFEREE_ROLE = 1455502932790214747
CASTER_ROLE = 1455503580827222219

TRANSACTION_LOG_CHANNEL = 1460337594339426578

# remember teams
TEAMS_FILE = "teams.json"

def load_teams() -> dict:
    if not os.path.exists(TEAMS_FILE):
        return {}
    with open(TEAMS_FILE, "r") as f:
        data = json.load(f)
    return {k.lower(): v for k, v in data.items()}

def save_teams():
    with open(TEAMS_FILE, "w") as f:
        json.dump(teams, f, indent=4)

teams: dict = load_teams()

# autocomplete(list options)
async def team_autocomplete(interaction: discord.Interaction, current: str):
    return [
        app_commands.Choice(name=name.title(), value=name)
        for name in teams if current.lower() in name.lower()
    ][:25]

# buttons
class View(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def has_role(self, interaction: discord.Interaction, role_id: int):
        if role_id not in [role.id for role in interaction.user.roles]:
            await interaction.response.send_message("Sorry twin, you don't have the required role for this.", ephemeral=True)
            return False
        return True

    def lock_if_full(self, description: str):
        if ("🎙️ **Commentator:** None" not in description
            and "🎤 **2nd Commentator:** None" not in description
            and "⁉️ **Referee:** None" not in description
            and "📸 **Caster:** None" not in description):
            for item in self.children:
                item.disabled = True

    @discord.ui.button(label="Be Commentator", style=discord.ButtonStyle.green, emoji="🎙️", custom_id="scrim:commentator")
    async def com(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.has_role(interaction, COMMENTATOR_ROLE):
            return
        embed = interaction.message.embeds[0]
        if "🎙️ **Commentator:** None" not in embed.description:
            await interaction.response.send_message("Sorry twin, commentator already taken.", ephemeral=True)
            return
        embed.description = embed.description.replace(
            "🎙️ **Commentator:** None",
            f"🎙️ **Commentator:** {interaction.user.mention}")
        button.disabled = True
        self.lock_if_full(embed.description)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Be 2nd Commentator", style=discord.ButtonStyle.gray, emoji="🎤", custom_id="scrim:commentator2")  # ← indented
    async def com2(self, interaction: discord.Interaction, button: discord.ui.Button):                                           # ← indented
        if not await self.has_role(interaction, COMMENTATOR_ROLE):
            return
        embed = interaction.message.embeds[0]
        if "🎤 **2nd Commentator:** None" not in embed.description:
            await interaction.response.send_message("Sorry twin, 2nd commentator already taken.", ephemeral=True)
            return
        embed.description = embed.description.replace(
            "🎤 **2nd Commentator:** None",
            f"🎤 **2nd Commentator:** {interaction.user.mention}")
        button.disabled = True
        self.lock_if_full(embed.description)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Be Referee", style=discord.ButtonStyle.blurple, emoji="⁉️", custom_id="scrim:referee")
    async def ref(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.has_role(interaction, REFEREE_ROLE):
            return
        embed = interaction.message.embeds[0]
        if "⁉️ **Referee:** None" not in embed.description:
            await interaction.response.send_message("Sorry twin, referee already taken.", ephemeral=True)
            return
        embed.description = embed.description.replace(
            "⁉️ **Referee:** None",
            f"⁉️ **Referee:** {interaction.user.mention}")
        button.disabled = True
        self.lock_if_full(embed.description)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Be Caster", style=discord.ButtonStyle.red, emoji="📸", custom_id="scrim:caster")
    async def cast(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.has_role(interaction, CASTER_ROLE):
            return
        embed = interaction.message.embeds[0]
        if "📸 **Caster:** None" not in embed.description:
            await interaction.response.send_message("Sorry twin, caster already taken.", ephemeral=True)
            return
        embed.description = embed.description.replace(
            "📸 **Caster:** None",
            f"📸 **Caster:** {interaction.user.mention}")
        button.disabled = True
        self.lock_if_full(embed.description)
        await interaction.response.edit_message(embed=embed, view=self)

# /info
@client.tree.command(name="info", description="Bot Info", guild=GUILD_ID)
async def info(interaction: discord.Interaction):
    embed = discord.Embed(description=(
            "## PGC Bot System - Command Guide\n"
            "- What every command does and who is allowed to use it :\n"
            "\n"
            ">>> **/info**\n" 
            "* Who can use it: Anyone\n"
            "* Sends information about the bots command.\n"
            "\n"
            "**/print**\n" 
            "* Who can use it: Adminsitrators\n"
            "* Prints whatever the user inputs into the command.\n"
            "\n"
            "**/set_scrim**\n" \
            "* Who can use it: Administrators\n"
            "* Allows an adminsitrator to set up a time for a scrim.\n"
            "\n"
            "**/create_team**\n" \
            "* Who can use it: Administrators\n"
            "* Allows an adminstrator to enter and setup a team for the league.\n"
            "\n"
            "**/disband_team**\n" \
            "* Who can use it: Administrators\n"
            "* Disbands an exsisting team withing the league disqualifying them from participating.\n"
            "\n"
            "**/disband_all_teams**\n" \
            "* Who can use it: Adminsitrators\n"
            "* Disbands all exsisting teams removing them from the league.\n"
            "\n"
            "**/invite_player**\n" \
            "* Who can use it: Captains, Co-Captains, and Administrators\n"
            "* Invites a member in the league to join a team\n"
            "\n"
            "**/accept_invite**\n" \
            "* Who can use it: Anyone\n"
            "* Shows a list of invites from a team, allowing them to pick which team they'd like to join.\n"
            "\n"
            "**/add_player**\n" \
            "* Who can use it: Administrators\n"
            "* Allows an administrator to manually add players to a team.\n"
            "\n"
            "**/leave_team**\n" \
            "* Who can use it: Anyone\n"
            "* Allows a player on a team to leave their current team.\n"
            "\n"
            "**/roster**\n" \
            "* Who can use it: Anyone\n"
            "* Shows the roster of a specific team.\n"
            "\n"
            "**/lock_roster**\n" \
            "* Who can use it: Administrators\n"
            "* Locks all rosters not allowing players to leave or join teams.\n"
            "\n"
            "**/unlock_rosters**\n" \
            "* Who can use it: Administrators\n"
            "* Unlocks all rosters allowing players to leave or join teams.\n"
            "\n"
            "**/kick_player**\n" \
            "* Who can use it: Captains, Co-Captains, and Administrators\n"
            "* Manually kicks a player off a team, forcibly removing them from the roster.\n"
            "\n"
            "**/assign_captain**\n" \
            "* Who can use it: Administrators\n"
            "* Assigns the captain of a team to manage and control the players.\n"
            "\n"
            "**/assign_co_captain**\n" \
            "* Who can use it: Captains and Administrators\n"
            "* Assigns the co-captain of a team to manage and control the players.\n"
            "\n"
            "**/transfer_captain**\n" \
            "* Who can use it: Captains and Administrators\n"
            "* Transfers the captain to another member so they can now manage the players.\n"
            "\n"
            "**/list_teams**\n" \
            "* Who can use it: Anyone\n"
            "* Lists the current teams playing within the league.<<<\n"
            "\n"
            "-# PGC Season Management System - Created by Had3s"), color=0x15D466)
    await interaction.response.send_message(embed=embed, ephemeral=True) # When sending the information of the slash commands in a server change the "✅ Done" to embed=embed and remove the await interaction.channel.send(embed=embed) AFTER you send the info

# /print
@client.tree.command(name="print", description="Re-say what you say", guild=GUILD_ID)
async def printing(interaction: discord.Interaction, printing: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Sorry twin, you don't have permission to use this command.", ephemeral=True)
        return
    await interaction.response.send_message("Hey look at that! Your message was sent!", ephemeral=True)
    await interaction.channel.send(printing)

# /set scrim
@client.tree.command(name="set_scrim", description="Set a time and date for scrim", guild=GUILD_ID)
@app_commands.autocomplete(first_team=team_autocomplete, second_team=team_autocomplete)
async def scrim(interaction: discord.Interaction, time: str, date: str, first_team: str, second_team: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Twin you don't have permission to create scrims.", ephemeral=True)
        return
    if first_team.lower() == second_team.lower():
        await interaction.response.send_message("Ey twin, just an fyi both teams cannot be the same.", ephemeral=True)
        return
    embed = discord.Embed(      
        description=(
            "## **----------PGC OFFICIAL SCRIM----------**\n"
            ">>> ### **Official Scrim For PGC:**\n"
            "\n"
            f"**Time:** {time}\n"
            f"**Day:** {date}\n"
            f"**First Team:** {first_team.title()}\n"
            f"**Second Team:** {second_team.title()}\n"
            "\n"
            "🎙️ **Commentator:** None\n"
            "🎤 **2nd Commentator:** None\n"
            "⁉️ **Referee:** None\n"
            "📸 **Caster:** None"
        ), color=0x15D466)
    await interaction.response.send_message("Scrim created, im so good at my job.", ephemeral=True)   
    await interaction.channel.send(embed=embed, view=View())                       

# /transaction logs
async def log_transaction(interaction: discord.Interaction, message: str):
    channel = interaction.guild.get_channel(TRANSACTION_LOG_CHANNEL)
    if channel:
        await channel.send(f"{message}")

# /create team
@client.tree.command(name="create_team", description="Create a new team", guild=GUILD_ID)
async def team_create(interaction: discord.Interaction, team_name: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Btw twin, you don't have permission to create teams. Yea ik bummer.", ephemeral=True)
        return
    if team_name.lower() in teams:
        await interaction.response.send_message(f"Ey dum dum **{team_name.title()}** already exists btw.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True) 
    team_role = await interaction.guild.create_role(name=team_name.title())
    captain_role = await interaction.guild.create_role(name=f"{team_name.title()} | Captain")
    co_captain_role = await interaction.guild.create_role(name=f"{team_name.title()} | Co-Captain")
    teams[team_name.lower()] = {
        "captain": None,
        "co_captain": None,
        "players": [],
        "locked": False,
        "team_role": team_role.id,
        "captain_role": captain_role.id,
        "co_captain_role": co_captain_role.id}
    save_teams()
    await log_transaction(interaction, f"Team **{team_name.title()}** was created.")
    embed = discord.Embed(
        description=(
            f">>> I created the roles for this team**{team_name.title()}, are you proud of me 🥹**\n"
            f"\n"
            f"Roles created:\n"
            f"• {team_role.mention}\n"
            f"• {captain_role.mention}\n"
            f"• {co_captain_role.mention}"
        ), color=discord.Color.green())
    await interaction.followup.send(embed=embed, ephemeral=True)  

# /disband team
@client.tree.command(name="disband_team", description="Disbands an existing team", guild=GUILD_ID)
@app_commands.autocomplete(team_name=team_autocomplete)
async def team_disband(interaction: discord.Interaction, team_name: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Ey twin, you don't have permission to disband teams.", ephemeral=True)
        return
    key = team_name.lower()
    if key not in teams:
        await interaction.response.send_message(f" Ey dum dum, **{team_name.title()}** does not exist bro.", ephemeral=True)
        return
    team = teams[key]
    for role_id in ["team_role", "captain_role", "co_captain_role"]:
        try:
            role = interaction.guild.get_role(team[role_id]) or discord.utils.get(
                await interaction.guild.fetch_roles(), id=team[role_id]
            )
            if role:
                await role.delete()
        except discord.NotFound:
            pass
    del teams[key]
    save_teams()
    await log_transaction(interaction, f"Team **{team_name.title()}** was disbanded by {interaction.user.mention}.")
    await interaction.response.send_message("I disbanded the team.", ephemeral=True)


# /disband all teams
@client.tree.command(name="disband_all", description="Disbands all teams", guild=GUILD_ID)
async def disband_all(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("heeeey you don't have permission to disband all teams, what are you doing bro 😭.", ephemeral=True)
        return
    if not teams:
        await interaction.response.send_message("There are no teams rn, come again later ✌️.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    for key in list(teams.keys()):
        team = teams[key]
        for role_id in ["team_role", "captain_role", "co_captain_role"]:
            try:
                role = interaction.guild.get_role(team[role_id]) or discord.utils.get(
                    await interaction.guild.fetch_roles(), id=team[role_id]
                )
                if role:
                    await role.delete()
            except discord.NotFound:
                pass
    teams.clear()
    save_teams()
    await log_transaction(interaction, f"All teams were disbanded by {interaction.user.mention}.")
    await interaction.followup.send("I disbanded all teams for u twin.", ephemeral=True) 

# save invites
pending_invites: dict = {}

# definition for invites
class MyInvitesView(discord.ui.View):
    def __init__(self, player: discord.Member, invites: list):
        super().__init__(timeout=60)
        self.player = player
        for invite in invites:
            self.add_item(InviteButton(invite["team_name"], invite["inviter_id"]))

class InviteButton(discord.ui.Button):
    def __init__(self, team_name: str, inviter_id: int):
        super().__init__(label=team_name.title(), style=discord.ButtonStyle.blurple, emoji="📨")
        self.team_name = team_name
        self.inviter_id = inviter_id

    async def callback(self, interaction: discord.Interaction):
        view = InviteActionView(interaction.user, self.team_name, self.inviter_id, self.view)
        await interaction.response.edit_message(
            content=f"📨 Invite to **{self.team_name.title()}** from <@{self.inviter_id}>. Accept or decline?",
            view=view
        )

class InviteActionView(discord.ui.View):
    def __init__(self, player: discord.Member, team_name: str, inviter_id: int, previous_view):
        super().__init__(timeout=60)
        self.player = player
        self.team_name = team_name
        self.inviter_id = inviter_id
        self.previous_view = previous_view

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green, emoji="✅")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        key = self.team_name.lower()
        if key not in teams:
            await interaction.response.edit_message(content="This team no longer exists dummy.", view=None)
            return
        team = teams[key]
        if team.get("locked"):
            await interaction.response.edit_message(content="This team's roster is locked, you cannot join right now. Sry bro, I tried", view=None)
            return
        if self.player.id in team["players"]:
            await interaction.response.edit_message(content="Bro.. you are already on this team.", view=None)
            return
        team_role = interaction.guild.get_role(team["team_role"])
        if team_role is None:
            await interaction.response.edit_message(content="I can't find the teams role. It may have been deleted.", view=None)
            return
        await self.player.add_roles(team_role)
        team["players"].append(self.player.id)
        save_teams()
        await log_transaction(interaction, f"{self.player.mention} accepted the invite to **{self.team_name.title()}**.")
        await interaction.response.edit_message(content=f"✅ You have joined **{self.team_name.title()}**!", view=None)

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.red, emoji="❌")
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.player.id in pending_invites:
            pending_invites[self.player.id] = [
                i for i in pending_invites[self.player.id] if i["team_name"] != self.team_name
            ]
        await interaction.response.edit_message(content=f"❌ You declined the invite to **{self.team_name.title()}**.", view=None)

# /invite player    
@client.tree.command(name="invite_player", description="Invite a player to a team", guild=GUILD_ID)
@app_commands.autocomplete(team_name=team_autocomplete)
async def invite_player(interaction: discord.Interaction, team_name: str, player: discord.Member):
    key = team_name.lower()
    if key not in teams:
        await interaction.response.send_message(f"Hey **{team_name.title()}** does not exist, you might wanna check ur memory.", ephemeral=True)
        return
    team = teams[key]
    is_captain = team["captain"] == interaction.user.id
    is_co_captain = team["co_captain"] == interaction.user.id
    is_admin = interaction.user.guild_permissions.administrator
    if not (is_captain or is_co_captain or is_admin):
        await interaction.response.send_message("Twin nly the captain, co-captain, or an admin can invite players not u 😭✌️.", ephemeral=True)
        return
    if team.get("locked"):
        await interaction.response.send_message(f"Hey twin all rosters are locked. You gotta wait until an Adminstrator unlocks rosters", ephemeral=True)
        return
    if player.id in team["players"]:
        await interaction.response.send_message(f"Hey {player.mention} is already on the team, shoul've checked rosters first.", ephemeral=True)
        return
    team_role = interaction.guild.get_role(team["team_role"])
    if team_role is None:
        await interaction.response.send_message("I can't find the teams role. It may have been deleted manually.", ephemeral=True)
        return
    if player.id in pending_invites:
        for invite in pending_invites[player.id]:
            if invite["team_name"] == key:
                await interaction.response.send_message(f"Hey {player.mention} already has a pending invite to this team. Let bro chill like cmon 😭", ephemeral=True)
                return
    if player.id not in pending_invites:
        pending_invites[player.id] = []
    pending_invites[player.id].append({"team_name": key, "inviter_id": interaction.user.id})
    await interaction.response.send_message(f"✅ Invite sent to {player.mention} for **{team_name.title()}**.", ephemeral=True)

# /accpt invites
@client.tree.command(name="accept_invites", description="View your pending team invites", guild=GUILD_ID)
async def my_invites(interaction: discord.Interaction):
    invites = pending_invites.get(interaction.user.id, [])
    if not invites:
        await interaction.response.send_message("You have no pending invites. Ha bum, no one wants u lololololol", ephemeral=True)
        return
    await interaction.response.send_message(
        content="📨 **Your pending invites** — click a team to accept or decline:",
        view=MyInvitesView(interaction.user, invites),
        ephemeral=True
    )

# /add player (admin only)
@client.tree.command(name="add_player", description="Manually add a player to a team (Admin only)", guild=GUILD_ID)
@app_commands.autocomplete(team_name=team_autocomplete)
async def add_player(interaction: discord.Interaction, team_name: str, player: discord.Member):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Are you an admin? Then why the freak are you tryna add people 😭", ephemeral=True)
        return
    key = team_name.lower()
    if key not in teams:
        await interaction.response.send_message(f"Hey **{team_name.title()}** does not exist, check ur brain if ur wrong.", ephemeral=True)
        return
    team = teams[key]
    if team.get("locked"):
        await interaction.response.send_message("This team's roster is locked. Try sometime later twin.", ephemeral=True)
        return
    if player.id in team["players"]:
        await interaction.response.send_message(f"Bro {player.mention} is already on this team. ", ephemeral=True)
        return
    team_role = interaction.guild.get_role(team["team_role"])
    if team_role:
        await player.add_roles(team_role)
    team["players"].append(player.id)
    save_teams()
    await log_transaction(interaction, f"{player.mention} was manually added to **{team_name.title()}** by {interaction.user.mention}.")
    await interaction.response.send_message(f"✅ {player.mention} has been added to **{team_name.title()}**.", ephemeral=True)

# /leave team
@client.tree.command(name="leave_team", description="Leave a team you are currently on", guild=GUILD_ID)
@app_commands.autocomplete(team_name=team_autocomplete)
async def leave_team(interaction: discord.Interaction, team_name: str):
    key = team_name.lower()
    if key not in teams:
        await interaction.response.send_message(f"**{team_name.title()}** does not exist. Check ur memory twin.", ephemeral=True)
        return
    team = teams[key]
    if interaction.user.id not in team["players"]:
        await interaction.response.send_message(f"You are not on **{team_name.title()}**. Sometimes wishes don't work twin", ephemeral=True)
        return
    if team.get("locked"):
        await interaction.response.send_message("This team's roster is locked, so I'm NOT letting u leave 💔", ephemeral=True)
        return
    # Remove all team-related roles
    for role_id in ["team_role", "captain_role", "co_captain_role"]:
        role = interaction.guild.get_role(team[role_id])
        if role and role in interaction.user.roles:
            await interaction.user.remove_roles(role)
    # Clear captain/co-captain if they were one
    if team["captain"] == interaction.user.id:
        team["captain"] = None
    if team["co_captain"] == interaction.user.id:
        team["co_captain"] = None
    team["players"].remove(interaction.user.id)
    save_teams()
    await log_transaction(interaction, f"{interaction.user.mention} left **{team_name.title()}**.")
    await interaction.response.send_message(f"You have left **{team_name.title()}**. They prob miss u ngl.", ephemeral=True)

# /roster
@client.tree.command(name="roster", description="Show the roster of a team", guild=GUILD_ID)
@app_commands.autocomplete(team_name=team_autocomplete)
async def roster(interaction: discord.Interaction, team_name: str):
    key = team_name.lower()
    if key not in teams:
        await interaction.response.send_message(f"Twin **{team_name.title()}** does not exist. Lock in 😭", ephemeral=True)
        return
    team = teams[key]
    captain = f"<@{team['captain']}>" if team["captain"] else "None"
    co_captain = f"<@{team['co_captain']}>" if team["co_captain"] else "None"
    players = "\n".join([f"<@{p}>" for p in team["players"]]) if team["players"] else "None"
    locked = "🔒 Locked" if team.get("locked") else "🔓 Open"
    embed = discord.Embed(
        description=(
            f"### 📜  **Roster — {team_name.title()}**\n"
            f"\n"
            f">>> 👑 **Captain:** {captain}\n"
            f"🥈 **Co-Captain:** {co_captain}\n"
            f"\n"
            f"**Players:**\n{players}"
            f"\n{locked}"
        ),
        color=0x15D466)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# /lock rosters
@client.tree.command(name="lock_rosters", description="Lock all team rosters", guild=GUILD_ID)
async def roster_lock(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You don't have permission to lock rosters. Ya bum", ephemeral=True)
        return
    if not teams:
        await interaction.response.send_message("Sorry but no teams currently exist. Wait till they start exisiting", ephemeral=True)
        return
    for key in teams:
        teams[key]["locked"] = True
    save_teams()
    await log_transaction(interaction, f"All rosters were locked.")
    await interaction.response.send_message("Okay, rosters are now locked.", ephemeral=True)

# /unlock rosters
@client.tree.command(name="unlock_rosters", description="Unlock all team rosters", guild=GUILD_ID)
async def roster_unlock(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("ou don't have permission to unlock rosters. Lock in twin", ephemeral=True)
        return
    if not teams:
        await interaction.response.send_message("No teams currently exist. Why do you forget so much honestly.", ephemeral=True)
        return
    for key in teams:
        teams[key]["locked"] = False
    save_teams()
    await log_transaction(interaction, f"All rosters were unlocked.")
    await interaction.response.send_message("Okay, rosters are now unlocked.", ephemeral=True)

# /kick player
@client.tree.command(name="kick_player", description="Kick a player from a team", guild=GUILD_ID)
@app_commands.autocomplete(team_name=team_autocomplete)
async def remove_player(interaction: discord.Interaction, team_name: str, player: discord.Member):
    key = team_name.lower()
    if key not in teams:
        await interaction.response.send_message(f"Hey btw **{team_name.title()}** does not exist. Go to a doctor for altimers or however u spell it.", ephemeral=True)
        return
    team = teams[key]
    is_captain = team["captain"] == interaction.user.id
    is_co_captain = team["co_captain"] == interaction.user.id
    is_admin = interaction.user.guild_permissions.administrator
    if not (is_captain or is_co_captain or is_admin):
        await interaction.response.send_message("Hey twin, only the captain, co-captain, or an admin can remove players. Not u ya bum", ephemeral=True)
        return
    if player.id not in team["players"]:
        await interaction.response.send_message(f"❌ {player.mention} is not on the team.", ephemeral=True)
        return
    for role_id in ["team_role", "captain_role", "co_captain_role"]:
        role = interaction.guild.get_role(team[role_id])
        if role and role in player.roles:
            await player.remove_roles(role)
    team["players"].remove(player.id)
    if team["captain"] == player.id:
        team["captain"] = None
    if team["co_captain"] == player.id:
        team["co_captain"] = None
    save_teams()
    await log_transaction(interaction, f"{player.mention} was removed from **{team_name.title()}**.")
    await interaction.response.send_message("Js kicked them 👍.", ephemeral=True)

# /assign captians
@client.tree.command(name="assign_captain", description="Assign a captain to a team", guild=GUILD_ID)
@app_commands.autocomplete(team_name=team_autocomplete)
async def assign_captain(interaction: discord.Interaction, team_name: str, player: discord.Member):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You don't have permission to assign captains.", ephemeral=True)
        return
    key = team_name.lower()
    if key not in teams:
        await interaction.response.send_message(f"Hey **{team_name.title()}** does not exist. Pick a different one.", ephemeral=True)
        return
    team = teams[key]
    if team["captain"] == player.id:
        await interaction.response.send_message(f"If you forgot, btw {player.mention} is already the captain.", ephemeral=True)
        return
    if team["captain"]:
        old_captain = interaction.guild.get_member(team["captain"])
        old_captain_role = interaction.guild.get_role(team["captain_role"])
        if old_captain and old_captain_role:
            await old_captain.remove_roles(old_captain_role)
    captain_role = interaction.guild.get_role(team["captain_role"])
    team_role = interaction.guild.get_role(team["team_role"])
    if captain_role:
        await player.add_roles(captain_role)
    if team_role and team_role not in player.roles:
        await player.add_roles(team_role)
    team["captain"] = player.id
    if player.id not in team["players"]:
        team["players"].append(player.id)
    save_teams()
    await log_transaction(interaction, f"{player.mention} was assigned as captain of **{team_name.title()}**.")
    await interaction.response.send_message("I did it.", ephemeral=True)

# /assign co captains
@client.tree.command(name="assign_cocaptain", description="Assign a co-captain to a team", guild=GUILD_ID)
@app_commands.autocomplete(team_name=team_autocomplete)
async def assign_cocaptain(interaction: discord.Interaction, team_name: str, player: discord.Member):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You don't have permission to assign co-captains.", ephemeral=True)
        return
    key = team_name.lower()
    if key not in teams:
        await interaction.response.send_message(f"Bro... **{team_name.title()}** does not exist. Lock in 😭", ephemeral=True)
        return
    team = teams[key]
    if team["co_captain"] == player.id:
        await interaction.response.send_message(f"Hey {player.mention} is already the co-captain.", ephemeral=True)
        return
    if team["co_captain"]:
        old_co_captain = interaction.guild.get_member(team["co_captain"])
        old_co_captain_role = interaction.guild.get_role(team["co_captain_role"])
        if old_co_captain and old_co_captain_role:
            await old_co_captain.remove_roles(old_co_captain_role)
    co_captain_role = interaction.guild.get_role(team["co_captain_role"])
    team_role = interaction.guild.get_role(team["team_role"])
    if co_captain_role:
        await player.add_roles(co_captain_role)
    if team_role and team_role not in player.roles:
        await player.add_roles(team_role)
    team["co_captain"] = player.id
    if player.id not in team["players"]:
        team["players"].append(player.id)
    save_teams()
    await log_transaction(interaction, f"{player.mention} was assigned as co-captain of **{team_name.title()}** by {interaction.user.mention}.")
    await interaction.response.send_message("I did it 😃.", ephemeral=True)

# /transfer captain
@client.tree.command(name="transfer_captain", description="Transfer captaincy to another player", guild=GUILD_ID)
@app_commands.autocomplete(team_name=team_autocomplete)
async def transfer_captain(interaction: discord.Interaction, team_name: str, player: discord.Member):
    key = team_name.lower()
    if key not in teams:
        await interaction.response.send_message(f"**{team_name.title()}** does not exist.", ephemeral=True)
        return
    team = teams[key]
    is_captain = team["captain"] == interaction.user.id
    is_admin = interaction.user.guild_permissions.administrator
    if not (is_captain or is_admin):
        await interaction.response.send_message("Only the current captain or an admin can transfer captaincy. Not u ya bum", ephemeral=True)
        return
    if player.id == interaction.user.id:
        await interaction.response.send_message("You can't transfer captaincy to yourself. Stupid 😭", ephemeral=True)
        return
    if team["captain"] == player.id:
        await interaction.response.send_message(f"{player.mention} is already the captain. Pick someone else", ephemeral=True)
        return
    if team["captain"]:
        old_captain = interaction.guild.get_member(team["captain"])
        captain_role = interaction.guild.get_role(team["captain_role"])
        if old_captain and captain_role:
            await old_captain.remove_roles(captain_role)
    captain_role = interaction.guild.get_role(team["captain_role"])
    team_role = interaction.guild.get_role(team["team_role"])
    if captain_role:
        await player.add_roles(captain_role)
    if team_role and team_role not in player.roles:
        await player.add_roles(team_role)
    team["captain"] = player.id
    if player.id not in team["players"]:
        team["players"].append(player.id)
    save_teams()
    await log_transaction(interaction, f"Captaincy of **{team_name.title()}** was transferred to {player.mention} by {interaction.user.mention}.")
    embed = discord.Embed(description=f">>> 👑 Captaincy of **{team_name.title()}** has been transferred to {player.mention}.", color=discord.Color.gold())
    await interaction.response.send_message("I did it.", ephemeral=True)
    await interaction.channel.send(embed=embed)

# /list teams
@client.tree.command(name="list_teams", description="List all active teams", guild=GUILD_ID)
async def list_teams(interaction: discord.Interaction):
    if not teams:
        await interaction.response.send_message("No teams currently exist. Try again later twin", ephemeral=True)
        return
    team_list = "\n".join([f"• **{name.title()}** {'🔒' if teams[name].get('locked') else '🔓'}" for name in teams])
    embed = discord.Embed(description=f">>> **Active Teams**\n\n{team_list}", color=discord.Color.blue())# When sending the list of teams in a server change the "✅ Done" to embed=embed and remove the await interaction.channel.send(embed=embed) AFTER you send the info
    await interaction.response.send_message("I finished.", ephemeral=True)
    await interaction.channel.send(embed=embed)

client.run('TOKEN') 
