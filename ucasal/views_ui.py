from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
from django.http import JsonResponse
from django.conf import settings
from django.core.exceptions import PermissionDenied
from external_services.ucasal.ucasal_services import UcasalServices
from ucasal.utils import TituloStates, can_transition
import json

DEFAULT_PAGE = getattr(settings, "UCASAL_DEFAULT_PAGE", 1)
DEFAULT_PAGE_SIZE_LIST = getattr(settings, "UCASAL_DEFAULT_PAGE_SIZE_LIST", 20)
DEFAULT_PAGE_SIZE_API = getattr(settings, "UCASAL_DEFAULT_PAGE_SIZE_API", 200)


def group_required(group_name: str):
    """Restringe acceso a usuarios autenticados que pertenezcan al grupo dado.

    Si el usuario no está autenticado, se redirige al login. Si está autenticado
    pero no pertenece al grupo requerido, se lanza PermissionDenied (403) para
    dejar claro que es un problema de permisos y no de login.
    """

    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated:
                return redirect("ui_login")
            if not user.groups.filter(name=group_name).exists():
                raise PermissionDenied("No tiene acceso al grupo requerido.")
            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator

@require_http_methods(["GET", "POST"]) 
def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)
            return redirect("ui_titles_list")
        return render(request, "ui/login.html", {"error": "Credenciales inválidas"})
    return render(request, "ui/login.html")

@require_http_methods(["POST"]) 
def logout_view(request):
    auth_logout(request)
    return redirect("ui_login")

@group_required("Titulos")
@login_required
@require_http_methods(["GET", "POST"]) 
def titles_list_view(request):
    items = []
    error = None
    page_param = request.GET.get("page") or request.POST.get("page")
    page_size_param = request.GET.get("page_size") or request.POST.get("page_size")
    try:
        page = int(page_param) if page_param is not None else DEFAULT_PAGE
    except ValueError:
        page = DEFAULT_PAGE
    try:
        page_size = int(page_size_param) if page_size_param is not None else DEFAULT_PAGE_SIZE_LIST
    except ValueError:
        page_size = DEFAULT_PAGE_SIZE_LIST
    if page < 1:
        page = DEFAULT_PAGE
    if page_size < 1:
        page_size = DEFAULT_PAGE_SIZE_LIST
    # Permitir consulta por GET (?query=...) y por POST (form)
    if request.method == "POST":
        query = request.POST.get("query")
        if query:
            try:
                res = UcasalServices.search_query(query, page=page, page_size=page_size)
                # Normalizar posibles formatos de respuesta de Athento
                raw_items = (
                    res.get("results")
                    or res.get("result", {}).get("entries")
                    or res
                )
                items = raw_items or []
            except Exception as e:
                error = str(e)
            return render(request, "ui/titles_list.html", {"items": items, "error": error, "query": query or ""})
        # Si no hay query en POST, comportarse como GET por defecto para mostrar resultados
        try:
            default_query = "SELECT uuid, filename, created, author, life_cycle_state FROM form_titulo"
            res = UcasalServices.search_query(default_query, page=page, page_size=page_size)
            raw_items = (
                res.get("results")
                or res.get("result", {}).get("entries")
                or res
            )
            items = raw_items or []
            query = default_query
        except Exception as e:
            error = str(e)
        return render(request, "ui/titles_list.html", {"items": items, "error": error, "query": query or ""})

    # GET: usar query si viene, sino listar por defecto los últimos 20
    query = request.GET.get("query")
    if not query:
        # Consulta por defecto sobre form_titulo (últimos 20 por fecha de creación)
        default_query = "SELECT * FROM form_titulo "
        try:
            res = UcasalServices.search_query(default_query, page=page, page_size=page_size)
            raw_items = (
                res.get("results")
                or res.get("result", {}).get("entries")
                or res
            )
            items = []
            for it in raw_items or []:
                items.append({
                    "uuid": it.get("uuid") or it.get("id") or "",
                    "filename": it.get("filename") or it.get("titulo") or "",
                    # La plantilla muestra "created"; mapear desde creation_date/created
                    "created": it.get("creation_date") or it.get("created") or "",
                    # Campos no presentes en form_titulo, se dejan vacíos
                    "estado": it.get("life_cycle_state") or it.get("estado") or it.get("lifecycle_state") or "",
                    "author": it.get("author") or it.get("autor") or "",
                })
            query = default_query
        except Exception as e:
            error = str(e)
    else:
        try:
            res = UcasalServices.search_query(query, page=page, page_size=page_size)
            raw_items = (
                res.get("results")
                or res.get("result", {}).get("entries")
                or res
            )
            items = []
            for it in raw_items or []:
                items.append({
                    "uuid": it.get("uuid") or it.get("id") or "",
                    "filename": it.get("filename") or it.get("titulo") or "",
                    "created": it.get("creation_date") or it.get("created") or "",
                    "estado": it.get("life_cycle_state") or it.get("estado") or it.get("lifecycle_state") or "",
                    "author": it.get("author") or it.get("autor") or "",
                })
        except Exception as e:
            error = str(e)
    return render(request, "ui/titles_list.html", {"items": items, "error": error, "query": query or ""})

@group_required("Titulos")
@login_required
@require_http_methods(["GET", "POST"]) 
def upload_title_view(request):
    ctx = {"error": None, "ok": False}
    if request.method == "POST":
        file_obj = request.FILES.get("file")
        filename = request.POST.get("filename")
        doctype = request.POST.get("doctype") or "form_titulo"
        serie = request.POST.get("serie")
        metadatas_raw = request.POST.get("metadatas")
        metadatas = None
        if metadatas_raw:
            try:
                metadatas = json.loads(metadatas_raw)
            except Exception:
                ctx["error"] = "metadatas debe ser JSON válido"
                return render(request, "ui/upload_title.html", ctx)
        # serie es opcional: Athento puede generarla automáticamente
        if not file_obj or not filename or not doctype:
            ctx["error"] = "file, filename y doctype son obligatorios"
            return render(request, "ui/upload_title.html", ctx)
        try:
            data = {
                'filename': filename,
                'doctype': doctype,
                'metadatas': metadatas or {}
            }
            if serie:
                data['serie'] = serie
            result = UcasalServices.create_file(
                file_tuple=(file_obj.name or filename, file_obj.read(), file_obj.content_type or 'application/pdf'),
                data=data
            )
            ctx["ok"] = True
            ctx["result"] = result
        except Exception as e:
            ctx["error"] = str(e)
    return render(request, "ui/upload_title.html", ctx)

@group_required("Titulos")
@login_required
@require_http_methods(["GET"]) 
def title_detail_view(request, uuid):
    try:
        fetch_mode = request.GET.get('fetch_mode')
        data = UcasalServices.get_file(str(uuid), fetch_mode=fetch_mode)
        return render(request, "ui/title_detail.html", {"uuid": uuid, "data": data})
    except Exception as e:
        return render(request, "ui/title_detail.html", {"uuid": uuid, "error": str(e), "data": None})

@group_required("Titulos")
@login_required
@require_http_methods(["POST"]) 
def delete_title_view(request, uuid):
    try:
        UcasalServices.delete_file(str(uuid))
        return redirect("ui_titles_list")
    except Exception as e:
        return HttpResponse(str(e), status=400)

@group_required("Titulos")
@login_required
@require_http_methods(["GET"]) 
def titles_console_view(request):
    return render(request, "ui/titles_console.html")

@group_required("Titulos")
@login_required
@require_http_methods(["GET"]) 
def titles_search_api(request):
    """
    API para abstraer datos desde Athento y servirlos a la UI (DataTables).
    Acepta ?query=... opcional; si no, usa una consulta por defecto limitada.
    Retorna en formato { data: [ {uuid, filename, acciones_html} ] }
    """
    try:
        query = request.GET.get("query")
        page_param = request.GET.get("page")
        page_size_param = request.GET.get("page_size")
        try:
            page = int(page_param) if page_param is not None else DEFAULT_PAGE
        except ValueError:
            page = DEFAULT_PAGE
        try:
            page_size = int(page_size_param) if page_size_param is not None else DEFAULT_PAGE_SIZE_API
        except ValueError:
            page_size = DEFAULT_PAGE_SIZE_API
        if page < 1:
            page = DEFAULT_PAGE
        if page_size < 1:
            page_size = DEFAULT_PAGE_SIZE_API
        if not query:
            # Preferir form_titulo (modelo específico de títulos) y dejar Document como fallback
            queries = [
                (
                    "SELECT uuid, filename, estado, created, author "
                    "FROM form_titulo "
                ),
                (
                    "SELECT uuid, filename, created, author, life_cycle_state "
                    "FROM Document "
                ),
            ]
            items = []
            last_err = None
            for q in queries:
                try:
                    res = UcasalServices.search_query(q, page=page, page_size=page_size)
                    raw_items = (
                        res.get("results")
                        or res.get("result", {}).get("entries")
                        or res
                    )
                    items = raw_items or []
                    if items:
                        break
                except Exception as e:
                    last_err = e
            if not items and last_err:
                raise last_err
        else:
            res = UcasalServices.search_query(query, page=page, page_size=page_size)
            raw_items = (
                res.get("results")
                or res.get("result", {}).get("entries")
                or res
            )
            items = raw_items or []
        data = []
        for it in items:
            uid = it.get("uuid") or it.get("id") or ""
            filename = it.get("filename") or it.get("titulo") or ""
            estado = it.get("life_cycle_state") or it.get("estado") or it.get("lifecycle_state") or ""
            # Soportar distintos nombres de campo de fecha de creación
            created = it.get("created") or it.get("creation_date") or it.get("fecha_creacion") or ""
            author = it.get("author") or it.get("autor") or ""
            acciones = (
                f"<a class='btn btn-sm btn-outline-primary me-1' href='/ui/titulos/{uid}/'><i class='bi bi-eye' title='Ver'></i></a>"
                f"<a class='btn btn-sm btn-outline-secondary me-1' href='/athento/files/{uid}/download'><i class='bi bi-download' title='Descargar'></i></a>"
                f"<a class='btn btn-sm btn-outline-warning me-1' href='/ui/titulos/{uid}/edit/'><i class='bi bi-pencil-square' title='Editar metadatos'></i></a>"
                f"<a class='btn btn-sm btn-outline-info me-1' href='/ui/titulos/{uid}/replace/'><i class='bi bi-file-earmark-arrow-up' title='Reemplazar archivo'></i></a>"
                f"<a class='btn btn-sm btn-outline-info me-1' href='/ui/titulos/{uid}/attach/'><i class='bi bi-paperclip' title='Adjuntar doc.'></i></a>"
                f"<a class='btn btn-sm btn-outline-success me-1' href='/ui/titulos/{uid}/firm/'><i class='bi bi-check2-circle' title='Firmar'></i></a>"
                f"<a class='btn btn-sm btn-outline-warning me-1' href='/ui/titulos/{uid}/reject/'><i class='bi bi-x-circle' title='Rechazar'></i></a>"
                f"<a class='btn btn-sm btn-outline-secondary me-1' href='/ui/titulos/{uid}/state/'><i class='bi bi-arrow-repeat' title='Cambiar estado'></i></a>"
                f"<button type='button' class='btn btn-sm btn-outline-danger me-1 btn-delete-title' data-uuid='{uid}'><i class='bi bi-trash' title='Eliminar'></i></button>"
                f"<a class='btn btn-sm btn-outline-dark' href='/ui/titulos/{uid}/status/'><i class='bi bi-clipboard-data' title='Estado'></i></a>"
            )
            data.append({
                "uuid": uid,
                "filename": filename,
                "estado": estado,
                "created": created,
                "author": author,
                "acciones": acciones
            })
        return JsonResponse({"data": data})
    except Exception as e:
        return JsonResponse({"error": str(e), "data": []}, status=400)

@group_required("Titulos")
@login_required
@require_http_methods(["POST"]) 
def titles_bulk_delete_api(request):
    """
    Elimina múltiples títulos por UUID. Body JSON: { "uuids": ["uuid1", "uuid2", ...] }
    """
    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
        uuids = payload.get('uuids') or []
        if not isinstance(uuids, list) or not uuids:
            return JsonResponse({"error": "Debe enviar una lista 'uuids'"}, status=400)
        ok = []
        errs = []
        for uid in uuids:
            try:
                UcasalServices.delete_file(str(uid))
                ok.append(uid)
            except Exception as e:
                errs.append({"uuid": uid, "error": str(e)})
        return JsonResponse({"deleted": ok, "errors": errs})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@group_required("Titulos")
@login_required
@require_http_methods(["GET", "POST"])
def edit_title_metadata_view(request, uuid):
    """Permite editar metadatos básicos de un título en Athento.

    Se apoya en UcasalServices.update_file enviando únicamente el diccionario
    de metadatos. Para simplificar, se expone un textarea donde se puede pegar
    un JSON de metadatos (clave/valor) y se valida mínimamente.
    """
    ctx = {"uuid": uuid, "error": None, "ok": False, "metadatas": "{}"}

    if request.method == "POST":
        metadatas_raw = request.POST.get("metadatas") or "{}"
        try:
            metadatas = json.loads(metadatas_raw)
            if not isinstance(metadatas, dict):
                raise ValueError("metadatos debe ser un objeto JSON (dict)")
        except Exception as exc:  # noqa: BLE001
            ctx["error"] = f"metadatos debe ser JSON válido: {exc}"
            ctx["metadatas"] = metadatas_raw
            return render(request, "ui/edit_title_metadata.html", ctx)

        try:
            UcasalServices.update_file(str(uuid), data={"metadatas": metadatas})
            ctx["ok"] = True
        except Exception as exc:  # noqa: BLE001
            ctx["error"] = str(exc)
        ctx["metadatas"] = metadatas_raw
        return render(request, "ui/edit_title_metadata.html", ctx)

    # GET: intentar precargar metadatos existentes si es posible
    try:
        data = UcasalServices.get_file(str(uuid), fetch_mode="default")
        # En Athento, los metadatos suelen venir bajo "metadatas" o similar
        existing = data.get("metadatas") or {}
        if isinstance(existing, dict):
            ctx["metadatas"] = json.dumps(existing, ensure_ascii=False, indent=2)
    except Exception:
        # Si falla, se deja el valor por defecto
        pass
    return render(request, "ui/edit_title_metadata.html", ctx)


@group_required("Titulos")
@login_required
@require_http_methods(["GET", "POST"])
def replace_title_file_view(request, uuid):
    """Permite reemplazar el archivo físico asociado a un título en Athento."""
    ctx = {"uuid": uuid, "error": None, "ok": False}

    if request.method == "POST":
        file_obj = request.FILES.get("file")
        filename = request.POST.get("filename") or (file_obj.name if file_obj else None)
        if not file_obj or not filename:
            ctx["error"] = "Debe seleccionar un archivo y un nombre de archivo."
            return render(request, "ui/replace_title_file.html", ctx)

        try:
            file_tuple = (filename, file_obj.read(), file_obj.content_type or "application/pdf")
            UcasalServices.update_file(str(uuid), file_tuple=file_tuple, data={"filename": filename})
            ctx["ok"] = True
        except Exception as exc:  # noqa: BLE001
            ctx["error"] = str(exc)

    return render(request, "ui/replace_title_file.html", ctx)


@group_required("Titulos")
@login_required
@require_http_methods(["GET"])
def title_status_view(request, uuid):
    """Muestra un resumen simple de estado/log de un título.

    Para no depender de estructuras complejas, se apoya en get_file y muestra
    los campos más relevantes tal como los devuelve Athento (estado, fechas,
    autor, serie, etc.).
    """
    ctx = {"uuid": uuid, "error": None, "data": None}
    try:
        data = UcasalServices.get_file(str(uuid), fetch_mode="default")
        ctx["data"] = data
    except Exception as exc:  # noqa: BLE001
        ctx["error"] = str(exc)
    return render(request, "ui/title_status.html", ctx)


@group_required("Titulos")
@login_required
@require_http_methods(["GET", "POST"])
def firm_title_view(request, uuid):
    """Marca un título como firmado actualizando metadatos estándar.

    No realiza firma criptográfica; solo marca en Athento algo equivalente a lo
    que haces desde Postman con metadata.form_titulo_firmar="ok" y
    metadata.form_titulo_rechazar="".
    """
    ctx = {"uuid": uuid, "error": None, "ok": False}

    if request.method == "POST":
        try:
            data = UcasalServices.get_file(str(uuid), fetch_mode="default")
            meta = data.get("metadatas") or data.get("metadata") or {}
            current_state = (
                meta.get("metadata.lifecycle_state")
                or data.get("life_cycle_state")
                or data.get("lifecycle_state")
                or meta.get("life_cycle_state")
                or meta.get("estado")
                or data.get("estado")
                or ""
            )
            if current_state and current_state != TituloStates.pendiente_firma_otp:
                ctx["error"] = (
                    f"Sólo se puede firmar el título si se encuentra en estado '{TituloStates.pendiente_firma_otp}', "
                    f"pero el estado actual es '{current_state}'."
                )
                return render(request, "ui/firm_title.html", ctx)
            if current_state and not can_transition(current_state, TituloStates.firmado):
                ctx["error"] = (
                    f"Transición no permitida: '{current_state}' → '{TituloStates.firmado}'"
                )
                return render(request, "ui/firm_title.html", ctx)

            metadatas = {
                "metadata.form_titulo_firmar": "ok",
                "metadata.form_titulo_rechazar": "",
                # Clave de ciclo de vida real utilizada por Athento
                "metadata.lifecycle_state": TituloStates.firmado,
            }
            UcasalServices.update_file(str(uuid), data={"metadatas": metadatas})
            ctx["ok"] = True
        except Exception as exc:  # noqa: BLE001
            ctx["error"] = str(exc)
    return render(request, "ui/firm_title.html", ctx)


@group_required("Titulos")
@login_required
@require_http_methods(["GET", "POST"])
def reject_title_view(request, uuid):
    """Marca un título como rechazado con un motivo.

    Actualiza metadatos tipo metadata.form_titulo_rechazar con el motivo
    ingresado y limpia metadata.form_titulo_firmar.
    """
    ctx = {"uuid": uuid, "error": None, "ok": False, "reason": ""}

    if request.method == "POST":
        reason = (request.POST.get("reason") or "").strip()
        if not reason:
            ctx["error"] = "Debe indicar un motivo de rechazo."
            return render(request, "ui/reject_title.html", ctx)
        try:
            data = UcasalServices.get_file(str(uuid), fetch_mode="default")
            meta = data.get("metadatas") or data.get("metadata") or {}
            current_state = (
                data.get("life_cycle_state")
                or data.get("lifecycle_state")
                or meta.get("life_cycle_state")
                or meta.get("estado")
                or data.get("estado")
                or ""
            )
            if current_state and not can_transition(current_state, TituloStates.rechazado):
                ctx["error"] = (
                    f"Transición no permitida: '{current_state}' → '{TituloStates.rechazado}'"
                )
                return render(request, "ui/reject_title.html", ctx)

            metadatas = {
                "metadata.form_titulo_firmar": "",
                "metadata.form_titulo_rechazar": reason,
                "metadata.lifecycle_state": TituloStates.rechazado,
            }
            UcasalServices.update_file(str(uuid), data={"metadatas": metadatas})
            ctx["ok"] = True
            ctx["reason"] = reason
        except Exception as exc:  # noqa: BLE001
            ctx["error"] = str(exc)
    return render(request, "ui/reject_title.html", ctx)


@group_required("Titulos")
@login_required
@require_http_methods(["GET", "POST"])
def change_title_state_view(request, uuid):
    """Permite cambiar un campo simple de estado en metadatos del título.

    Se limita a escribir un metadato "estado" (o similar) en el documento de
    Athento, sin forzar un flujo complejo. Puedes adaptarlo a los nombres de
    campo reales que utilice tu serie.
    """
    ctx = {"uuid": uuid, "error": None, "ok": False, "estado": ""}

    if request.method == "POST":
        estado = (request.POST.get("estado") or "").strip()
        if not estado:
            ctx["error"] = "Debe indicar un valor de estado."
            return render(request, "ui/change_title_state.html", ctx)
        try:
            data = UcasalServices.get_file(str(uuid), fetch_mode="default")
            meta = data.get("metadatas") or data.get("metadata") or {}
            current_state = (
                data.get("life_cycle_state")
                or data.get("lifecycle_state")
                or meta.get("life_cycle_state")
                or meta.get("estado")
                or data.get("estado")
                or ""
            )
            if current_state and not can_transition(current_state, estado):
                ctx["error"] = (
                    f"Transición no permitida: '{current_state}' → '{estado}'"
                )
                ctx["estado"] = estado
                return render(request, "ui/change_title_state.html", ctx)

            metadatas = {
                "metadata.lifecycle_state": estado,
            }
            UcasalServices.update_file(str(uuid), data={"metadatas": metadatas})
            ctx["ok"] = True
            ctx["estado"] = estado
        except Exception as exc:  # noqa: BLE001
            ctx["error"] = str(exc)
    return render(request, "ui/change_title_state.html", ctx)


@group_required("Titulos")
@login_required
@require_http_methods(["GET", "POST"])
def add_title_attachment_view(request, uuid):
    """Permite adjuntar un archivo adicional asociado a un título.

    Crea un nuevo documento en Athento (por ejemplo, usando un formulario de
    anexos) y lo vincula al título principal mediante un metadato que guarda el
    UUID del título padre.
    """
    ctx = {"uuid": uuid, "error": None, "ok": False}

    if request.method == "POST":
        file_obj = request.FILES.get("file")
        filename = request.POST.get("filename") or (file_obj.name if file_obj else None)
        description = request.POST.get("description") or ""

        if not file_obj or not filename:
            ctx["error"] = "Debe seleccionar un archivo y un nombre de archivo."
            return render(request, "ui/add_title_attachment.html", ctx)

        try:
            file_tuple = (
                filename,
                file_obj.read(),
                file_obj.content_type or "application/pdf",
            )
            metadatas = {
                "parent_title_uuid": str(uuid),
            }
            if description:
                metadatas["description"] = description

            # Crear un documento de anexo en Athento relacionado al título padre.
            # Usamos un doctype genérico configurable desde metadatos si fuera necesario.
            data = {
                "filename": filename,
                # Ajustar este doctype si en Athento existe uno específico para anexos.
                "doctype": "form_titulo_anexo",
                "metadatas": metadatas,
            }

            UcasalServices.create_file(
                file_tuple=file_tuple,
                data=data,
            )
            ctx["ok"] = True
        except Exception as exc:  # noqa: BLE001
            ctx["error"] = str(exc)

    return render(request, "ui/add_title_attachment.html", ctx)
