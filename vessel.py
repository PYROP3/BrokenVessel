import asyncio
import discord
import discord_slash
import logging
import os
import sys
import sqlite3 as sl
from discord import flags
from dotenv import load_dotenv
from flask import Flask
from threading import Thread
from discord.ext import commands
from discord_slash import SlashCommand, SlashContext

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
if TOKEN is None:
    print("DISCORD_TOKEN env var not set! Exiting")
    exit(1)

LEXICON_REPLY = os.getenv('LEXICON_REPLY')

_ids = os.getenv('GUILD_IDS') or ""
_guild_ids = [int(id) for id in _ids.split('.') if id != ""]
guild_ids = _guild_ids if len(_guild_ids) else None

CMD_PREFIX_OLD = os.getenv('CMD_PREFIX_OLD') or "!"
CMD_PREFIX = os.getenv('CMD_PREFIX') or "/"

bot = commands.Bot(command_prefix=CMD_PREFIX, self_bot=True, intents=discord.Intents.all())
slash = SlashCommand(bot, sync_commands=True)
app = Flask(__name__)
app.logger.root.setLevel(logging.getLevelName(os.getenv('LOG_LEVEL') or 'DEBUG'))
app.logger.addHandler(logging.StreamHandler(sys.stdout))

lexicon_db_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), "db", "lexicon.db")

@bot.event
async def on_ready():
    app.logger.info(f"{bot.user} has connected to Discord")

@bot.event
async def on_message(msg: discord.Message):
    if msg.author.id != bot.user.id:
        app.logger.debug(f"[{msg.channel.guild.name} / {msg.channel.name}] {msg.author.name} says \"{msg.content}\"")
        if msg.content[0] == CMD_PREFIX_OLD:
            cmd = msg.content[1:]
            if cmd == "lexicon":
                msg = await msg.channel.fetch_message(LEXICON_REPLY)
                await msg.channel.send("🐛",reference=msg)
            return
        if "lexicon" in msg.content:
            await msg.reply(f"We should probably set up a {CMD_PREFIX}lexicon command! Go pester one of the mods for it")

# Commands

opts = [discord_slash.manage_commands.create_option(name="word", description="Hallowspeak word to search (WIP)", option_type=3, required=False)]
@slash.slash(name="lexicon", description="Fetch the entire lexicon or search for a specific hallowspeak word", options=opts, guild_ids=guild_ids)
async def _lexicon(ctx: SlashContext, **kwargs):
    vargs = [kwargs[x] for x in kwargs if kwargs[x] is not None]
    app.logger.debug(f"[{ctx.channel.guild.name} / {ctx.channel.name}] {ctx.author.name} used lexicon : {vargs}")
    if len(vargs): # User wants a specific word
        word = vargs[0]
        with sl.connect(lexicon_db_file) as con:
            data = con.execute("SELECT definition, source, notes FROM LEXICON WHERE hallowspeak LIKE ?", [f"%{word}%"]).fetchone()
            if data is not None: # Found a match
                app.logger.debug(f"[{ctx.channel.guild.name} / {ctx.channel.name} / {ctx.author}] Found match for '{word}' as '{data}'")
                notes_str = f"\n**Notes: **{data[2]}" if data[2] != "" else ""
                await ctx.send(content=f"📚 The meaning of '{word}' seems to be '{data[0]}'.\n> {data[1]}{notes_str}",
                    hidden=True)
            else: # No such luck
                app.logger.debug(f"[{ctx.channel.guild.name} / {ctx.channel.name} / {ctx.author}] Could not find match for '{word}'")
                await ctx.send(content=f"Sorry {ctx.author.name}, but I could not find the meaning of '{word}'. Are you sure that's a real word?",
                    hidden=True)
    else: # Just reply with the whole lexicon
        resdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "res", "lexicon")
        await ctx.send(content=f"Hey {ctx.author.name}! Here is the lexicon you requested!",
            files=[discord.File(os.path.join(resdir, f)) for f in sorted(os.listdir(resdir))],
            hidden=True)

opts = [discord_slash.manage_commands.create_option(name="word", description="English word to translate (WIP)", option_type=3, required=True)]
@slash.slash(name="translate", description="Search for the translation of a specific english word", options=opts, guild_ids=guild_ids)
async def _translate(ctx: SlashContext, **kwargs):
    vargs = [kwargs[x] for x in kwargs if kwargs[x] is not None]
    app.logger.debug(f"[{ctx.channel.guild.name} / {ctx.channel.name}] {ctx.author.name} used translate : {vargs}")
    word = vargs[0]
    with sl.connect(lexicon_db_file) as con:
        data = con.execute("SELECT hallowspeak FROM LEXICON WHERE definition LIKE ?", [f"%{word}%"]).fetchone()
        if data is not None: # Found a match
            result = data[0]
            app.logger.debug(f"[{ctx.channel.guild.name} / {ctx.channel.name} / {ctx.author}] Found match for '{word}' as '{result}'")
            await ctx.send(content=f"📚 The translation of '{word}' seems to be '{result}'",
                hidden=True)
        else: # No such luck
            app.logger.debug(f"[{ctx.channel.guild.name} / {ctx.channel.name} / {ctx.author}] Could not find match for '{word}'")
            await ctx.send(content=f"Sorry {ctx.author.name}, but I could not find a translation for '{word}'",
                hidden=True)

opts = [discord_slash.manage_commands.create_option(name="word", description="Hallowspeak word to search (WIP)", option_type=3, required=True)]
@slash.slash(name="meaning", description="Search for the translation of a specific english word", options=opts, guild_ids=guild_ids)
async def _meaning(ctx: SlashContext, **kwargs):
    vargs = [kwargs[x] for x in kwargs if kwargs[x] is not None]
    app.logger.debug(f"[{ctx.channel.guild.name} / {ctx.channel.name}] {ctx.author.name} used meaning : {vargs}")
    word = vargs[0]
    with sl.connect(lexicon_db_file) as con:
        data = con.execute("SELECT definition FROM LEXICON WHERE hallowspeak LIKE ?", [f"%{word}%"]).fetchone()
        if data is not None: # Found a match
            result = data[0]
            app.logger.debug(f"[{ctx.channel.guild.name} / {ctx.channel.name} / {ctx.author}] Found match for '{word}' as '{result}'")
            await ctx.send(content=f"📚 The meaning of '{word}' seems to be '{result}'",
                hidden=True)
        else: # No such luck
            app.logger.debug(f"[{ctx.channel.guild.name} / {ctx.channel.name} / {ctx.author}] Could not find match for '{word}'")
            await ctx.send(content=f"Sorry {ctx.author.name}, but I could not find the meaning of '{word}'. Are you sure that's a real word?",
                hidden=True)

bot.run(TOKEN)
