# Production image: build the static app, serve dist/ with nginx.
# Build context is the repo root (vite.config.ts reads backend/pipeline/catalog.csv).
FROM node:24-alpine AS build
WORKDIR /repo/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
COPY backend/pipeline/catalog.csv /repo/backend/pipeline/catalog.csv
ARG VITE_API_URL
ENV VITE_API_URL=${VITE_API_URL}
RUN npm run build

FROM nginx:1.27-alpine
COPY frontend/nginx.conf /etc/nginx/templates/default.conf.template
COPY --from=build /repo/frontend/dist /usr/share/nginx/html
ENV PORT=80
