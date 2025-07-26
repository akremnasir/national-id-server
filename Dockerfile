# Base image with Node.js and Python
FROM node:18-slim

# Install Python 3, pip, and virtualenv support
RUN apt-get update && \
    apt-get install -y python3 python3-pip python3-venv && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy Node.js dependencies and install
COPY package*.json ./
RUN npm install

# Copy Python dependencies and install
COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY . .

# Expose the server port
EXPOSE 5000

# Start the app
CMD ["node", "app.js"]
