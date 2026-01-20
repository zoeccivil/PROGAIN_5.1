"""
theme_constants.py
Definiciones de constantes de diseño, paletas de colores y tipografía para PROGRAIN 5.0.
"""

class AppFonts:
    # Fuentes de sistema que renderizan bien en todos los OS
    MAIN_FONT = "Segoe UI, Roboto, San Francisco, Helvetica Neue, sans-serif"
    MONO_FONT = "Consolas, Monaco, monospace"
    
    # Tamaños
    H1 = "24px"
    H2 = "18px"
    H3 = "16px"
    BODY = "14px"
    SMALL = "12px"

class AppMargins:
    STANDARD = "8px"
    LARGE = "16px"
    SMALL = "4px"
    RADIUS = "6px"  # Bordes redondeados modernos

# Paletas de colores
THEMES = {
    "light": {
        "name": "Light Professional",
        "bg_main": "#F3F4F6",       # Gris muy claro para fondo de app
        "bg_surface": "#FFFFFF",    # Blanco para tarjetas/tablas
        "bg_sidebar": "#FFFFFF",
        "fg_primary": "#1F2937",    # Texto casi negro (menos fatiga que #000000)
        "fg_secondary": "#6B7280",  # Texto gris para subtítulos
        "accent": "#2563EB",        # Azul moderno (Royal Blue)
        "accent_hover": "#1D4ED8",
        "accent_text": "#FFFFFF",
        "border": "#E5E7EB",
        "success": "#10B981",
        "warning": "#F59E0B",
        "danger": "#EF4444",
        "table_alt": "#F9FAFB",     # Zebra striping muy sutil
        "sidebar_text": "#4B5563",
        "sidebar_hover": "#F3F4F6",
        "sidebar_active": "#EFF6FF",
        "sidebar_active_text": "#2563EB"
    },
    "dark": {
        "name": "Dark Professional",
        "bg_main": "#111827",       # Gris muy oscuro (mejor que negro puro)
        "bg_surface": "#1F2937",
        "bg_sidebar": "#1F2937",
        "fg_primary": "#F9FAFB",
        "fg_secondary": "#9CA3AF",
        "accent": "#3B82F6",        # Azul un poco más claro para modo oscuro
        "accent_hover": "#60A5FA",
        "accent_text": "#FFFFFF",
        "border": "#374151",
        "success": "#34D399",
        "warning": "#FBBF24",
        "danger": "#F87171",
        "table_alt": "#252f3f",     
        "sidebar_text": "#D1D5DB",
        "sidebar_hover": "#374151",
        "sidebar_active": "#1E3A8A", # Azul oscuro muy sutil
        "sidebar_active_text": "#60A5FA"
    },
    "midnight": {
        "name": "Midnight Premium",
        "bg_main": "#0F172A",       # Azul noche profundo
        "bg_surface": "#1E293B",
        "bg_sidebar": "#020617",
        "fg_primary": "#E2E8F0",
        "fg_secondary": "#94A3B8",
        "accent": "#818CF8",        # Índigo vibrante
        "accent_hover": "#A5B4FC",
        "accent_text": "#0F172A",
        "border": "#334155",
        "success": "#4ADE80",
        "warning": "#FACC15",
        "danger": "#F472B6",
        "table_alt": "#1a2436",
        "sidebar_text": "#CBD5E1",
        "sidebar_hover": "#334155",
        "sidebar_active": "#312E81",
        "sidebar_active_text": "#C7D2FE"
    },
    "coral": {
        "name": "Sunset Professional",
        "bg_main": "#FFF7ED",       # Crema cálido
        "bg_surface": "#FFFFFF",
        "bg_sidebar": "#FFEDD5",
        "fg_primary": "#431407",    # Marrón muy oscuro
        "fg_secondary": "#9A3412",
        "accent": "#EA580C",        # Naranja quemado
        "accent_hover": "#C2410C",
        "accent_text": "#FFFFFF",
        "border": "#FED7AA",
        "success": "#059669",
        "warning": "#D97706",
        "danger": "#DC2626",
        "table_alt": "#fffaf5",
        "sidebar_text": "#7C2D12",
        "sidebar_hover": "#FED7AA",
        "sidebar_active": "#FFedd5",
        "sidebar_active_text": "#EA580C"
    },
    "high_contrast": {
        "name": "High Contrast (Accesibilidad)",
        "bg_main": "#000000",
        "bg_surface": "#000000",
        "bg_sidebar": "#000000",
        "fg_primary": "#FFFFFF",
        "fg_secondary": "#FFFF00",  # Amarillo puro
        "accent": "#00FFFF",        # Cyan puro
        "accent_hover": "#FFFFFF",
        "accent_text": "#000000",
        "border": "#FFFFFF",        # Bordes blancos fuertes
        "success": "#00FF00",
        "warning": "#FFFF00",
        "danger": "#FF0000",
        "table_alt": "#000000",
        "sidebar_text": "#FFFFFF",
        "sidebar_hover": "#333333",
        "sidebar_active": "#00FFFF",
        "sidebar_active_text": "#000000"
    }
}