# Base image with Node.js and Python
FROM node:18-slim

# Install Python and pip
RUN apt-get update && \
    apt-get install -y python3 python3-pip && \
    pip3 install --upgrade pip

# Set the working directory
WORKDIR /app

# Copy Node.js dependencies and install
COPY package*.json ./
RUN npm install

# Copy Python dependencies and install
COPY requirements.txt ./
RUN pip3 install -r requirements.txt

# Copy everything else
COPY . .

# Expose backend port
EXPOSE 5000

# Start the server
CMD ["node", "app.js"]
