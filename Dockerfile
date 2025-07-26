# Base image with Node.js and Python support
FROM node:18-slim

# Install Python and required tools
RUN apt-get update && \
    apt-get install -y python3 python3-venv python3-pip && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /national-id-server

# Create a Python virtual environment
RUN python3 -m venv /opt/venv

# Ensure pip inside venv is up-to-date
RUN /opt/venv/bin/pip install --upgrade pip

# Copy Python requirements and install them using the venv's pip
COPY requirements.txt .
RUN /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# Copy Node.js files and install dependencies
COPY package*.json ./
RUN npm install

# Copy the rest of your app
COPY . .

# Expose the port
EXPOSE 5000

# Use venv for Python scripts and run your Node app
ENV PATH="/opt/venv/bin:$PATH"

# Start the app (adjust if using something like nodemon)
CMD ["node", "app/app.js"]
