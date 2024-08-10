import requests
from bs4 import BeautifulSoup
import sqlite3
import time
import tkinter as tk
from tkinter import messagebox, StringVar, OptionMenu, Label, Button
from PIL import Image, ImageTk
import pandas as pd

BASE_URL = "https://www.basketball-reference.com"

# Connect to SQLite database (or create it)
conn = sqlite3.connect('nba_data.db')
c = conn.cursor()

# Create tables
c.execute('''CREATE TABLE IF NOT EXISTS games (
                date TEXT,
                visitor_team TEXT,
                visitor_score INTEGER,
                home_team TEXT,
                home_score INTEGER
            )''')

c.execute('''CREATE TABLE IF NOT EXISTS players (
                player_name TEXT,
                position TEXT,
                height TEXT,
                weight TEXT,
                birth_date TEXT,
                team TEXT,
                season INTEGER
            )''')

c.execute('''CREATE TABLE IF NOT EXISTS player_stats (
                player_id TEXT,
                season INTEGER,
                points_per_game REAL
            )''')

conn.commit()

def get_season_games(season):
    url = f"{BASE_URL}/leagues/NBA_{season}_games.html"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    games = []
    months = soup.select('div#div_games th[data-stat="month_name"] a')
    for month in months:
        month_url = BASE_URL + month['href']
        month_response = requests.get(month_url)
        month_soup = BeautifulSoup(month_response.text, 'html.parser')
        rows = month_soup.select('table#schedule tbody tr')
        for row in rows:
            if row.get('class') and 'thead' in row.get('class'):
                continue
            date = row.find('th', {'data-stat': 'date_game'}).text.strip()
            teams = row.find_all('td', {'data-stat': ['visitor_team_name', 'home_team_name']})
            scores = row.find_all('td', {'data-stat': ['visitor_pts', 'home_pts']})
            if teams and scores:
                visitor_team = teams[0].text.strip()
                home_team = teams[1].text.strip()
                visitor_score = scores[0].text.strip()
                home_score = scores[1].text.strip()
                games.append([date, visitor_team, int(visitor_score), home_team, int(home_score)])
    
    return games

def get_team_roster(team, season):
    team_url = f"{BASE_URL}/teams/{team}/{season}.html"
    response = requests.get(team_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    roster_table = soup.find('table', {'id': 'roster'})
    players = []
    if roster_table:
        rows = roster_table.find('tbody').find_all('tr')
        for row in rows:
            player_name = row.find('td', {'data-stat': 'player'}).text.strip()
            position = row.find('td', {'data-stat': 'pos'}).text.strip()
            height = row.find('td', {'data-stat': 'height'}).text.strip()
            weight = row.find('td', {'data-stat': 'weight'}).text.strip()
            birth_date = row.find('td', {'data-stat': 'birth_date'}).text.strip()
            players.append([player_name, position, height, weight, birth_date, team, season])
    return players

def get_player_stats(player_id, season):
    player_url = f"{BASE_URL}/players/{player_id[0]}/{player_id}.html"
    response = requests.get(player_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    stats_table = soup.find('table', {'id': 'per_game'})
    stats = {}
    if stats_table:
        rows = stats_table.find('tbody').find_all('tr')
        for row in rows:
            if row.find('th', {'data-stat': 'season'}).text.strip() == f"{season}-{season + 1}":
                points = row.find('td', {'data-stat': 'pts_per_g'}).text.strip()
                stats['points_per_game'] = float(points) if points else 0.0
                break
    return stats

def save_games_to_db(games):
    c.executemany('INSERT INTO games VALUES (?, ?, ?, ?, ?)', games)
    conn.commit()

def save_players_to_db(players):
    c.executemany('INSERT INTO players VALUES (?, ?, ?, ?, ?, ?, ?)', players)
    conn.commit()

def save_player_stats_to_db(player_id, season, stats):
    c.execute('INSERT INTO player_stats VALUES (?, ?, ?)', (player_id, season, stats['points_per_game']))
    conn.commit()

def fetch_data():
    seasons = list(range(2020, 2025))
    all_games = []
    all_players = []
    teams = set()
    
    for season in seasons:
        print(f"Fetching games for season {season}...")
        games = get_season_games(season)
        save_games_to_db(games)
        for game in games:
            teams.add(game[1])
            teams.add(game[3])
        time.sleep(1)  # to avoid hitting the site too frequently
    
    print("Fetching rosters for each team...")
    for team in teams:
        for season in seasons:
            print(f"Fetching roster for team {team} in season {season}...")
            players = get_team_roster(team, season)
            save_players_to_db(players)
            time.sleep(1)  # to avoid hitting the site too frequently

    messagebox.showinfo("Data Fetch", "Data fetching complete and saved to the database.")

def predict_game(team1, team2):
    c.execute('''SELECT AVG(visitor_score) FROM games WHERE visitor_team = ? OR home_team = ?''', (team1, team1))
    team1_avg_score = c.fetchone()[0] or 0.0
    
    c.execute('''SELECT AVG(visitor_score) FROM games WHERE visitor_team = ? OR home_team = ?''', (team2, team2))
    team2_avg_score = c.fetchone()[0] or 0.0
    
    result = f"Predicted Score:\n{team1}: {team1_avg_score:.2f}\n{team2}: {team2_avg_score:.2f}"
    return result

def display_players(team, season):
    c.execute('''SELECT player_name, position, height, weight, birth_date 
                 FROM players WHERE team = ? AND season = ?''', (team, season))
    players = c.fetchall()
    return players

def predict_player_scores(team, season):
    c.execute('''SELECT player_name FROM players WHERE team = ? AND season = ?''', (team, season))
    players = c.fetchall()
    
    player_scores = {}
    for player in players:
        player_name = player[0]
        player_id = player_name.split(' ')[1][:5].lower() + player_name.split(' ')[0][:2].lower()
        c.execute('''SELECT points_per_game FROM player_stats WHERE player_id = ? AND season = ?''', (player_id, season))
        points_per_game = c.fetchone()
        player_scores[player_name] = points_per_game[0] if points_per_game else 0.0
    
    return player_scores

def on_predict():
    team1 = team1_var.get()
    team2 = team2_var.get()
    season = 2024  # Example season, can be dynamic
    if team1 and team2:
        result = predict_game(team1, team2)
        players_team1 = display_players(team1, season)
        players_team2 = display_players(team2, season)
        player_scores_team1 = predict_player_scores(team1, season)
        player_scores_team2 = predict_player_scores(team2, season)
        messagebox.showinfo("Prediction Result", f"{result}\n\n{team1} Players:\n{players_team1}\n\n{team2} Players:\n{players_team2}\n\n{team1} Player Scores:\n{player_scores_team1}\n\n{team2} Player Scores:\n{player_scores_team2}")
    else:
        messagebox.showwarning("Input Error", "Please select both teams.")


# GUI Setup
root = tk.Tk()
root.title("NBA Prediction")
root.geometry("900x700")
root.configure(bg='white')

frame = tk.Frame(root, bg="white")
frame.pack(side="top", padx=20, pady=20)

title = tk.Label(frame, text="Welcome to our project", font=("DM Sans", 22, "bold italic"), bg='white', fg="blue")
title.pack(side="top", pady=10)

info = tk.Label(frame, text="Our goal is to predict the future result of a game between two NBA teams.\n"
                           "And to see each player's progress.", font=("Comic Sans MS", 18), bg='white')
info.pack(side="bottom", pady=10)

image = Image.open("NBA_Logo.png")
resized_image = image.resize((100, 200))
photo = ImageTk.PhotoImage(resized_image)

label = tk.Label(root, image=photo)
label.place(x=400, y=100)

fetch_button = tk.Button(root, text="Fetch Data", command=fetch_data, font=("DM Sans", 16), bg="blue", fg="black")
fetch_button.place(x=400, y=450)

team1_var = StringVar()
team2_var = StringVar()

teams = ["ATL", "BOS", "BRK", "CHO", "CHI", "CLE", "DAL", "DEN", "DET", "GSW", "HOU", "IND", "LAC", "LAL", "MEM", "MIA", "MIL", "MIN", "NOP", "NYK", "OKC", "ORL", "PHI", "PHO", "POR", "SAC", "SAS", "TOR", "UTA", "WAS"]

team1_label = tk.Label(root, text="Select Team 1", font=("DM Sans", 16), bg='blue')
team1_label.place(x=350, y=350)
team1_menu = OptionMenu(root, team1_var, *teams)
team1_menu.place(x=500, y=350)

team2_label = tk.Label(root, text="Select Team 2", font=("DM Sans", 16), bg='blue')
team2_label.place(x=350, y=400)
team2_menu = OptionMenu(root, team2_var, *teams)
team2_menu.place(x=500, y=400)

predict_button = tk.Button(root, text="Predict Game", command=on_predict, font=("Arial", 16), bg="blue", fg="black")
predict_button.place(x=400, y=500)

root.mainloop()