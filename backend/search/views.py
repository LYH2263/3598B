from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import SearchQuerySerializer
from .services.search_service import aggregate_search


class GlobalSearchView(APIView):
    """跨模块聚合搜索接口"""

    def get(self, request):
        serializer = SearchQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        keyword = data['q']
        limit = data['limit']
        categories_raw = data.get('categories') or ''
        categories = [c.strip() for c in categories_raw.split(',') if c.strip()] if categories_raw else None

        result = aggregate_search(
            keyword=keyword,
            user=request.user,
            limit=limit,
            categories=categories,
        )
        return Response(result, status=status.HTTP_200_OK)
