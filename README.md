# Real-time Communication Protocols

This project demonstrates three key real-time communication protocols used in modern web applications:

1. **WebSockets** - Full-duplex, persistent connections
2. **Server-Sent Events (SSE)** - One-way server-to-client streaming
3. **Long Polling** - Request-response pattern with delayed server responses

## Features

- **WebSockets**: Interactive chat functionality with bidirectional communication
- **Server-Sent Events**: Live system metrics monitoring (CPU, Memory, Disk)
- **Long Polling**: Real-time global weather monitoring from multiple cities
- **Connection Simulator**: Test the scalability of WebSocket connections

## Technologies Used

- **Backend**: FastAPI (Python)
- **Frontend**: HTML, CSS, JavaScript
- **Data Visualization**: Chart.js
- **External APIs**: OpenMeteo for weather data
- **System Monitoring**: psutil library

## How It Works

### WebSockets
- Creates a persistent, bidirectional connection between client and server
- Both sides can send messages at any time
- Perfect for chat applications, collaborative editing, and gaming

### Server-Sent Events (SSE)
- Creates a one-way connection from server to client
- Server pushes updates without client requests
- Ideal for dashboards, stock tickers, and monitoring applications

### Long Polling
- Client makes a request, server holds it open until data is available
- Once data is received, client immediately sends a new request
- Works with standard HTTP infrastructure and supports older browsers

## Asynchronous Implementation with asyncio

This project leverages Python's asyncio library to handle concurrent connections efficiently:

- **Non-blocking I/O**: All network operations and API calls are non-blocking, allowing the server to handle multiple clients simultaneously without dedicated threads
- **Parallel API Requests**: Weather data from multiple cities is fetched in parallel using `asyncio.gather()`
- **Event Generators**: Server-Sent Events use async generators to stream updates to clients
- **Timeout Handling**: WebSocket connections implement timeouts to prevent resource leaks
- **Coroutine-based Error Handling**: Try-except blocks in coroutines provide graceful error recovery

Key asyncio patterns demonstrated:

```python
# Parallel data fetching
tasks = [self._fetch_city_weather(city) for city in self.cities]
await asyncio.gather(*tasks)

# Event streaming
async def event_generator():
    while True:
        if await request.is_disconnected():
            break
        yield { ... }
        await asyncio.sleep(2)

# Non-blocking I/O with blocking functions
response = await asyncio.to_thread(requests.get, url, params=params)
```

This approach allows the application to scale efficiently, handling hundreds of connections on modest hardware.

## Running the Project

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Start the server:
   ```
   python main.py
   ```

3. Open your browser and navigate to:
   ```
   http://localhost:8000
   ```

## Learning Objectives

This helps understand:

- When to use each protocol based on application requirements
- The advantages and limitations of different real-time approaches
- How to implement real-time features in a modern web application
- Visualization techniques for real-time data