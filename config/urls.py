"""
Configuración de URLs principales de Music Pro Bodega.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('bodega.urls')),
]
