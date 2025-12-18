"""
Service serializers for API.
"""

from rest_framework import serializers
from apps.services.models import Service, ServiceCategory, ServiceIntervention


class ServiceCategorySerializer(serializers.ModelSerializer):
    """Serializer for service categories."""
    
    services_count = serializers.SerializerMethodField()
 
    
    class Meta:
        model = ServiceCategory
        fields = [
            'id', 'name', 'description', 'is_active',
            'services_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def validate_name(self, value):
        """Validate unique category name."""
        instance = self.instance
        if ServiceCategory.objects.exclude(pk=instance.pk if instance else None).filter(name=value).exists():
            raise serializers.ValidationError("Une catégorie de service avec ce nom existe déjà.")
        return value
 
    
    def get_services_count(self, obj):
        return obj.services.filter(is_active=True).count()


class ServiceListSerializer(serializers.ModelSerializer):
    """Serializer for service list view."""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    assigned_staff_count = serializers.IntegerField(
        source='assigned_staff.count',
        read_only=True
    )
    
    class Meta:
        model = Service
        fields = [
            'id', 'reference', 'name', 'description', 'category', 'category_name',
            'unit_price', 'estimated_duration', 'assigned_staff_count',
            'is_active', 'created_at'
        ]


class ServiceDetailSerializer(serializers.ModelSerializer):
    """Serializer for service detail view."""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    unit_price_with_tax = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True
    )
    assigned_staff_list = serializers.SerializerMethodField()
    
    class Meta:
        model = Service
        fields = [
            'id', 'reference', 'name', 'description', 'category',
            'category_name', 'unit_price', 'tax_rate', 'unit_price_with_tax',
            'estimated_duration', 'assigned_staff', 'assigned_staff_list',
            'is_active', 'created_at', 'updated_at',
            'created_by', 'updated_by'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    
    def get_assigned_staff_list(self, obj):
        from apps.accounts.serializers import UserListSerializer
        return UserListSerializer(obj.assigned_staff.all(), many=True).data


class ServiceCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for service creation and update."""
    
    class Meta:
        model = Service
        fields = [
            'reference', 'name', 'description', 'category',
            'unit_price', 'tax_rate', 'estimated_duration',
            'assigned_staff', 'is_active'
        ]
    
    def validate_reference(self, value):
        """Validate unique reference."""
        instance = self.instance
        if Service.objects.exclude(pk=instance.pk if instance else None).filter(reference=value).exists():
            raise serializers.ValidationError("Un service avec cette référence existe déjà.")
        return value


class ServiceInterventionListSerializer(serializers.ModelSerializer):
    """Serializer for intervention list view."""
    
    service_name = serializers.CharField(source='service.name', read_only=True)
    customer_name = serializers.CharField(source='customer.get_display_name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = ServiceIntervention
        fields = [
            'id', 'service', 'service_name', 'customer', 'customer_name',
            'assigned_to', 'assigned_to_name', 'scheduled_date',
            'scheduled_time', 'status', 'status_display',
            'quantity', 'unit_price', 'created_at'
        ]


class ServiceInterventionDetailSerializer(serializers.ModelSerializer):
    """Serializer for intervention detail view."""
    
    service_detail = ServiceListSerializer(source='service', read_only=True)
    customer_name = serializers.CharField(source='customer.get_display_name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    total_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_price_with_tax = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = ServiceIntervention
        fields = [
            'id', 'service', 'service_detail', 'customer', 'customer_name',
            'assigned_to', 'assigned_to_name', 'scheduled_date', 'scheduled_time',
            'actual_start', 'actual_end', 'status', 'status_display',
            'quantity', 'unit_price', 'total_price', 'total_price_with_tax',
            'notes', 'internal_notes', 'quality_rating', 'quality_comments',
            'created_at', 'updated_at', 'created_by', 'updated_by'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']


class ServiceInterventionCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for intervention creation and update."""
    
    class Meta:
        model = ServiceIntervention
        fields = [
            'service', 'customer', 'assigned_to', 'scheduled_date',
            'scheduled_time', 'status', 'quantity', 'unit_price',
            'notes', 'internal_notes'
        ]
    
    def validate(self, attrs):
        """Validate intervention data."""
        # Set unit_price from service if not provided
        if not attrs.get('unit_price') and attrs.get('service'):
            attrs['unit_price'] = attrs['service'].unit_price
        
        return attrs