from django.urls import path
from . import views

urlpatterns = [
    # 1. Página pública de inicio / Landing del sistema
    path('', views.index, name='index'),

    # 2. Autenticación de usuarios (django.contrib.auth)
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # 3. Panel de control administrativo (KPIs y alertas)
    path('admin-panel/dashboard/', views.dashboard, name='dashboard'),

    # 4. Catálogo de inventario con filtros por categoría y estado
    path('admin-panel/inventario/', views.inventario_lista, name='inventario'),
    path('admin-panel/inventario-lista/', views.inventario_lista, name='inventario_lista'),

    # 5. Ficha técnica detallada ("Modo Show") y trazabilidad
    path('admin-panel/producto/<str:codigo>/', views.detalle_producto, name='detalle'),
    path('admin-panel/producto-detalle/<str:codigo>/', views.detalle_producto, name='detalle_producto'),

    # 6. Formulario para registro de entradas, salidas y ajustes
    path('admin-panel/movimientos/nuevo/', views.nuevo_movimiento, name='movimiento_nuevo'),
    path('admin-panel/movimientos-nuevo/', views.nuevo_movimiento, name='nuevo_movimiento'),

    # 7. Gestión y flujo de solicitudes de sucursales
    path('admin-panel/solicitudes/', views.lista_solicitudes, name='lista_solicitudes'),
    path('admin-panel/solicitudes/<int:solicitud_id>/<str:accion>/', views.procesar_solicitud, name='procesar_solicitud'),

    # 8. Módulo de reportes analíticos e indicadores de gestión (20 indicadores)
    path('admin-panel/reportes/', views.reportes_panel, name='reportes_panel'),
]
