from django.urls import path
from . import views

urlpatterns = [
    # Página pública de inicio / Landing del sistema de bodega
    path('', views.index, name='index'),
    
    # Dashboard administrativo con métricas e indicadores clave
    path('admin-panel/dashboard/', views.dashboard, name='dashboard'),
    
    # Catálogo de inventario con filtros por categoría y estado
    path('admin-panel/inventario/', views.inventario_lista, name='inventario'),
    
    # Vista Modo Show: Ficha técnica y trazabilidad del producto
    path('admin-panel/producto/<str:codigo>/', views.detalle_producto, name='detalle'),
    
    # Formulario para registro de entradas y salidas de mercadería
    path('admin-panel/movimientos/nuevo/', views.nuevo_movimiento, name='movimiento_nuevo'),
]
