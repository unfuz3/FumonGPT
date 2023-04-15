import os
from dotenv import load_dotenv
import openai
import discord
from discord.ext import commands
import json

#Setup
load_dotenv()

with open(os.path.join(os.getcwd(),"danmode.json"),"r",encoding="utf-8") as file:
	dan = json.loads(file.read())

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

def getDANCompletion(prompt: str) -> str:
	completion = openai.ChatCompletion.create(
		model="gpt-3.5-turbo",
		message=[
			{"role":"user","content":dan["user"]},
			{"role":"assistant","content":dan["assistant"]},
			{"role":"user","content":prompt}
		]
	)
	return completion.choice[0].message.content


# Commands
@client.command(name="send")
async def send_func(ctx, prompt: str = commands.parameter(description="El prompt para dar a ChatGPT. Escribir entre comillas")):
	resp = getCompletion(prompt)
	await ctx.send(resp)

send_func.brief = "Crea una respuesta de ChatGPT"
send_func.help = "Crea y devulve una respuesta de ChatGPT con una prompt dado entre comillas"

@client.command(name="dan")
async def dan_func(ctx, prompt: str = commands.parameter(description="El prompt para dar a ChatGPT. Escribir entre comillas")):
	resp = getDANCompletion(prompt)
	await ctx.send(resp)

dan_func.brief = "Crea una respuesta de ChatGPT en modo DAN"
dan_func.help = "Crea y devulve una respuesta de ChatGPT con una prompt dado entre comillas con el prompt de activacion del modo DAN preescrito"


# Events
@client.event
async def on_message(msg):
	if (msg.author == client.user):
		return
	
	await client.process_commands(msg)

client.run(os.getenv("TOKEN"))