import requests
from bs4 import BeautifulSoup
import sqlite3
import time
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox, StringVar, OptionMenu
from PIL import Image, ImageTk
import pandas as pd
import tensorflow as tf
from tensorflow import keras
from keras import layers
from sklearn.model_selection import train_test_split
from tensorflow.keras.layers import Input
import os

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


# Function to handle HTTP requests with error handling
def get_request_with_error_handling(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None

# Function to get season games
def get_season_games(team, season):
    url = f"{BASE_URL}/teams/{team}/{season}_games.html"
    response = get_request_with_error_handling(url)
    if not response:
        return []  # Return empty list if the request failed

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

        visitor_team_element = row.find("td", {"data-stat": "opp_name"})
        if visitor_team_element:
            visitor_team = visitor_team_element.text.strip()
        else:
            continue

        scores = row.find_all("td", {"data-stat": ["pts", "opp_pts"]})
        if visitor_team and scores:
            visitor_score = scores[0].text.strip()
            home_score = scores[1].text.strip()
            if visitor_score.isdigit() and home_score.isdigit():
                games.append([date, visitor_team, int(visitor_score), team, int(home_score)])

    return games

# Function to get team roster
def get_team_roster(team, season):
    url = f"{BASE_URL}/teams/{team}/{season}.html"
    response = get_request_with_error_handling(url)
    if not response:
        return []  # Return empty list if the request failed

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
    url = f"{BASE_URL}/players/{player_id[0]}/{player_id}.html"
    response = get_request_with_error_handling(url)
    if not response:
        return {}  # Return empty dictionary if the request failed

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
            c.execute("SELECT COUNT(*) FROM games WHERE home_team = ? AND date LIKE ?", (team, f"%{season}%"))
            if c.fetchone()[0] == 0:
                games = get_season_games(team, season)
                save_games_to_db(games)

            c.execute("SELECT COUNT(*) FROM players WHERE team = ? AND season = ?", (team, season))
            if c.fetchone()[0] == 0:
                players = get_team_roster(team, season)
                save_players_to_db(players)

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
    
    # Split data into training and testing sets
    try:
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    except ValueError as e:
        messagebox.showerror("Error", f"Data split failed: {e}")
        return
    model = tf.keras.Sequential([
        Input(shape=(X_train.shape[1],)),  
        tf.keras.layers.Dense(128, activation='relu'),
        tf.keras.layers.Dense(64, activation='relu'),
        tf.keras.layers.Dense(1, activation='sigmoid')
    ])
    
    if os.path.exists("model_weights.h5"):
        model.save_weights("model_weights.weights.h5")
        print("Loaded existing weights.")
    else:
        print("No existing weights found. Training a new model.")

    if not os.path.exists("model_weights.h5"):
        model.compile(loss='binary_crossentropy', optimizer='adam', metrics=['accuracy'])

        model.fit(X_train, y_train, epochs=10, batch_size=32, verbose=1)

        model.save_weights("model_weights.weights.h5")
        print("Model trained and weights saved.")

    # Make predictions for the input teams
    input_data = pd.get_dummies(pd.DataFrame([[team1, team2]], columns=['visitor_team', 'home_team']), dtype=float)
    input_data = input_data.reindex(columns=X_train.columns, fill_value=0)
    
    # Ensure the input data is converted to a NumPy array and is of the correct type
    input_data = input_data.to_numpy().astype(float)

    if input_data.size == 0:
        messagebox.showerror("Error", "Invalid input data format.")
        return

    prediction = model.predict(input_data)[0][0]
    winner = team1 if prediction > 0.5 else team2

    # Display the prediction in the GUI
    messagebox.showinfo("Prediction", f"Predicted winner: {winner}")


# Function to retrain the model (for the button)
def retrain_model():
    c.execute('''SELECT visitor_team, visitor_score, home_team, home_score FROM games''')
    games_data = c.fetchall()

    if not games_data:
        messagebox.showerror("Error", "No game data available.")
        return

    data = pd.DataFrame(games_data, columns=['visitor_team', 'visitor_score', 'home_team', 'home_score'])
    data['outcome'] = (data['visitor_score'] > data['home_score']).astype(int)

    X = pd.get_dummies(data[['visitor_team', 'home_team']], dtype=float)
    y = data['outcome']

    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(X.shape[1],)),
        tf.keras.layers.Dense(128, activation='relu'),
        tf.keras.layers.Dense(64, activation='relu'),
        tf.keras.layers.Dense(1, activation='sigmoid')
    ])

    model.compile(loss='binary_crossentropy', optimizer='adam', metrics=['accuracy'])
    model.fit(X, y, epochs=10, batch_size=32, verbose=0)

    model.save_weights("model_weights.weights.h5")
    messagebox.showinfo("Model Update", "Model retrained and weights saved.")


## Main GUI setup
root = tk.Tk()
root.title("NBA Prediction Model")
root.configure(bg='white')

# Add NBA logo image
logo = Image.open("NBA_logo.png")  
logo = logo.resize((100, 100), Image.Resampling.LANCZOS)
logo_image = ImageTk.PhotoImage(logo)

logo_label = tk.Label(root, image=logo_image, bg='white')
logo_label.grid(row=0, column=0, columnspan=2, pady=10)

# Labels, Buttons, and Input Fields with a clean and friendly interface
team1_var = StringVar()
team2_var = StringVar()

team_list = ["ATL", "BOS", "BRK", "CHO", "CHI", "CLE", "DAL", "DEN", "DET", "GSW", "HOU", "IND", "LAC", "LAL", "MEM", "MIA", "MIL", "MIN", "NOP", "NYK", "OKC", "ORL", "PHI", "PHO", "POR", "SAC", "SAS", "TOR", "UTA", "WAS"]

team1_dropdown = OptionMenu(root, team1_var, *team_list)
team1_dropdown.grid(row=1, column=0, padx=10, pady=5)
team2_dropdown = OptionMenu(root, team2_var, *team_list)
team2_dropdown.grid(row=1, column=1, padx=10, pady=5)

predict_button = ttk.Button(root, text="Predict Game Outcome", command=lambda: predict_game(team1_var.get(), team2_var.get()))
predict_button.grid(row=2, column=0, columnspan=2, pady=10)

root.mainloop()