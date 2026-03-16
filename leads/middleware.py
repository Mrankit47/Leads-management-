from django.utils.cache import add_never_cache_headers

class LogoutSecurityMiddleware:
    """
    Middleware to prevent authenticated pages from being cached by the browser.
    This ensures that once a user logs out, they cannot use the 'Back' button
    to view sensitive information, as the browser will be forced to re-request
    the page and the server will redirect them to the login screen.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Only apply 'never cache' headers if the user is authenticated.
        # This prevents the browser from storing sensitive authenticated pages.
        if hasattr(request, 'user') and request.user.is_authenticated:
            add_never_cache_headers(response)
            
        return response
