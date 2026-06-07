import logging

from django.db import OperationalError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def api_exception_handler(exc, context):
    if isinstance(exc, OperationalError):
        logger.exception('Database operational error: %s', exc)
        return Response(
            {'detail': '数据库连接异常，请稍后重试。'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    response = exception_handler(exc, context)
    if response is None:
        logger.exception('Unhandled exception: %s', exc)
        return Response(
            {'detail': '服务器内部错误，请联系管理员。'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    return response
