from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
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
    query = request.POST.get("query") if request.method == "POST" else None
    if query:
        try:
            page = 1
            page_size = 20
            res = UcasalServices.search_query(query, page=page, page_size=page_size)
            items = res.get("results") or res
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
