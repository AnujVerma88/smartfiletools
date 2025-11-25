# Images Directory

This directory contains all static images for the SmartFileTools platform.

## Directory Structure

```
static/images/
├── logo/           # Brand logos and favicons
├── icons/          # Icon documentation (using Font Awesome)
├── tools/          # Tool-specific images
├── features/       # Feature illustrations
├── hero/           # Hero section images
└── placeholders/   # Placeholder images
```

## Required Images

### Logo Files
- `logo/logo.png` - Main logo (transparent background, 500x500px)
- `logo/logo-white.png` - White version for dark backgrounds
- `logo/logo-icon.png` - Icon only (square, 512x512px)
- `logo/favicon.ico` - Browser favicon (32x32px)
- `logo/apple-touch-icon.png` - iOS home screen icon (180x180px)

### Hero Images
- `hero/hero-bg.jpg` - Hero section background (1920x1080px)
- `hero/hero-illustration.svg` - Hero illustration (vector)

### Feature Images
- `features/fast.svg` - Fast processing illustration
- `features/secure.svg` - Security illustration
- `features/easy.svg` - Easy to use illustration
- `features/cloud.svg` - Cloud storage illustration

### Tool Images (Optional)
- `tools/pdf-converter.png` - PDF conversion preview
- `tools/image-tools.png` - Image tools preview
- `tools/video-tools.png` - Video tools preview

## Image Optimization

All images should be optimized for web:

### JPEG Images
- Quality: 80-85%
- Progressive encoding
- Max width: 1920px for backgrounds, 800px for content

### PNG Images
- Use for logos and icons with transparency
- Compress with tools like TinyPNG
- Max file size: 100KB for logos

### SVG Images
- Preferred for icons and illustrations
- Minify SVG code
- Remove unnecessary metadata

## Responsive Images

Use srcset for responsive images:

```html
<img 
    src="hero/hero-bg.jpg" 
    srcset="hero/hero-bg-sm.jpg 640w,
            hero/hero-bg-md.jpg 1024w,
            hero/hero-bg-lg.jpg 1920w"
    sizes="(max-width: 640px) 640px,
           (max-width: 1024px) 1024px,
           1920px"
    alt="Hero background"
>
```

## Lazy Loading

Enable lazy loading for images below the fold:

```html
<img src="image.jpg" loading="lazy" alt="Description">
```

## Alt Text Guidelines

Always include descriptive alt text:

- **Decorative images**: `alt=""`
- **Informative images**: Describe the content
- **Functional images**: Describe the function
- **Complex images**: Provide detailed description

## Image CDN (Optional)

For production, consider using a CDN:

- Cloudinary
- Imgix
- AWS CloudFront

## Placeholder Images

During development, use placeholder services:

- https://via.placeholder.com/800x600
- https://picsum.photos/800/600
- https://placehold.co/800x600

## Brand Guidelines

### Logo Usage
- Minimum size: 120px width
- Clear space: Equal to height of logo
- Don't distort or rotate
- Don't change colors (except white version)

### Color Palette
- Primary: #14B8A6 (Teal)
- Secondary: #0F766E (Dark Teal)
- Accent: #5EEAD4 (Light Teal)

## File Naming Convention

Use lowercase with hyphens:
- ✅ `hero-background.jpg`
- ✅ `logo-white.png`
- ❌ `HeroBackground.jpg`
- ❌ `logo_white.png`

## Copyright

Ensure all images are:
- Created in-house
- Licensed for commercial use
- Properly attributed if required
- Free from copyright restrictions

## Tools for Image Creation

### Design Tools
- Figma (UI/UX design)
- Adobe Illustrator (vector graphics)
- Canva (quick graphics)

### Optimization Tools
- TinyPNG (PNG compression)
- ImageOptim (Mac)
- Squoosh (web-based)

### Icon Resources
- Font Awesome (icons)
- Heroicons (SVG icons)
- Feather Icons (minimal icons)

## Performance Checklist

- [ ] All images optimized
- [ ] Responsive images implemented
- [ ] Lazy loading enabled
- [ ] Alt text added
- [ ] WebP format considered
- [ ] CDN configured (production)
- [ ] Image dimensions specified in HTML
- [ ] Proper caching headers set
