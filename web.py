"""FastAPI integration: bounded requests, operator access, and local templates."""
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape

from core import Problem, Settings, Store

TEMPLATES = Environment(loader=FileSystemLoader(Path(__file__).parent / 'templates'), autoescape=select_autoescape())


def create_base(title, settings=None, mailer=None, private=False):
    settings = settings or Settings.from_env()
    app = FastAPI(title=title, version='1.0.0')
    app.state.settings = settings
    app.state.store = Store(settings, mailer)

    @app.exception_handler(Problem)
    async def problem_handler(request, error):
        headers = {'WWW-Authenticate': 'Basic realm="Operator"'} if error.status == 401 else {}
        return JSONResponse({'detail': str(error)}, status_code=error.status, headers=headers)

    @app.middleware('http')
    async def limits_and_headers(request: Request, call_next):
        try:
            if private and request.url.path != '/health':
                settings.authorize(request.headers.get('authorization', ''))
            if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
                settings.check_origin(request.headers.get('origin'))
                if request.headers.get('sec-fetch-site') == 'cross-site':
                    raise Problem('Cross-site form submissions are not accepted.', 403)
                parts, size = [], 0
                async for chunk in request.stream():
                    size += len(chunk)
                    if size > 5 * 1024 * 1024:
                        raise Problem('Request exceeds the 5 MiB limit.', 413)
                    parts.append(chunk)
                request._body = b''.join(parts)
            response = await call_next(request)
        except Problem as error:
            response = await problem_handler(request, error)
        response.headers.update({'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer', 'X-Frame-Options': 'DENY'})
        return response

    @app.get('/health', include_in_schema=False)
    def health():
        return {'status': 'ok'}

    @app.get('/admin', include_in_schema=False, response_class=HTMLResponse)
    def admin(request: Request):
        settings.authorize(request.headers.get('authorization', ''))
        return TEMPLATES.get_template('admin.html').render(title=title, records=app.state.store.records())

    @app.get('/', include_in_schema=False, response_class=HTMLResponse)
    def home():
        return TEMPLATES.get_template('index.html').render(title=title)

    return app


def client_identity(request):
    # Ignore forwarded IP headers: there is no trusted-proxy configuration in this demo.
    return request.client.host if request.client else 'shared-client'
