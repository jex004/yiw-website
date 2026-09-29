FROM python:3.11-slim
WORKDIR /app

# Install the uv package manager
RUN pip install uv

COPY requirements.txt .
# Use uv to install the packages system-wide inside the container
RUN uv pip install --system --no-cache -r requirements.txt

COPY . .

# Start the server with live-reload enabled
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "2000", "--reload"]