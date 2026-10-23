from django.http import HttpResponseForbidden

class LocalOnlyMiddleware:
    """The pilot has no user accounts: never expose it directly to a network."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.META.get('REMOTE_ADDR') not in {'127.0.0.1', '::1'}:
            return HttpResponseForbidden('Document AI è configurato per accesso locale. Usa un tunnel SSH per la VM.')
        response = self.get_response(request)
        if not request.path.startswith('/static/'):
            response['Cache-Control'] = 'no-store'
        return response
