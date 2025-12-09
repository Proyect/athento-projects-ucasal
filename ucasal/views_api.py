from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.utils.encoding import force_str
from external_services.ucasal.ucasal_services import UcasalServices
import base64
import json

@csrf_exempt
@require_http_methods(["POST"])  # autenticación puede agregarse luego (JWT/Session)
def titulos_command(request):
    """
    Gateway unificado para operaciones de Athento Files API relacionadas a Títulos.
    Body JSON: {
      "action": "create|update|delete|get|download|search|resultset|list",
      ... params ...
    }

    Respuestas devuelven JSON simple listo para UI.
    """
    try:
        try:
            payload = json.loads(force_str(request.body or b"{}"))
        except Exception:
            return JsonResponse({"error": "JSON inválido"}, status=400)

        action = (payload.get("action") or "").lower()
        if not action:
            return JsonResponse({"error": "Falta 'action'"}, status=400)

        # SEARCH (query) ------------------------------------------------------
        if action == "search":
            query = payload.get("query")
            if not query:
                return JsonResponse({"error": "Falta 'query'"}, status=400)
            page = int(payload.get("page") or 1)
            page_size = int(payload.get("page_size") or 20)
            res = UcasalServices.search_query(query, page=page, page_size=page_size)
            return JsonResponse({"success": True, "results": res})

        # RESULTSET -----------------------------------------------------------
        if action == "resultset":
            query = payload.get("query")
            if not query:
                return JsonResponse({"error": "Falta 'query'"}, status=400)
            page = int(payload.get("page") or 1)
            page_size = int(payload.get("page_size") or 20)
            res = UcasalServices.search_resultset(query, page=page, page_size=page_size)
            return JsonResponse({"success": True, "results": res})

        # LIST (alias común para SELECT * FROM form_titulo) -------------------
        if action == "list":
            page = int(payload.get("page") or 1)
            page_size = int(payload.get("page_size") or 20)
            default_query = payload.get("query") or "SELECT * FROM form_titulo"
            res = UcasalServices.search_query(default_query, page=page, page_size=page_size)
            return JsonResponse({"success": True, "results": res})

        # GET -----------------------------------------------------------------
        if action == "get":
            uuid = payload.get("uuid")
            fetch_mode = payload.get("fetch_mode") or "default"
            if not uuid:
                return JsonResponse({"error": "Falta 'uuid'"}, status=400)
            data = UcasalServices.get_file(str(uuid), fetch_mode=fetch_mode)
            return JsonResponse({"success": True, "data": data})

        # DOWNLOAD (retorna URL utilizable en UI) -----------------------------
        if action == "download":
            uuid = payload.get("uuid")
            if not uuid:
                return JsonResponse({"error": "Falta 'uuid'"}, status=400)
            return JsonResponse({"success": True, "download_url": f"/athento/files/{uuid}/download"})

        # CREATE --------------------------------------------------------------
        if action == "create":
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
                file_tuple=(filename, file_bytes, 'application/octet-stream'),
                data={'filename': filename, 'doctype': doctype, 'serie': serie, 'metadatas': metadatas}
            )
            return JsonResponse({"success": True, "result": result})

        # UPDATE --------------------------------------------------------------
        if action == "update":
            uuid = payload.get("uuid")
            if not uuid:
                return JsonResponse({"error": "Falta 'uuid'"}, status=400)
            new_filename = payload.get("filename")
            metadatas = payload.get("metadatas") or {}
            file_b64 = payload.get("file_base64")
            file_tuple = None
            if file_b64:
                try:
                    file_bytes = base64.b64decode(file_b64)
                except Exception:
                    return JsonResponse({"error": "file_base64 inválido"}, status=400)
                file_tuple = (new_filename or 'updated_file', file_bytes, 'application/octet-stream')
            data = {}
            if new_filename:
                data['filename'] = new_filename
            if metadatas:
                data['metadatas'] = metadatas
            result = UcasalServices.update_file(str(uuid), file_tuple=file_tuple, data=data)
            return JsonResponse({"success": True, "result": result})

        # DELETE --------------------------------------------------------------
        if action == "delete":
            uuid = payload.get("uuid")
            if not uuid:
                return JsonResponse({"error": "Falta 'uuid'"}, status=400)
            UcasalServices.delete_file(str(uuid))
            return JsonResponse({"success": True})

        return JsonResponse({"error": f"Acción no soportada: {action}"}, status=400)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)
