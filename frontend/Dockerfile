FROM node:22-alpine AS build

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# Build with an empty API base so the SPA uses relative URLs (/api, /health),
# which nginx (see nginx.conf) reverse-proxies to the api service. Hardcoding
# http://localhost:3070 here would break any non-localhost deployment.
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
