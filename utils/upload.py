"""Utilidades para guardar archivos subidos."""
import os, uuid
from fastapi import UploadFile

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/tmp/uploads")
TIPOS_ETIQUETA = {
    "propuesta": "Propuesta",
    "orden_compra": "Orden de Compra",
    "contrato": "Contrato",
    "otro": "Documento",
}


async def guardar_archivo(archivo: UploadFile) -> str:
    """Guarda el archivo en UPLOAD_DIR y devuelve el nombre almacenado (UUID + extensión)."""
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = ""
    if archivo.filename:
        _, ext = os.path.splitext(archivo.filename)
        ext = ext.lower()
    nombre = f"{uuid.uuid4().hex}{ext}"
    ruta = os.path.join(UPLOAD_DIR, nombre)
    contents = await archivo.read()
    with open(ruta, "wb") as f:
        f.write(contents)
    return nombre


def eliminar_archivo(nombre_archivo: str) -> None:
    """Elimina un archivo del disco si existe."""
    ruta = os.path.join(UPLOAD_DIR, nombre_archivo)
    if os.path.exists(ruta):
        os.remove(ruta)
