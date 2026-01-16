"""
Serializers for field configuration.
"""

from rest_framework import serializers
from core.models_field_config import FieldConfiguration


class FieldConfigurationSerializer(serializers.ModelSerializer):
    """Serializer for field configuration."""
    
    form_name_display = serializers.CharField(source='get_form_name_display', read_only=True)
    
    class Meta:
        model = FieldConfiguration
        fields = [
            'id',
            'form_name',
            'form_name_display',
            'field_name',
            'field_label',
            'is_visible',
            'is_required',
            'display_order',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class FieldConfigurationBulkUpdateSerializer(serializers.Serializer):
    """Serializer for bulk updating field configurations."""
    
    configurations = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=False
    )
    
    def validate_configurations(self, value):
        """Validate each configuration in the list."""
        for config in value:
            if 'id' not in config:
                raise serializers.ValidationError("Chaque configuration doit avoir un 'id'")
            if not any(key in config for key in ['is_visible', 'is_required', 'display_order']):
                raise serializers.ValidationError(
                    "Chaque configuration doit avoir au moins un champ à mettre à jour"
                )
        return value
