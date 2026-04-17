from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
import database, models

from routers import auth_router, dashboard, clientes, proyectos, actividades, usuarios

app = FastAPI(title="Sigma Proyectos")
app.add_middleware(SessionMiddleware, secret_key="sigma-session-key-2026")

models.Base.metadata.create_all(bind=database.engine)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(auth_router.router)
app.include_router(dashboard.router)
app.include_router(clientes.router)
app.include_router(proyectos.router)
app.include_router(actividades.router)
app.include_router(usuarios.router)


@app.get("/")
async def root():
    from fastapi.responses import RedirectResponse
    return RedirectResponse("/dashboard", status_code=302)
