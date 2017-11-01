import logging

from django.http import JsonResponse
from django.utils import timezone

logger = logging.getLogger("django")


def logger_middleware(get_response):
    def middleware(request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        # path = request.META.get("HOST")
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        path = request.get_full_path()

        logger.info("request from: {0},  to: {1}, post_data: {2}".format(ip, path, request.POST))
        if path == '/ping':
            return get_response(request)

        ts = timezone.now()
        # logger.info("receive request for path {0}".format(request.META))
        response = get_response(request)
        seconds = (timezone.now() - ts).total_seconds()

        ua = request.META.get('user-agent')

        try:
            if seconds > 60:
                logger.error("API %s latency is %s, check it", request.path_info, seconds)

            if isinstance(response, JsonResponse):
                logger.info(
                    "process request from: {0}, to: {1}, post_data: {2}, response_data: {3}, latency: {4}, ua: {5}"
                    .format(ip, request.path_info, request.POST, response.content.decode('unicode_escape'),
                            seconds, ua))
            else:
                logger.info("process request from: {0}, to: {1}, post_data: {2}, "
                            "response_http_code: {3}, latency: {4}, ua: {5}"
                            .format(ip, request.path_info, request.POST, response.status_code,
                                    seconds, ua))

                # 'platform' 'app' 'version' 'user_id' 'device_id' 'ip' 'app' [date] 'host'
                # 'method uri' 'code' 'api_code' 'size' 'time' 'ua'
        except:
            pass

        return response

    return middleware
