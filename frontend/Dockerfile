# Stage 1: Build the React application
FROM node:20-alpine as builder

WORKDIR /app

COPY package.json ./
COPY package-lock.json ./

RUN npm install

COPY . .

# Use ARG to receive build-time environment variable
ARG VITE_API_BASE
ENV VITE_API_BASE=$VITE_API_BASE

RUN npm run build

# Stage 2: Serve the application with Nginx
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80 for the frontend
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
