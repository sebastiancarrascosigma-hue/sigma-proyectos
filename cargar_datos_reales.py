"""
Carga clientes reales y cuentas de equipo en Supabase.
Ejecutar una sola vez: python cargar_datos_reales.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://postgres.burpgfobhpszpvagcvjg:Sigma20026..%40@aws-1-sa-east-1.pooler.supabase.com:5432/postgres"
)

from database import SessionLocal, engine
import models
from auth import hash_password

models.Base.metadata.create_all(bind=engine)
db = SessionLocal()

# ── Clientes ──────────────────────────────────────────────────────────────────
clientes_data = [
    ("KDM",                  "Pablo Bustos",          "pbustos@kdmenergia.cl"),
    ("MASISA",               "Marcelo Carrion",        "marcelo.carrion@masisa.com"),
    ("CMP",                  "Daniel Bolbaran",        "dbolbaran@cmp.cl"),
    ("ENESA",                "José Miguel Grandon",    "jgrandon@enesa.cl"),
    ("GNL",                  "Daniel Fuentes",         "daniel.fuentes@gnlm.cl"),
    ("INERSA",               "Rodrigo Leiva",          "rodrigo.leiva@inersa.com"),
    ("PETROQUIM",            "Sergio Reyes",           "sreyes@petroquim.cl"),
    ("MINERA VALLE CENTRAL", "Victor Reyes",           "victor.reyes@mineravallecentral.cl"),
    ("ESPINOS",              "Vladimir Bonacic",       "vladimir.bonacic@potenciachile.cl"),
    ("MOLYCOP",              "Bernardo Campos",        "bernardo.campos@molycop.cl"),
    ("ANTUCOYA",             "Thamara Brown Gomila",   "tbrown@antucoya.cl"),
    ("SAESA",                "Hernan Castillo",        "hernan.castillo@saesa.cl"),
    ("AGUAS CAP",            "Pablo Lorca",            "plorcab@aguascap.cl"),
    ("COMASA",               "Hector Saavedra",        "hsaavedra@comasageneracion.cl"),
    ("FPC TISSUE",           "Victor Flores",          "vflores@fpc.cl"),
    ("PRIME ENERGÍA",        "Francisco Leiva",        "francisco.leiva@enfragen.com"),
    ("INDURA S.A.",          "Andrea Tornera",         "torneraf@airproducts.com"),
    ("GUANACO",              "Hector Alvarez",         "hector.alvarez@australgold.com"),
    ("ATLAS RENEWABLE E.",   "Sebastian Araneda",      "saraneda@atlasren.com"),
    ("SIERRA GORDA",         "Jorge Saavedra",         "jorge.saavedra@sgscm.cl"),
    ("INNERGEX",             "Patricio Grandon",       "pgrandon@innergex.com"),
    ("ENAEX",                "Eudomar Zabala",         "eudomar.zabala@enaex.com"),
]

insertados = 0
omitidos = 0
for nombre, contacto, email in clientes_data:
    existe = db.query(models.Cliente).filter(models.Cliente.nombre == nombre).first()
    if existe:
        omitidos += 1
        continue
    db.add(models.Cliente(
        nombre=nombre,
        contacto_nombre=contacto,
        contacto_email=email,
        activo=True,
    ))
    insertados += 1

db.commit()
print(f"Clientes insertados: {insertados} | Omitidos (ya existían): {omitidos}")

# ── Usuarios del equipo ───────────────────────────────────────────────────────
PASSWORD_DEFAULT = "Sigma2026"

equipo = [
    ("Sebastián Carrasco", "sebastian.carrasco@sigmaenergia.cl", "admin"),
    ("Erwin Monsalve",     "erwin.monsalve@sigmaenergia.cl",     "usuario"),
    ("Gonzalo Lizama",     "gonzalo.lizama@sigmaenergia.cl",     "usuario"),
    ("Nicolás Ebner",      "nicolas.ebner@sigmaenergia.cl",      "usuario"),
    ("Braulio Villa",      "braulio.villa@sigmaenergia.cl",      "usuario"),
    ("Alex Hernández",     "alex.hernandez@sigmaenergia.cl",     "usuario"),
]

u_insertados = 0
u_omitidos = 0
for nombre, email, rol in equipo:
    existe = db.query(models.Usuario).filter(models.Usuario.email == email).first()
    if existe:
        u_omitidos += 1
        continue
    db.add(models.Usuario(
        nombre=nombre,
        email=email,
        password_hash=hash_password(PASSWORD_DEFAULT),
        rol=rol,
        activo=True,
    ))
    u_insertados += 1

db.commit()
db.close()

print(f"Usuarios insertados: {u_insertados} | Omitidos (ya existían): {u_omitidos}")
print(f"\nContraseña inicial de todos: {PASSWORD_DEFAULT}")
print("Recuerda pedirle a cada uno que la cambie en su primer ingreso.")
