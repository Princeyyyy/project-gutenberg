import logging

from django.conf import settings
from django.http import JsonResponse

logger = logging.getLogger(__name__)


class JsonExceptionMiddleware:
    """Middleware to catch uncaught exceptions and return JSON error responses in production.

    Ensures that mobile client apps receive clean JSON error structures
    instead of raw HTML error/traceback screens when unexpected errors happen.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        # Log the stack trace automatically
        logger.exception('Unhandled exception in request %s: %s', request.path, exception)

        # In local debug mode, return None to let Django's interactive traceback view run
        if settings.DEBUG:
            return None

        # Return a structured JSON response in production
        return JsonResponse(
            {
                'error': 'Internal Server Error',
                'message': 'An unexpected error occurred on the server. Please check the logs or contact support.',
                'path': request.path,
            },
            status=500,
        )
