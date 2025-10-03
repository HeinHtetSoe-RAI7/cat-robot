# Use an official Node.js runtime as a parent image
FROM node:alpine

# Set the working directory
WORKDIR /app

# Copy the package.json and install dependencies
COPY package.json ./
COPY package-lock.json ./

# Install dependencies
RUN npm install

# Copy the rest of the application
COPY . .

# Expose the port
EXPOSE 3000

# Start the application
CMD ["npm", "start"]
