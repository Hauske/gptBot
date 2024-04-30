from bs4 import BeautifulSoup
import time
import pyautogui
import pyperclip
from typing import List
import discord
import asyncio

maxReadTries = 3
fileName = "ChatGPT.htm"

lookForBrowserWindow = False
waitingForResponse = 20
waitingSecondsReadTry = 5
waitingSecondsFailedRead = 5

browserButtonCoord = {
    "x": 149,
    "y": 1060
}

chatBoxCoord = {
    "x": 797,
    "y": 981
}

def getCursorPosition():
    '''Prints the current cursor position every 1.5 seconds.'''
    while True:
        print(pyautogui.position())
        time.sleep(1.5)
        
class HTML_handler:
    '''Class for handling the HTML file.'''
    def __init__(self, fileName, maxReadTries, waitingSecondsReadTry, waitingSecondsFailedRead):
        self.fileName = fileName
        self.maxReadTries = maxReadTries
        self.waitingSecondsReadTry = waitingSecondsReadTry
        self.waitingSecondsFailedRead = waitingSecondsFailedRead
    
    def ifResponseFinished(self):
        with open(self.fileName, "r", encoding="utf-8") as file:
            html_content = file.read()

        soup = BeautifulSoup(html_content, "html.parser")

        stopButton = soup.find(
            "button",
            attrs={
                "class": "rounded-full border-2 border-gray-950 p-1 dark:border-gray-200"
            })

        return stopButton == None

    def openHTMLFile(self):
        '''Opens the HTML file and reads the conversation from it.'''
        res_handler = response_handler()  # create an instance of response_handler
        for attempt in range(self.maxReadTries):
            try:
                finished = self.ifResponseFinished()
                if finished:
                    break
                elif attempt == self.maxReadTries - 1:
                    print(f"Attempt {attempt + 1} Failed to read the file.")
                    return []
                else:
                    print(f"Reading attempt {attempt + 1} failed. Retrying...")
                    # Still generating, wait and keep trying
                    time.sleep(self.waitingSecondsReadTry)
                    res_handler.save_new_HTML()  # call save_new_HTML on the instance
            except:
                print(f"EXCEPT ERROR: Retrying...")
                time.sleep(self.waitingSecondsFailedRead)
                res_handler.save_new_HTML()

        with open(self.fileName, "r", encoding="utf-8") as file:
            html_content = file.read()

        soup = BeautifulSoup(html_content, "html.parser")

        response_divs = soup.find_all("div", class_="markdown prose w-full break-words dark:prose-invert dark")
        if(len(response_divs) == 0):
            print("Div element with specified class not found.")
            return []

        conversation: List[str] = []
        for div in response_divs:
            text = ""
            children = div.findChildren()

            for child in children:
                if child.name == "p":
                    text += child.text
                if child.name == "code":
                    text += child.text
            conversation.append(text)

        return conversation

class HTMLFacade:
    '''Facade class for the HTML_handler.'''
    def __init__(self, fileName, maxReadTries, waitingSecondsReadTry, waitingSecondsFailedRead):
        self.html_handler = HTML_handler(fileName, maxReadTries, waitingSecondsReadTry, waitingSecondsFailedRead)

    def get_conversation(self):
        '''Returns the conversation from the HTML file.'''
        return self.html_handler.openHTMLFile()

    def is_response_finished(self):
        '''Checks if the response is finished.'''
        return self.html_handler.ifResponseFinished()
    
class response_handler():
    def save_new_HTML(self):
        '''Saves the new HTML file with the conversation to the specified file name.'''
        pyautogui.hotkey('ctrl', 's')
        time.sleep(1)
        pyautogui.typewrite(fileName.split('.')[0])
        time.sleep(0.5)
        pyautogui.press('enter') # Click on Save
        time.sleep(0.5)
        pyautogui.press('y') # Click on Replace
        time.sleep(1)

class message_handler():
    def send_message(self, message: str):
        '''Copies the message to the clipboard and pastes it in the chat box of the browser window.'''
        pyperclip.copy(message)

        if lookForBrowserWindow:
            # We need to switch to the browser window
            pyautogui.hotkey('win', 'd')
            time.sleep(1)
            pyautogui.click(browserButtonCoord['x'], browserButtonCoord['y'])
            time.sleep(1)

        pyautogui.click(chatBoxCoord['x'], chatBoxCoord['y'])
        time.sleep(0.5)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.2)
        pyautogui.press('enter')

def singleton(cls):
    instances = {}
    def wrapper(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    return wrapper

@singleton 
class MyClient(discord.Client):
    async def typing(self, channel, time):
        '''Simulates typing in the chat for the specified time.'''
        async with channel.typing():
            await asyncio.sleep(time)

    async def on_ready(self):
        print(f'Logged on as {self.user}!')

    async def on_message(self, message):
        '''Reads the message from the chat and sends it to the GPT-3 model.'''
        if message.author == self.user:
            return

        msg_handler = message_handler()
        res_handler = response_handler()
        html_facade = HTMLFacade(fileName, maxReadTries, waitingSecondsReadTry, waitingSecondsFailedRead)

        content: str = message.content
        if(content.startswith("!gpt")):
            cleanMessage = content.replace("!gpt", "")
            msg_handler.send_message(cleanMessage)

            await self.typing(message.channel, waitingForResponse)
            res_handler.save_new_HTML()

            current_conversation = html_facade.get_conversation()
            response_finished = html_facade.is_response_finished()

            if not response_finished:
                return "Failed to read the file."

            length = len(current_conversation)
            if length == 0:
                return "Failed to read the file."

            response = current_conversation[length-1]
            chunks = [response[i:i+2000] for i in range(0, len(response), 2000)]
            for chunk in chunks:
                await message.reply(chunk)


intents = discord.Intents.default()
intents.message_content = True
client = MyClient(intents=intents)
client.run('<Bot token>')