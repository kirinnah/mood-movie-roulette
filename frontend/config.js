// При локальном запуске фронтенда отдельно от Docker используется порт 8000.
// В Docker файл заменяется: запросы идут через nginx на тот же origin.
window.APP_CONFIG = { apiBase: 'http://localhost:8000/api/v1', healthUrl: 'http://localhost:8000/health' };
