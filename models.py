from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey, Date
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime


class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    rol = Column(String(20), default="usuario")  # admin / usuario
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    proyectos_responsable = relationship("Proyecto", back_populates="responsable", foreign_keys="Proyecto.responsable_id")
    actividades_asignadas = relationship("Actividad", back_populates="responsable_usuario", foreign_keys="Actividad.responsable_usuario_id")
    comentarios = relationship("Comentario", back_populates="usuario")


class Cliente(Base):
    __tablename__ = "clientes"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(200), nullable=False)
    rut = Column(String(20), nullable=True)
    contacto_nombre = Column(String(100))
    contacto_email = Column(String(150))
    contacto_telefono = Column(String(30))
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    proyectos = relationship("Proyecto", back_populates="cliente")
    cuentas   = relationship("CuentaCliente", back_populates="cliente", cascade="all, delete-orphan", order_by="CuentaCliente.nombre_sistema")
    minutas   = relationship("Minuta", back_populates="cliente", order_by="Minuta.fecha.desc()")


class CuentaCliente(Base):
    __tablename__ = "cuentas_cliente"
    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    nombre_sistema = Column(String(200), nullable=False)   # Ej: "Portal CEN", "SAP", "SEC en línea"
    url = Column(String(500), nullable=True)
    usuario = Column(String(200), nullable=False)
    password = Column(String(500), nullable=False)          # Almacenado en texto (credenciales de terceros)
    notas = Column(Text, nullable=True)
    activo = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("usuarios.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    cliente = relationship("Cliente", back_populates="cuentas")


class Proyecto(Base):
    __tablename__ = "proyectos"
    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(50), unique=True, nullable=False)
    nombre = Column(String(300), nullable=False)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    tipo_proyecto = Column(String(50), nullable=False)
    descripcion = Column(Text)
    orden_compra = Column(String(100))
    valor_contrato = Column(Float)
    fecha_inicio = Column(DateTime, nullable=False)
    fecha_estimada_cierre = Column(DateTime)
    fecha_cierre_real = Column(DateTime)
    estado = Column(String(30), default="Activo")  # Activo / En Espera / Completado / Cancelado
    responsable_id = Column(Integer, ForeignKey("usuarios.id"))
    created_by = Column(Integer, ForeignKey("usuarios.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    cliente = relationship("Cliente", back_populates="proyectos")
    responsable = relationship("Usuario", back_populates="proyectos_responsable", foreign_keys=[responsable_id])
    actividades = relationship("Actividad", back_populates="proyecto", cascade="all, delete-orphan", order_by="Actividad.fecha_limite")
    comentarios = relationship("Comentario", back_populates="proyecto", cascade="all, delete-orphan", order_by="Comentario.created_at.desc()")
    documentos  = relationship("Documento",  back_populates="proyecto", cascade="all, delete-orphan", order_by="Documento.created_at.desc()")


class Actividad(Base):
    __tablename__ = "actividades"
    id = Column(Integer, primary_key=True, index=True)
    proyecto_id = Column(Integer, ForeignKey("proyectos.id"), nullable=False)
    titulo = Column(String(300), nullable=False)
    descripcion = Column(Text)
    tipo = Column(String(30), default="Tarea")           # Tarea / Hito / Entregable / Reunión / Revisión
    responsable_tipo = Column(String(20), default="Sigma")  # Sigma / Cliente
    responsable_usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    responsable_cliente_nombre = Column(String(100), nullable=True)
    estado = Column(String(30), default="Pendiente")     # Pendiente / En Progreso / Completado / Atrasado / Cancelado
    prioridad = Column(String(20), default="Media")      # Baja / Media / Alta / Crítica
    fecha_limite = Column(DateTime, nullable=True)
    fecha_completado = Column(DateTime, nullable=True)
    created_by = Column(Integer, ForeignKey("usuarios.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    proyecto = relationship("Proyecto", back_populates="actividades")
    responsable_usuario = relationship("Usuario", back_populates="actividades_asignadas", foreign_keys=[responsable_usuario_id])
    comentarios = relationship("Comentario", back_populates="actividad")
    subtareas = relationship("SubActividad", back_populates="actividad",
                             cascade="all, delete-orphan", order_by="SubActividad.created_at")


class SubActividad(Base):
    __tablename__ = "subactividades"
    id           = Column(Integer, primary_key=True, index=True)
    actividad_id = Column(Integer, ForeignKey("actividades.id", ondelete="CASCADE"), nullable=False)
    texto        = Column(String(500), nullable=False)
    completado   = Column(Boolean, default=False)
    created_by   = Column(Integer, ForeignKey("usuarios.id"))
    created_at   = Column(DateTime, default=datetime.utcnow)

    actividad = relationship("Actividad", back_populates="subtareas")
    creador   = relationship("Usuario", foreign_keys=[created_by])


class Minuta(Base):
    __tablename__ = "minutas"
    id             = Column(Integer, primary_key=True, index=True)
    cliente_id     = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    titulo         = Column(String(300), nullable=False)
    fecha          = Column(DateTime, nullable=False)
    resumen        = Column(Text)
    email_enviado         = Column(Boolean, default=False)
    notificacion_enviada  = Column(Boolean, default=False)
    created_by            = Column(Integer, ForeignKey("usuarios.id"))
    created_at     = Column(DateTime, default=datetime.utcnow)
    updated_at     = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    cliente       = relationship("Cliente", back_populates="minutas")
    creador       = relationship("Usuario", foreign_keys=[created_by])
    temas         = relationship("MinutaTema", back_populates="minuta",
                                 cascade="all, delete-orphan", order_by="MinutaTema.id")
    participantes = relationship("MinutaParticipante", back_populates="minuta",
                                 cascade="all, delete-orphan", order_by="MinutaParticipante.id")


class MinutaParticipante(Base):
    __tablename__ = "minuta_participantes"
    id        = Column(Integer, primary_key=True, index=True)
    minuta_id = Column(Integer, ForeignKey("minutas.id"), nullable=False)
    nombre    = Column(String(150), nullable=False)
    email     = Column(String(150))
    empresa   = Column(String(150))

    minuta = relationship("Minuta", back_populates="participantes")


class MinutaTema(Base):
    __tablename__ = "minuta_temas"
    id          = Column(Integer, primary_key=True, index=True)
    minuta_id   = Column(Integer, ForeignKey("minutas.id"), nullable=False)
    proyecto_id = Column(Integer, ForeignKey("proyectos.id"), nullable=False)
    lo_tratado  = Column(Text, nullable=False)
    acuerdos    = Column(Text)
    responsable_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    fecha_estimada_respuesta = Column(Date, nullable=True)

    minuta      = relationship("Minuta", back_populates="temas")
    proyecto    = relationship("Proyecto")
    responsable = relationship("Usuario", foreign_keys=[responsable_id])


class Correspondencia(Base):
    __tablename__ = "correspondencia"
    id           = Column(Integer, primary_key=True, index=True)
    correlativo  = Column(String(60), unique=True, nullable=False, index=True)
    fecha        = Column(Date, nullable=True, index=True)
    empresas     = Column(Text)
    remitente    = Column(Text)
    destinatario = Column(Text)
    materia_macro = Column(String(300))
    materia_micro = Column(Text)
    referencia   = Column(Text)
    respondida   = Column(String(20))
    estado       = Column(String(100))
    pdf_url      = Column(String(500), nullable=True)   # URL pública (Supabase Storage u otro)
    created_at   = Column(DateTime, default=datetime.utcnow)
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Comentario(Base):
    __tablename__ = "comentarios"
    id = Column(Integer, primary_key=True, index=True)
    proyecto_id = Column(Integer, ForeignKey("proyectos.id"), nullable=False)
    actividad_id = Column(Integer, ForeignKey("actividades.id"), nullable=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    minuta_id = Column(Integer, ForeignKey("minutas.id", ondelete="SET NULL"), nullable=True)
    texto = Column(Text, nullable=False)
    tipo_registro = Column(String(30), default="comentario")  # comentario / cambio_estado / sistema
    created_at = Column(DateTime, default=datetime.utcnow)

    proyecto = relationship("Proyecto", back_populates="comentarios")
    actividad = relationship("Actividad", back_populates="comentarios")
    usuario = relationship("Usuario", back_populates="comentarios")
    documentos = relationship("Documento", back_populates="comentario")


class Documento(Base):
    __tablename__ = "documentos"
    id = Column(Integer, primary_key=True, index=True)
    proyecto_id = Column(Integer, ForeignKey("proyectos.id", ondelete="CASCADE"), nullable=False)
    comentario_id = Column(Integer, ForeignKey("comentarios.id", ondelete="SET NULL"), nullable=True)
    nombre_original = Column(String(300), nullable=False)
    nombre_archivo = Column(String(300), nullable=False)   # UUID-based stored filename
    tipo = Column(String(30), default="otro")              # propuesta / orden_compra / contrato / otro
    uploaded_by = Column(Integer, ForeignKey("usuarios.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    proyecto = relationship("Proyecto", back_populates="documentos")
    comentario = relationship("Comentario", back_populates="documentos",
                              foreign_keys=[comentario_id])
    uploader = relationship("Usuario", foreign_keys=[uploaded_by])
