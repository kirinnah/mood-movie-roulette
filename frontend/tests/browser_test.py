"""Contract-level browser tests. Run against the static server, no real accounts/API key needed."""
import json
import os
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright, expect

BASE = os.environ.get('FRONTEND_URL', 'http://localhost:4173')
ARTIFACTS = Path(__file__).parent / 'artifacts'
ARTIFACTS.mkdir(exist_ok=True)
MOODS = ['happy','sad','cozy','adventure','scary','thoughtful','romantic']
MOVIE = dict(imdb_id='tt0133093', title='The Matrix', year=1999, rating=8.7,
             poster_url=None, description='Хакер Нео узнаёт, что привычный мир — лишь иллюзия.',
             genres=['Action','Sci-Fi'], actors=['Keanu Reeves','Carrie-Anne Moss'])
NULL_MOVIE = dict(MOVIE, imdb_id='tt0111161', title='<img src=x onerror=alert(1)>',
                  year=None, rating=None, description=None, genres=[], actors=[], poster_url='https://invalid.test/poster.jpg')

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width':1440,'height':1050}, reduced_motion='reduce')
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    calls = []
    state = {'favorites':[], 'spin_error':0, 'health':200, 'expire':False, 'register_error':0, 'login_error':False, 'search_error':0}
    def api(route):
        req = route.request
        parsed = urlparse(req.url)
        path = parsed.path.replace('/api/v1','')
        query = parse_qs(parsed.query)
        calls.append((path,req.method,query,req.post_data,req.headers))
        status, data = 200, {}
        if req.method == 'OPTIONS':
            route.fulfill(status=204, headers={'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'*','Access-Control-Allow-Methods':'*'})
            return
        if path == '/health': status, data = state['health'], {'status':'ok'}
        elif path == '/moods': data = [{'key':m} for m in MOODS]
        elif path == '/roulette':
            if state['spin_error']: status, data = state['spin_error'], {'detail':'Upstream failure'}
            else: data = MOVIE
        elif path == '/movies/search':
            if state['search_error']: status,data = state['search_error'], {'detail':[{'loc':['query','q'],'msg':'Invalid query'}]}
            else: data = [] if query['q'][0] == 'nothing' else [MOVIE,NULL_MOVIE]
        elif path.startswith('/movies/'): data = NULL_MOVIE if path.endswith('tt0111161') else MOVIE
        elif path == '/auth/register': status,data = (state['register_error'],{'detail':'Conflict'}) if state['register_error'] else (201,{'id':1,'email':'test@example.com','created_at':'2026-11-02'})
        elif path == '/auth/login':
            assert req.headers['content-type'] == 'application/x-www-form-urlencoded'
            assert parse_qs(req.post_data)['username'] == ['test@example.com']
            status,data = (401,{'detail':'Invalid credentials'}) if state['login_error'] else (200,{'access_token':'test-token','token_type':'bearer'})
        elif path == '/users/me': data = {'id':1,'email':'test@example.com'}
        elif path.startswith('/favorites'):
            assert req.headers.get('authorization') == 'Bearer test-token'
            if state['expire']: status,data = 401,{'detail':'Expired'}
            elif req.method == 'POST':
                movie = MOVIE if json.loads(req.post_data)['imdb_id'] == MOVIE['imdb_id'] else NULL_MOVIE
                data = {'created_at':'2026-11-02','movie':movie}
                status = 200 if any(f['movie']['imdb_id']==movie['imdb_id'] for f in state['favorites']) else 201
                if status == 201: state['favorites'].append(data)
            elif req.method == 'DELETE':
                state['favorites'] = [f for f in state['favorites'] if f['movie']['imdb_id'] != path.split('/')[-1]]
                status,data = 204,None
            else: data = state['favorites']
        else: raise AssertionError(path)
        route.fulfill(status=status,content_type='application/json',body='' if status==204 else json.dumps(data),headers={'Access-Control-Allow-Origin':'*'})
    page.route('http://localhost:8000/**',api)
    page.route('https://invalid.test/**',lambda route: route.abort())
    page.goto(BASE)
    expect(page.locator('.mood')).to_have_count(7)
    expect(page.locator('#connection')).to_be_hidden()
    page.screenshot(path=str(ARTIFACTS/'desktop.png'),full_page=True)
    page.locator('#spin').click()
    expect(page.locator('#roulette-result h3')).to_have_text('The Matrix')
    page.locator('#spin').click()
    expect(page.locator('#roulette-message')).to_contain_text('круг замкнулся')
    assert [c for c in calls if c[0]=='/roulette'][-1][2]['exclude'] == ['tt0133093']
    page.locator('#reset-history').click()
    state['spin_error'] = 502
    page.locator('#spin').click()
    expect(page.locator('#roulette-message')).to_contain_text('Попробуйте ещё раз')
    state['spin_error'] = 404
    page.locator('#spin').click()
    expect(page.locator('#roulette-message')).to_contain_text('настроение недоступно')
    state['spin_error'] = 0
    page.locator('[data-nav="search"]').click()
    page.locator('#search-query').fill('matrix')
    page.locator('#search-form button').click()
    expect(page.locator('.movie-card')).to_have_count(2)
    assert page.locator('#search-results img').count() == 2 # API markup must remain plain text
    page.locator('.poster-button').nth(1).click()
    expect(page.locator('#movie-detail')).to_contain_text('Год не указан')
    expect(page.locator('#movie-detail')).to_contain_text('Описание пока недоступно')
    expect(page.locator('#movie-detail img')).to_have_attribute('src','assets/poster-placeholder.svg')
    page.keyboard.press('Escape')
    expect(page.locator('#movie-dialog')).not_to_be_visible()
    page.locator('#search-results .favorite-button').first.click()
    expect(page.locator('#auth-dialog')).to_be_visible()
    page.locator('#auth-switch').click()
    page.locator('#email').fill('test@example.com')
    page.locator('#password').fill('password123')
    state['register_error'] = 409
    page.locator('#auth-submit').click()
    expect(page.locator('#auth-error')).to_contain_text('уже зарегистрирована')
    state['register_error'] = 422
    page.locator('#auth-submit').click()
    expect(page.locator('#auth-error')).to_be_visible()
    state['register_error'] = 0
    page.locator('#auth-submit').click()
    expect(page.locator('#auth-dialog')).not_to_be_visible()
    expect(page.locator('#search-results .favorite-button').first).to_have_attribute('aria-pressed','true')
    page.locator('[data-nav="favorites"]').click()
    expect(page.locator('#favorites-results .movie-card')).to_have_count(1)
    page.locator('#favorites-results .favorite-button').click()
    expect(page.locator('#favorites-results .movie-card')).to_have_count(0)
    expect(page.locator('#favorites-message')).to_contain_text('Здесь будут')
    state['expire'] = True
    page.locator('#favorites-retry').click()
    expect(page.locator('#auth-dialog')).to_be_visible()
    expect(page.locator('#auth-error')).to_contain_text('Сессия закончилась')
    assert page.evaluate("sessionStorage.getItem('kadr-token')") is None
    state['expire'] = False
    state['login_error'] = True
    page.locator('#password').fill('password123')
    page.locator('#auth-submit').click()
    expect(page.locator('#auth-error')).to_contain_text('Неверная почта')
    page.keyboard.press('Escape')
    state['health'] = 503
    page.reload()
    expect(page.locator('#connection')).to_be_visible()
    state['health'] = 200
    page.locator('#check-health').click()
    expect(page.locator('#connection')).to_be_hidden()
    page.locator('[data-nav="search"]').click()
    page.locator('#search-query').fill('nothing')
    page.locator('#search-form button').click()
    expect(page.locator('#search-message')).to_contain_text('Ничего не нашлось')
    state['search_error'] = 422
    page.locator('#search-query').fill('test')
    page.locator('#search-form button').click()
    expect(page.locator('#search-message')).to_contain_text('q: Invalid query')
    page.locator('[data-nav="roulette"]').click()
    expect(page.locator('#roulette-view')).to_be_visible()
    for width in [390,320,768]:
        page.set_viewport_size({'width':width,'height':844})
        page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), f'Overflow at {width}'
        if width == 390: page.screenshot(path=str(ARTIFACTS/'mobile.png'),full_page=True)
    assert not errors, errors
    browser.close()
    print('PASS: moods, roulette/exclude/reset, 404/502, search, null fields, safe text, broken poster, dialogs, register 409/422, form login, Bearer auth, favorites POST/DELETE 204, session 401, health 503/retry, responsive 320/390/768, no JS exceptions.')
