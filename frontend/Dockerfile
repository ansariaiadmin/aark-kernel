# syntax=docker/dockerfile:1
# AARK Frontend — production image, non-root, minimal, healthcheck

FROM node:22-alpine AS deps
WORKDIR /app
RUN apk add --no-cache libc6-compat
COPY package.json package-lock.json* ./
RUN npm ci --ignore-scripts

FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1

# Leave the browser-facing base EMPTY on purpose: the dashboard calls the
# same-origin /api/v1/* and Next proxies it to the API (see next.config.mjs).
# Baking http://localhost:8000 here made every browser call cross-origin and
# broke any deployment behind a reverse proxy or preview host.
ARG NEXT_PUBLIC_API_URL=
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

# next.config.mjs rewrites() are resolved and *serialised at build time*, so the
# proxy target must be a build argument — a runtime ENV on the runner stage
# would be ignored. Default matches the docker-compose service name.
ARG AARK_BACKEND_ORIGIN=http://backend:8000
ENV AARK_BACKEND_ORIGIN=${AARK_BACKEND_ORIGIN}
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD node -e "fetch('http://127.0.0.1:3000').then(r=>{if(!r.ok)process.exit(1)}).catch(()=>process.exit(1))"

CMD ["node", "server.js"]
