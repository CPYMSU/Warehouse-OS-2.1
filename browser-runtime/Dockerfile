# Keep the Browser Runtime layer explicit in the first cloud sync so an older
# standby without a browser image bootstraps it before later fast reuse.
FROM mcr.microsoft.com/playwright:v1.62.0-noble

ENV NODE_ENV=production \
    PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1

USER root
WORKDIR /app
COPY browser-runtime/package.json browser-runtime/package-lock.json ./
RUN npm ci --omit=dev --ignore-scripts \
    && mkdir -p /data/browser-runtime \
    && chown -R pwuser:pwuser /app /data/browser-runtime
COPY --chown=pwuser:pwuser browser-runtime/index.mjs ./index.mjs

USER pwuser
CMD ["node", "index.mjs"]
