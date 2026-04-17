"""
Carga datos de demostración para presentación a la dirección.
Ejecutar una sola vez: python seed_data.py
"""
from database import SessionLocal, engine
import models
from auth import hash_password
from datetime import datetime, timedelta

models.Base.metadata.create_all(bind=engine)
db = SessionLocal()

# ── Usuarios ──────────────────────────────────────────────
usuarios_data = [
    {"nombre": "Sebastián Carrasco", "email": "sebastian.carrasco@sigmaenergia.cl", "password": "sigma123", "rol": "admin"},
    {"nombre": "María González",     "email": "maria.gonzalez@sigmaenergia.cl",     "password": "sigma123", "rol": "usuario"},
    {"nombre": "Carlos Silva",       "email": "carlos.silva@sigmaenergia.cl",       "password": "sigma123", "rol": "usuario"},
    {"nombre": "Admin Sistema",      "email": "admin@sigmaenergia.cl",              "password": "admin123", "rol": "admin"},
]
usuarios = {}
for u in usuarios_data:
    existing = db.query(models.Usuario).filter(models.Usuario.email == u["email"]).first()
    if not existing:
        obj = models.Usuario(nombre=u["nombre"], email=u["email"],
                             password_hash=hash_password(u["password"]), rol=u["rol"])
        db.add(obj)
        db.flush()
        usuarios[u["email"]] = obj
    else:
        usuarios[u["email"]] = existing
db.commit()
print("✓ Usuarios creados")

seba   = usuarios["sebastian.carrasco@sigmaenergia.cl"]
maria  = usuarios["maria.gonzalez@sigmaenergia.cl"]
carlos = usuarios["carlos.silva@sigmaenergia.cl"]

# ── Clientes ──────────────────────────────────────────────
clientes_data = [
    {"nombre": "Atlas Power SpA",               "rut": "76.543.210-K", "contacto_nombre": "Juan Muñoz",         "contacto_email": "jmunoz@atlaspower.cl",   "contacto_telefono": "+56 9 9123 4567"},
    {"nombre": "Minera Antucoya",               "rut": "76.234.567-2", "contacto_nombre": "Alejandro Vera",     "contacto_email": "avera@antucoya.cl",      "contacto_telefono": "+56 9 8765 4321"},
    {"nombre": "ENAEX S.A.",                    "rut": "91.505.000-4", "contacto_nombre": "María Fernández",    "contacto_email": "mfernandez@enaex.cl",    "contacto_telefono": "+56 2 2345 6789"},
    {"nombre": "CMP - Cía. Minera del Pacífico","rut": "91.081.000-6", "contacto_nombre": "Rodrigo Torres",    "contacto_email": "rtorres@cmp.cl",         "contacto_telefono": "+56 9 7654 3210"},
    {"nombre": "KDM Energía S.A.",              "rut": "76.890.123-5", "contacto_nombre": "Patricia Soto",     "contacto_email": "psoto@kdm.cl",           "contacto_telefono": "+56 9 6543 2109"},
]
clientes = {}
for c in clientes_data:
    existing = db.query(models.Cliente).filter(models.Cliente.nombre == c["nombre"]).first()
    if not existing:
        obj = models.Cliente(**c)
        db.add(obj)
        db.flush()
        clientes[c["nombre"]] = obj
    else:
        clientes[c["nombre"]] = existing
db.commit()
print("✓ Clientes creados")

atlas   = clientes["Atlas Power SpA"]
antucoya = clientes["Minera Antucoya"]
enaex   = clientes["ENAEX S.A."]
cmp     = clientes["CMP - Cía. Minera del Pacífico"]
kdm     = clientes["KDM Energía S.A."]

hoy = datetime.utcnow()

# ── Proyectos ─────────────────────────────────────────────
proyectos_data = [
    {
        "codigo": "SE-2026-001",
        "nombre": "Estudio de Conexión PMGD Zona Norte",
        "cliente": atlas,
        "tipo_proyecto": "Estudio",
        "orden_compra": "OC-2026-00145",
        "valor_contrato": 850.0,
        "fecha_inicio": hoy - timedelta(days=60),
        "fecha_estimada_cierre": hoy + timedelta(days=90),
        "estado": "Activo",
        "responsable": seba,
    },
    {
        "codigo": "SE-2026-002",
        "nombre": "Análisis Tarifario Regulatorio Periodo 2026–2030",
        "cliente": antucoya,
        "tipo_proyecto": "Análisis Regulatorio",
        "orden_compra": "OC-2026-00203",
        "valor_contrato": 620.0,
        "fecha_inicio": hoy - timedelta(days=30),
        "fecha_estimada_cierre": hoy + timedelta(days=60),
        "estado": "Activo",
        "responsable": maria,
    },
    {
        "codigo": "SE-2026-003",
        "nombre": "Supervisión Contrato Energía Enero–Diciembre 2026",
        "cliente": enaex,
        "tipo_proyecto": "Contrato Supervisión",
        "orden_compra": "OC-2026-00089",
        "valor_contrato": 1200.0,
        "fecha_inicio": hoy - timedelta(days=90),
        "fecha_estimada_cierre": hoy + timedelta(days=270),
        "estado": "Activo",
        "responsable": carlos,
    },
    {
        "codigo": "SE-2025-008",
        "nombre": "Auditoría Técnica Instalaciones Eléctricas BT/MT",
        "cliente": cmp,
        "tipo_proyecto": "Auditoría",
        "orden_compra": "OC-2025-00412",
        "valor_contrato": 430.0,
        "fecha_inicio": hoy - timedelta(days=45),
        "fecha_estimada_cierre": hoy + timedelta(days=30),
        "estado": "En Espera",
        "responsable": seba,
    },
    {
        "codigo": "SE-2025-011",
        "nombre": "Revisión Normativa SEC – Adecuación Reglamentaria 2025",
        "cliente": kdm,
        "tipo_proyecto": "Análisis Regulatorio",
        "orden_compra": "OC-2025-00501",
        "valor_contrato": 280.0,
        "fecha_inicio": hoy - timedelta(days=180),
        "fecha_estimada_cierre": hoy - timedelta(days=10),
        "fecha_cierre_real": hoy - timedelta(days=10),
        "estado": "Completado",
        "responsable": maria,
    },
]

proyectos = {}
for p in proyectos_data:
    existing = db.query(models.Proyecto).filter(models.Proyecto.codigo == p["codigo"]).first()
    if not existing:
        obj = models.Proyecto(
            codigo=p["codigo"],
            nombre=p["nombre"],
            cliente_id=p["cliente"].id,
            tipo_proyecto=p["tipo_proyecto"],
            orden_compra=p.get("orden_compra"),
            valor_contrato=p.get("valor_contrato"),
            fecha_inicio=p["fecha_inicio"],
            fecha_estimada_cierre=p.get("fecha_estimada_cierre"),
            fecha_cierre_real=p.get("fecha_cierre_real"),
            estado=p["estado"],
            responsable_id=p["responsable"].id,
            created_by=seba.id,
            updated_at=hoy - timedelta(days=2),
        )
        db.add(obj)
        db.flush()
        proyectos[p["codigo"]] = obj
    else:
        proyectos[p["codigo"]] = existing
db.commit()
print("✓ Proyectos creados")


def add_act(proyecto, titulo, tipo, resp_tipo, resp_usuario=None, resp_cliente=None,
            prioridad="Media", estado="Pendiente", dias_limite=30, completado=False):
    f_limite = hoy + timedelta(days=dias_limite) if dias_limite is not None else None
    f_comp = hoy - timedelta(days=abs(dias_limite)) if completado else None
    act = models.Actividad(
        proyecto_id=proyecto.id,
        titulo=titulo,
        tipo=tipo,
        responsable_tipo=resp_tipo,
        responsable_usuario_id=resp_usuario.id if resp_usuario else None,
        responsable_cliente_nombre=resp_cliente,
        prioridad=prioridad,
        estado="Completado" if completado else estado,
        fecha_limite=f_limite,
        fecha_completado=f_comp,
        created_by=seba.id,
    )
    db.add(act)
    db.flush()
    return act

# ── Actividades SE-2026-001 (Atlas Power) ──
p1 = proyectos["SE-2026-001"]
if not p1.actividades:
    add_act(p1, "Reunión de kick-off con cliente", "Reunión", "Sigma", seba, prioridad="Alta", completado=True, dias_limite=55)
    add_act(p1, "Recopilación de antecedentes técnicos", "Tarea", "Sigma", carlos, prioridad="Alta", completado=True, dias_limite=45)
    add_act(p1, "Entrega de planos y documentación de red", "Entregable", "Cliente", None, "Juan Muñoz", prioridad="Alta", completado=True, dias_limite=40)
    add_act(p1, "Modelamiento eléctrico en software", "Tarea", "Sigma", carlos, prioridad="Alta", estado="En Progreso", dias_limite=10)
    add_act(p1, "Revisión normativa técnica Coordinador", "Tarea", "Sigma", maria, prioridad="Media", dias_limite=15)
    add_act(p1, "Validación parámetros de conexión por cliente", "Entregable", "Cliente", None, "Juan Muñoz", prioridad="Alta", dias_limite=5)
    add_act(p1, "Informe técnico preliminar", "Entregable", "Sigma", seba, prioridad="Alta", dias_limite=20)
    add_act(p1, "Aprobación informe preliminar por cliente", "Hito", "Cliente", None, "Juan Muñoz", prioridad="Media", dias_limite=30)
    add_act(p1, "Informe técnico final", "Entregable", "Sigma", seba, prioridad="Crítica", dias_limite=60)
    add_act(p1, "Recepción conforme del cliente", "Hito", "Cliente", None, "Juan Muñoz", prioridad="Alta", dias_limite=75)

# ── Actividades SE-2026-002 (Antucoya) - algunas ATRASADAS ──
p2 = proyectos["SE-2026-002"]
if not p2.actividades:
    add_act(p2, "Solicitud de datos históricos de consumo", "Tarea", "Sigma", maria, prioridad="Alta", completado=True, dias_limite=25)
    add_act(p2, "Entrega de facturas 2023–2025 por cliente", "Entregable", "Cliente", None, "Alejandro Vera", prioridad="Alta", estado="En Progreso", dias_limite=-5)  # ATRASADA
    add_act(p2, "Análisis de estructura tarifaria actual", "Tarea", "Sigma", maria, prioridad="Alta", estado="Pendiente", dias_limite=-2)  # ATRASADA
    add_act(p2, "Modelamiento tarifario escenarios 2026–2030", "Tarea", "Sigma", carlos, prioridad="Media", dias_limite=20)
    add_act(p2, "Reunión de revisión de escenarios", "Reunión", "Sigma", maria, prioridad="Media", dias_limite=25)
    add_act(p2, "Informe de recomendaciones tarifarias", "Entregable", "Sigma", maria, prioridad="Alta", dias_limite=45)

# ── Actividades SE-2026-003 (ENAEX) - supervisión mensual ──
p3 = proyectos["SE-2026-003"]
if not p3.actividades:
    add_act(p3, "Informe supervisión Enero 2026", "Entregable", "Sigma", carlos, completado=True, dias_limite=60)
    add_act(p3, "Informe supervisión Febrero 2026", "Entregable", "Sigma", carlos, completado=True, dias_limite=30)
    add_act(p3, "Informe supervisión Marzo 2026", "Entregable", "Sigma", carlos, completado=True, dias_limite=10)
    add_act(p3, "Aprobación informe Marzo por cliente", "Hito", "Cliente", None, "María Fernández", prioridad="Alta", estado="En Progreso", dias_limite=-3)  # ATRASADA
    add_act(p3, "Informe supervisión Abril 2026", "Entregable", "Sigma", carlos, prioridad="Alta", dias_limite=13)
    add_act(p3, "Revisión contrato modificaciones Q2", "Revisión", "Sigma", seba, prioridad="Media", dias_limite=20)
    add_act(p3, "Informe supervisión Mayo 2026", "Entregable", "Sigma", carlos, prioridad="Media", dias_limite=44)

# ── Actividades SE-2025-008 (CMP) - En Espera ──
p4 = proyectos["SE-2025-008"]
if not p4.actividades:
    add_act(p4, "Definición del alcance de auditoría", "Reunión", "Sigma", seba, prioridad="Alta", completado=True, dias_limite=30)
    add_act(p4, "Entrega de planos eléctricos por CMP", "Entregable", "Cliente", None, "Rodrigo Torres", prioridad="Alta", estado="Pendiente", dias_limite=20)
    add_act(p4, "Inspección en terreno instalaciones BT", "Tarea", "Sigma", carlos, prioridad="Alta", dias_limite=30)
    add_act(p4, "Inspección en terreno instalaciones MT", "Tarea", "Sigma", carlos, prioridad="Alta", dias_limite=35)
    add_act(p4, "Informe de auditoría preliminar", "Entregable", "Sigma", seba, prioridad="Media", dias_limite=50)

# ── Actividades SE-2025-011 (KDM) - Completado ──
p5 = proyectos["SE-2025-011"]
if not p5.actividades:
    add_act(p5, "Recopilación normativa vigente SEC", "Tarea", "Sigma", maria, completado=True, dias_limite=120)
    add_act(p5, "Análisis de brechas normativas", "Tarea", "Sigma", maria, completado=True, dias_limite=90)
    add_act(p5, "Informe de brechas y recomendaciones", "Entregable", "Sigma", maria, completado=True, dias_limite=60)
    add_act(p5, "Validación de informe por KDM", "Hito", "Cliente", None, "Patricia Soto", completado=True, dias_limite=30)
    add_act(p5, "Informe final entregado", "Entregable", "Sigma", maria, completado=True, dias_limite=15)

db.commit()
print("✓ Actividades creadas")

# ── Bitácora inicial ──────────────────────────────────────
def add_comment(proyecto, usuario, texto, tipo="comentario"):
    db.add(models.Comentario(
        proyecto_id=proyecto.id,
        usuario_id=usuario.id,
        texto=texto,
        tipo_registro=tipo,
    ))

if not db.query(models.Comentario).filter(models.Comentario.proyecto_id == p1.id).first():
    add_comment(p1, seba,   "Proyecto iniciado. Kick-off realizado con éxito, cliente confirmó disponibilidad de planos para la semana siguiente.", "sistema")
    add_comment(p1, carlos, "Modelamiento en software iniciado. Se están ajustando los parámetros de la red de distribución con los datos entregados por el cliente.")
    add_comment(p1, seba,   "Cliente confirmó reunión de revisión para el próximo martes. Se avanza bien en los plazos.")

if not db.query(models.Comentario).filter(models.Comentario.proyecto_id == p2.id).first():
    add_comment(p2, maria,  "Proyecto iniciado. Pendiente que cliente entregue facturas históricas.", "sistema")
    add_comment(p2, maria,  "Se realizó recordatorio al cliente por las facturas. Indicaron que enviarían esta semana, pero aún no llegan. Esto está generando atraso en el análisis.")

if not db.query(models.Comentario).filter(models.Comentario.proyecto_id == p3.id).first():
    add_comment(p3, carlos, "Informes de enero, febrero y marzo entregados y aprobados.", "sistema")
    add_comment(p3, carlos, "El cliente tiene pendiente aprobar el informe de marzo. Se envió por email el 10 de abril.")

db.commit()
print("✓ Bitácora creada")

print("\n✅ Datos de demostración cargados exitosamente.")
print("\nUsuarios de acceso:")
print("  admin@sigmaenergia.cl  /  admin123  (Administrador)")
print("  sebastian.carrasco@sigmaenergia.cl  /  sigma123")
print("  maria.gonzalez@sigmaenergia.cl      /  sigma123")
print("  carlos.silva@sigmaenergia.cl        /  sigma123")
