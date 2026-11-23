# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

FROM node:20-alpine

WORKDIR /app

# Install git for cloning public git repositories
RUN apk add --no-cache git

COPY package.json ./
RUN npm install --production

COPY server.mjs ./

EXPOSE 3000

CMD ["node", "server.mjs"]
