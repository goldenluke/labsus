from django.http import JsonResponse

def api_response(data=None, meta=None, status="ok", status_code=200):
    return JsonResponse({
        "status": status,
        "data": data if data is not None else [],
        "meta": meta if meta is not None else {}
    }, status=status_code, safe=False)
