"""Envío de minutas por email via Microsoft Graph API (Office 365)."""
import os, json, base64
import urllib.request, urllib.parse

EMAIL_SENDER        = os.getenv("EMAIL_SENDER", "")
EMAIL_PASSWORD      = os.getenv("EMAIL_PASSWORD", "")
AZURE_TENANT_ID     = os.getenv("AZURE_TENANT_ID", "")
AZURE_CLIENT_ID     = os.getenv("AZURE_CLIENT_ID", "")
AZURE_CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET", "")
APP_URL             = os.getenv("APP_URL", "https://sebas1989-sigma-proyectos.hf.space")


# ── Autenticación Graph API ────────────────────────────────────────────────────

def _obtener_token() -> str | None:
    """Obtiene access token via ROPC flow (usuario + contraseña + app credentials)."""
    if not all([AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, EMAIL_SENDER, EMAIL_PASSWORD]):
        return None
    data = urllib.parse.urlencode({
        "grant_type":    "password",
        "client_id":     AZURE_CLIENT_ID,
        "client_secret": AZURE_CLIENT_SECRET,
        "username":      EMAIL_SENDER,
        "password":      EMAIL_PASSWORD,
        "scope":         "https://graph.microsoft.com/Mail.Send offline_access",
    }).encode()
    try:
        req  = urllib.request.Request(
            f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/oauth2/v2.0/token",
            data=data, method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())["access_token"]
    except Exception as e:
        print(f"[email] Error obteniendo token: {e}")
        return None


def _enviar_graph(token: str, destinatarios: list[str], asunto: str,
                  html: str, adjuntos: list[dict] | None = None) -> tuple[bool, str]:
    """Envía un email via Graph API."""
    payload = {
        "message": {
            "subject": asunto,
            "body": {"contentType": "HTML", "content": html},
            "toRecipients": [{"emailAddress": {"address": d}} for d in destinatarios],
        },
        "saveToSentItems": True,
    }
    if adjuntos:
        payload["message"]["attachments"] = adjuntos

    data = json.dumps(payload).encode("utf-8")
    req  = urllib.request.Request(
        f"https://graph.microsoft.com/v1.0/users/{EMAIL_SENDER}/sendMail",
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status in (200, 202), ""
    except urllib.error.HTTPError as e:
        detalle = e.read().decode()[:200]
        return False, f"HTTP {e.code}: {detalle}"
    except Exception as e:
        return False, str(e)


def _credenciales_ok() -> bool:
    return all([EMAIL_SENDER, EMAIL_PASSWORD, AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET])


# ── Funciones públicas ─────────────────────────────────────────────────────────

def enviar_notificacion_interna(minuta, emails_sigma: list[str]) -> tuple[bool, str]:
    """Notifica al equipo Sigma que la minuta está lista para revisión."""
    if not _credenciales_ok():
        return False, "Credenciales de email no configuradas en los secrets de HF Spaces."
    if not emails_sigma:
        return False, "No hay usuarios Sigma con email para notificar."

    token = _obtener_token()
    if not token:
        return False, "No se pudo obtener token de autenticación."

    asunto      = f"[Para revisión] Minuta {minuta.fecha.strftime('%d/%m/%Y')} · {minuta.cliente.nombre}"
    url_minuta  = f"{APP_URL}/minutas/{minuta.id}"
    temas_lista = "".join(
        f'<li style="margin-bottom:6px"><strong style="color:#1d4ed8">{t.proyecto.codigo}</strong> — '
        f'{t.lo_tratado[:120]}{"…" if len(t.lo_tratado) > 120 else ""}</li>'
        for t in minuta.temas
    )

    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;margin:0;padding:0;background:#f9fafb">
<div style="max-width:580px;margin:30px auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08)">
  <div style="background:linear-gradient(135deg,#f59e0b,#d97706);padding:24px 32px">
    <div style="color:#fef3c7;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.05em">Sigma Energía SpA · Revisión interna</div>
    <h1 style="color:#fff;margin:6px 0 4px;font-size:20px;font-weight:700">Minuta lista para revisión</h1>
    <div style="color:#fef9c3;font-size:13px">{minuta.titulo}</div>
  </div>
  <div style="padding:24px 32px">
    <p style="color:#374151;font-size:14px;margin-top:0">
      <strong>{minuta.creador.nombre if minuta.creador else "Un compañero"}</strong> ha creado una nueva minuta
      del <strong>{minuta.fecha.strftime("%d/%m/%Y")}</strong> para el cliente
      <strong>{minuta.cliente.nombre}</strong>. Por favor revísala, complementa o agrega observaciones antes de enviarla al cliente.
    </p>
    {"<p style='font-size:13px;color:#6b7280;margin-bottom:4px'><strong>Proyectos tratados:</strong></p><ul style='font-size:13px;color:#374151;padding-left:20px'>" + temas_lista + "</ul>" if minuta.temas else ""}
    <div style="text-align:center;margin:24px 0">
      <a href="{url_minuta}" style="display:inline-block;background:#1d4ed8;color:#fff;text-decoration:none;
         padding:12px 28px;border-radius:8px;font-weight:700;font-size:14px">
        Ver minuta en la app →
      </a>
    </div>
  </div>
  <div style="padding:14px 32px;background:#f9fafb;border-top:1px solid #e5e7eb;font-size:11px;color:#9ca3af;text-align:center">
    Este correo fue generado automáticamente por Sigma Proyectos · Sigma Energía SpA
  </div>
</div>
</body></html>"""

    ok, err = _enviar_graph(token, emails_sigma, asunto, html)
    if ok:
        return True, f"Notificación enviada a {len(emails_sigma)} persona(s) del equipo Sigma."
    return False, f"Error al enviar notificación: {err}"


def enviar_minuta(minuta, destinatarios: list[str]) -> tuple[bool, str]:
    """Envía la minuta al cliente con PDF adjunto."""
    if not _credenciales_ok():
        return False, "Credenciales de email no configuradas en los secrets de HF Spaces."
    if not destinatarios:
        return False, "No hay participantes con email."

    token = _obtener_token()
    if not token:
        return False, "No se pudo obtener token de autenticación."

    asunto  = f"Minuta {minuta.fecha.strftime('%d/%m/%Y')} · {minuta.cliente.nombre} · {minuta.titulo}"
    html    = _construir_html(minuta)
    adjuntos = []

    # PDF adjunto
    try:
        from utils.pdf_generator import generar_pdf_minuta
        pdf_bytes = generar_pdf_minuta(minuta)
        if pdf_bytes:
            nombre_pdf = f"Minuta_{minuta.fecha.strftime('%Y%m%d')}_{minuta.cliente.nombre.replace(' ', '_')}.pdf"
            adjuntos.append({
                "@odata.type":  "#microsoft.graph.fileAttachment",
                "name":         nombre_pdf,
                "contentType":  "application/pdf",
                "contentBytes": base64.b64encode(pdf_bytes).decode(),
            })
    except Exception as _e:
        print(f"[email] No se pudo generar PDF: {_e}")

    ok, err = _enviar_graph(token, destinatarios, asunto, html, adjuntos or None)
    if ok:
        sufijo = " (con PDF adjunto)" if adjuntos else ""
        return True, f"Minuta enviada a {len(destinatarios)} participante(s){sufijo}."
    return False, f"Error al enviar email: {err}"


# ── HTML del email al cliente ──────────────────────────────────────────────────

def _construir_html(minuta) -> str:
    filas_temas = ""
    for t in minuta.temas:
        acuerdo_cell = f'<div style="border-left:3px solid #16a34a;padding-left:8px;white-space:pre-wrap;color:#374151">{t.acuerdos}</div>' if t.acuerdos else '<span style="color:#9ca3af">—</span>'
        resp_cell    = f'<strong style="color:#111827">{t.responsable.nombre}</strong>' if t.responsable else '<span style="color:#9ca3af">—</span>'
        fecha_cell   = (f'<span style="background:#fef3c7;color:#92400e;padding:2px 8px;border-radius:12px;font-size:11px">'
                        f'{t.fecha_estimada_respuesta.strftime("%d/%m/%Y")}</span>'
                        if t.fecha_estimada_respuesta else '<span style="color:#9ca3af">—</span>')
        filas_temas += f"""
        <tr style="border-bottom:1px solid #f3f4f6;vertical-align:top">
          <td style="padding:10px 12px">
            <strong style="color:#1d4ed8;font-size:13px">{t.proyecto.codigo}</strong><br>
            <span style="color:#6b7280;font-size:11px">{t.proyecto.nombre[:60]}</span>
          </td>
          <td style="padding:10px 12px;font-size:13px;white-space:pre-wrap;color:#374151">{t.lo_tratado}</td>
          <td style="padding:10px 12px;font-size:13px">{acuerdo_cell}</td>
          <td style="padding:10px 12px;font-size:13px;white-space:nowrap">{resp_cell}</td>
          <td style="padding:10px 12px;font-size:13px;white-space:nowrap">{fecha_cell}</td>
        </tr>"""

    temas_html = f"""
    <table style="width:100%;border-collapse:collapse;font-size:13px">
      <thead>
        <tr style="background:#f8fafc">
          <th style="padding:8px 12px;text-align:left;font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:.05em;border-bottom:2px solid #e2e8f0;width:18%">Proyecto</th>
          <th style="padding:8px 12px;text-align:left;font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:.05em;border-bottom:2px solid #e2e8f0;width:28%">Lo Tratado</th>
          <th style="padding:8px 12px;text-align:left;font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:.05em;border-bottom:2px solid #e2e8f0;width:28%">Acuerdo / Compromiso</th>
          <th style="padding:8px 12px;text-align:left;font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:.05em;border-bottom:2px solid #e2e8f0;width:15%">Responsable</th>
          <th style="padding:8px 12px;text-align:left;font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:.05em;border-bottom:2px solid #e2e8f0;width:11%">Fecha Resp.</th>
        </tr>
      </thead>
      <tbody>{filas_temas}</tbody>
    </table>"""

    participantes_html = "".join(
        f'<span style="display:inline-block;margin:3px;padding:4px 10px;background:#f3f4f6;border-radius:20px;font-size:13px">'
        f'{"📧 " if p.email else ""}{p.nombre}'
        f'{"  ·  <span style=color:#6b7280>" + p.empresa + "</span>" if p.empresa else ""}'
        f'</span>'
        for p in minuta.participantes
    )

    resumen_html = (
        f'<div style="margin-bottom:20px;padding:12px 16px;background:#fafafa;border:1px solid #e5e7eb;border-radius:8px">'
        f'<strong>Resumen general</strong><br><span style="white-space:pre-wrap">{minuta.resumen}</span></div>'
    ) if minuta.resumen else ""

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;margin:0;padding:0;background:#f9fafb">
<div style="max-width:680px;margin:30px auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08)">
  <div style="background:linear-gradient(135deg,#1d4ed8,#3b82f6);padding:28px 32px">
    <div style="color:#bfdbfe;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.05em">Sigma Energía SpA</div>
    <h1 style="color:#fff;margin:6px 0 4px;font-size:22px;font-weight:700">Minuta de Reunión</h1>
    <div style="color:#dbeafe;font-size:14px">{minuta.titulo}</div>
  </div>
  <div style="padding:28px 32px">
    <table style="width:100%;margin-bottom:24px;font-size:14px;color:#374151">
      <tr><td style="padding:4px 0;width:130px;color:#6b7280;font-weight:600">Cliente</td><td style="padding:4px 0"><strong>{minuta.cliente.nombre}</strong></td></tr>
      <tr><td style="padding:4px 0;color:#6b7280;font-weight:600">Fecha</td><td style="padding:4px 0">{minuta.fecha.strftime("%d de %B de %Y")}</td></tr>
      <tr><td style="padding:4px 0;color:#6b7280;font-weight:600">Elaboró</td><td style="padding:4px 0">{minuta.creador.nombre if minuta.creador else "—"}</td></tr>
    </table>
    {f'<div style="margin-bottom:24px"><div style="font-size:12px;font-weight:700;color:#6b7280;text-transform:uppercase;margin-bottom:8px">Participantes</div>{participantes_html}</div>' if minuta.participantes else ""}
    {resumen_html}
    <div style="font-size:12px;font-weight:700;color:#6b7280;text-transform:uppercase;margin-bottom:12px">Proyectos Tratados ({len(minuta.temas)})</div>
    {temas_html}
  </div>
  <div style="padding:16px 32px;background:#f9fafb;border-top:1px solid #e5e7eb;font-size:12px;color:#9ca3af;text-align:center">
    Este correo fue generado automáticamente por el sistema Sigma Proyectos · Sigma Energía SpA
  </div>
</div>
</body></html>"""
