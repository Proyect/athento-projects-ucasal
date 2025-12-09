from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse, HttpResponseNotAllowed
from django.utils.encoding import force_str
from external_services.ucasal.ucasal_services import UcasalServices
from rest_framework_simplejwt.authentication import JWTAuthentication
import base64
import json


def jwt_required(view_func):
    """Protege vistas con JWT (SimpleJWT) usando el header Authorization: Bearer <token>."""
    def _wrapped(request, *args, **kwargs):
        authenticator = JWTAuthentication()
        try:
            auth_result = authenticator.authenticate(request)
        except Exception as e:
            return JsonResponse({"detail": "Token inválido", "error": str(e)}, status=401)

        if auth_result is None:
            return JsonResponse({"detail": "Credenciales de autenticación no provistas"}, status=401)

        user, token = auth_result
        request.user = user
        request.auth = token
        return view_func(request, *args, **kwargs)

    return _wrapped


@csrf_exempt
@require_http_methods(["GET", "POST"])
@jwt_required
def titles_collection(request):
    """Lista o crea títulos.

    GET /api/titulos/
        Query params: q (opcional), page (opcional), page_size (opcional)

    POST /api/titulos/
        Body JSON:
        {
          "filename": "titulo.pdf",
          "doctype": "titulos",
          "serie": "titulos",
          "metadatas": {...},
          "file_base64": "..."
        }
    """
    if request.method == "GET":
        query = request.GET.get("q")
        page = int(request.GET.get("page") or 1)
        page_size = int(request.GET.get("page_size") or 20)

        if not query:
            query = "SELECT * FROM form_titulo"

        res = UcasalServices.search_query(query, page=page, page_size=page_size)
        return JsonResponse({"results": res})

    if request.method == "POST":
        try:
            payload = json.loads(force_str(request.body or b"{}"))
        except Exception:
            return JsonResponse({"error": "JSON inválido"}, status=400)

        filename = payload.get("filename")
        doctype = payload.get("doctype")
        serie = payload.get("serie")
        metadatas = payload.get("metadatas") or {}
        file_b64 = payload.get("file_base64")

        if not (filename and doctype and serie and file_b64):
            return JsonResponse({"error": "Faltan 'filename', 'doctype', 'serie' o 'file_base64'"}, status=400)

        try:
            file_bytes = base64.b64decode(file_b64)
        except Exception:
            return JsonResponse({"error": "file_base64 inválido"}, status=400)

        result = UcasalServices.create_file(
            file_tuple=(filename, file_bytes, "application/octet-stream"),
            data={"filename": filename, "doctype": doctype, "serie": serie, "metadatas": metadatas},
        )
        return JsonResponse({"success": True, "result": result}, status=201)

    return HttpResponseNotAllowed(["GET", "POST"])


@csrf_exempt
@require_http_methods(["GET", "PUT", "DELETE"])
@jwt_required
def title_detail(request, uuid):
    """Obtiene, actualiza o elimina un título.

    GET /api/titulos/{uuid}/
    PUT /api/titulos/{uuid}/
    DELETE /api/titulos/{uuid}/
    """
    if request.method == "GET":
        fetch_mode = request.GET.get("fetch_mode") or "default"
        data = UcasalServices.get_file(str(uuid), fetch_mode=fetch_mode)
        if not data:
            return JsonResponse({"error": "No encontrado"}, status=404)
        return JsonResponse({"success": True, "data": data})

    if request.method == "PUT":
        try:
            payload = json.loads(force_str(request.body or b"{}"))
        except Exception:
            return JsonResponse({"error": "JSON inválido"}, status=400)

        new_filename = payload.get("filename")
        metadatas = payload.get("metadatas") or {}
        file_b64 = payload.get("file_base64")

        file_tuple = None
        if file_b64:
            try:
                file_bytes = base64.b64decode(file_b64)
            except Exception:
                return JsonResponse({"error": "file_base64 inválido"}, status=400)
            file_tuple = (new_filename or "updated_file", file_bytes, "application/octet-stream")

        data = {}
        if new_filename:
            data["filename"] = new_filename
        if metadatas:
            data["metadatas"] = metadatas

        result = UcasalServices.update_file(str(uuid), file_tuple=file_tuple, data=data)
        return JsonResponse({"success": True, "result": result})

    if request.method == "DELETE":
        UcasalServices.delete_file(str(uuid))
        return JsonResponse({"success": True})

    return HttpResponseNotAllowed(["GET", "PUT", "DELETE"])


@csrf_exempt
@require_http_methods(["GET"])
@jwt_required
def title_download(request, uuid):
    """Devuelve URL de descarga para un título.

    GET /api/titulos/{uuid}/download/
    """
    return JsonResponse({"success": True, "download_url": f"/athento/files/{uuid}/download"})
