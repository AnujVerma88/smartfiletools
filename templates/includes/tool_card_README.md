# Tool Card Component

## Overview
The tool card component is a responsive, touch-friendly card used to display file conversion tools throughout the SmartToolPDF platform.

## Features
- **Responsive Grid Layout**: Adapts from 1 column (mobile) to 4+ columns (large desktop)
- **Touch-Friendly**: All interactive elements meet 44x44px minimum touch target size
- **Hover Effects**: Smooth animations with visual feedback
- **Accessibility**: Proper ARIA labels and keyboard navigation support
- **Premium Badge**: Visual indicator for premium tools
- **Usage Statistics**: Displays tool popularity

## Usage

### Basic Usage
```django
{% include 'includes/tool_card.html' with tool=tool_object %}
```

### With Featured Flag
```django
{% include 'includes/tool_card.html' with tool=tool_object featured=True %}
```

### In a Grid
```django
<div class="tools-grid">
    {% for tool in tools %}
        {% include 'includes/tool_card.html' with tool=tool %}
    {% endfor %}
</div>
```

## CSS Classes

### Main Classes
- `.tool-card` - Base card styling
- `.tool-card.featured` - Featured tool variant with gradient background
- `.tool-card.premium` - Premium tool styling
- `.tool-card.loading` - Loading state with spinner
- `.tool-card.disabled` - Disabled state

### Grid Container
- `.tools-grid` - Responsive grid container for tool cards

## Responsive Breakpoints

| Screen Size | Columns | Gap | Card Padding |
|-------------|---------|-----|--------------|
| Mobile (320-767px) | 1 | 1rem | 1.5rem |
| Tablet (768-1023px) | 2-3 | 1rem | 1.5rem |
| Desktop (1024-1439px) | 3-4 | 1.5rem | 2rem |
| Large Desktop (1440px+) | 4+ | 2rem | 2rem |

## Accessibility Features
- Minimum 44x44px touch targets
- Proper ARIA labels for screen readers
- Keyboard navigation support
- Focus indicators
- Semantic HTML structure

## Browser Support
- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers (iOS Safari, Chrome Mobile)

## Performance Considerations
- CSS transforms use GPU acceleration
- Reduced motion on mobile devices
- Optimized hover effects
- Lazy loading compatible

## Examples

### Standard Tool Card
```html
<div class="tool-card">
    <a href="/tools/pdf-to-docx/">
        <div class="tool-icon">
            <i class="fas fa-file-pdf"></i>
        </div>
        <h3>PDF to DOCX</h3>
        <p>Convert PDF documents to editable Word files</p>
        <div class="tool-meta">
            <span class="usage-count">
                <i class="fas fa-users"></i>
                <span>1,234 uses</span>
            </span>
        </div>
    </a>
</div>
```

### Premium Tool Card
```html
<div class="tool-card premium">
    <a href="/tools/advanced-pdf-editor/">
        <div class="tool-icon">
            <i class="fas fa-edit"></i>
        </div>
        <h3>Advanced PDF Editor</h3>
        <p>Professional PDF editing with advanced features</p>
        <div class="tool-meta">
            <span class="usage-count">
                <i class="fas fa-users"></i>
                <span>856 uses</span>
            </span>
            <span class="premium-badge">Premium</span>
        </div>
    </a>
</div>
```

## Customization

### Custom Colors
Override CSS variables in your theme:
```css
:root {
    --primary-color: #your-color;
    --primary-color-rgb: r, g, b;
}
```

### Custom Hover Effects
```css
.tool-card:hover {
    /* Your custom hover styles */
}
```

## Testing Checklist
- [ ] Cards display correctly on all screen sizes
- [ ] Hover effects work smoothly
- [ ] Touch targets are at least 44x44px
- [ ] Keyboard navigation works
- [ ] Screen readers announce content properly
- [ ] Premium badges display correctly
- [ ] Loading states work
- [ ] Grid layout adapts responsively
