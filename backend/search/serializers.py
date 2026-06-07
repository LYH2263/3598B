from rest_framework import serializers


class SearchQuerySerializer(serializers.Serializer):
    q = serializers.CharField(max_length=200, required=True, trim_whitespace=True)
    limit = serializers.IntegerField(min_value=1, max_value=50, default=5)
    categories = serializers.CharField(
        max_length=200,
        required=False,
        allow_blank=True,
        help_text='逗号分隔的类别筛选，如 users,orders',
    )
