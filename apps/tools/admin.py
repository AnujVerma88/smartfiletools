"""
Admin interface for tools app models.
"""
from django.contrib import admin
from .models import ToolCategory, Tool, ConversionHistory


class ToolInline(admin.TabularInline):
    """
    Inline admin for tools within a category.
    """
    model = Tool
    extra = 0
    fields = ['name', 'tool_type', 'is_active', 'is_premium', 'display_order']
    readonly_fields = ['usage_count']


@admin.register(ToolCategory)
class ToolCategoryAdmin(admin.ModelAdmin):
    """
    Admin interface for tool categories.
    """
    list_display = ['name', 'slug', 'display_order', 'is_active', 'tool_count', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ToolInline]
    
    fieldsets = (
        ('Category Information', {
            'fields': ('name', 'slug', 'icon', 'description')
        }),
        ('Display Settings', {
            'fields': ('display_order', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def tool_count(self, obj):
        """Display number of tools in this category."""
        return obj.tools.count()
    tool_count.short_description = 'Tools'


@admin.register(Tool)
class ToolAdmin(admin.ModelAdmin):
    """
    Admin interface for individual tools.
    """
    list_display = [
        'name', 'category', 'tool_type', 'is_active', 
        'is_premium', 'usage_count', 'max_file_size_mb', 'has_instructional_content'
    ]
    list_filter = ['category', 'is_active', 'is_premium', 'created_at']
    search_fields = ['name', 'description', 'tool_type']
    prepopulated_fields = {'slug': ('name',)}
    
    fieldsets = (
        ('Tool Information', {
            'fields': ('category', 'name', 'slug', 'description', 'icon')
        }),
        ('Configuration', {
            'fields': ('tool_type', 'max_file_size_mb', 'supported_formats')
        }),
        ('Instructional Content', {
            'fields': (
                'input_format', 
                'output_format', 
                'long_description',
            ),
            'description': 'Content displayed in the "How to Use" section on the tool page. Leave blank to use defaults.',
        }),
        ('Custom Steps (Optional)', {
            'fields': (
                'step_1_title', 
                'step_1_description',
                'step_2_title', 
                'step_2_description',
                'step_3_title', 
                'step_3_description',
            ),
            'classes': ('collapse',),
            'description': (
                'Customize the step-by-step instructions. Leave blank to use default steps. '
                'Default Step 1: "Select Your File" | '
                'Default Step 2: "Start Conversion" | '
                'Default Step 3: "Download Your File"'
            ),
        }),
        ('Settings', {
            'fields': ('is_active', 'is_premium', 'display_order')
        }),
        ('Statistics', {
            'fields': ('usage_count',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['usage_count', 'created_at', 'updated_at']
    
    def has_instructional_content(self, obj):
        """Check if tool has instructional content."""
        return bool(obj.input_format and obj.output_format and obj.long_description)
    has_instructional_content.boolean = True
    has_instructional_content.short_description = 'Has Instructions'
    
    actions = ['activate_tools', 'deactivate_tools', 'make_premium', 'make_free', 'preview_instructions']
    
    def activate_tools(self, request, queryset):
        """Activate selected tools."""
        count = queryset.update(is_active=True)
        self.message_user(request, f'{count} tool(s) activated.', level='success')
    activate_tools.short_description = 'Activate selected tools'
    
    def deactivate_tools(self, request, queryset):
        """Deactivate selected tools."""
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count} tool(s) deactivated.', level='success')
    deactivate_tools.short_description = 'Deactivate selected tools'
    
    def make_premium(self, request, queryset):
        """Mark selected tools as premium."""
        count = queryset.update(is_premium=True)
        self.message_user(request, f'{count} tool(s) marked as premium.', level='success')
    make_premium.short_description = 'Mark as premium'
    
    def make_free(self, request, queryset):
        """Mark selected tools as free."""
        count = queryset.update(is_premium=False)
        self.message_user(request, f'{count} tool(s) marked as free.', level='success')
    make_free.short_description = 'Mark as free'
    
    def preview_instructions(self, request, queryset):
        """Preview instructional content for selected tools."""
        if queryset.count() != 1:
            self.message_user(
                request, 
                'Please select exactly one tool to preview.', 
                level='warning'
            )
            return
        
        tool = queryset.first()
        
        # Build preview message
        preview = f"<h3>Instructional Content Preview: {tool.name}</h3>"
        preview += f"<p><strong>Input Format:</strong> {tool.input_format or '(not set)'}</p>"
        preview += f"<p><strong>Output Format:</strong> {tool.output_format or '(not set)'}</p>"
        preview += f"<p><strong>Description:</strong> {tool.get_tool_description()[:200]}...</p>"
        preview += "<h4>Steps:</h4><ol>"
        
        for i, step in enumerate(tool.get_all_steps(), 1):
            preview += f"<li><strong>{step['title']}</strong><br>{step['description']}</li>"
        
        preview += "</ol>"
        preview += f"<p><a href='/tools/{tool.slug}/' target='_blank'>View Full Page →</a></p>"
        
        from django.utils.html import format_html
        self.message_user(request, format_html(preview), level='success')
    
    preview_instructions.short_description = 'Preview instructional content'


@admin.register(ConversionHistory)
class ConversionHistoryAdmin(admin.ModelAdmin):
    """
    Admin interface for conversion history.
    """
    list_display = ['id', 'user', 'tool_type', 'status', 'created_at']
    list_filter = ['tool_type', 'status', 'created_at']
    search_fields = ['user__username', 'user__email', 'tool_type']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Conversion Information', {
            'fields': ('user', 'tool_type', 'status')
        }),
        ('Files', {
            'fields': ('input_file', 'output_file')
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )
    
    def has_add_permission(self, request):
        """Disable adding conversions through admin."""
        return False
