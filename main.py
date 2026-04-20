import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
import database, models

from routers import auth_router, dashboard, clientes, proyectos, actividades, usuarios, correspondencia, minutas

app = FastAPI(title="Sigma Proyectos", debug=True)
app.add_middleware(SessionMiddleware, secret_key="sigma-session-key-2026")

models.Base.metadata.create_all(bind=database.engine)

app.mount("/static", StaticFiles(directory="static"), name="static")

# Directorio de archivos subidos (persistente en HF Spaces si UPLOAD_DIR=/data/uploads)
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/tmp/uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
try:
    app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
except Exception as _e:
    print(f"[warn] No se pudo montar /uploads: {_e}")

app.include_router(auth_router.router)
app.include_router(dashboard.router)
app.include_router(clientes.router)
app.include_router(proyectos.router)
app.include_router(actividades.router)
app.include_router(usuarios.router)
app.include_router(correspondencia.router)
app.include_router(minutas.router)


@app.get("/")
async def root():
    from fastapi.responses import RedirectResponse
    return RedirectResponse("/dashboard", status_code=302)
