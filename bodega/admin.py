from django.contrib import admin
from .models import Categoria, Bodega, Producto, Movimiento


class CategoriaAdmin(admin.ModelAdmin):
    list_display = ['id', 'nombre', 'descripcion']
    search_fields = ['nombre']


class BodegaAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre', 'direccion']
    search_fields = ['codigo', 'nombre']


class ProductoAdmin(admin.ModelAdmin):
    list_display = ['sku', 'nombre', 'categoria', 'precio', 'stock_minimo']
    list_filter = ['categoria']
    search_fields = ['sku', 'nombre']


class MovimientoAdmin(admin.ModelAdmin):
    list_display = ['id', 'tipo', 'producto', 'bodega', 'cantidad', 'fecha']
    list_filter = ['tipo', 'bodega']
    search_fields = ['producto__sku', 'producto__nombre']


admin.site.register(Categoria, CategoriaAdmin)
admin.site.register(Bodega, BodegaAdmin)
admin.site.register(Producto, ProductoAdmin)
admin.site.register(Movimiento, MovimientoAdmin)
