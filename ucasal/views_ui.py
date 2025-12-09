from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.http import JsonResponse
from external_services.ucasal.ucasal_services import UcasalServices
import json

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

@login_required
@require_http_methods(["GET", "POST"]) 
def titles_list_view(request):
    items = []
    error = None
    # Permitir consulta por GET (?query=...) y por POST (form)
    if request.method == "POST":
        query = request.POST.get("query")
        if query:
            try:
                page = 1
                page_size = 20
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
            default_query = "SELECT uuid, filename, created, author, life_cycle_state FROM Document ORDER BY created DESC LIMIT 20"
            page = 1
            page_size = 20
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
        default_query = "SELECT uuid, filename, creation_date FROM form_titulo ORDER BY creation_date DESC LIMIT 20"
        try:
            page = 1
            page_size = 20
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
            page = 1
            page_size = 20
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

@login_required
@require_http_methods(["GET", "POST"]) 
def upload_title_view(request):
    ctx = {"error": None, "ok": False}
    if request.method == "POST":
        file_obj = request.FILES.get("file")
        filename = request.POST.get("filename")
        doctype = request.POST.get("doctype")
        serie = request.POST.get("serie")
        metadatas_raw = request.POST.get("metadatas")
        metadatas = None
        if metadatas_raw:
            try:
                metadatas = json.loads(metadatas_raw)
            except Exception:
                ctx["error"] = "metadatas debe ser JSON válido"
                return render(request, "ui/upload_title.html", ctx)
        if not file_obj or not filename or not doctype or not serie:
            ctx["error"] = "file, filename, doctype y serie son obligatorios"
            return render(request, "ui/upload_title.html", ctx)
        try:
            result = UcasalServices.create_file(
                file_tuple=(file_obj.name or filename, file_obj.read(), file_obj.content_type or 'application/pdf'),
                data={
                    'filename': filename,
                    'doctype': doctype,
                    'serie': serie,
                    'metadatas': metadatas or {}
                }
            )
            ctx["ok"] = True
            ctx["result"] = result
        except Exception as e:
            ctx["error"] = str(e)
    return render(request, "ui/upload_title.html", ctx)

@login_required
@require_http_methods(["GET"]) 
def title_detail_view(request, uuid):
    try:
        fetch_mode = request.GET.get('fetch_mode')
        data = UcasalServices.get_file(str(uuid), fetch_mode=fetch_mode)
        return render(request, "ui/title_detail.html", {"uuid": uuid, "data": data})
    except Exception as e:
        return render(request, "ui/title_detail.html", {"uuid": uuid, "error": str(e), "data": None})

@login_required
@require_http_methods(["POST"]) 
def delete_title_view(request, uuid):
    try:
        UcasalServices.delete_file(str(uuid))
        return redirect("ui_titles_list")
    except Exception as e:
        return HttpResponse(str(e), status=400)

@login_required
@require_http_methods(["GET"]) 
def titles_console_view(request):
    return render(request, "ui/titles_console.html")

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
        if not query:
            # Preferir form_titulo (modelo específico de títulos) y dejar Document como fallback
            queries = [
                (
                    "SELECT uuid, filename, creation_date "
                    "FROM form_titulo "
                    "ORDER BY creation_date DESC LIMIT 200"
                ),
                (
                    "SELECT uuid, filename, created, author, life_cycle_state "
                    "FROM Document ORDER BY created DESC LIMIT 200"
                ),
            ]
            items = []
            last_err = None
            for q in queries:
                try:
                    res = UcasalServices.search_query(q, page=1, page_size=200)
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
            res = UcasalServices.search_query(query, page=1, page_size=200)
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
                f"<a class='btn btn-sm btn-outline-primary me-1' href='/ui/titulos/{uid}/'><i class='bi bi-eye'></i> Ver</a>"
                f"<a class='btn btn-sm btn-outline-secondary' href='/athento/files/{uid}/download'><i class='bi bi-download'></i> Descargar</a>"
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
