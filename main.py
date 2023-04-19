import os
from dotenv import load_dotenv
import openai
import discord
from discord.ext import commands
import json
import logging
import pymongo

### Setup ###

# Load the .env file
load_dotenv()

# Log debug info into logging. If false, just log info.
DEBUG_LEVEL = True

# Get the DAN mode text from the .json file
with open(os.path.join(os.getcwd(),"resources","danmode.json"),"r",encoding="utf-8") as file:
	DAN = json.loads(file.read())

if not os.path.exists(os.path.join(os.getcwd(),"log")):
	os.mkdir("log")

# Setup basic logging into the log directory, onto the logging.log file
logging.basicConfig(filename=os.path.join(os.getcwd(),"log","logging.log"), encoding="utf-8", level=logging.DEBUG if DEBUG_LEVEL else logging.INFO, format="[%(levelname)s] %(asctime)s : %(message)s", datefmt="%y/%m/%d %H:%M:%S")

# Set the OpenAI key from .env
openai.api_key = os.getenv("APIKEY") 

#Setup the discord bot client
client = commands.Bot(intents=discord.Intents.all(), command_prefix="gpt!", help_command=commands.DefaultHelpCommand(no_category = "Commands")) 

# Connect to the MongoDB on the cloud
mongoClient = pymongo.MongoClient(os.getenv('MONGOLINK')) 


### Functions ###

# Default ChatGPT 3.5 completition with chat history
def getCompletion(prompt: str, history: list = []) -> str:
	completion = openai.ChatCompletion.create(
		model="gpt-3.5-turbo",
		messages=history + [
			{"role": "user", "content": prompt}
		]
	)
	return completion.choices[0].message.content

# Same as the default completition, but adds the DAN mode payload
def getDANCompletion(prompt: str, history: list = []) -> str:
	completion = openai.ChatCompletion.create(
		model="gpt-3.5-turbo",
		messages=history + [
			{"role":"user","content":DAN["user"]},
			{"role":"assistant","content":DAN["assistant"]},
			{"role":"user","content":prompt}
		]
	)
	return completion.choices[0].message.content

# Check whether a certain chat exists
def checkChat(member: discord.Member) -> bool:
	Chats = mongoClient["Chats"]
	Server = Chats[str(member.guild.id)]
	result = Server.find_one({"UserId":member.id})
	return True if result else False

# Create a new chat for a member
def createChat(member: discord.Member, danmode: bool) -> bool:
	Chats = mongoClient["Chats"]
	Server = Chats[str(member.guild.id)]
	exists = checkChat(member=member)
	if not exists:
		if danmode:
			Server.insert_one({"UserId":member.id,"ChatHistory":[{"role":"user","content": DAN["user"]},{"role":"assistant","content": DAN["assistant"]}]})
		else:
			Server.insert_one({"UserId":member.id,"ChatHistory":[]})
		return True # User chat created successfully
	else:
		return False # The user's chat already exists, or some other unexpected error

# Deletes the chat from a member
def deleteChat(member: discord.Member) -> bool:
	Chats = mongoClient["Chats"]
	Server = Chats[str(member.guild.id)]
	exists = checkChat(member=member)
	if not exists:
		return False # The user's chats doesn't exist

	Server.delete_one({"UserId":member.id})
	return True

# Retrieves the chat from a member
def getChat(member: discord.Member) -> list:
	Chats = mongoClient["Chats"]
	Server = Chats[str(member.guild.id)]
	search = Server.find({"UserId":member.id},{"_id":0,"UserId":0})
	return next(search)["ChatHistory"] # Returns the ChatHistory, a list of dicts with messages

# Updates the chat from a member
def updateChat(member: discord.Member, newhistory: list) -> bool:
	if not newhistory:
		return False
	
	Chats = mongoClient["Chats"]
	Server = Chats[str(member.guild.id)]
	Server.update_one({"UserId":member.id},{"$set":{"ChatHistory":newhistory}})
	return True

# Create and embed message for pretty info display
def embedGenerator(fields: dict, user: discord.User, title: str = None, color: int = 0xffffff) -> discord.Embed:
	embed = discord.Embed(title=title, color=color)
	for ftitle, text in fields.items():
		embed.add_field(name=ftitle,value=text)
	embed.set_footer(text=f"Pregunta de: {user.name}", icon_url=user.avatar.url)
	return embed


### Commands ###

# gpt!send command
@client.command(name="send")
async def send_func(ctx: commands.Context, prompt: str = commands.parameter(default="", description="El prompt para dar a ChatGPT. Escribir entre comillas")):
	if not prompt:
		await ctx.send(embed=embedGenerator(fields={"Error":"No existe el chat"},user=ctx.author, color=0xff3333))
		return
	
	resp = getCompletion(prompt)
	embedResp = embedGenerator(fields={"Respuesta":resp}, user=ctx.author)
	await ctx.send(embed=embedResp)

send_func.brief = "Crea una respuesta de ChatGPT."
send_func.help = "Crea y devulve una respuesta de ChatGPT con una prompt dado entre comillas."

# gpt!dan command
@client.command(name="dan")
async def dan_func(ctx: commands.Context, prompt: str = commands.parameter(default="", description="El prompt para dar a ChatGPT. Escribir entre comillas.")):
	if not prompt:
		await ctx.send(embed=embedGenerator(fields={"Error":"No existe el chat"},user=ctx.author, color=0xff3333))
		return
	
	resp = getDANCompletion(prompt)
	embedResp = embedGenerator(fields={"Respuesta":resp}, user=ctx.author)
	await ctx.send(embed=embedResp)

dan_func.brief = "Crea una respuesta de ChatGPT en modo DAN."
dan_func.help = "Crea y devulve una respuesta de ChatGPT con una prompt dado entre comillas con el prompt de activacion del modo DAN preescrito."

# gpt!create command
@client.command(name="create")
async def create_func(ctx: commands.Context, danmode: str = commands.parameter(default="", description="Argumento para el modo DAN. Escribe dan para activarlo.")):
	result = createChat(ctx.author, True if (danmode=="dan") else False)
	if result:
		await ctx.send(embed=embedGenerator(fields={"Chat creado":"Ahora puedes usar tu chat en este servidor."}, user=ctx.author))
	else: 
		await ctx.send(embed=embedGenerator(fields={"Error":"No se ha podido crear el chat. Quizás ya existe uno."}, user=ctx.author, color=0xff3333))

create_func.brief = "Crea un chat en el servidor."
create_func.help = "Crea un nuevo chat a nombre del usuario para chatear usando memoria del bot. Cada usuario puede crear un chat por servidor."

# gpt!chat command
@client.command(name="chat")
async def chat_func(ctx: commands.Context, prompt: str = commands.parameter(default="", description="El prompt para usar en tu chat de un servidor.")):
	if not prompt:
		await ctx.send(embed=embedGenerator(fields={"Error":"Introduzca un prompt para enviar"}, user=ctx.author, color=0xff3333))
		return
	
	if not checkChat(member=ctx.author):
		await ctx.send(embed=embedGenerator(fields={"Error":"No existe el chat"},user=ctx.author, color=0xff3333))
		return

	history = getChat(ctx.author)
	resp = getCompletion(prompt=prompt, history=history)
	updateChat(member=ctx.author,newhistory=history+[{"role":"user","content":prompt},{"role":"assistant","content":resp}])
	embedResp = embedGenerator(title=None, fields={"Respuesta":resp}, user=ctx.author)
	await ctx.send(embed=embedResp)

chat_func.brief = "Manda un mensaje por tu chat del servidor"
chat_func.help = "Manda un mensaje por el canal de chat creado en el servidor"

# gpt!read command
@client.command(name="read")
async def read_func(ctx: commands.Context):
	if not checkChat(ctx.author):
		await ctx.send(embed=embedGenerator(fields={"Error":"No existe el chat"},user=ctx.author, color=0xff3333))
		return

	rawchat = getChat(member=ctx.author)
	chat = ""
	for msg in rawchat:
		chat = chat + f"{msg['role'].capitalize()}: {msg['content']}\n"
	embedResp = embedGenerator(fields={"Chat":chat}, user=ctx.author)
	await ctx.send(embed=embedResp)

read_func.brief = "Lee tu chat con el bot"
read_func.help = "Muestra la conversación que llevas con el bot en el servidor"

# gpt!delete command
@client.command(name="delete")
async def delete_func(ctx: commands.Context):
	result = deleteChat(member=ctx.author)
	if result:
		await ctx.send(embed=embedGenerator(fields={"Chat borrado":"Se ha eliminado el chat en este servidor."},user=ctx.author))
	else:
		await ctx.send(embed=embedGenerator(fields={"Error":"No se ha podido borrar el chat. Quizás no exista."},user=ctx.author, color=0xff3333))
	
delete_func.brief = "Borra un chat de un servidor"
delete_func.help = "Borra tu chat en el servidor en el que mandes el mensaje"

### Events ###

@client.event
async def on_ready():
	await client.change_presence(status=discord.Status.online, activity=discord.Activity(type=discord.ActivityType.listening, name=" a gpt!"))
	logging.info("Client started and ready!")

@client.event
async def on_message(msg):
	if (msg.author == client.user):
		return
	
	await client.process_commands(msg)


# Run the client
if __name__=="__main__":
	client.run(os.getenv("TOKEN"))