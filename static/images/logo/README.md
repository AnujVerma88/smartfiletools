# SmartToolPDF Logo Assets

## Logo Design Specifications

### Brand Identity
- **Site Name**: SmartToolPDF
- **Domain**: smarttoolpdf.com
- **Tagline**: "Your Smart Solution for PDF and File Conversions"
- **Primary Color**: Teal (#14B8A6)
- **Secondary Color**: Dark Teal (#0F766E)
- **Accent Color**: Light Teal (#5EEAD4)

### Logo Concept
Modern, clean design combining document/file iconography with smart/tech elements. The logo represents intelligent file processing with a focus on PDF tools.

### Logo Variations

#### 1. Full Logo (Horizontal)
- **Dimensions**: 200px × 50px
- **Usage**: Main header, marketing materials
- **Components**: Icon + "SmartToolPDF" text
- **File**: `logo-full.svg`, `logo-full.png`

#### 2. Icon Only
- **Dimensions**: 40px × 40px (square)
- **Usage**: Favicon, mobile menu, app icons
- **Components**: Stylized PDF document with gear/tool symbol
- **File**: `logo-icon.svg`, `logo-icon.png`

#### 3. Stacked Logo
- **Dimensions**: 100px × 100px
- **Usage**: Square spaces, social media
- **Components**: Icon above text
- **File**: `logo-stacked.svg`, `logo-stacked.png`

#### 4. White Version
- **Usage**: Dark backgrounds
- **File**: `logo-white.svg`, `logo-white.png`

#### 5. Monochrome
- **Usage**: Print, special uses
- **File**: `logo-mono.svg`, `logo-mono.png`

### Favicon Specifications
- **favicon.ico**: 16x16, 32x32, 48x48 (multi-resolution)
- **apple-touch-icon.png**: 180x180
- **favicon-32x32.png**: 32x32
- **favicon-16x16.png**: 16x16
- **android-chrome-192x192.png**: 192x192
- **android-chrome-512x512.png**: 512x512

### Logo Design Elements

#### Icon Design
```
┌─────────────┐
│  ┌───────┐  │  PDF Document shape
│  │ ⚙️    │  │  Gear/tool symbol overlay
│  │       │  │  Represents smart processing
│  └───────┘  │
└─────────────┘
```

#### Typography
- **Font Family**: Inter, Poppins, or Montserrat (modern sans-serif)
- **Font Weight**: 600 (Semi-bold) for "Smart"
- **Font Weight**: 400 (Regular) for "ToolPDF"
- **Letter Spacing**: -0.5px for tight, modern look

#### Color Usage
- **Primary Icon**: Teal (#14B8A6)
- **Text**: Dark Teal (#0F766E)
- **Accent/Highlight**: Light Teal (#5EEAD4)
- **White Version**: #FFFFFF
- **Monochrome**: #000000 or #333333

### File Structure
```
static/images/logo/
├── logo-full.svg          # Full color horizontal logo (SVG)
├── logo-full.png          # Full color horizontal logo (PNG, 2x)
├── logo-icon.svg          # Icon only (SVG)
├── logo-icon.png          # Icon only (PNG, 2x)
├── logo-stacked.svg       # Stacked version (SVG)
├── logo-stacked.png       # Stacked version (PNG, 2x)
├── logo-white.svg         # White version for dark backgrounds
├── logo-white.png         # White version (PNG, 2x)
├── logo-mono.svg          # Monochrome version
├── logo-mono.png          # Monochrome version (PNG)
├── favicon.ico            # Multi-resolution favicon
├── apple-touch-icon.png   # Apple touch icon (180x180)
├── favicon-32x32.png      # Favicon 32x32
├── favicon-16x16.png      # Favicon 16x16
├── android-chrome-192x192.png  # Android icon
├── android-chrome-512x512.png  # Android icon
└── README.md              # This file
```

### Usage Guidelines

#### DO:
- Use the full logo in headers and main branding
- Use the icon for favicons and small spaces
- Maintain minimum clear space around logo (equal to height of icon)
- Use white version on dark backgrounds
- Scale proportionally

#### DON'T:
- Distort or stretch the logo
- Change the colors (except for white/mono versions)
- Add effects (shadows, gradients, etc.)
- Place on busy backgrounds
- Use low-resolution versions

### Implementation in Templates

```html
<!-- Full Logo in Header -->
<img src="{% static 'images/logo/logo-full.svg' %}" alt="SmartToolPDF" class="logo">

<!-- Icon Only -->
<img src="{% static 'images/logo/logo-icon.svg' %}" alt="SmartToolPDF" class="logo-icon">

<!-- Favicon Links -->
<link rel="icon" type="image/x-icon" href="{% static 'images/logo/favicon.ico' %}">
<link rel="apple-touch-icon" sizes="180x180" href="{% static 'images/logo/apple-touch-icon.png' %}">
<link rel="icon" type="image/png" sizes="32x32" href="{% static 'images/logo/favicon-32x32.png' %}">
<link rel="icon" type="image/png" sizes="16x16" href="{% static 'images/logo/favicon-16x16.png' %}">
```

### Creating the Logo

To create the actual logo files, you can:

1. **Use a design tool**: Figma, Adobe Illustrator, or Inkscape
2. **Follow the specifications** above
3. **Export in multiple formats**: SVG (vector) and PNG (raster at 2x resolution)
4. **Generate favicons**: Use a favicon generator tool

### Placeholder Logo

Until the actual logo is designed, you can use a text-based placeholder:

```html
<div class="logo-placeholder">
    <span class="logo-icon">📄⚙️</span>
    <span class="logo-text">SmartToolPDF</span>
</div>
```

### Brand Colors Reference

```css
:root {
    --brand-primary: #14B8A6;      /* Teal */
    --brand-primary-rgb: 20, 184, 166;
    --brand-secondary: #0F766E;    /* Dark Teal */
    --brand-accent: #5EEAD4;       /* Light Teal */
    --brand-dark: #134E4A;         /* Very Dark Teal */
    --brand-light: #CCFBF1;        /* Very Light Teal */
}
```
