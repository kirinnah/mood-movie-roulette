import {request, hasToken, setToken, storage, errorText} from './api.js';
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const MOODS = {
  happy: ['Радостно', 'Для улыбки без особого повода', '<circle cx="20" cy="20" r="15"/><path d="M12 23q8 10 16 0M14 15v2m12-2v2"/>'],
  sad: ['Грустно', 'Иногда кино понимает лучше слов', '<circle cx="20" cy="20" r="15"/><path d="M13 28q7-9 14 0M14 14v2m12-2v2M29 18q6 7 0 7q-5 0 0-7"/>'],
  cozy: ['Уютно', 'Тёплое кино к пледу и чашке чая', '<path d="M7 16h22v10a10 10 0 0 1-10 9h-2A10 10 0 0 1 7 26zM29 18h3a5 5 0 0 1 0 10h-3M13 10q-4-3 0-6m7 6q-4-3 0-6m7 6q-4-3 0-6"/>'],
  adventure: ['За приключениями', 'Пора отправиться куда-нибудь далеко', '<circle cx="20" cy="20" r="16"/><path d="m27 12-4 12-11 4 4-12zM20 2v5m0 26v5M2 20h5m26 0h5"/>'],
  scary: ['Хочу бояться', 'Выключи свет. Если решишься', '<path d="M8 34V17a12 12 0 0 1 24 0v17l-6-4-6 4-6-4z"/><ellipse cx="15" cy="18" rx="2" ry="3"/><ellipse cx="25" cy="18" rx="2" ry="3"/><path d="M18 26h4"/>'],
  thoughtful: ['Есть о чём подумать', 'Истории, которые остаются с тобой', '<path d="M14 29c0-6-7-6-7-14a13 13 0 0 1 26 0c0 8-7 8-7 14zM14 33h12m-9 4h6M17 29V18l-4-4m10 15V18l4-4"/>'],
  romantic: ['Влюблённо', 'Для больших чувств и маленьких чудес', '<path d="M20 34S3 24 3 13C3 3 16 2 20 11 24 2 37 3 37 13c0 11-17 21-17 21Z"/>'],
};
const state = {mood:'happy', moods:[], movie:null, favorites:[], favoritesLoaded:false, user:null, spinning:false, authMode:'login', authBusy:false, generation:0, pendingFavorite:null};
let history = {};
try { const stored = JSON.parse(storage.get('kadr-history') || '{}'); if (stored && typeof stored === 'object' && !Array.isArray(stored)) history = stored; } catch { /* Ignore invalid old state. */ }
let searchController, detailController, toastTimer, favoriteLoad;
const pendingFavorites = new Set();
function message(id, text, error = false) { const element = $(id); element.textContent = text; element.hidden = !text; element.classList.toggle('error', error); }
function toast(text) { clearTimeout(toastTimer); message('#toast', text); toastTimer = setTimeout(() => { $('#toast').hidden = true; }, 4500); }
function node(tag, className, text) { const element = document.createElement(tag); if (className) element.className = className; if (text != null) element.textContent = text; return element; }
function currentView() { return ['search','favorites'].includes(location.hash.slice(1)) ? location.hash.slice(1) : 'roulette'; }
function isSaved(id) { return state.favorites.some(item => item.movie.imdb_id === id); }
function poster(movie) {
  const img = node('img', 'poster'); img.alt = `Постер: ${movie.title || 'Без названия'}`; img.loading = 'lazy';
  let url = '';
  try { const candidate = new URL(movie.poster_url); if (['https:','http:'].includes(candidate.protocol)) url = candidate.href; } catch { /* Missing or invalid poster. */ }
  img.src = url || 'assets/poster-placeholder.svg';
  img.addEventListener('error', () => { img.src = 'assets/poster-placeholder.svg'; }, {once:true});
  return img;
}
function favoriteButton(movie) {
  const button = node('button', 'button outline favorite-button'); button.dataset.movieId = movie.imdb_id;
  button.addEventListener('click', () => toggleFavorite(movie)); updateFavoriteButton(button); return button;
}
function updateFavoriteButton(button) { const saved = isSaved(button.dataset.movieId); button.textContent = saved ? '♥ В избранном · убрать' : '♡ В избранное'; button.setAttribute('aria-pressed', String(saved)); button.disabled = pendingFavorites.has(button.dataset.movieId); }
function refreshFavoritesUI() {
  $$('.favorite-button').forEach(updateFavoriteButton); $$('.fav-count').forEach(e => { e.textContent = state.favorites.length; });
  if (currentView() === 'favorites') renderFavorites();
}
function feature(movie) {
  const article = node('article','feature-film'); article.append(poster(movie));
  const info = node('div','feature-info');
  info.append(node('p','genres',(movie.genres || []).join(' / ') || 'КИНО ДЛЯ ТВОЕГО ВЕЧЕРА'));
  info.append(node('h3','',movie.title || 'Без названия'));
  info.append(node('p','card-meta',`${movie.year ?? 'Год не указан'}   ·   IMDb ${movie.rating ?? '—'} / 10`));
  info.append(node('p','film-description',movie.description || 'Описание пока недоступно. Возможно, этот фильм лучше открыть для себя без подсказок.'));
  const actors = Array.isArray(movie.actors) ? movie.actors.join(', ') : movie.actors;
  if (actors) info.append(node('p','card-meta',`В ролях: ${actors}`));
  const actions = node('div','film-actions'); actions.append(favoriteButton(movie));
  if (/^tt\d+$/.test(movie.imdb_id)) { const link = node('a','button outline','О фильме на IMDb ↗'); link.href = `https://www.imdb.com/title/${movie.imdb_id}/`; link.target = '_blank'; link.rel = 'noopener noreferrer'; actions.append(link); }
  info.append(actions); article.append(info); return article;
}
function card(movie) {
  const article = node('article','movie-card');
  const open = node('button','poster-button'); open.setAttribute('aria-label', `Открыть фильм «${movie.title || 'Без названия'}»`); open.append(poster(movie)); open.addEventListener('click', () => openMovie(movie.imdb_id));
  const info = node('div','card-info'); const title = node('h3'); const titleButton = node('button','text-button',movie.title || 'Без названия'); titleButton.addEventListener('click', () => openMovie(movie.imdb_id)); title.append(titleButton);
  info.append(title, node('p','card-meta',String(movie.year ?? 'Год не указан')), favoriteButton(movie)); article.append(open, info); return article;
}
async function openMovie(id) {
  detailController?.abort(); detailController = new AbortController(); const own = detailController;
  $('#movie-detail').replaceChildren(node('p','message','Загружаем фильм…'));
  if (!$('#movie-dialog').open) $('#movie-dialog').showModal();
  try { const movie = await request(`/movies/${encodeURIComponent(id)}`,{signal:own.signal}); if (!own.signal.aborted) $('#movie-detail').replaceChildren(feature(movie)); }
  catch (error) { if (error.name !== 'AbortError') { const msg = node('p','message error',errorText(error)); const retry = node('button','button outline','Попробовать ещё раз'); retry.onclick = () => openMovie(id); $('#movie-detail').replaceChildren(msg,retry); } }
}
function renderMoods() {
  $('#moods').replaceChildren(...state.moods.map(({key}) => {
    const [label, , icon] = MOODS[key] || [key, '', '<circle cx="20" cy="20" r="14"/>'];
    const button = node('button','mood'); button.dataset.mood = key; button.setAttribute('aria-pressed',String(state.mood === key));
    const symbol = node('span','mood-icon'); symbol.setAttribute('aria-hidden','true'); symbol.innerHTML = `<svg viewBox="0 0 40 40">${icon}</svg>`; button.append(symbol,node('span','',label));
    button.disabled = state.spinning;
    button.onclick = () => { state.mood = key; message('#roulette-message',''); renderMoods(); };
    return button;
  }));
  $('#mood-description').textContent = MOODS[state.mood]?.[1] || 'Выбери настроение для своего вечера';
  $('#spin').disabled = !state.moods.length || state.spinning;
  $('#reset-history').hidden = !(history[state.mood]?.length);
}
async function loadMoods() {
  try {
    const moods = await request('/moods'); if (!Array.isArray(moods) || !moods.length) throw new Error('Список настроений пока пуст. Попробуйте обновить страницу.');
    state.moods = moods; if (!moods.some(m => m.key === state.mood)) state.mood = moods[0].key;
    renderMoods(); message('#roulette-message','');
  } catch (error) { $('#mood-description').textContent = 'Не удалось загрузить настроения'; message('#roulette-message',errorText(error),true); }
}
async function spin() {
  if (state.spinning) return;
  state.spinning = true; renderMoods(); $('#spin').textContent = 'Выбираем твоё кино…'; $('#spin').classList.add('busy'); message('#roulette-message','');
  const mood = state.mood; const seen = Array.isArray(history[mood]) ? history[mood] : [];
  try {
    const params = new URLSearchParams({mood, exclude:seen.join(',')}); const movie = await request(`/roulette?${params}`);
    if (seen.includes(movie.imdb_id)) { message('#roulette-message','Кажется, круг замкнулся: сервер вернул уже показанный фильм. Начни новый круг или выбери другое настроение.'); return; }
    history[mood] = [...seen,movie.imdb_id]; storage.set('kadr-history',JSON.stringify(history)); state.movie = movie;
    $('#roulette-result').replaceChildren(feature(movie)); $('#result-section').hidden = false;
    $('#result-section').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth',block:'nearest'});
    $('#spin').textContent = 'Ещё один фильм ↗';
  } catch (error) { message('#roulette-message',error.status === 404 ? 'Такое настроение недоступно. Обнови страницу и выбери другое.' : errorText(error),true); }
  finally { state.spinning = false; $('#spin').classList.remove('busy'); $('#spin').textContent = state.movie ? 'Ещё один фильм ↗' : '⤨ Крутить рулетку ↗'; renderMoods(); }
}
async function search(event) {
  event?.preventDefault(); searchController?.abort();
  const query = $('#search-query').value.trim();
  if (query.length < 2) { $('#search-results').replaceChildren(); message('#search-message','Введи хотя бы 2 символа.'); return; }
  searchController = new AbortController(); const own = searchController;
  message('#search-message','Ищем фильм…'); $('#search-results').replaceChildren();
  try {
    const movies = await request(`/movies/search?${new URLSearchParams({q:query})}`,{signal:own.signal});
    if (own.signal.aborted) return;
    $('#search-results').replaceChildren(...movies.map(card)); message('#search-message',movies.length ? `Найдено: ${movies.length}. Нажми на постер, чтобы узнать больше.` : 'Ничего не нашлось. Попробуй другое или оригинальное название.');
  } catch (error) { if (error.name !== 'AbortError') message('#search-message',errorText(error),true); }
}
function renderFavorites() {
  $('#favorites-login').hidden = hasToken(); $('#favorites-retry').hidden = !hasToken();
  $('#favorites-results').replaceChildren(...state.favorites.map(f => card(f.movie)));
  if (!hasToken()) message('#favorites-message','Войди, чтобы сохранять находки и видеть свою коллекцию с любого устройства.');
  else if (state.favoritesLoaded) message('#favorites-message',state.favorites.length ? `В твоей коллекции: ${state.favorites.length}` : 'Здесь будут любимые находки. Выбери фильм в рулетке или найди его по названию.');
}
async function loadFavorites() {
  if (!hasToken()) { renderFavorites(); return false; }
  if (favoriteLoad) return favoriteLoad;
  const generation = state.generation;
  const run = (async () => {
    message('#favorites-message','Загружаем коллекцию…');
    try { const favorites = await request('/favorites',{auth:true}); if (generation !== state.generation) return false; state.favorites = favorites; state.favoritesLoaded = true; refreshFavoritesUI(); return true; }
    catch (error) { if (generation === state.generation) message('#favorites-message',errorText(error),true); return false; }
  })();
  favoriteLoad = run;
  try { return await run; } finally { if (favoriteLoad === run) favoriteLoad = null; }
}
async function toggleFavorite(movie) {
  if (!hasToken()) { state.pendingFavorite = movie; openAuth(); return; }
  if (pendingFavorites.has(movie.imdb_id)) return;
  pendingFavorites.add(movie.imdb_id); refreshFavoritesUI();
  const generation = state.generation;
  try {
    if (!state.favoritesLoaded && !await loadFavorites()) throw new Error('Не удалось загрузить избранное. Попробуйте ещё раз.');
    if (generation !== state.generation) return;
    if (isSaved(movie.imdb_id)) {
      await request(`/favorites/${encodeURIComponent(movie.imdb_id)}`,{method:'DELETE',auth:true});
      if (generation !== state.generation) return;
      state.favorites = state.favorites.filter(f => f.movie.imdb_id !== movie.imdb_id); toast('Фильм удалён из избранного');
    } else {
      const result = await request('/favorites',{method:'POST',data:{imdb_id:movie.imdb_id},auth:true});
      if (generation !== state.generation) return;
      state.favorites.push(result); toast('Сохранено для хорошего вечера');
    }
  } catch (error) { if (generation === state.generation) toast(errorText(error)); }
  finally { pendingFavorites.delete(movie.imdb_id); refreshFavoritesUI(); }
}
function updateAccount() { $('#account-button').textContent = hasToken() ? 'Выйти ↗' : 'Войти ↗'; $('#account-email').hidden = !state.user; $('#account-email').textContent = state.user?.email || ''; refreshFavoritesUI(); }
function logout() { state.generation++; setToken(''); state.user = null; state.favorites = []; state.favoritesLoaded = false; state.pendingFavorite = null; favoriteLoad = null; updateAccount(); }
function authLabels() {
  const register = state.authMode === 'register'; $('#auth-title').textContent = register ? 'Твоё место в кадре.' : 'С возвращением.';
  $('#auth-subtitle').textContent = register ? 'Создай аккаунт для своей коллекции кино.' : 'Войди, чтобы собрать свою коллекцию фильмов.';
  $('#auth-submit').textContent = register ? 'Создать аккаунт ↗' : 'Войти ↗'; $('#auth-switch').textContent = register ? 'Уже есть аккаунт? Войти' : 'Нет аккаунта? Зарегистрироваться';
  $('#password').minLength = register ? 8 : 1; $('#password').autocomplete = register ? 'new-password' : 'current-password'; $('#password-hint').hidden = !register; message('#auth-error','');
}
function openAuth(text = '') { state.authMode = 'login'; authLabels(); if (!$('#auth-dialog').open) $('#auth-dialog').showModal(); if (text) message('#auth-error',text,true); }
async function authenticate(event) {
  event.preventDefault(); if (state.authBusy) return;
  state.authBusy = true; $('#auth-submit').disabled = true; $('#auth-switch').disabled = true; message('#auth-error','');
  const email = $('#email').value.trim(); const password = $('#password').value; const generation = state.generation;
  try {
    if (state.authMode === 'register') { await request('/auth/register',{method:'POST',data:{email,password}}); state.authMode = 'login'; authLabels(); toast('Аккаунт создан. Выполняем вход…'); }
    const result = await request('/auth/login',{method:'POST',data:{username:email,password},form:true});
    if (generation !== state.generation) return;
    setToken(result.access_token); state.user = await request('/users/me',{auth:true});
    updateAccount(); $('#auth-dialog').close(); $('#password').value = ''; toast('Ты в кадре. Хорошего вечера!');
    await loadFavorites(); const pending = state.pendingFavorite; state.pendingFavorite = null;
    if (pending && hasToken() && !isSaved(pending.imdb_id)) await toggleFavorite(pending);
  } catch (error) {
    if (hasToken()) { state.user = null; updateAccount(); }
    message('#auth-error',error.status === 401 ? 'Неверная почта или пароль.' : error.status === 409 ? 'Эта почта уже зарегистрирована. Попробуй войти.' : errorText(error),true);
  } finally { state.authBusy = false; $('#auth-submit').disabled = false; $('#auth-switch').disabled = false; }
}
function route() {
  const view = currentView(); $$('.view').forEach(e => { e.hidden = e.id !== `${view}-view`; });
  $$('[data-nav]').forEach(e => { const active = e.dataset.nav === view; e.classList.toggle('active',active); active ? e.setAttribute('aria-current','page') : e.removeAttribute('aria-current'); });
  if (view === 'favorites') { renderFavorites(); loadFavorites(); }
  if (location.hash === '#mood-picker') $('#mood-picker').scrollIntoView({block:'start'});
}
async function checkHealth() {
  $('#check-health').disabled = true;
  try { await request('/health'); $('#connection').hidden = true; if (!state.moods.length) await loadMoods(); }
  catch { $('#connection').hidden = false; }
  finally { $('#check-health').disabled = false; }
}
$('#spin').onclick = spin;
$('#reset-history').onclick = () => { history[state.mood] = []; storage.set('kadr-history',JSON.stringify(history)); message('#roulette-message','Новый круг: фильмы снова могут повторяться.'); renderMoods(); };
$('#search-form').onsubmit = search;
$('#search-query').oninput = () => { searchController?.abort(); $('#search-results').replaceChildren(); message('#search-message','Нажми «Найти», чтобы выполнить поиск.'); };
$('#favorites-login').onclick = () => openAuth(); $('#favorites-retry').onclick = loadFavorites;
$('#account-button').onclick = () => { if (hasToken()) { logout(); toast('Ты вышел из аккаунта'); } else openAuth(); };
$('#auth-switch').onclick = () => { state.authMode = state.authMode === 'login' ? 'register' : 'login'; authLabels(); };
$('#auth-form').onsubmit = authenticate;
$('#show-password').onclick = () => { const show = $('#password').type === 'password'; $('#password').type = show ? 'text' : 'password'; $('#show-password').textContent = show ? 'Скрыть' : 'Показать'; $('#show-password').setAttribute('aria-label',show ? 'Скрыть пароль' : 'Показать пароль'); $('#show-password').setAttribute('aria-pressed',String(show)); };
$$('[data-close]').forEach(button => { button.onclick = () => { const dialog = document.getElementById(button.dataset.close); if (dialog.id === 'auth-dialog' && state.authBusy) return; dialog.close(); }; });
$('#auth-dialog').addEventListener('cancel',event => { if (state.authBusy) event.preventDefault(); });
$('#auth-dialog').addEventListener('close',() => { $('#password').value = ''; $('#password').type = 'password'; $('#show-password').textContent = 'Показать'; $('#show-password').setAttribute('aria-pressed','false'); $('#show-password').setAttribute('aria-label','Показать пароль'); if (!hasToken()) state.pendingFavorite = null; });
$('#movie-dialog').addEventListener('close',() => detailController?.abort());
$('#check-health').onclick = checkHealth;
window.addEventListener('hashchange',route);
window.addEventListener('auth-expired',() => { logout(); if ($('#movie-dialog').open) $('#movie-dialog').close(); openAuth('Сессия закончилась. Войди ещё раз.'); });
window.addEventListener('online',checkHealth);
route(); updateAccount(); loadMoods(); checkHealth();
if (hasToken()) {
  const generation = state.generation;
  request('/users/me',{auth:true}).then(user => { if (generation === state.generation) { state.user = user; updateAccount(); loadFavorites(); } }).catch(error => { if (error.status !== 401) toast(errorText(error)); });
}
