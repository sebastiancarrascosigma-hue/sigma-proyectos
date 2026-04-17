"""
Ejecutar UNA SOLA VEZ en producción para crear el usuario administrador.
  python crear_admin.py
"""
import os, sys
from database import SessionLocal, engine
import models
from auth import hash_password

models.Base.metadata.create_all(bind=engine)
db = SessionLocal()

email    = input("Email del admin (ej: admin@sigmaenergia.cl): ").strip()
nombre   = input("Nombre completo: ").strip()
password = input("Contraseña: ").strip()

existe = db.query(models.Usuario).filter(models.Usuario.email == email).first()
if existe:
    print(f"El usuario {email} ya existe.")
    sys.exit(0)

admin = models.Usuario(
    nombre=nombre,
    email=email,
    password_hash=hash_password(password),
    rol="admin",
    activo=True,
)
db.add(admin)
db.commit()
print(f"\nAdministrador '{nombre}' creado exitosamente.")
print("Ahora puedes crear el resto de los usuarios desde el panel /usuarios")
