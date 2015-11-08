from __future__ import unicode_literals

import django_filters
from django.conf import settings
from rest_framework import filters, viewsets, serializers
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse
from . import models


APPLICATION_SEARCH_FIELDS = (
    "name_fi", "name_en", "name_sv", "name_ru",
    "description_fi", "description_en", "description_sv", "description_ru",
    "vendor",
)

class TranslatedField(serializers.Field):
    def field_to_native(self, obj, field_name):
        # If source is given, use it as the attribute(chain) of obj to be
        # translated and ignore the original field_name
        if self.source:
            bits = self.source.split(".")
            field_name = bits[-1]
            for name in bits[:-1]:
                obj = getattr(obj, name)

        return {
            code: getattr(obj, field_name + "_" + code, None)
            for code, _ in settings.LANGUAGES
        }


def get_full_image_url(self, obj):
    request = self.context["request"]
    return request.build_absolute_uri(obj.image.url)


def create_tag_serializer(model_class):
    class TagSerializer(serializers.HyperlinkedModelSerializer):
        name = TranslatedField()

        class Meta:
            model = model_class
            fields = ('url', 'id', 'name', 'slug', 'applications')
    return TagSerializer

CategorySerializer = create_tag_serializer(models.Category)
PlatformSerializer = create_tag_serializer(models.Platform)
AccessibilitySerializer = create_tag_serializer(models.Accessibility)


class ScreenshotSerializer(serializers.ModelSerializer):
    platform = serializers.Field(source='platform.slug')
    image = serializers.SerializerMethodField('get_full_image_url')

    class Meta:
        model = models.ApplicationScreenshot
        fields = ('image', 'platform')

    get_full_image_url = get_full_image_url


class SupportedPlatformSerializer(serializers.ModelSerializer):
    """
    PlatformSerializer with custom fields from ApplicationPlatformSupport
    """
    name = TranslatedField(source="platform.name")
    slug = serializers.Field(source='platform.slug')
    url = serializers.HyperlinkedRelatedField(view_name='platform-detail',
                                              source='platform')

    class Meta:
        model = models.ApplicationPlatformSupport
        fields = ('url', 'id', 'name', 'slug', 'store_url',
                  'rating', 'nr_reviews', 'last_updated')


class PlatformViewSet(viewsets.ModelViewSet):
    queryset = models.Platform.objects.all()
    serializer_class = PlatformSerializer


class SupportedCategorySerializer(CategorySerializer):
    class Meta(CategorySerializer.Meta):
        fields = ('url', 'id', 'name', 'slug')


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = models.Category.objects.all()
    serializer_class = CategorySerializer


class SupportedAccessibilitySerializer(AccessibilitySerializer):
    class Meta(CategorySerializer.Meta):
        fields = ('url', 'id', 'name', 'slug')


class AccessibilityViewSet(viewsets.ModelViewSet):
    queryset = models.Accessibility.objects.all()
    serializer_class = AccessibilitySerializer


class ApplicationSerializer(serializers.HyperlinkedModelSerializer):
    name = TranslatedField()
    short_description = TranslatedField()
    description = TranslatedField()
    platforms = SupportedPlatformSerializer(source='applicationplatformsupport_set',
                                            read_only=True,
                                            many=True)
    languages = serializers.SlugRelatedField(many=True,
                                             read_only=True,
                                             slug_field='language')
    image = serializers.SerializerMethodField('get_full_image_url')
    categories = SupportedCategorySerializer(read_only=True)
    accessibilities = SupportedAccessibilitySerializer(read_only=True)
    screenshots = ScreenshotSerializer(source="applicationscreenshot_set",
                                       many=True,
                                       read_only=True)

    class Meta:
        model = models.Application
        fields = ('url', 'id', 'name', 'slug', 'image', 'short_description',
                  'description', 'vendor', 'publish_date', 'rating',
                  'publisher_url', 'support_url', 'contact_email', 'created',
                  'modified', 'languages', 'categories', 'accessibilities',
                  'platforms','screenshots')

    get_full_image_url = get_full_image_url


class ApplicationFilterSet(django_filters.FilterSet):
    category = django_filters.CharFilter(name="categories__slug")
    accessibility = django_filters.CharFilter(name="accessibilities__slug")
    platform = django_filters.CharFilter(name="platforms__slug")
    language = django_filters.CharFilter(name="languages__language")
    min_rating = django_filters.NumberFilter(name="rating", lookup_type="gte")
    max_rating = django_filters.NumberFilter(name="rating", lookup_type="lte")

    class Meta:
        model = models.Application
        fields = APPLICATION_SEARCH_FIELDS + ("category", "accessibility",
                 "platform", "min_rating", "max_rating")


class ApplicationViewSet(viewsets.ModelViewSet):
    queryset = models.Application.objects.all()
    serializer_class = ApplicationSerializer
    filter_class = ApplicationFilterSet
    filter_backends = (filters.DjangoFilterBackend,
                       filters.SearchFilter,
                       filters.OrderingFilter,)
    search_fields = APPLICATION_SEARCH_FIELDS
    ordering_fields = ("publish_date", "created", "modified")
    ordering = ("created",)
