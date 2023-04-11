import os
from dotenv import load_dotenv
import openai
import discord
from discord.ext import commands

#Setup
load_dotenv()

openai.api_key = os.getenv("APIKEY")

client = commands.Bot(intents=discord.Intents.all(), command_prefix="gpt!", help_command=commands.DefaultHelpCommand(no_category = "Commands"))

# Functions
def getCompletion(prompt: str) -> str:
	completion = openai.ChatCompletion.create(
		model="gpt-3.5-turbo",
		messages=[
			{"role": "user", "content": prompt}
		]
	)
	return completion.choices[0].message.content

# Commands
@client.command(name="send")
async def send_func(ctx, prompt: str = commands.parameter(description="El prompt para dar a ChatGPT. Escribir entre comillas")):
	resp = getCompletion(prompt)
	await ctx.send(resp)

send_func.brief = "Crea una respuesta de ChatGPT"
send_func.help = "Crea y devulve una respuesta de ChatGPT con una prompt dado entre comillas"
	

# Events
@client.event
async def on_message(msg):
	if (msg.author == client.user):
		return
	
	await client.process_commands(msg)

client.run(os.getenv("TOKEN"))