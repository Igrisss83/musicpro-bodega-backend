"""
Controladores y Lógica de Negocio — Music Pro Bodega Central
Evaluación N°3: Tecnologías del Lado del Servidor (INACAP)
"""

from decimal import Decimal
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import (
    Sum, Case, When, IntegerField, F, Value, Q, Count, Avg, DecimalField
)
from django.db.models.functions import Coalesce
from django.utils import timezone

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


# ==============================================================================
# 1. FUNCIONES AUXILIARES DE CÁLCULO DE STOCK Y METADATOS
# ==============================================================================

def obtener_expresion_stock():
    """
    Retorna la expresión ORM para calcular el stock actual en tiempo real
    a partir de las relaciones de Movimientos de un Producto:
    ENTRADA: suma (+)
    AJUSTE: suma (+)
    SALIDA: resta (-)
    """
    return Coalesce(
        Sum(
            Case(
                When(movimientos__tipo='ENTRADA', then=F('movimientos__cantidad')),
                When(movimientos__tipo='AJUSTE', then=F('movimientos__cantidad')),
                When(movimientos__tipo='SALIDA', then=-F('movimientos__cantidad')),
                default=Value(0),
                output_field=IntegerField()
            )
        ),
        Value(0)
    )


def enriquecer_producto(prod, stock=None):
    """
    Calcula dinámicamente el stock actual en tiempo real de un producto y
    añade atributos visuales y metadatos para las plantillas.
    """
    prod.codigo = prod.sku
    prod.pasillo = getattr(prod, 'pasillo', "Pasillo A")
    prod.estante = getattr(prod, 'estante', "Estante 1 - Nivel 2")

    if stock is not None:
        prod.stock_actual = max(0, int(stock))
    elif not hasattr(prod, 'stock_actual'):
        stock_calc = Movimiento.objects.filter(producto=prod).aggregate(
            total=Coalesce(
                Sum(
                    Case(
                        When(tipo='ENTRADA', then=F('cantidad')),
                        When(tipo='AJUSTE', then=F('cantidad')),
                        When(tipo='SALIDA', then=-F('cantidad')),
                        default=Value(0),
                        output_field=IntegerField()
                    )
                ),
                Value(0)
            )
        )['total']
        prod.stock_actual = max(0, int(stock_calc or 0))

    # Determinación de estado operativo y semáforos UI
    prod.es_critico = prod.stock_actual <= prod.stock_minimo

    if prod.stock_actual == 0:
        prod.estado_label = "Agotado"
        prod.estado_badge = "bg-danger"
        prod.estado_card = "border-danger"
    elif prod.es_critico:
        prod.estado_label = "Stock Crítico"
        prod.estado_badge = "bg-warning text-dark"
        prod.estado_card = "border-warning"
    else:
        prod.estado_label = "Óptimo"
        prod.estado_badge = "bg-success"
        prod.estado_card = "border-success"

    return prod


def enriquecer_movimiento(mov):
    """Agrega atributos auxiliares a la instancia de Movimiento para las plantillas."""
    mov.codigo = mov.producto.sku
    mov.nombre = mov.producto.nombre
    mov.responsable = "Operador de Bodega Central"
    mov.glosa = mov.observacion
    return mov


# ==============================================================================
# 2. AUTENTICACIÓN Y CONTROL DE ACCESO
# ==============================================================================

def login_view(request):
    """
    Vista de inicio de sesión personalizada utilizando django.contrib.auth
    sin depender del panel de administración por defecto.
    """
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'¡Bienvenido(a) a Bodega Central, {user.first_name or user.username}!')
            next_url = request.POST.get('next') or request.GET.get('next') or 'dashboard'
            return redirect(next_url)
        else:
            messages.error(request, 'Credenciales inválidas. Verifique su usuario y contraseña.')
    else:
        form = AuthenticationForm(request)

    return render(request, 'login.html', {
        'form': form,
        'next': request.GET.get('next', '')
    })


def logout_view(request):
    """Cierra la sesión del usuario actual y redirige a la pantalla de login."""
    logout(request)
    messages.info(request, 'Has cerrado sesión correctamente. ¡Hasta pronto!')
    return redirect('login')


# ==============================================================================
# 3. VISTAS PÚBLICAS Y DE GESTIÓN OPERATIVA
# ==============================================================================

def index(request):
    """Landing pública institucional de Music Pro Bodega Central."""
    total_items = Producto.objects.filter(activo=True).count()
    return render(request, 'index.html', {
        'total_items': total_items
    })


@login_required(login_url='login')
def dashboard(request):
    """
    Dashboard administrativo principal con KPIs clave, alertas críticas
    y trazabilidad de los últimos movimientos.
    """
    stock_expr = obtener_expresion_stock()
    productos_qs = Producto.objects.select_related('categoria', 'proveedor').annotate(calc_stock=stock_expr)
    productos = [enriquecer_producto(p, stock=p.calc_stock) for p in productos_qs]

    total_items = len(productos)
    total_unidades = sum(p.stock_actual for p in productos)
    productos_criticos = [p for p in productos if p.es_critico]
    alertas_criticas = len(productos_criticos)

    ultimos_movimientos_qs = Movimiento.objects.select_related('producto', 'bodega').order_by('-fecha')[:8]
    ultimos_movimientos = [enriquecer_movimiento(m) for m in ultimos_movimientos_qs]

    # Indicadores rápidos de solicitudes
    solicitudes_pendientes = Solicitud.objects.filter(estado='PENDIENTE').count()
    total_sucursales = Sucursal.objects.filter(activa=True).count()

    context = {
        'total_items': total_items,
        'total_unidades': total_unidades,
        'alertas_criticas': alertas_criticas,
        'ultimos_movimientos': ultimos_movimientos,
        'productos_criticos': productos_criticos,
        'solicitudes_pendientes': solicitudes_pendientes,
        'total_sucursales': total_sucursales,
    }
    return render(request, 'dashboard.html', context)


@login_required(login_url='login')
def inventario_lista(request):
    """Catálogo completo de productos con filtros combinables por categoría, estado y búsqueda."""
    categorias = list(Categoria.objects.values_list('nombre', flat=True).order_by('nombre'))

    cat_filtro = request.GET.get('categoria', '').strip()
    busqueda = request.GET.get('q', '').strip()
    estado_filtro = request.GET.get('estado', '').strip()

    stock_expr = obtener_expresion_stock()
    qs = Producto.objects.select_related('categoria', 'proveedor').annotate(calc_stock=stock_expr)

    if cat_filtro:
        qs = qs.filter(categoria__nombre=cat_filtro)

    if busqueda:
        qs = qs.filter(Q(sku__icontains=busqueda) | Q(nombre__icontains=busqueda))

    productos = [enriquecer_producto(p, stock=p.calc_stock) for p in qs]

    if estado_filtro == 'critico':
        productos_filtrados = [p for p in productos if p.es_critico]
    elif estado_filtro == 'optimo':
        productos_filtrados = [p for p in productos if not p.es_critico]
    elif estado_filtro == 'agotado':
        productos_filtrados = [p for p in productos if p.stock_actual == 0]
    else:
        productos_filtrados = productos

    context = {
        'productos': productos_filtrados,
        'categorias': categorias,
        'cat_filtro': cat_filtro,
        'busqueda': busqueda,
        'estado_filtro': estado_filtro,
        'total_filtrados': len(productos_filtrados),
    }
    return render(request, 'inventario.html', context)


@login_required(login_url='login')
def detalle_producto(request, codigo):
    """Ficha técnica detallada e historial de trazabilidad de un producto específico."""
    producto = Producto.objects.select_related('categoria', 'proveedor').filter(sku__iexact=codigo).first()

    if not producto:
        messages.error(request, f'No se encontró ningún producto registrado con el código "{codigo}".')
        return redirect('inventario')

    producto = enriquecer_producto(producto)
    movimientos_qs = Movimiento.objects.filter(producto=producto).select_related('bodega').order_by('-fecha')[:50]
    movimientos = [enriquecer_movimiento(m) for m in movimientos_qs]

    context = {
        'producto': producto,
        'movimientos': movimientos,
    }
    return render(request, 'detalle.html', context)


@login_required(login_url='login')
def nuevo_movimiento(request):
    """
    Formulario operativo para registrar entradas, salidas y ajustes de stock
    con validaciones estrictas en el servidor para evitar descuadres.
    """
    productos_qs = Producto.objects.filter(activo=True).select_related('categoria').order_by('nombre')
    inventario = [enriquecer_producto(p) for p in productos_qs]
    codigo_preseleccionado = request.GET.get('codigo', '').strip()

    if request.method == 'POST':
        codigo = request.POST.get('codigo', '').strip()
        tipo_form = request.POST.get('tipo', '').strip()
        cantidad_raw = request.POST.get('cantidad', '').strip()
        responsable = request.POST.get('responsable', '').strip()
        glosa = request.POST.get('glosa', '').strip()

        producto = Producto.objects.filter(sku__iexact=codigo).first()

        form_data = {
            'codigo': codigo,
            'tipo': tipo_form,
            'cantidad': cantidad_raw,
            'responsable': responsable,
            'glosa': glosa
        }

        errores = False

        if not producto:
            messages.error(request, 'Debe seleccionar un producto válido de la lista.')
            errores = True

        try:
            cantidad = int(cantidad_raw)
            if cantidad <= 0:
                messages.error(request, 'La cantidad debe ser un número entero estrictamente mayor a 0.')
                errores = True
        except (ValueError, TypeError):
            messages.error(request, 'Ingrese un valor numérico válido para la cantidad.')
            errores = True
            cantidad = 0

        # Mapeo y validación de tipos
        if tipo_form in ['Ingreso', 'ENTRADA']:
            tipo_db = 'ENTRADA'
        elif tipo_form in ['Salida', 'SALIDA']:
            tipo_db = 'SALIDA'
        elif tipo_form in ['Ajuste', 'AJUSTE']:
            tipo_db = 'AJUSTE'
        else:
            messages.error(request, 'El tipo de movimiento debe ser "Ingreso", "Salida" o "Ajuste".')
            errores = True
            tipo_db = None

        # Validación estricta de stock disponible para salidas
        if not errores and producto and tipo_db == 'SALIDA':
            producto = enriquecer_producto(producto)
            if cantidad > producto.stock_actual:
                messages.error(
                    request,
                    f'Operación rechazada: La cantidad requerida ({cantidad} un.) excede el stock '
                    f'disponible actual ({producto.stock_actual} un.) de "{producto.nombre}".'
                )
                errores = True

        if errores:
            return render(request, 'movimiento.html', {
                'inventario': inventario,
                'codigo_preseleccionado': codigo,
                'form_data': form_data
            })

        # Asignar Bodega Central por defecto
        bodega = Bodega.objects.first()
        if not bodega:
            bodega = Bodega.objects.create(
                nombre="Bodega Central Santiago",
                codigo="BOD-CENTRAL",
                direccion="Av. Providencia 1234, Santiago"
            )

        observacion_final = glosa
        resp_nombre = responsable or (request.user.get_full_name() or request.user.username)
        observacion_final = f"{glosa} (Resp: {resp_nombre})" if glosa else f"Resp: {resp_nombre}"

        Movimiento.objects.create(
            producto=producto,
            bodega=bodega,
            tipo=tipo_db,
            cantidad=cantidad,
            observacion=observacion_final
        )

        producto = enriquecer_producto(producto)
        messages.success(
            request,
            f'¡Movimiento de {tipo_db.lower()} registrado con éxito! El stock actualizado de '
            f'"{producto.nombre}" es de {producto.stock_actual} unidades.'
        )
        return redirect('detalle', codigo=producto.sku)

    return render(request, 'movimiento.html', {
        'inventario': inventario,
        'codigo_preseleccionado': codigo_preseleccionado
    })


# ==============================================================================
# 4. FLUJO DE SOLICITUDES DE SUCURSALES
# ==============================================================================

@login_required(login_url='login')
def lista_solicitudes(request):
    """
    Listado y administración de solicitudes realizadas por sucursales a Bodega Central.
    Permite filtrar por estado, sucursal y crear nuevas solicitudes de prueba.
    """
    estado_filtro = request.GET.get('estado', '').strip()
    sucursal_filtro = request.GET.get('sucursal', '').strip()

    solicitudes_qs = Solicitud.objects.select_related(
        'sucursal', 'usuario_solicitante'
    ).prefetch_related(
        'detalles__producto'
    ).all()

    if estado_filtro:
        solicitudes_qs = solicitudes_qs.filter(estado=estado_filtro)
    if sucursal_filtro:
        solicitudes_qs = solicitudes_qs.filter(sucursal__id=sucursal_filtro)

    # Procesar creación rápida de solicitud desde modal/formulario POST
    if request.method == 'POST' and request.POST.get('accion') == 'crear_solicitud':
        sucursal_id = request.POST.get('sucursal_id')
        producto_id = request.POST.get('producto_id')
        cantidad_raw = request.POST.get('cantidad', '1')
        observaciones = request.POST.get('observaciones', '').strip()

        try:
            cantidad = int(cantidad_raw)
            if cantidad <= 0:
                raise ValueError()
            sucursal = Sucursal.objects.get(id=sucursal_id)
            producto = Producto.objects.get(id=producto_id)

            with transaction.atomic():
                nueva_sol = Solicitud.objects.create(
                    sucursal=sucursal,
                    usuario_solicitante=request.user,
                    estado='PENDIENTE',
                    observaciones=observaciones
                )
                DetalleSolicitud.objects.create(
                    solicitud=nueva_sol,
                    producto=producto,
                    cantidad_solicitada=cantidad
                )
            messages.success(request, f'¡Solicitud #{nueva_sol.id} creada exitosamente para {sucursal.nombre}!')
            return redirect('lista_solicitudes')
        except Exception as e:
            messages.error(request, f'Error al registrar la solicitud: {str(e)}')

    # Enriquecer detalles con información de stock actual en bodega para facilidad visual
    solicitudes = []
    for sol in solicitudes_qs:
        detalles_info = []
        puede_aprobar = True
        for d in sol.detalles.all():
            prod = enriquecer_producto(d.producto)
            suficiente = prod.stock_actual >= d.cantidad_solicitada
            if not suficiente:
                puede_aprobar = False
            detalles_info.append({
                'detalle': d,
                'stock_actual': prod.stock_actual,
                'suficiente': suficiente,
            })
        sol.detalles_enriquecidos = detalles_info
        sol.puede_aprobar = puede_aprobar
        solicitudes.append(sol)

    sucursales = Sucursal.objects.filter(activa=True).order_by('nombre')
    productos = Producto.objects.filter(activo=True).order_by('nombre')

    context = {
        'solicitudes': solicitudes,
        'sucursales': sucursales,
        'productos': productos,
        'estado_filtro': estado_filtro,
        'sucursal_filtro': sucursal_filtro,
        'estados': Solicitud.ESTADOS,
    }
    return render(request, 'solicitudes.html', context)


@login_required(login_url='login')
def procesar_solicitud(request, solicitud_id, accion):
    """
    Controlador de acciones sobre solicitudes:
    - 'aprobar': Valida stock disponible de todos los productos en Bodega Central.
      Si hay suficiente, cambia estado a 'APROBADA' y crea automáticamente los
      Movimientos de 'SALIDA'. Si no hay stock, rechaza la operación con mensaje explicativo.
    - 'rechazar': Cambia el estado a 'RECHAZADA'.
    - 'despachar': Cambia el estado de una solicitud previamente aprobada a 'DESPACHADA'.
    """
    solicitud = get_object_or_404(
        Solicitud.objects.select_related('sucursal', 'usuario_solicitante'),
        id=solicitud_id
    )

    bodega_central = Bodega.objects.first()
    if not bodega_central:
        bodega_central = Bodega.objects.create(
            nombre="Bodega Central Santiago",
            codigo="BOD-CENTRAL",
            direccion="Av. Providencia 1234, Santiago"
        )

    accion = accion.lower().strip()

    if accion == 'aprobar':
        if solicitud.estado != 'PENDIENTE':
            messages.warning(
                request,
                f'La solicitud #{solicitud.id} ya se encuentra en estado "{solicitud.get_estado_display()}" '
                f'y no puede ser aprobada nuevamente.'
            )
            return redirect('lista_solicitudes')

        detalles = list(solicitud.detalles.select_related('producto').all())
        if not detalles:
            messages.error(request, f'La solicitud #{solicitud.id} no posee productos asociados.')
            return redirect('lista_solicitudes')

        # Verificación estricta de stock disponible para TODOS los productos requeridos
        faltantes = []
        for det in detalles:
            prod = enriquecer_producto(det.producto)
            if prod.stock_actual < det.cantidad_solicitada:
                faltantes.append(
                    f'"{prod.nombre}" (Disponible: {prod.stock_actual} un., Requerido: {det.cantidad_solicitada} un.)'
                )

        if faltantes:
            detalle_faltantes = "; ".join(faltantes)
            messages.error(
                request,
                f'Operación rechazada: No hay stock suficiente en Bodega Central para aprobar la '
                f'solicitud #{solicitud.id}. Ítems con quiebre: {detalle_faltantes}.'
            )
            return redirect('lista_solicitudes')

        # Aprobación atómica y generación de movimientos de SALIDA
        with transaction.atomic():
            solicitud.estado = 'APROBADA'
            solicitud.save()

            for det in detalles:
                Movimiento.objects.create(
                    producto=det.producto,
                    bodega=bodega_central,
                    tipo='SALIDA',
                    cantidad=det.cantidad_solicitada,
                    observacion=(
                        f"Despacho Solicitud #{solicitud.id} hacia sucursal "
                        f"{solicitud.sucursal.nombre} (Aprobado por: {request.user.username})"
                    )
                )

        messages.success(
            request,
            f'¡Solicitud #{solicitud.id} APROBADA exitosamente! Se generaron {len(detalles)} '
            f'movimientos de salida en Bodega Central y el stock fue actualizado automáticamente.'
        )

    elif accion == 'rechazar':
        if solicitud.estado == 'DESPACHADA':
            messages.error(request, f'No se puede rechazar la solicitud #{solicitud.id} porque ya fue despachada.')
            return redirect('lista_solicitudes')

        solicitud.estado = 'RECHAZADA'
        solicitud.save()
        messages.warning(
            request,
            f'La solicitud #{solicitud.id} de la sucursal "{solicitud.sucursal.nombre}" fue RECHAZADA.'
        )

    elif accion == 'despachar':
        if solicitud.estado != 'APROBADA':
            messages.error(
                request,
                f'Solo las solicitudes aprobadas pueden marcarse como despachadas. '
                f'Estado actual: "{solicitud.get_estado_display()}".'
            )
            return redirect('lista_solicitudes')

        solicitud.estado = 'DESPACHADA'
        solicitud.save()
        messages.success(
            request,
            f'¡Solicitud #{solicitud.id} marcada como DESPACHADA hacia sucursal {solicitud.sucursal.nombre}!'
        )

    else:
        messages.error(request, f'Acción "{accion}" no reconocida en el sistema.')

    return redirect('lista_solicitudes')


# ==============================================================================
# 5. MÓDULO DE REPORTES Y ANALÍTICA (20 INDICADORES ORM)
# ==============================================================================

@login_required(login_url='login')
def reportes_panel(request):
    """
    Panel integral de reportes ejecutivos e indicadores de rendimiento (KPIs).
    Implementa 20 consultas ORM optimizadas mediante agregaciones y anotaciones.
    """
    ahora = timezone.now()
    hace_30_dias = ahora - timedelta(days=30)
    stock_expr = obtener_expresion_stock()

    # Todos los productos con stock anotado
    todos_productos = [
        enriquecer_producto(p, stock=p.calc_stock)
        for p in Producto.objects.select_related('categoria', 'proveedor').annotate(calc_stock=stock_expr)
    ]

    # -------------------------------------------------------------------------
    # INDICADOR 1: Productos con stock bajo el mínimo o en alerta crítica
    # -------------------------------------------------------------------------
    ind1_productos_criticos = [p for p in todos_productos if p.es_critico]
    ind1_conteo = len(ind1_productos_criticos)

    # -------------------------------------------------------------------------
    # INDICADOR 2: Top 10 productos más caros del catálogo
    # -------------------------------------------------------------------------
    ind2_top10_caros = Producto.objects.filter(activo=True).select_related(
        'categoria', 'proveedor'
    ).order_by('-precio')[:10]

    # -------------------------------------------------------------------------
    # INDICADOR 3: Conteo y distribución de productos por categoría
    # -------------------------------------------------------------------------
    ind3_conteo_por_categoria = Categoria.objects.annotate(
        total_productos=Count('productos')
    ).order_by('-total_productos')

    # -------------------------------------------------------------------------
    # INDICADOR 4: Total de solicitudes por estado (Pendientes, Aprobadas, etc.)
    # -------------------------------------------------------------------------
    ind4_solicitudes_estados = Solicitud.objects.values('estado').annotate(
        total=Count('id')
    ).order_by('estado')
    ind4_resumen_estados = {
        'PENDIENTE': 0,
        'APROBADA': 0,
        'RECHAZADA': 0,
        'DESPACHADA': 0,
    }
    for item in ind4_solicitudes_estados:
        ind4_resumen_estados[item['estado']] = item['total']

    # -------------------------------------------------------------------------
    # INDICADOR 5: Top 5 sucursales con más solicitudes emitidas
    # -------------------------------------------------------------------------
    ind5_top_sucursales = Sucursal.objects.annotate(
        total_solicitudes=Count('solicitudes')
    ).order_by('-total_solicitudes')[:5]

    # -------------------------------------------------------------------------
    # INDICADOR 6: Top 5 productos más solicitados por las sucursales
    # -------------------------------------------------------------------------
    ind6_top_solicitados = DetalleSolicitud.objects.values(
        'producto__sku', 'producto__nombre'
    ).annotate(
        total_unidades=Coalesce(Sum('cantidad_solicitada'), Value(0)),
        veces_pedido=Count('id')
    ).order_by('-total_unidades')[:5]

    # -------------------------------------------------------------------------
    # INDICADOR 7: Valor total monetario estimado del inventario en bodega (CLP)
    # -------------------------------------------------------------------------
    ind7_valor_total_inventario = sum(p.stock_actual * p.precio for p in todos_productos)

    # -------------------------------------------------------------------------
    # INDICADOR 8: Total de salidas registradas en el último mes (30 días)
    # -------------------------------------------------------------------------
    ind8_salidas_mes = Movimiento.objects.filter(
        tipo='SALIDA',
        fecha__gte=hace_30_dias
    ).aggregate(
        total_unidades=Coalesce(Sum('cantidad'), Value(0)),
        total_movimientos=Count('id')
    )

    # -------------------------------------------------------------------------
    # INDICADOR 9: Total de entradas registradas en el último mes (30 días)
    # -------------------------------------------------------------------------
    ind9_entradas_mes = Movimiento.objects.filter(
        tipo='ENTRADA',
        fecha__gte=hace_30_dias
    ).aggregate(
        total_unidades=Coalesce(Sum('cantidad'), Value(0)),
        total_movimientos=Count('id')
    )

    # -------------------------------------------------------------------------
    # INDICADOR 10: Top 5 proveedores con más productos en catálogo
    # -------------------------------------------------------------------------
    ind10_top_proveedores = Proveedor.objects.annotate(
        total_productos=Count('productos')
    ).order_by('-total_productos')[:5]

    # -------------------------------------------------------------------------
    # INDICADOR 11: Total de productos totalmente agotados (Stock = 0)
    # -------------------------------------------------------------------------
    ind11_productos_agotados = [p for p in todos_productos if p.stock_actual == 0]
    ind11_conteo = len(ind11_productos_agotados)

    # -------------------------------------------------------------------------
    # INDICADOR 12: Total de productos con stock en nivel óptimo
    # -------------------------------------------------------------------------
    ind12_productos_optimos = [p for p in todos_productos if not p.es_critico]
    ind12_conteo = len(ind12_productos_optimos)

    # -------------------------------------------------------------------------
    # INDICADOR 13: Precio promedio de productos por categoría
    # -------------------------------------------------------------------------
    ind13_promedio_categoria = Categoria.objects.annotate(
        precio_promedio=Coalesce(Avg('productos__precio'), Value(Decimal('0.00'), output_field=DecimalField()))
    ).order_by('-precio_promedio')

    # -------------------------------------------------------------------------
    # INDICADOR 14: Total global de unidades físicas almacenadas en bodega
    # -------------------------------------------------------------------------
    ind14_total_unidades_fisicas = sum(p.stock_actual for p in todos_productos)

    # -------------------------------------------------------------------------
    # INDICADOR 15: Conteo histórico total de movimientos por tipo
    # -------------------------------------------------------------------------
    ind15_movimientos_tipo = Movimiento.objects.values('tipo').annotate(
        operaciones=Count('id'),
        unidades=Coalesce(Sum('cantidad'), Value(0))
    ).order_by('tipo')

    # -------------------------------------------------------------------------
    # INDICADOR 16: Top 5 productos con mayor rotación / salidas de bodega
    # -------------------------------------------------------------------------
    ind16_top_rotacion = Movimiento.objects.filter(
        tipo='SALIDA'
    ).values(
        'producto__sku', 'producto__nombre'
    ).annotate(
        total_salidas=Coalesce(Sum('cantidad'), Value(0))
    ).order_by('-total_salidas')[:5]

    # -------------------------------------------------------------------------
    # INDICADOR 17: Top 5 usuarios que más solicitudes han emitido
    # -------------------------------------------------------------------------
    ind17_top_usuarios = User.objects.annotate(
        total_solicitudes=Count('solicitudes')
    ).filter(total_solicitudes__gt=0).order_by('-total_solicitudes')[:5]

    # -------------------------------------------------------------------------
    # INDICADOR 18: Tasa porcentual de aprobación de solicitudes
    # -------------------------------------------------------------------------
    total_solicitudes = Solicitud.objects.count()
    aprobadas_o_despachadas = Solicitud.objects.filter(estado__in=['APROBADA', 'DESPACHADA']).count()
    if total_solicitudes > 0:
        ind18_tasa_aprobacion = round((aprobadas_o_despachadas / total_solicitudes) * 100, 1)
    else:
        ind18_tasa_aprobacion = 0.0

    # -------------------------------------------------------------------------
    # INDICADOR 19: Distribución de sucursales activas vs inactivas
    # -------------------------------------------------------------------------
    ind19_sucursales_estado = Sucursal.objects.aggregate(
        activas=Count('id', filter=Q(activa=True)),
        inactivas=Count('id', filter=Q(activa=False)),
        total=Count('id')
    )

    # -------------------------------------------------------------------------
    # INDICADOR 20: Trazabilidad de las últimas 10 solicitudes registradas
    # -------------------------------------------------------------------------
    ind20_ultimas_solicitudes = Solicitud.objects.select_related(
        'sucursal', 'usuario_solicitante'
    ).prefetch_related(
        'detalles__producto'
    ).order_by('-fecha_solicitud')[:10]

    context = {
        'ind1_productos_criticos': ind1_productos_criticos,
        'ind1_conteo': ind1_conteo,
        'ind2_top10_caros': ind2_top10_caros,
        'ind3_conteo_por_categoria': ind3_conteo_por_categoria,
        'ind4_resumen_estados': ind4_resumen_estados,
        'ind4_solicitudes_estados': ind4_solicitudes_estados,
        'ind5_top_sucursales': ind5_top_sucursales,
        'ind6_top_solicitados': ind6_top_solicitados,
        'ind7_valor_total_inventario': ind7_valor_total_inventario,
        'ind8_salidas_mes': ind8_salidas_mes,
        'ind9_entradas_mes': ind9_entradas_mes,
        'ind10_top_proveedores': ind10_top_proveedores,
        'ind11_productos_agotados': ind11_productos_agotados,
        'ind11_conteo': ind11_conteo,
        'ind12_productos_optimos': ind12_productos_optimos,
        'ind12_conteo': ind12_conteo,
        'ind13_promedio_categoria': ind13_promedio_categoria,
        'ind14_total_unidades_fisicas': ind14_total_unidades_fisicas,
        'ind15_movimientos_tipo': ind15_movimientos_tipo,
        'ind16_top_rotacion': ind16_top_rotacion,
        'ind17_top_usuarios': ind17_top_usuarios,
        'ind18_tasa_aprobacion': ind18_tasa_aprobacion,
        'ind19_sucursales_estado': ind19_sucursales_estado,
        'ind20_ultimas_solicitudes': ind20_ultimas_solicitudes,
        'total_productos_catalogo': len(todos_productos),
        'total_solicitudes': total_solicitudes,
    }
    return render(request, 'reportes.html', context)
