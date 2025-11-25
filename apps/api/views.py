"""
API Views for SmartFileTools Platform.
Provides RESTful API endpoints for authentication, file conversion, and user management.
"""
from rest_framework import generics, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404

from apps.tools.models import Tool, ToolCategory, ConversionHistory
from apps.tools.tasks import process_conversion
from apps.accounts.models import UserProfile
from .serializers import (
    UserRegistrationSerializer,
    UserSerializer,
    UserProfileSerializer,
    ToolSerializer,
    ToolCategorySerializer,
    ConversionHistorySerializer,
    ConversionCreateSerializer,
    UsageStatisticsSerializer,
)
from .exceptions import success_response, error_response

User = get_user_model()


# ============================================================================
# Authentication Views
# ============================================================================

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT token serializer that includes user information."""
    
    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Add user information to response
        data['user'] = {
            'id': self.user.id,
            'username': self.user.username,
            'email': self.user.email,
            'is_premium': self.user.is_premium,
        }
        
        return data


class UserLoginView(TokenObtainPairView):
    """API endpoint for user login."""
    serializer_class = CustomTokenObtainPairSerializer
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
            return success_response(
                data=serializer.validated_data,
                message='Login successful',
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return error_response(
                message='Invalid credentials',
                errors={'code': 'INVALID_CREDENTIALS', 'details': str(e)},
                status=status.HTTP_401_UNAUTHORIZED
            )


class UserRegistrationView(generics.CreateAPIView):
    """API endpoint for user registration."""
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        
        if not serializer.is_valid():
            return error_response(
                message='Validation error',
                errors={'code': 'VALIDATION_ERROR', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = serializer.save()
        UserProfile.objects.create(user=user)
        refresh = RefreshToken.for_user(user)
        
        return success_response(
            data={
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                },
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            },
            message='Registration successful',
            status=status.HTTP_201_CREATED
        )


class UserLogoutView(APIView):
    """API endpoint for user logout."""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if not refresh_token:
                return error_response(
                    message='Refresh token required',
                    errors={'code': 'MISSING_TOKEN', 'details': 'Refresh token is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            token = RefreshToken(refresh_token)
            token.blacklist()
            
            return success_response(
                message='Logout successful',
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return error_response(
                message='Logout failed',
                errors={'code': 'LOGOUT_ERROR', 'details': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


# ============================================================================
# Tool Views
# ============================================================================

class ToolListView(generics.ListAPIView):
    """API endpoint to list all available tools."""
    serializer_class = ToolSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        queryset = Tool.objects.filter(is_active=True).select_related('category')
        
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__slug=category)
        
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )
        
        return queryset.order_by('category__display_order', 'display_order')
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        return success_response(
            data={
                'tools': serializer.data,
                'count': queryset.count()
            },
            message='Tools retrieved successfully'
        )


class ToolDetailView(generics.RetrieveAPIView):
    """API endpoint to get details of a specific tool."""
    queryset = Tool.objects.filter(is_active=True)
    serializer_class = ToolSerializer
    lookup_field = 'slug'
    permission_classes = [permissions.AllowAny]
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        
        return success_response(
            data=serializer.data,
            message='Tool details retrieved successfully'
        )


# ============================================================================
# Conversion Views
# ============================================================================

class BaseConversionView(APIView):
    """Base view for file conversion endpoints."""
    permission_classes = [permissions.IsAuthenticated]
    tool_type = None
    
    def post(self, request):
        if not self.tool_type:
            return error_response(
                message='Tool type not specified',
                errors={'code': 'INVALID_TOOL', 'details': 'Tool type is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = ConversionCreateSerializer(
            data=request.data,
            context={'tool_type': self.tool_type}
        )
        
        if not serializer.is_valid():
            return error_response(
                message='Validation error',
                errors={'code': 'VALIDATION_ERROR', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = request.user
        if not user.is_premium and user.daily_usage_count >= user.credits:
            return error_response(
                message='Daily usage limit exceeded',
                errors={
                    'code': 'QUOTA_EXCEEDED',
                    'details': f'You have reached your daily limit of {user.credits} conversions'
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        
        uploaded_file = serializer.validated_data['file']
        conversion = ConversionHistory.objects.create(
            user=user,
            tool_type=self.tool_type,
            input_file=uploaded_file,
            file_size_before=uploaded_file.size,
            status='pending'
        )
        
        task = process_conversion.delay(conversion.id)
        conversion.celery_task_id = task.id
        conversion.save(update_fields=['celery_task_id'])
        
        user.daily_usage_count += 1
        user.save(update_fields=['daily_usage_count'])
        
        try:
            tool = Tool.objects.get(tool_type=self.tool_type)
            tool.increment_usage()
        except Tool.DoesNotExist:
            pass
        
        return success_response(
            data={
                'conversion_id': conversion.id,
                'status': conversion.status,
                'tool_type': conversion.tool_type,
                'file_size_before': conversion.file_size_before,
                'created_at': conversion.created_at.isoformat(),
                'status_url': f'/api/v1/conversions/{conversion.id}/',
            },
            message='Conversion started successfully',
            status=status.HTTP_202_ACCEPTED
        )


class ConvertPDFToDocxView(BaseConversionView):
    tool_type = 'pdf_to_docx'


class ConvertDocxToPDFView(BaseConversionView):
    tool_type = 'docx_to_pdf'


class ConvertXLSXToPDFView(BaseConversionView):
    tool_type = 'xlsx_to_pdf'


class ConvertPPTXToPDFView(BaseConversionView):
    tool_type = 'pptx_to_pdf'


class ConvertImageToPDFView(BaseConversionView):
    tool_type = 'image_to_pdf'


class MergePDFView(BaseConversionView):
    tool_type = 'merge_pdf'


class SplitPDFView(BaseConversionView):
    tool_type = 'split_pdf'


class CompressPDFView(BaseConversionView):
    tool_type = 'compress_pdf'


class CompressImageView(BaseConversionView):
    tool_type = 'compress_image'


class ConvertImageView(BaseConversionView):
    tool_type = 'convert_image'


class CompressVideoView(BaseConversionView):
    tool_type = 'compress_video'


class ExtractTextView(BaseConversionView):
    tool_type = 'extract_text'


# ============================================================================
# Conversion Status and Download Views
# ============================================================================

class ConversionDetailView(generics.RetrieveAPIView):
    """Get conversion status and details."""
    serializer_class = ConversionHistorySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return ConversionHistory.objects.filter(user=self.request.user)
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, context={'request': request})
        
        return success_response(
            data=serializer.data,
            message='Conversion details retrieved successfully'
        )


class ConversionDownloadView(APIView):
    """Download converted file."""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, pk):
        conversion = get_object_or_404(
            ConversionHistory,
            pk=pk,
            user=request.user
        )
        
        if conversion.status != 'completed':
            return error_response(
                message='Conversion not completed',
                errors={
                    'code': 'NOT_COMPLETED',
                    'details': f'Conversion status is {conversion.status}'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not conversion.output_file:
            return error_response(
                message='Output file not found',
                errors={'code': 'FILE_NOT_FOUND', 'details': 'Output file is missing'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        file_url = request.build_absolute_uri(conversion.output_file.url)
        
        return success_response(
            data={
                'download_url': file_url,
                'file_name': conversion.output_file.name.split('/')[-1],
                'file_size': conversion.file_size_after,
            },
            message='Download URL generated successfully'
        )


class ConversionHistoryListView(generics.ListAPIView):
    """List user's conversion history."""
    serializer_class = ConversionHistorySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = ConversionHistory.objects.filter(user=self.request.user)
        
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        tool_type = self.request.query_params.get('tool_type')
        if tool_type:
            queryset = queryset.filter(tool_type=tool_type)
        
        return queryset.order_by('-created_at')
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True, context={'request': request})
        
        return success_response(
            data={
                'conversions': serializer.data,
                'count': queryset.count()
            },
            message='Conversion history retrieved successfully'
        )


# ============================================================================
# User Profile and Usage Views
# ============================================================================

class UserProfileView(generics.RetrieveAPIView):
    """Get user profile information."""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        
        return success_response(
            data=serializer.data,
            message='Profile retrieved successfully'
        )


class UserProfileUpdateView(generics.UpdateAPIView):
    """Update user profile information."""
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        return profile
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        
        if not serializer.is_valid():
            return error_response(
                message='Validation error',
                errors={'code': 'VALIDATION_ERROR', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        self.perform_update(serializer)
        
        return success_response(
            data=serializer.data,
            message='Profile updated successfully'
        )


class UserUsageStatisticsView(APIView):
    """Get user usage statistics."""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        total_conversions = ConversionHistory.objects.filter(user=user).count()
        
        conversions_by_type = dict(
            ConversionHistory.objects.filter(user=user)
            .values('tool_type')
            .annotate(count=Count('id'))
            .values_list('tool_type', 'count')
        )
        
        recent_conversions = ConversionHistory.objects.filter(user=user).order_by('-created_at')[:10]
        recent_serializer = ConversionHistorySerializer(
            recent_conversions,
            many=True,
            context={'request': request}
        )
        
        data = {
            'total_conversions': total_conversions,
            'daily_usage_count': user.daily_usage_count,
            'remaining_credits': max(0, user.credits - user.daily_usage_count),
            'is_premium': user.is_premium,
            'conversions_by_type': conversions_by_type,
            'recent_conversions': recent_serializer.data,
        }
        
        return success_response(
            data=data,
            message='Usage statistics retrieved successfully'
        )


class UserConversionHistoryView(generics.ListAPIView):
    """Get user's conversion history with pagination."""
    serializer_class = ConversionHistorySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return ConversionHistory.objects.filter(user=self.request.user).order_by('-created_at')
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True, context={'request': request})
        
        return success_response(
            data={
                'history': serializer.data,
                'count': queryset.count()
            },
            message='Conversion history retrieved successfully'
        )


# ============================================================================
# API Access Request Views
# ============================================================================

from django.views.generic import FormView, TemplateView
from django.contrib import messages
from django.urls import reverse_lazy
from .forms import APIAccessRequestForm
from .emails import (
    send_api_access_request_confirmation,
    send_api_access_request_notification_to_admins
)
import logging

logger = logging.getLogger('apps.api')


class APIAccessRequestView(FormView):
    """
    View for requesting API access.
    Displays form and handles submission.
    """
    template_name = 'api/api_access_request.html'
    form_class = APIAccessRequestForm
    success_url = reverse_lazy('api:api_access_thank_you')
    
    def form_valid(self, form):
        """Handle valid form submission."""
        # Save the request
        request_obj = form.save()
        
        logger.info(
            f"New API access request submitted: {request_obj.company_name} "
            f"({request_obj.email}) - Request ID: {request_obj.id}"
        )
        
        # Send confirmation email to requester
        try:
            send_api_access_request_confirmation(request_obj)
        except Exception as e:
            logger.error(f"Failed to send confirmation email: {str(e)}")
            # Don't fail the request if email fails
        
        # Send notification to admins
        try:
            send_api_access_request_notification_to_admins(request_obj)
        except Exception as e:
            logger.error(f"Failed to send admin notification: {str(e)}")
            # Don't fail the request if email fails
        
        # Add success message
        messages.success(
            self.request,
            'Your API access request has been submitted successfully! '
            'We will review your application and get back to you within 1-2 business days.'
        )
        
        return super().form_valid(form)
    
    def form_invalid(self, form):
        """Handle invalid form submission."""
        messages.error(
            self.request,
            'There was an error with your submission. Please check the form and try again.'
        )
        return super().form_invalid(form)
    
    def get_context_data(self, **kwargs):
        """Add additional context to template."""
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Request API Access'
        context['page_description'] = (
            'Apply for API access to integrate SmartToolPDF file conversion '
            'capabilities into your application.'
        )
        return context


class APIAccessThankYouView(TemplateView):
    """
    Thank you page displayed after successful API access request submission.
    """
    template_name = 'api/api_access_thank_you.html'
    
    def get_context_data(self, **kwargs):
        """Add additional context to template."""
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Thank You for Your Request'
        return context
