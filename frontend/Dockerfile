# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

FROM nginx:alpine

# Copy pre-built production assets directly (0s build time, 15MB total image)
COPY dist /usr/share/nginx/html

# Copy custom nginx config to support React SPA client-side routing
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
