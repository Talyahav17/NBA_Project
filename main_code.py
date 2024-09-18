import requests
from bs4 import BeautifulSoup
import sqlite3
import time
import tkinter as tk
from tkinter import messagebox, StringVar, OptionMenu
from PIL import Image, ImageTk
import pandas as pd
import tensorflow as tf
from sklearn.model_selection import train_test_split

# Base URL for basketball-reference
BASE_URL = "https://www.basketball-reference.com"

conn = sqlite3.connect('nba_data.db')
c = conn.cursor()

# Create tables if they don't exist
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


# Function to get season games
def get_season_games(team, season):
    url = f"{BASE_URL}/teams/{team}/{season}_games.html"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    games = []
    rows = soup.select('table[id="games"] tbody tr')
    for row in rows:
        if row.get('class') and 'thead' in row.get('class'):
            continue

        date_cell = row.find("td", {"data-stat": "date_game"})
        if not date_cell: 
            continue  # Skip rows where date is not found

        date = date_cell.text.strip()

        visitor_team_element = row.find(
            "td", {"data-stat": "opp_name"}
        ) 
        a_tag = visitor_team_element.find("a")
        # Extract the team name
        visitor_team = a_tag.text

        scores = row.find_all(
            "td", {"data-stat": ["pts", "opp_pts"]}
        ) 

        if visitor_team and scores:  
            visitor_team = visitor_team[0].strip()
            home_team = team 
            visitor_score = scores[0].text.strip()
            home_score = scores[1].text.strip()
            if visitor_score and home_score:
                games.append(
                    [date, visitor_team, int(visitor_score), home_team, int(home_score)]
                )
 
    return games


# Function to get team roster
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
            if player_name and position and height and weight and birth_date:
                players.append([player_name, position, height, weight, birth_date, team, season])

    return players

# Function to get player stats
def get_player_stats(player_id, season):
    player_url = f"{BASE_URL}/players/{player_id[0]}/{player_id}.html"
    response = requests.get(player_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    stats_table = soup.find('table', {'id': 'per_game'})
    stats = {}
    if stats_table:
        rows = stats_table.find('tbody').find_all('tr')
        for row in rows:
            if row.find('th', {'data-stat': 'season'}) and \
               row.find('th', {'data-stat': 'season'}).text.strip() == f"{season}-{season + 1}":
                points = row.find('td', {'data-stat': 'pts_per_g'}).text.strip()
                stats['points_per_game'] = float(points) if points else 0.0
                break

    return stats


# Function to save games to database
def save_games_to_db(games):
    c.executemany('INSERT INTO games VALUES (?, ?, ?, ?, ?)', games)
    conn.commit()


# Function to save players to database
def save_players_to_db(players):
    c.executemany('INSERT INTO players VALUES (?, ?, ?, ?, ?, ?, ?)', players)
    conn.commit()


# Function to save player stats to database
def save_player_stats_to_db(player_id, season, stats):
    c.execute('INSERT INTO player_stats VALUES (?, ?, ?)', (player_id, season, stats['points_per_game']))
    conn.commit()


# Function to fetch data for multiple seasons and teams
def fetch_data():
    seasons = list(range(2020, 2025))
    teams = ["ATL", "BOS", "BRK", "CHO", "CHI", "CLE", "DAL", "DEN", "DET", "GSW", "HOU", "IND", "LAC", "LAL", "MEM", "MIA", "MIL", "MIN", "NOP", "NYK", "OKC", "ORL", "PHI", "PHO", "POR", "SAC", "SAS", "TOR", "UTA", "WAS"]

    for team in teams:
        for season in seasons:
            # print(f"Fetching games for team {team} in season {season}...")
            games = get_season_games(team, season)
            save_games_to_db(games)
            time.sleep(1)  # to avoid hitting the site too frequently
   
    for team in teams:
        for season in seasons:
            players = get_team_roster(team, season)
            save_players_to_db(players)
            time.sleep(1)  # to avoid hitting the site too frequently

    messagebox.showinfo("Data Fetch", "Data fetching complete and saved to the database.")


# Function to predict game result using Neural Network
def predict_game(team1, team2):
    # Load data from the database
    c.execute('''SELECT visitor_team, visitor_score, home_team, home_score FROM games''')
    games_data = c.fetchall()

    if not games_data:
        messagebox.showerror("Error", "No game data available.")
        return
    
    # Prepare the data for the neural network
    data = pd.DataFrame(games_data, columns=['visitor_team', 'visitor_score', 'home_team', 'home_score'])
    data['outcome'] = (data['visitor_score'] > data['home_score']).astype(int)  # 1 if visitor wins, 0 if home wins
    
    # One-hot encode team names
    X = pd.get_dummies(data[['visitor_team', 'home_team']], dtype=float)
    y = data['outcome']
    
    if X.empty or y.empty:
        messagebox.showerror("Error", "The dataset is empty or not formatted correctly.")
        return
    
    print(f"Data Shape: X={X.shape}, y={y.shape}")
    
    # Split data into training and testing sets
    try:
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    except ValueError as e:
        messagebox.showerror("Error", f"Data split failed: {e}")
        return
    
    # Define the neural network model
    model = tf.keras.Sequential([
        tf.keras.layers.Dense(128, activation='relu', input_shape=(X_train.shape[1],)),
        tf.keras.layers.Dense(64, activation='relu'),
        tf.keras.layers.Dense(1, activation='sigmoid')
    ])
    
    # Compile the model
    model.compile(loss='binary_crossentropy', optimizer='adam', metrics=['accuracy'])
    
    # Train the model
    model.fit(X_train, y_train, epochs=10, batch_size=32, verbose=1)
    
    # Make predictions for the input teams
    input_data = pd.get_dummies(pd.DataFrame([[team1, team2]], columns=['visitor_team', 'home_team']), dtype=float)
    input_data = input_data.reindex(columns=X_train.columns, fill_value=0)
    
    # Ensure the input data is converted to a NumPy array and is of the correct type
    input_data = input_data.values.astype(float)
    
    prediction = model.predict(input_data)[0][0]
    result = f"Predicted probability that {team1} will win against {team2}: {prediction:.2f}"
    
    return result


# Function triggered when the "Predict Game" button is clicked
def on_predict():
    team1 = team1_var.get()
    team2 = team2_var.get()
    if team1 and team2:
        result = predict_game(team1, team2)
        messagebox.showinfo("Prediction Result", result)
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