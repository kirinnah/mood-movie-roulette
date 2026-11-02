FROM nginx:1.28-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html styles.css app.js api.js /usr/share/nginx/html/
COPY assets /usr/share/nginx/html/assets
RUN printf '%s\n' 'window.APP_CONFIG = { apiBase: "/api/v1", healthUrl: "/health" };' > /usr/share/nginx/html/config.js
EXPOSE 80
