const config = window.APP_CONFIG || {};
const base = (config.apiBase || 'http://localhost:8000/api/v1').replace(/\/$/, '');
export const storage = {
  get(key) { try { return sessionStorage.getItem(key); } catch { return null; } },
  set(key, value) { try { sessionStorage.setItem(key, value); } catch { /* Private browsing may disallow storage. */ } },
  remove(key) { try { sessionStorage.removeItem(key); } catch { /* Keep in-memory state usable. */ } },
};
let token = storage.get('kadr-token') || '';
export function setToken(value) { token = value || ''; token ? storage.set('kadr-token', token) : storage.remove('kadr-token'); }
export function hasToken() { return Boolean(token); }
export class ApiError extends Error {
  constructor(status, message) { super(message); this.status = status; }
}
export async function request(path, {method = 'GET', data, form = false, auth = false, signal} = {}) {
  const controller = new AbortController();
  const abort = () => controller.abort(signal?.reason);
  signal?.addEventListener('abort', abort, {once:true});
  if (signal?.aborted) abort();
  const timer = setTimeout(() => controller.abort(), 25000);
  const headers = {Accept:'application/json'};
  const sentToken = token;
  if (auth && sentToken) headers.Authorization = `Bearer ${sentToken}`;
  let body;
  if (data !== undefined) {
    headers['Content-Type'] = form ? 'application/x-www-form-urlencoded' : 'application/json';
    body = form ? new URLSearchParams(data).toString() : JSON.stringify(data);
  }
  try {
    const response = await fetch(path === '/health' ? (config.healthUrl || new URL('/health', base).href) : base + path, {method, headers, body, signal:controller.signal, credentials:'omit'});
    let payload = null;
    if (response.status !== 204) { try { payload = await response.json(); } catch { /* Non-JSON proxy error. */ } }
    if (!response.ok) {
      if (response.status === 401 && auth && sentToken === token) {
        setToken(''); window.dispatchEvent(new Event('auth-expired'));
      }
      const detail = payload?.detail;
      const message = typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map(e => `${(e.loc || []).slice(1).join('.')}: ${e.msg}`).join('; ') : 'Не удалось выполнить запрос.';
      throw new ApiError(response.status, message);
    }
    return payload;
  } catch (error) {
    if (signal?.aborted) throw new DOMException('Aborted', 'AbortError');
    if (error instanceof ApiError) throw error;
    throw new ApiError(0, controller.signal.aborted ? 'Сервер долго не отвечает. Попробуйте ещё раз.' : 'Нет соединения с сервером. Проверьте подключение и попробуйте ещё раз.');
  } finally { clearTimeout(timer); signal?.removeEventListener('abort', abort); }
}
export function errorText(error) {
  if (error.status === 502) return 'Сервис фильмов временно недоступен. Попробуйте ещё раз.';
  if (error.status === 503) return 'Сервер временно недоступен. Попробуйте немного позже.';
  if (error.status === 401) return 'Сессия закончилась. Войдите ещё раз.';
  if (error.status >= 500) return 'На сервере произошла ошибка. Попробуйте ещё раз.';
  return error.message || 'Не удалось загрузить данные. Попробуйте ещё раз.';
}
