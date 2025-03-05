import requests
import json
import pandas as pd
import folium
from flask import Flask, render_template
from flask_caching import Cache
import plotly.express as px

app = Flask(__name__)
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

def fetch_balloon_data():
    base_url = "https://a.windbornesystems.com/treasure/"
    data = []
    
    for i in range(24):
        try:
            url = f"{base_url}{str(i).zfill(2)}.json"
            response = requests.get(url)
            if response.status_code == 200:
                json_data = response.json()
                if isinstance(json_data, list):
                    for entry in json_data:
                        if isinstance(entry, dict) and 'latitude' in entry and 'longitude' in entry:
                            data.append(entry)
        except (requests.RequestException, json.JSONDecodeError) as e:
            print(f"Error fetching {url}: {e}")
    
    return pd.DataFrame(data)

@cache.memoize(timeout=1800)  # Cache responses for 30 minutes
def fetch_weather_data(lat, lon):
    weather_api_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
    try:
        response = requests.get(weather_api_url)
        if response.status_code == 200:
            return response.json().get("current_weather", {})
    except requests.RequestException as e:
        print(f"Error fetching weather data: {e}")
    return {}

def generate_map(df):
    balloon_map = folium.Map(location=[0, 0], zoom_start=2)
    
    for _, row in df.iterrows():
        try:
            lat, lon = row["latitude"], row["longitude"]
            weather = fetch_weather_data(lat, lon)
            popup_info = f"Balloon ID: {row.get('id', 'Unknown')}\n"
            if weather:
                popup_info += f"Temp: {weather.get('temperature', 'N/A')}°C, Wind: {weather.get('windspeed', 'N/A')} km/h"
            folium.Marker([lat, lon], popup=popup_info).add_to(balloon_map)
        except KeyError:
            continue
    
    return balloon_map._repr_html_()

def generate_altitude_chart(df):
    if "altitude" in df.columns:
        fig = px.line(df, x=df.index, y="altitude", title="Altitude Changes Over Time")
        return fig.to_html()
    return "<p>No altitude data available.</p>"

@app.route('/')
def home():
    df = fetch_balloon_data()
    balloon_map = generate_map(df)
    altitude_chart = generate_altitude_chart(df)
    return render_template('index.html', map=balloon_map, chart=altitude_chart)

if __name__ == '__main__':
    app.run(debug=True)

