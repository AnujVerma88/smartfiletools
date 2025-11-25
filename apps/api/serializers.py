"""
Serializers for API endpoints.
Handles data validation and serialization for API requests/responses.
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from apps.tools.models import Tool, ToolCategory, ConversionHistory
from apps.accounts.models import UserProfile

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 'password_confirm', 'first_name', 'last_name')
        extra_kwargs = {
            'first_name': {'required': False},
            'last_name': {'required': False},
        }
    
    def validate(self, attrs):
        """Validate that passwords match."""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': 'Passwords do not match.'
            })
        return attrs
    
    def create(self, validated_data):
        """Create new user with hashed password."""
        validated_data.pop('password_confirm')
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile information."""
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    is_premium = serializers.BooleanField(source='user.is_premium', read_only=True)
    daily_usage_count = serializers.IntegerField(source='user.daily_usage_count', read_only=True)
    credits = serializers.IntegerField(source='user.credits', read_only=True)
    
    class Meta:
        model = UserProfile
        fields = (
            'username', 'email', 'is_premium', 'daily_usage_count', 'credits',
            'phone_number', 'bio', 'email_notifications', 'marketing_emails',
            'created_at', 'updated_at'
        )
        read_only_fields = ('created_at', 'updated_at')


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user information."""
    profile = UserProfileSerializer(read_only=True)
    
    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name',
            'is_premium', 'credits', 'daily_usage_count', 'last_reset_date',
            'avatar', 'date_joined', 'profile'
        )
        read_only_fields = (
            'id', 'is_premium', 'credits', 'daily_usage_count',
            'last_reset_date', 'date_joined'
        )


class ToolCategorySerializer(serializers.ModelSerializer):
    """Serializer for tool categories."""
    tools_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ToolCategory
        fields = (
            'id', 'name', 'slug', 'icon', 'description',
            'display_order', 'is_active', 'tools_count'
        )
    
    def get_tools_count(self, obj):
        """Get count of active tools in this category."""
        return obj.tools.filter(is_active=True).count()


class ToolSerializer(serializers.ModelSerializer):
    """Serializer for conversion tools."""
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_slug = serializers.CharField(source='category.slug', read_only=True)
    
    class Meta:
        model = Tool
        fields = (
            'id', 'name', 'slug', 'description', 'icon', 'tool_type',
            'max_file_size_mb', 'supported_formats', 'is_premium',
            'is_active', 'usage_count', 'category_name', 'category_slug'
        )


class ConversionHistorySerializer(serializers.ModelSerializer):
    """Serializer for conversion history."""
    user_username = serializers.CharField(source='user.username', read_only=True)
    tool_name = serializers.SerializerMethodField()
    compression_ratio = serializers.SerializerMethodField()
    file_size_saved = serializers.SerializerMethodField()
    input_file_url = serializers.SerializerMethodField()
    output_file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ConversionHistory
        fields = (
            'id', 'user_username', 'tool_type', 'tool_name', 'status',
            'error_message', 'file_size_before', 'file_size_after',
            'compression_ratio', 'file_size_saved', 'processing_time',
            'created_at', 'completed_at', 'input_file_url', 'output_file_url'
        )
        read_only_fields = (
            'id', 'user_username', 'status', 'error_message',
            'file_size_before', 'file_size_after', 'processing_time',
            'created_at', 'completed_at'
        )
    
    def get_tool_name(self, obj):
        """Get human-readable tool name."""
        return dict(ConversionHistory.TOOL_CHOICES).get(obj.tool_type, obj.tool_type)
    
    def get_compression_ratio(self, obj):
        """Get compression ratio if applicable."""
        return obj.get_compression_ratio()
    
    def get_file_size_saved(self, obj):
        """Get bytes saved through compression."""
        return obj.get_file_size_saved()
    
    def get_input_file_url(self, obj):
        """Get input file URL."""
        if obj.input_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.input_file.url)
        return None
    
    def get_output_file_url(self, obj):
        """Get output file URL."""
        if obj.output_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.output_file.url)
        return None


class ConversionCreateSerializer(serializers.Serializer):
    """Serializer for creating a new conversion."""
    file = serializers.FileField(required=True)
    webhook_url = serializers.URLField(required=False, allow_blank=True)
    
    def validate_file(self, value):
        """Validate uploaded file."""
        if not value:
            raise serializers.ValidationError('No file provided.')
        
        # Get tool type from context
        tool_type = self.context.get('tool_type')
        if not tool_type:
            raise serializers.ValidationError('Tool type not specified.')
        
        # Get tool configuration
        try:
            tool = Tool.objects.get(tool_type=tool_type, is_active=True)
        except Tool.DoesNotExist:
            raise serializers.ValidationError('Invalid tool type.')
        
        # Check file size
        max_size = tool.max_file_size_mb * 1024 * 1024  # Convert MB to bytes
        if value.size > max_size:
            raise serializers.ValidationError(
                f'File size exceeds maximum allowed size of {tool.max_file_size_mb}MB.'
            )
        
        # Check file extension
        file_ext = value.name.split('.')[-1].lower()
        if file_ext not in tool.supported_formats:
            raise serializers.ValidationError(
                f'File format .{file_ext} is not supported. '
                f'Supported formats: {", ".join(tool.supported_formats)}'
            )
        
        return value


class UsageStatisticsSerializer(serializers.Serializer):
    """Serializer for user usage statistics."""
    total_conversions = serializers.IntegerField()
    daily_usage_count = serializers.IntegerField()
    remaining_credits = serializers.IntegerField()
    is_premium = serializers.BooleanField()
    conversions_by_type = serializers.DictField()
    recent_conversions = ConversionHistorySerializer(many=True)
