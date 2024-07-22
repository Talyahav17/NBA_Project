import csv
import time
import tkinter as tk
from tkinter import messagebox, StringVar, OptionMenu
from PIL import Image, ImageTk
import requests
from bs4 import BeautifulSoup
import pandas as pd

# Constants
BASE_URL = "https://www.basketball-reference.com"

def get_season_games(season):
    """Fetches NBA game data for a specific season."""
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
                games.append([date, visitor_team, visitor_score, home_team, home_score])
    
    return games

def get_team_roster(team, season):
    """Fetches roster data for a specific NBA team in a season."""
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
            players.append([player_name, position, height, weight, birth_date])
    return players

def get_player_stats(player_id, season):
    """Fetches player statistics for a specific player in a season."""
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

def save_to_csv(data, filename):
    """Saves data to a CSV file."""
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerows(data)

def fetch_data():
    """Fetches NBA games and team rosters for seasons 2020-2024 and saves them to CSV files."""
    seasons = list(range(2020, 2025))
    all_games = []
    all_players = []
    teams = set()
    
    for season in seasons:
        print(f"Fetching games for season {season}...")
        games = get_season_games(season)
        all_games.extend(games)
        for game in games:
            teams.add(game[1])
            teams.add(game[3])
        time.sleep(1)  # to avoid hitting the site too frequently
    
    print("Fetching rosters for each team...")
    for team in teams:
        for season in seasons:
            print(f"Fetching roster for team {team} in season {season}...")
            players = get_team_roster(team, season)
            for player in players:
                player.append(team)
                player.append(season)
            all_players.extend(players)
            time.sleep(1)  # to avoid hitting the site too frequently
    
    save_to_csv(all_games, 'nba_games_2020_2024.csv')
    save_to_csv(all_players, 'nba_players_2020_2024.csv')
    messagebox.showinfo("Data Fetch", "Data fetching complete and saved to CSV files.")

def predict_game(team1, team2):
    """Predicts game scores between two NBA teams."""
    try:
        # Check if the file exists and is not empty
        with open('nba_games_2020_2024.csv', 'r') as file:
            if file.read().strip():  # Check if the file is not empty
                file.seek(0)  # Reset file pointer to the beginning
                games_df = pd.read_csv(file)
            else:
                raise ValueError("The CSV file is empty.")
    except FileNotFoundError:
        raise FileNotFoundError("The file 'nba_games_2020_2024.csv' does not exist.")
    except pd.errors.EmptyDataError:
        raise ValueError("No columns to parse from file. Ensure the file is properly formatted.")
    games_df = pd.read_csv('nba_games_2020_2024.csv', header=None)
    games_df.columns = ['Date', 'Visitor Team', 'Visitor Score', 'Home Team', 'Home Score']
    
    team1_games = games_df[(games_df['Visitor Team'] == team1) | (games_df['Home Team'] == team1)]
    team2_games = games_df[(games_df['Visitor Team'] == team2) | (games_df['Home Team'] == team2)]
    
    team1_avg_score = (team1_games['Visitor Score'].sum() + team1_games['Home Score'].sum()) / len(team1_games)
    team2_avg_score = (team2_games['Visitor Score'].sum() + team2_games['Home Score'].sum()) / len(team2_games)
    
    result = f"Predicted Score:\n{team1}: {team1_avg_score:.2f}\n{team2}: {team2_avg_score:.2f}"
    return result

def display_players(team, season):
    """Displays players' details for a specific NBA team in a season."""
    players_df = pd.read_csv('nba_players_2020_2024.csv', header=None)
    players_df.columns = ['Player Name', 'Position', 'Height', 'Weight', 'Birth Date', 'Team', 'Season']
    
    team_players = players_df[(players_df['Team'] == team) & (players_df['Season'] == season)]
    return team_players[['Player Name', 'Position', 'Height', 'Weight', 'Birth Date']].to_string(index=False)

def predict_player_scores(team, season):
    """Predicts player scores for a specific NBA team in a season."""
    players_df = pd.read_csv('nba_players_2020_2024.csv', header=None)
    players_df.columns = ['Player Name', 'Position', 'Height', 'Weight', 'Birth Date', 'Team', 'Season']
    
    team_players = players_df[(players_df['Team'] == team) & (players_df['Season'] == season)]
    player_scores = {}
    for _, row in team_players.iterrows():
        player_name = row['Player Name']
        player_id = row['Player Name'].split(' ')[1][:5].lower() + row['Player Name'].split(' ')[0][:2].lower()
        stats = get_player_stats(player_id, season)
        player_scores[player_name] = stats.get('points_per_game', 0.0)
    
    return player_scores

def on_predict():
    """Handles prediction button click event."""
    team1 = team1_var.get()
    team2 = team2_var.get()
    season = 2024  
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
label.place(x=670, y=150)

fetch_button = tk.Button(root, text="Fetch Data", command=fetch_data, font=("DM Sans", 16), bg="blue", fg="black")
fetch_button.place(x=670, y=550)

team1_var = StringVar()
team2_var = StringVar()

teams = ["ATL", "BOS", "BRK", "CHO", "CHI", "CLE", "DAL", "DEN", "DET", "GSW", "HOU", "IND", "LAC", "LAL", "MEM", "MIA", "MIL", "MIN", "NOP", "NYK", "OKC", "ORL", "PHI", "PHO", "POR", "SAC", "SAS", "TOR", "UTA", "WAS"]

team1_label = tk.Label(root, text="Select Team 1", font=("DM Sans", 16), bg='blue')
team1_label.place(x=550, y=650)
team1_menu = OptionMenu(root, team1_var, *teams)
team1_menu.place(x=700, y=650)

team2_label = tk.Label(root, text="Select Team 2", font=("DM Sans", 16), bg='blue')
team2_label.place(x=550, y=700)
team2_menu = OptionMenu(root, team2_var, *teams)
team2_menu.place(x=700, y=700)

predict_button = tk.Button(root, text="Predict Game", command=on_predict, font=("Arial", 16), bg="blue", fg="black")
predict_button.place(x=670, y=800)

root.mainloop()