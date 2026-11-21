# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

# Multi-stage build: Tự động hóa 100%, không cần máy ngoài phải cài Node hay chạy build trước
# Stage 1: Build production bundle
FROM node:20-alpine AS builder

WORKDIR /app

RUN npm install -g pnpm

COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile --dangerously-allow-all-builds

COPY . .
RUN pnpm run build

# Stage 2: Serve bằng Nginx siêu nhẹ (~15MB)
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
