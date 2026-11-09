from django.contrib import admin
from .models import (
    Categoria,
    Proveedor,
    Bodega,
    Sucursal,
    Producto,
    Solicitud,
    DetalleSolicitud,
    Movimiento,
)


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ['id', 'nombre', 'descripcion']
    search_fields = ['nombre']


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ['rut', 'nombre', 'contacto', 'telefono']
    search_fields = ['rut', 'nombre', 'contacto']


@admin.register(Bodega)
class BodegaAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre', 'direccion']
    search_fields = ['codigo', 'nombre']


@admin.register(Sucursal)
class SucursalAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre', 'direccion', 'activa']
    list_filter = ['activa']
    search_fields = ['codigo', 'nombre', 'direccion']


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ['sku', 'nombre', 'categoria', 'proveedor', 'precio', 'stock_minimo', 'activo']
    list_filter = ['categoria', 'proveedor', 'activo']
    search_fields = ['sku', 'nombre']


class DetalleSolicitudInline(admin.TabularInline):
    model = DetalleSolicitud
    extra = 1


@admin.register(Solicitud)
class SolicitudAdmin(admin.ModelAdmin):
    list_display = ['id', 'sucursal', 'usuario_solicitante', 'fecha_solicitud', 'estado']
    list_filter = ['estado', 'sucursal']
    search_fields = ['sucursal__nombre', 'usuario_solicitante__username', 'observaciones']
    inlines = [DetalleSolicitudInline]


@admin.register(DetalleSolicitud)
class DetalleSolicitudAdmin(admin.ModelAdmin):
    list_display = ['id', 'solicitud', 'producto', 'cantidad_solicitada']
    list_filter = ['producto']
    search_fields = ['solicitud__id', 'producto__sku', 'producto__nombre']


@admin.register(Movimiento)
class MovimientoAdmin(admin.ModelAdmin):
    list_display = ['id', 'tipo', 'producto', 'bodega', 'cantidad', 'fecha']
    list_filter = ['tipo', 'bodega']
    search_fields = ['producto__sku', 'producto__nombre', 'observacion']
