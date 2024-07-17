import pandas as pd
import requests
import time
from matplotlib import pyplot as plt
from bs4 import BeautifulSoup
import tkinter as Tk, Label, Button, StringVar, OptionMenu, Frame, messagebox, PhotoImage
from PIL import image, ImageTk


root = Tk()
root.title("NBA Prediction")
root.geomatry("900x500")
root.configure(bg='white')

Frame = Label(root, bg="white")
Frame.pack(side="top", padex=20, pady=20)

#label
title = Label(Frame, text="Welcome to our project", font=("DM Sans", 22, "bold italic"), bg='white', fg="blue")
title.pack(side="top", pady=10)

info = Label(Frame, text="our goal is to predict the future result of a game between to nba teams.\n"
                         "And to see each player progress.", font=("Comic Sans MS", 18), bg='white')
info.pack(side="bottom", pady=10)

image = image.open("NBA_Logo.png")
resized_image = image.resize((200,200))
photo = ImageTk.PhotoImage(resized_image)

label = Label(root, image=photo)
Label.place(x=535, y=root.winfo_height() - photo.height() - -570)

root.mainloop()



#to do take data from url to get all the scores
url = https://www.basketball-reference.com/leagues/NBA_{Seasons}_games.html
requests.get(url)
Seasons = list(range(2020, 2025))




#todo take data from url to get all player from the box score
#the nums in the url it's game date yyyymmdd0
url = https://www.basketball-reference.com/boxscores/202009130{teams}.html
data = requests.get(url)

teams = ["ATL", "BOS", "NJN", "CHA", "CHI", "CLE", "DLA", "DEN", "DET", "GSW", "HOU", "IND", "LAC", "LAL", "MEM", "MIA", "MIL", "MIN", "NOH", "NYK", "OKC", "ORL", "PHI", "PHO", "POR", "SAC", "SAS", "TOR", "UTA", "WAS"]