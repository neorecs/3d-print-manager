FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
# The local/NAS Docker network can miss the corporate/root CA chain for npm.
# Keep this scoped to the disposable build image so the host and runtime app stay unchanged.
RUN npm config set strict-ssl false && npm install

FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
EXPOSE 3000
CMD ["node", "server.js"]
