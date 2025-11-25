# Icons Guide

This directory contains icons for the SmartFileTools platform.

## Icon Library

We use **Font Awesome 6** for icons. Include in your HTML:

```html
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
```

## Tool Category Icons

### Convert Category
- **Icon**: `<i class="fas fa-exchange-alt"></i>`
- **Color**: Primary (Teal)
- **Usage**: PDF to DOCX, DOCX to PDF, etc.

### Compress Category
- **Icon**: `<i class="fas fa-compress-alt"></i>`
- **Color**: Success (Green)
- **Usage**: PDF Compress, Image Compress, Video Compress

### Edit Category
- **Icon**: `<i class="fas fa-edit"></i>`
- **Color**: Info (Blue)
- **Usage**: Merge PDF, Split PDF, Extract Text

### Image Tools Category
- **Icon**: `<i class="fas fa-image"></i>`
- **Color**: Warning (Orange)
- **Usage**: Image conversion, compression

## Individual Tool Icons

### PDF Tools
- **PDF to DOCX**: `<i class="fas fa-file-word"></i>`
- **DOCX to PDF**: `<i class="fas fa-file-pdf"></i>`
- **PDF to Excel**: `<i class="fas fa-file-excel"></i>`
- **PDF to PowerPoint**: `<i class="fas fa-file-powerpoint"></i>`
- **Merge PDF**: `<i class="fas fa-object-group"></i>`
- **Split PDF**: `<i class="fas fa-cut"></i>`
- **Compress PDF**: `<i class="fas fa-compress"></i>`
- **Extract Text**: `<i class="fas fa-file-alt"></i>`

### Image Tools
- **Image to PDF**: `<i class="fas fa-images"></i>`
- **Compress Image**: `<i class="fas fa-compress-arrows-alt"></i>`
- **Convert Image**: `<i class="fas fa-sync-alt"></i>`

### Video Tools
- **Compress Video**: `<i class="fas fa-video"></i>`

## UI Icons

### Navigation
- **Home**: `<i class="fas fa-home"></i>`
- **Tools**: `<i class="fas fa-tools"></i>`
- **Dashboard**: `<i class="fas fa-tachometer-alt"></i>`
- **Profile**: `<i class="fas fa-user"></i>`
- **Settings**: `<i class="fas fa-cog"></i>`
- **Logout**: `<i class="fas fa-sign-out-alt"></i>`

### Actions
- **Upload**: `<i class="fas fa-cloud-upload-alt"></i>`
- **Download**: `<i class="fas fa-download"></i>`
- **Delete**: `<i class="fas fa-trash-alt"></i>`
- **Edit**: `<i class="fas fa-edit"></i>`
- **Copy**: `<i class="fas fa-copy"></i>`
- **Share**: `<i class="fas fa-share-alt"></i>`
- **Search**: `<i class="fas fa-search"></i>`

### Status
- **Success**: `<i class="fas fa-check-circle"></i>`
- **Error**: `<i class="fas fa-times-circle"></i>`
- **Warning**: `<i class="fas fa-exclamation-triangle"></i>`
- **Info**: `<i class="fas fa-info-circle"></i>`
- **Processing**: `<i class="fas fa-spinner fa-spin"></i>`

### Features
- **Fast**: `<i class="fas fa-bolt"></i>`
- **Secure**: `<i class="fas fa-lock"></i>`
- **Free**: `<i class="fas fa-gift"></i>`
- **Premium**: `<i class="fas fa-crown"></i>`
- **Cloud**: `<i class="fas fa-cloud"></i>`
- **Mobile**: `<i class="fas fa-mobile-alt"></i>`

## Usage Examples

### Tool Card
```html
<div class="tool-card">
    <div class="tool-icon">
        <i class="fas fa-file-word"></i>
    </div>
    <h3>PDF to DOCX</h3>
    <p>Convert PDF files to editable Word documents</p>
</div>
```

### Button with Icon
```html
<button class="btn btn-primary">
    <i class="fas fa-cloud-upload-alt"></i>
    Upload File
</button>
```

### Status Badge
```html
<span class="status-badge status-completed">
    <i class="fas fa-check-circle"></i>
    Completed
</span>
```

## Custom SVG Icons (Optional)

For custom branding, you can add SVG icons in this directory:

- `logo-icon.svg` - App icon/favicon
- `logo-full.svg` - Full logo with text
- `logo-white.svg` - White version for dark backgrounds

## Icon Sizing

Use CSS classes for consistent sizing:

```css
.icon-sm { font-size: 0.875rem; }
.icon-md { font-size: 1rem; }
.icon-lg { font-size: 1.5rem; }
.icon-xl { font-size: 2rem; }
.icon-2xl { font-size: 3rem; }
```

## Accessibility

Always include aria-labels for icon-only buttons:

```html
<button aria-label="Delete file">
    <i class="fas fa-trash-alt"></i>
</button>
```

## Performance

- Font Awesome is loaded from CDN for better caching
- Icons are vector-based, so they scale perfectly
- No additional image files needed for most icons
