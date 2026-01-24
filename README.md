# Fitness Coach

A streaming fitness coach chatbot powered by LangChain and Ollama. The app learns your fitness profile and generates personalized daily workouts with detailed rationales.

## Features

- **Streaming responses** - Real-time workout generation
- **Persistent memory** - Chat history and profile stored in SQLite
- **Profile-based personalization** - Tracks gender, age, fitness level, and goals
- **Single-user demo** - Simplified setup with fixed session management
- **Containerized** - Easy deployment with Docker

## Prerequisites

- [Docker](https://www.docker.com/products/docker-desktop)
- [Docker Compose](https://docs.docker.com/compose/)
- [Ollama](https://ollama.ai/) running locally with the `llama3.2` model

## Quickstart with Docker

### 1. Pull the Ollama model

Before running the app, ensure Ollama is installed and has the `llama3.2` model:

```bash
ollama pull llama3.2
ollama serve
```

This will start Ollama on `http://localhost:11434` (the default port).

### 2. Start the application

In the project directory, run:

```bash
docker-compose up --build
```

This will:
- Build the Docker image for the fitness coach app
- Start the Gradio web server on port 7860
- Connect to your local Ollama instance

### 3. Access the app

Open your browser and go to:

```
http://localhost:7860
```

## Usage

1. **Start chatting** - Ask for today's workout or introduce yourself
2. **Complete your profile** - The coach will ask for missing information:
   - Gender (male/female/non-binary)
   - Age
   - Fitness level (beginner/intermediate/advanced)
   - Fitness goals
3. **Get personalized workouts** - Once your profile is complete, the coach generates tailored daily workouts

Example conversation:
```
You: I'm a 30-year-old woman, intermediate fitness level, want to lose weight
Coach: Great! Today's workout is [workout details with rationale referencing your profile]
```

## Project Structure

```
.
├── main.py              # Main Gradio app with LangChain integration
├── Dockerfile           # Container configuration
├── docker-compose.yml   # Docker Compose setup
├── requirements.txt     # Python dependencies
├── data/                # Database and data storage
└── coach.db            # SQLite database (auto-created)
```

## Configuration

### Environment Variables

- `OLLAMA_HOST` - Ollama server URL (default: `http://host.docker.internal:11434` in Docker)
- `GRADIO_SERVER_NAME` - Gradio server address (default: `0.0.0.0`)
- `GRADIO_SERVER_PORT` - Gradio server port (default: `7860`)

### Database

Chat history and user profiles are stored in `./data/coach.db` (SQLite). The database persists across container restarts via Docker volumes.

## Troubleshooting

### Connection refused to Ollama
- Ensure Ollama is running: `ollama serve`
- Check that Ollama is accessible on `http://localhost:11434`

### Port 7860 already in use
Modify the `docker-compose.yml` to use a different port:
```yaml
ports:
  - "8000:7860"  # Access at http://localhost:8000
```

### Model not found
Pull the model first:
```bash
ollama pull llama3.2
```

## Development

To run locally without Docker:

```bash
pip install -r requirements.txt
ollama serve  # In another terminal
python main.py
```

The Gradio app will launch at `http://localhost:7860`.
