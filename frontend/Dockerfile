FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci

FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# Variables NEXT_PUBLIC_* se inyectan en build (Next.js las "hornea" en el bundle).
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_WHATSAPP_PHONE
ARG NEXT_PUBLIC_WHATSAPP_TEMPLATE
ARG CATALOG_SHOW_PRICES
ARG CATALOG_CURRENCY_SYMBOL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    NEXT_PUBLIC_WHATSAPP_PHONE=$NEXT_PUBLIC_WHATSAPP_PHONE \
    NEXT_PUBLIC_WHATSAPP_TEMPLATE=$NEXT_PUBLIC_WHATSAPP_TEMPLATE \
    CATALOG_SHOW_PRICES=$CATALOG_SHOW_PRICES \
    CATALOG_CURRENCY_SYMBOL=$CATALOG_CURRENCY_SYMBOL
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000
CMD ["node", "server.js"]
