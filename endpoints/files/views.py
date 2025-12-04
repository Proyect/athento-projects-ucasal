from django.http import HttpResponse, StreamingHttpResponse
from django.urls import re_path as url
from ucasal.utils import default_permissions, traceback_ret, encodeJSON, getJsonBody, METHOD_NOT_ALLOWED
from core.decorators import rate_limit_decorator
from external_services.ucasal.ucasal_services import UcasalServices
import json

@default_permissions
@traceback_ret
@rate_limit_decorator(key='ip', rate='5/m', method='POST')
def create_file_view(request):
    if request.method != 'POST':
        return METHOD_NOT_ALLOWED
    if not request.content_type or 'multipart/form-data' not in request.content_type:
        return HttpResponse('Content-Type debe ser multipart/form-data', status=400)
    file_obj = request.FILES.get('file')
    filename = request.POST.get('filename')
    doctype = request.POST.get('doctype')
    serie = request.POST.get('serie')
    metadatas_raw = request.POST.get('metadatas')
    metadatas = None
    if metadatas_raw:
        try:
            metadatas = json.loads(metadatas_raw)
        except Exception:
            return HttpResponse('metadatas debe ser JSON válido', status=400)
    if not file_obj or not filename or not doctype or not serie:
        return HttpResponse('file, filename, doctype y serie son obligatorios', status=400)
    result = UcasalServices.create_file(
        file_tuple=(file_obj.name or filename, file_obj.read(), file_obj.content_type or 'application/octet-stream'),
        data={
            'filename': filename,
            'doctype': doctype,
            'serie': serie,
            'metadatas': metadatas or {}
        }
    )
    return HttpResponse(encodeJSON(result), content_type='application/json', status=201)

@default_permissions
@traceback_ret
@rate_limit_decorator(key='ip', rate='5/m', method='PUT')
def update_file_view(request, uuid):
    if request.method != 'PUT' and request.method != 'POST':
        return METHOD_NOT_ALLOWED
    if not request.content_type or 'multipart/form-data' not in request.content_type:
        return HttpResponse('Content-Type debe ser multipart/form-data', status=400)
    file_obj = request.FILES.get('file')
    filename = request.POST.get('filename')
    metadatas_raw = request.POST.get('metadatas')
    metadatas = None
    if metadatas_raw:
        try:
            metadatas = json.loads(metadatas_raw)
        except Exception:
            return HttpResponse('metadatas debe ser JSON válido', status=400)
    file_tuple = None
    if file_obj:
        file_tuple = (file_obj.name or 'upload.bin', file_obj.read(), file_obj.content_type or 'application/octet-stream')
    result = UcasalServices.update_file(
        str(uuid),
        file_tuple=file_tuple,
        data={
            'filename': filename,
            'metadatas': metadatas or {}
        }
    )
    return HttpResponse(encodeJSON(result), content_type='application/json')

@default_permissions
@traceback_ret
@rate_limit_decorator(key='ip', rate='5/m', method='DELETE')
def delete_file_view(request, uuid):
    if request.method != 'DELETE':
        return METHOD_NOT_ALLOWED
    UcasalServices.delete_file(str(uuid))
    return HttpResponse('', status=204)

@default_permissions
@traceback_ret
@rate_limit_decorator(key='ip', rate='10/m', method='GET')
def get_file_view(request, uuid):
    if request.method != 'GET':
        return METHOD_NOT_ALLOWED
    fetch_mode = request.GET.get('fetch_mode')
    result = UcasalServices.get_file(str(uuid), fetch_mode=fetch_mode)
    return HttpResponse(encodeJSON(result), content_type='application/json')

@default_permissions
@traceback_ret
@rate_limit_decorator(key='ip', rate='10/m', method='GET')
def download_file_view(request, uuid):
    if request.method != 'GET':
        return METHOD_NOT_ALLOWED
    stream, filename, content_type = UcasalServices.download_file(str(uuid))
    response = StreamingHttpResponse(stream)
    response['Content-Type'] = content_type or 'application/octet-stream'
    if filename:
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

@default_permissions
@traceback_ret
@rate_limit_decorator(key='ip', rate='10/m', method='POST')
def search_query_view(request):
    if request.method != 'POST':
        return METHOD_NOT_ALLOWED
    body = getJsonBody(request)
    query = body.get('query')
    page = int(request.GET.get('page', '1'))
    page_size = int(request.GET.get('page_size', '20'))
    if not query or not str(query).strip().lower().startswith('select'):
        return HttpResponse('Sólo se permiten consultas SELECT', status=400)
    result = UcasalServices.search_query(query, page=page, page_size=page_size)
    return HttpResponse(encodeJSON(result), content_type='application/json')

@default_permissions
@traceback_ret
@rate_limit_decorator(key='ip', rate='10/m', method='POST')
def search_resultset_view(request):
    if request.method != 'POST':
        return METHOD_NOT_ALLOWED
    body = getJsonBody(request)
    query = body.get('query')
    page = int(request.GET.get('page', '1'))
    page_size = int(request.GET.get('page_size', '20'))
    if not query or not str(query).strip().lower().startswith('select'):
        return HttpResponse('Sólo se permiten consultas SELECT', status=400)
    result = UcasalServices.search_resultset(query, page=page, page_size=page_size)
    return HttpResponse(encodeJSON(result), content_type='application/json')
