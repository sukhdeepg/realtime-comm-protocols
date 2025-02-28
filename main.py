from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
import asyncio
import json
import time
import uvicorn
import logging
import psutil
from datetime import datetime
import requests

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Real-time Protocols",
    description="A demonstration of WebSockets, SSE, and Long Polling",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.simulated_connections: int = 0
        
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Client connected. Total connections: {self.get_total_connections()}")
        
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"Client disconnected. Total connections: {self.get_total_connections()}")
    
    def add_simulated(self, count: int = 1):
        self.simulated_connections += count
        logger.info(f"Added {count} simulated connections. Total: {self.get_total_connections()}")
        return self.simulated_connections
        
    def remove_simulated(self, count: int = 1):
        if count > self.simulated_connections:
            count = self.simulated_connections
        self.simulated_connections -= count
        logger.info(f"Removed {count} simulated connections. Total: {self.get_total_connections()}")
        return self.simulated_connections
        
    def get_total_connections(self):
        return len(self.active_connections) + self.simulated_connections

manager = ConnectionManager()

# Weather monitoring
class WeatherMonitor:
    def __init__(self):
        # Cities to monitor
        self.cities = [
            {"id": "london", "name": "London", "country": "GB"},
            {"id": "new_york", "name": "New York", "country": "US"},
            {"id": "tokyo", "name": "Tokyo", "country": "JP"},
            {"id": "sydney", "name": "Sydney", "country": "AU"},
            {"id": "bengaluru", "name": "Bengaluru", "country": "IN"}
        ]
        self.weather_data = {}
        self.last_updated = datetime.now()
        self.update_history = []
        
    async def update_weather(self):
        """Async method to update weather data for all cities"""
        now = datetime.now()
        self.last_updated = now
        
        # Limit history size
        if len(self.update_history) > 15:
            self.update_history.pop(0)
        
        # Add new update event
        self.update_history.append({"timestamp": now.timestamp(), "changes": {}})
        
        # Create tasks for all cities
        tasks = [self._fetch_city_weather(city) for city in self.cities]
        await asyncio.gather(*tasks)
        
        return self.weather_data
    
    async def _fetch_city_weather(self, city):
        """Fetch weather for a specific city"""
        try:
            logger.info(f"Fetching weather data for {city['name']}")
            
            # Use asyncio.to_thread for non-blocking HTTP request
            response = await asyncio.to_thread(
                requests.get,
                f"https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": self._get_city_coordinates(city["id"])["lat"],
                    "longitude": self._get_city_coordinates(city["id"])["lon"],
                    "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
                    "timezone": "auto"
                },
                timeout=5.0
            )
            
            if response.status_code == 200:
                data = response.json()
                current = data.get("current", {})
                
                # Get previous data
                previous_data = self.weather_data.get(city["id"], {})
                old_temp = previous_data.get("temperature", 0) 
                
                # Get weather condition
                weather_code = current.get("weather_code", 0)
                weather_condition = self._get_weather_condition(weather_code)
                
                # Calculate temperature change
                new_temp = current.get("temperature_2m", 0)
                temp_change = new_temp - old_temp
                
                # Store new data
                self.weather_data[city["id"]] = {
                    "city_name": city["name"],
                    "country": city["country"],
                    "temperature": new_temp,
                    "humidity": current.get("relative_humidity_2m", 0),
                    "wind_speed": current.get("wind_speed_10m", 0),
                    "condition": weather_condition,
                    "temp_change": temp_change
                }
                
                # Record significant changes
                if abs(temp_change) >= 0.5:
                    self.update_history[-1]["changes"][city["id"]] = {
                        "city_name": city["name"],
                        "temp_change": temp_change,
                        "new_temp": new_temp
                    }
                
                logger.info(f"Successfully updated weather for {city['name']}: {new_temp}°C, {weather_condition}")
            else:
                # Add fallback for failed API calls
                logger.error(f"Failed to get weather for {city['name']}: Status code {response.status_code}")
                
                # Use fallback data if the API call fails
                self.weather_data[city["id"]] = {
                    "city_name": city["name"],
                    "country": city["country"],
                    "temperature": 20 + (hash(city["id"]) % 10),  # Generate reasonable random temp
                    "humidity": 50 + (hash(city["id"]) % 30),
                    "wind_speed": 5 + (hash(city["id"]) % 10),
                    "condition": "API Error - Using Fallback Data",
                    "temp_change": 0
                }
                
        except Exception as e:
            logger.error(f"Error updating weather for {city['name']}: {str(e)}")
            
            # Add fallback for exceptions
            self.weather_data[city["id"]] = {
                "city_name": city["name"],
                "country": city["country"],
                "temperature": 20 + (hash(city["id"]) % 10),
                "humidity": 50 + (hash(city["id"]) % 30),
                "wind_speed": 5 + (hash(city["id"]) % 10),
                "condition": "Error - Using Fallback Data",
                "temp_change": 0
            }
    
    def _get_city_coordinates(self, city_id):
        """Get coordinates for a city"""
        coordinates = {
            "london": {"lat": 51.5074, "lon": -0.1278},
            "new_york": {"lat": 40.7128, "lon": -74.0060},
            "tokyo": {"lat": 35.6762, "lon": 139.6503},
            "sydney": {"lat": -33.8688, "lon": 151.2093},
            "bengaluru": {"lat": 12.9716, "lon": 77.5946}
        }
        return coordinates.get(city_id, {"lat": 0, "lon": 0})
    
    def _get_weather_condition(self, code):
        """Convert weather code to human-readable condition"""
        conditions = {
            0: "Clear sky",
            1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
            45: "Fog", 48: "Fog",
            51: "Light drizzle", 53: "Drizzle", 55: "Drizzle",
            61: "Rain", 63: "Rain", 65: "Heavy rain",
            71: "Snow", 73: "Snow", 75: "Heavy snow",
            80: "Rain showers", 95: "Thunderstorm"
        }
        return conditions.get(code, "Unknown")

# Create weather monitor instance
weather_monitor = WeatherMonitor()

# Long Polling endpoint
@app.get("/poll")
async def long_poll():
    # Update weather data - now using async method
    await weather_monitor.update_weather()
    
    # Find all cities
    cities_by_temp = sorted(
        weather_monitor.weather_data.items(),
        key=lambda x: x[1]["temperature"],
        reverse=True
    )
    
    if not cities_by_temp:
        return {"error": "No weather data available"}
    
    # Create message with ALL cities instead of just hottest and coldest
    city_temps = []
    for city_id, city_data in weather_monitor.weather_data.items():
        city_temps.append(f"{city_data['city_name']} {city_data['temperature']:.1f}°C")
    
    weather_message = f"Weather update: {', '.join(city_temps)}"
    
    # Create summary
    weather_summary = {
        "timestamp": time.time(),
        "message": weather_message,  # Using the new message with all cities
        "count": manager.get_total_connections(),
        "weather_data": weather_monitor.weather_data,
        "updates": weather_monitor.update_history,
        "visual_data": {
            "color": f"#{int(time.time()) % 16777215:06x}",
            "labels": [city["name"] for city in weather_monitor.cities],
            "values": [weather_monitor.weather_data.get(city["id"], {}).get("temperature", 0) for city in weather_monitor.cities],
            "humidity": [weather_monitor.weather_data.get(city["id"], {}).get("humidity", 0) for city in weather_monitor.cities],
            "wind_speed": [weather_monitor.weather_data.get(city["id"], {}).get("wind_speed", 0) for city in weather_monitor.cities]
        }
    }
    
    return weather_summary

# Server-Sent Events endpoint
@app.get("/sse")
async def sse(request: Request):
    async def event_generator():
        while True:
            if await request.is_disconnected():
                logger.info("SSE client disconnected")
                break
            
            # Get system metrics
            metrics = await get_system_metrics()
            
            yield {
                "event": "message",
                "data": json.dumps({
                    "timestamp": metrics["timestamp"],
                    "message": f"System update: CPU: {metrics['cpu']['percent']:.1f}%, Memory: {metrics['memory']['percent']:.1f}%, Disk: {metrics['disk']['percent']:.1f}%",
                    "count": manager.get_total_connections(),
                    "visual_data": {
                        "labels": ["CPU", "Memory", "Disk"],
                        "values": [
                            metrics["cpu"]["percent"],
                            metrics["memory"]["percent"],
                            metrics["disk"]["percent"]
                        ]
                    },
                    "system_metrics": metrics
                })
            }
            
            await asyncio.sleep(2)  # Send update every 2 seconds
    
    return EventSourceResponse(event_generator())

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Send data to client
            data = {
                "timestamp": time.time(),
                "message": "Data from WebSocket",
                "count": manager.get_total_connections()
            }
            await websocket.send_json(data)
            
            # Wait for client message with timeout
            try:
                client_message = await asyncio.wait_for(websocket.receive_text(), timeout=3.0)
                # Echo back
                response = {
                    "timestamp": time.time(),
                    "message": f"Server received: {client_message}",
                    "type": "response"
                }
                await websocket.send_json(response)
            except asyncio.TimeoutError:
                # No client message received, continue
                await asyncio.sleep(1)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        manager.disconnect(websocket)

# System metrics endpoint with caching
last_metrics_time = 0
cached_metrics = None

@app.get("/system-metrics")
async def get_system_metrics():
    global last_metrics_time, cached_metrics
    
    # Use cached metrics if less than 1 second old
    current_time = time.time()
    if cached_metrics and current_time - last_metrics_time < 1:
        return cached_metrics
    
    # Get CPU usage
    cpu_percent = psutil.cpu_percent(interval=0.1)
    
    # Get memory usage
    memory = psutil.virtual_memory()
    
    # Get disk usage
    disk = psutil.disk_usage('/')
    
    # Update cache
    cached_metrics = {
        "timestamp": current_time,
        "cpu": {
            "percent": cpu_percent,
            "cores": psutil.cpu_count()
        },
        "memory": {
            "percent": memory.percent,
            "used": memory.used,
            "total": memory.total
        },
        "disk": {
            "percent": disk.percent,
            "used": disk.used,
            "total": disk.total
        }
    }
    last_metrics_time = current_time
    
    return cached_metrics

# Connection simulation endpoints
@app.post("/simulate/add")
async def add_simulated_connections(count: int = 1):
    total = manager.add_simulated(count)
    return {"simulated": manager.simulated_connections, "real": len(manager.active_connections), "total": total}

@app.post("/simulate/remove")
async def remove_simulated_connections(count: int = 1):
    total = manager.remove_simulated(count)
    return {"simulated": manager.simulated_connections, "real": len(manager.active_connections), "total": total}

@app.get("/connections")
async def get_connections():
    return {"simulated": manager.simulated_connections, "real": len(manager.active_connections), "total": manager.get_total_connections()}

# Serve the main HTML page
@app.get("/")
async def get_html():
    try:
        with open("static/index.html") as f:
            return HTMLResponse(f.read())
    except Exception as e:
        logger.error(f"Error serving HTML: {str(e)}")
        return HTMLResponse("<h1>Error loading page</h1><p>The application encountered an error.</p>")

if __name__ == "__main__":
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="info"
    )