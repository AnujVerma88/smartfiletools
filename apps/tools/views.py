"""
Views for tool listing, detail, and file conversion.
"""
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.views.generic import ListView, DetailView

from .models import Tool, ToolCategory, ConversionHistory
from apps.accounts.utils import check_credit_decorator

logger = logging.getLogger('apps.tools')


class ToolListView(ListView):
    """
    Display all active tools grouped by category.
    Includes search functionality.
    """
    model = Tool
    template_name = 'tools/tool_list.html'
    context_object_name = 'tools'
    
    def get_queryset(self):
        """Get active tools, optionally filtered by search query."""
        queryset = Tool.objects.filter(is_active=True).select_related('category')
        
        # Search functionality
        search_query = self.request.GET.get('q', '').strip()
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(category__name__icontains=search_query)
            )
        
        return queryset.order_by('category__display_order', 'display_order')
    
    def get_context_data(self, **kwargs):
        """Add categories and search query to context."""
        context = super().get_context_data(**kwargs)
        
        # Get all active categories
        context['categories'] = ToolCategory.objects.filter(
            is_active=True
        ).prefetch_related('tools').order_by('display_order')
        
        # Group tools by category
        tools_by_category = {}
        for tool in context['tools']:
            category_name = tool.category.name
            if category_name not in tools_by_category:
                tools_by_category[category_name] = []
            tools_by_category[category_name].append(tool)
        
        context['tools_by_category'] = tools_by_category
        context['search_query'] = self.request.GET.get('q', '')
        
        return context


class ToolDetailView(DetailView):
    """
    Display individual tool page with upload interface.
    Shows supported formats and file size limits.
    """
    model = Tool
    template_name = 'tools/tool_detail.html'
    context_object_name = 'tool'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    
    def get_queryset(self):
        """Only show active tools."""
        return Tool.objects.filter(is_active=True).select_related('category')
    
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        
        # Redirect E-Sign tool to its custom upload page
        if self.object.tool_type == 'esign':
            return redirect('esign:upload')
            
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        """Add additional context data."""
        context = super().get_context_data(**kwargs)
        tool = self.object
        
        # Format supported formats for display
        if tool.supported_formats:
            context['supported_formats_display'] = ', '.join(
                f'.{fmt}' for fmt in tool.supported_formats
            )
        else:
            context['supported_formats_display'] = 'All formats'
        
        # Check if user needs premium
        if self.request.user.is_authenticated:
            context['needs_premium'] = tool.is_premium and not self.request.user.is_premium
            context['remaining_conversions'] = self.request.user.daily_usage_count
        else:
            context['needs_premium'] = tool.is_premium
            context['remaining_conversions'] = 0
        
        # Add related tools from the same category
        context['related_tools'] = Tool.objects.filter(
            category=tool.category,
            is_active=True
        ).exclude(id=tool.id).order_by('display_order')[:4]
        
        # Check if tool requires multiple files (e.g., merge PDF)
        context['requires_multiple_files'] = tool.tool_type == 'merge_pdf'
        
        # Check if tool requires split options (e.g., split PDF)
        context['requires_split_options'] = tool.tool_type == 'split_pdf'
        
        return context


def tool_category_view(request, slug):
    """
    Display tools in a specific category.
    
    Args:
        slug: Category slug
    """
    category = get_object_or_404(ToolCategory, slug=slug, is_active=True)
    tools = Tool.objects.filter(
        category=category,
        is_active=True
    ).order_by('display_order')
    
    # Get all categories for "Explore Other Categories" section
    categories = ToolCategory.objects.filter(
        is_active=True
    ).prefetch_related('tools').order_by('display_order')
    
    context = {
        'category': category,
        'tools': tools,
        'categories': categories,
    }
    
    return render(request, 'tools/category_detail.html', context)


@login_required
def conversion_history_view(request):
    """
    Display user's conversion history with pagination.
    """
    conversions = ConversionHistory.objects.filter(
        user=request.user
    ).order_by('-created_at')[:50]  # Limit to 50 most recent
    
    context = {
        'conversions': conversions,
    }
    
    return render(request, 'tools/conversion_history.html', context)


@login_required
def conversion_detail_view(request, conversion_id):
    """
    Display detailed information about a specific conversion with ownership verification.
    
    Args:
        conversion_id: ConversionHistory ID
    """
    from apps.common.permissions import user_owns_conversion, log_access_denied
    
    # Get conversion
    conversion = get_object_or_404(ConversionHistory, id=conversion_id)
    
    # Verify ownership
    if not user_owns_conversion(request.user, conversion):
        log_access_denied(
            request.user,
            'conversion_detail',
            conversion_id,
            'User does not own this conversion'
        )
        messages.error(request, "You don't have permission to view this conversion.")
        return redirect('tools:conversion_history')
    
    context = {
        'conversion': conversion,
    }
    
    return render(request, 'tools/conversion_detail.html', context)



@login_required
@check_credit_decorator
def file_upload_view(request, tool_slug):
    """
    Handle file upload for conversion with comprehensive security validation.
    Validates file size, extension, MIME type, and sanitizes filename.
    
    Args:
        tool_slug: Tool slug identifier
    """
    tool = get_object_or_404(Tool, slug=tool_slug, is_active=True)
    
    if request.method == 'POST':
        uploaded_file = request.FILES.get('file')
        
        if not uploaded_file:
            messages.error(request, 'Please select a file to upload.')
            return redirect('tools:tool_detail', slug=tool_slug)
        
        try:
            # Import security utilities
            from .utils.file_utils import validate_file_comprehensive, FileValidationError
            from .utils.security import sanitize_filename, log_security_event, SecurityError
            
            # Comprehensive file validation (size, extension, MIME type)
            try:
                file_info = validate_file_comprehensive(
                    uploaded_file,
                    tool.max_file_size_mb,
                    tool.supported_formats
                )
                logger.info(
                    f"File validation passed: {file_info['name']} "
                    f"({file_info['size_mb']}MB, {file_info['extension']})"
                )
            except FileValidationError as e:
                # Log security event
                log_security_event(
                    'file_upload_rejected',
                    {
                        'user': request.user.username,
                        'tool': tool.name,
                        'filename': uploaded_file.name,
                        'reason': str(e)
                    },
                    severity='warning'
                )
                messages.error(request, str(e))
                return redirect('tools:tool_detail', slug=tool_slug)
            
            # Sanitize filename for security
            try:
                original_name = uploaded_file.name
                uploaded_file.name = sanitize_filename(original_name)
                if original_name != uploaded_file.name:
                    logger.info(
                        f"Filename sanitized: '{original_name}' -> '{uploaded_file.name}'"
                    )
            except SecurityError as e:
                log_security_event(
                    'filename_sanitization_failed',
                    {
                        'user': request.user.username,
                        'filename': uploaded_file.name,
                        'reason': str(e)
                    },
                    severity='error'
                )
                messages.error(request, 'Invalid filename. Please rename your file and try again.')
                return redirect('tools:tool_detail', slug=tool_slug)
            
            # Check premium requirement
            if tool.is_premium and not request.user.is_premium:
                messages.error(
                    request,
                    'This tool requires a premium subscription. Please upgrade your account.'
                )
                return redirect('tools:tool_detail', slug=tool_slug)
            
            # Create conversion record
            conversion = ConversionHistory.objects.create(
                user=request.user,
                tool_type=tool.tool_type,
                input_file=uploaded_file,
                status='pending',
                file_size_before=uploaded_file.size
            )
            
            # Increment tool usage
            tool.increment_usage()
            
            logger.info(
                f"File uploaded for conversion: {uploaded_file.name} "
                f"(User: {request.user.username}, Tool: {tool.name}, ID: {conversion.id})"
            )
            
            # Redirect to conversion initiation
            return redirect('tools:conversion_initiate', conversion_id=conversion.id)
            
        except Exception as e:
            logger.error(f"Error creating conversion record: {str(e)}", exc_info=True)
            messages.error(request, 'An error occurred while uploading your file. Please try again.')
            return redirect('tools:tool_detail', slug=tool_slug)
    
    # GET request - redirect to tool detail
    return redirect('tools:tool_detail', slug=tool_slug)


@login_required
def conversion_initiate_view(request, conversion_id):
    """
    Initiate conversion by queuing Celery task.
    Returns task ID and redirects to status page.
    
    Args:
        conversion_id: ConversionHistory ID
    """
    conversion = get_object_or_404(
        ConversionHistory,
        id=conversion_id,
        user=request.user
    )
    
    # Check if already processing or completed
    if conversion.status in ['processing', 'completed']:
        return redirect('tools:conversion_status', conversion_id=conversion_id)
    
    try:
        # Import here to avoid circular imports
        from .tasks import process_conversion
        
        # Queue Celery task
        task = process_conversion.delay(conversion_id)
        
        # Update conversion with task ID
        conversion.celery_task_id = task.id
        conversion.status = 'pending'
        conversion.save(update_fields=['celery_task_id', 'status'])
        
        # When running with CELERY_TASK_ALWAYS_EAGER, task runs synchronously
        # Refresh from database to get updated status
        from django.conf import settings
        if settings.CELERY_TASK_ALWAYS_EAGER:
            conversion.refresh_from_db()
        
        logger.info(
            f"Conversion queued: ID={conversion_id}, Task={task.id}, "
            f"User={request.user.username}"
        )
        
        # Set appropriate message based on actual status
        if conversion.status == 'completed':
            messages.success(request, 'Your file has been converted successfully!')
        elif conversion.status == 'failed':
            messages.error(request, f'Conversion failed: {conversion.error_message}')
        else:
            messages.success(request, 'Your file is being processed. Please wait...')
        
    except Exception as e:
        logger.error(f"Error queuing conversion task: {str(e)}")
        conversion.status = 'failed'
        conversion.error_message = f'Failed to queue conversion: {str(e)}'
        conversion.save(update_fields=['status', 'error_message'])
        messages.error(request, 'An error occurred while processing your file.')
    
    return redirect('tools:conversion_status', conversion_id=conversion_id)


@login_required
def conversion_status_view(request, conversion_id):
    """
    Display conversion status page with AJAX polling and ownership verification.
    Shows progress updates and completion status.
    
    Args:
        conversion_id: ConversionHistory ID
    """
    from apps.common.permissions import user_owns_conversion, log_access_denied
    
    # Get conversion
    conversion = get_object_or_404(ConversionHistory, id=conversion_id)
    
    # Verify ownership
    if not user_owns_conversion(request.user, conversion):
        log_access_denied(
            request.user,
            'conversion_status',
            conversion_id,
            'User does not own this conversion'
        )
        messages.error(request, "You don't have permission to view this conversion.")
        return redirect('tools:conversion_history')
    
    context = {
        'conversion': conversion,
    }
    
    return render(request, 'tools/conversion_status.html', context)


@login_required
def conversion_status_api(request, conversion_id):
    """
    AJAX endpoint to check conversion status with ownership verification.
    Returns JSON with current status and progress.
    
    Args:
        conversion_id: ConversionHistory ID
    """
    from django.http import JsonResponse
    from apps.common.permissions import user_owns_conversion, log_access_denied
    
    # Get conversion
    try:
        conversion = ConversionHistory.objects.get(id=conversion_id)
    except ConversionHistory.DoesNotExist:
        return JsonResponse({'error': 'Conversion not found'}, status=404)
    
    # Verify ownership
    if not user_owns_conversion(request.user, conversion):
        log_access_denied(
            request.user,
            'conversion_status_api',
            conversion_id,
            'User does not own this conversion'
        )
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    response_data = {
        'status': conversion.status,
        'tool_type': conversion.get_tool_type_display(),
        'created_at': conversion.created_at.isoformat(),
    }
    
    if conversion.status == 'completed':
        response_data['download_url'] = request.build_absolute_uri(
            f'/tools/download/{conversion_id}/'
        )
        response_data['processing_time'] = conversion.processing_time
        response_data['file_size_before'] = conversion.file_size_before
        response_data['file_size_after'] = conversion.file_size_after
        
        if conversion.file_size_before and conversion.file_size_after:
            response_data['compression_ratio'] = conversion.get_compression_ratio()
    
    elif conversion.status == 'failed':
        response_data['error_message'] = conversion.error_message
    
    return JsonResponse(response_data)


@login_required
def file_download_view(request, conversion_id):
    """
    Serve converted file for download with ownership verification.
    Ensures user owns the conversion before allowing download.
    
    Args:
        conversion_id: ConversionHistory ID
    """
    from apps.common.permissions import user_owns_conversion, log_access_denied
    
    # Get conversion (without filtering by user to check ownership explicitly)
    conversion = get_object_or_404(ConversionHistory, id=conversion_id, status='completed')
    
    # Verify ownership
    if not user_owns_conversion(request.user, conversion):
        log_access_denied(
            request.user,
            'conversion_download',
            conversion_id,
            'User does not own this conversion'
        )
        messages.error(request, "You don't have permission to download this file.")
        return redirect('tools:conversion_history')
    
    if not conversion.output_file:
        messages.error(request, 'Output file not found.')
        return redirect('tools:conversion_status', conversion_id=conversion_id)
    
    try:
        from django.http import FileResponse
        import os
        from .utils.security import validate_file_path, SecurityError
        
        # Get file path
        file_path = conversion.output_file.path
        
        # Validate file path is within allowed directories (security check)
        try:
            from django.conf import settings
            allowed_paths = [
                str(settings.OUTPUT_STORAGE_DIR),
                str(settings.MEDIA_ROOT / 'output')
            ]
            validate_file_path(file_path, allowed_paths)
        except SecurityError as e:
            logger.error(
                f"Security violation: Invalid file path for download: {file_path} "
                f"(User: {request.user.username}, Conversion: {conversion_id})"
            )
            messages.error(request, 'Invalid file path.')
            return redirect('tools:conversion_status', conversion_id=conversion_id)
        
        if not os.path.exists(file_path):
            messages.error(request, 'File not found. It may have been deleted.')
            return redirect('tools:conversion_status', conversion_id=conversion_id)
        
        # Get filename
        filename = os.path.basename(file_path)
        
        # Open file
        file_handle = open(file_path, 'rb')
        
        # Create response with secure headers
        response = FileResponse(file_handle)
        response['Content-Type'] = 'application/octet-stream'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['X-Content-Type-Options'] = 'nosniff'  # Prevent MIME sniffing
        response['X-Frame-Options'] = 'DENY'  # Prevent clickjacking
        
        logger.info(
            f"File downloaded: {filename} "
            f"(User: {request.user.username}, Conversion: {conversion_id})"
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error serving file for download: {str(e)}", exc_info=True)
        messages.error(request, 'An error occurred while downloading the file.')
        return redirect('tools:conversion_status', conversion_id=conversion_id)
