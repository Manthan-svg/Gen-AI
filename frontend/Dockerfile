FROM node:20-alpine

# Set working directory
WORKDIR /app

# Copy package files first
COPY package.json package-lock.json ./

# Install all npm dependencies
RUN npm ci

# Copy the entire frontend code
COPY . .

# Expose the Vite dev server port
EXPOSE 5173

# Start Vite dev server accessible from outside the container
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
