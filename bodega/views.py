from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Sum, Case, When, IntegerField, F, Value, Q
from django.db.models.functions import Coalesce

from .models import Categoria, Bodega, Producto, Movimiento


def enriquecer_producto(prod, stock=None):
    
    prod.codigo = prod.sku
    prod.pasillo = "Pasillo A"
    prod.estante = "Estante 1 - Nivel 2"

    if stock is not None:
        prod.stock_actual = max(0, stock)
    elif not hasattr(prod, 'stock_actual'):
        entradas = Movimiento.objects.filter(producto=prod, tipo='ENTRADA').aggregate(total=Sum('cantidad'))['total'] or 0
        salidas = Movimiento.objects.filter(producto=prod, tipo='SALIDA').aggregate(total=Sum('cantidad'))['total'] or 0
        ajustes = Movimiento.objects.filter(producto=prod, tipo='AJUSTE').aggregate(total=Sum('cantidad'))['total'] or 0
        prod.stock_actual = max(0, entradas - salidas + ajustes)

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
    mov.responsable = "Operador de Bodega"
    mov.glosa = mov.observacion
    return mov



def index(request):
    
    total_items = Producto.objects.count()
    return render(request, 'index.html', {
        'total_items': total_items
    })


def dashboard(request):
    
    stock_expr = Coalesce(
        Sum(
            Case(
                When(movimiento__tipo='ENTRADA', then=F('movimiento__cantidad')),
                When(movimiento__tipo='AJUSTE', then=F('movimiento__cantidad')),
                When(movimiento__tipo='SALIDA', then=-F('movimiento__cantidad')),
                default=Value(0),
                output_field=IntegerField()
            )
        ),
        Value(0)
    )

    productos_qs = Producto.objects.select_related('categoria').annotate(calc_stock=stock_expr)
    productos = [enriquecer_producto(p, stock=p.calc_stock) for p in productos_qs]

    total_items = len(productos)
    total_unidades = sum(p.stock_actual for p in productos)
    productos_criticos = [p for p in productos if p.es_critico]
    alertas_criticas = len(productos_criticos)


    ultimos_movimientos_qs = Movimiento.objects.select_related('producto', 'bodega').order_by('-fecha')[:5]
    ultimos_movimientos = [enriquecer_movimiento(m) for m in ultimos_movimientos_qs]

    context = {
        'total_items': total_items,
        'total_unidades': total_unidades,
        'alertas_criticas': alertas_criticas,
        'ultimos_movimientos': ultimos_movimientos,
        'productos_criticos': productos_criticos,
    }
    return render(request, 'dashboard.html', context)


def inventario_lista(request):
    """Catálogo completo de productos con filtros por categoría, búsqueda y estado."""
    categorias = list(Categoria.objects.values_list('nombre', flat=True).order_by('nombre'))

    cat_filtro = request.GET.get('categoria', '').strip()
    busqueda = request.GET.get('q', '').strip()
    estado_filtro = request.GET.get('estado', '').strip()

    stock_expr = Coalesce(
        Sum(
            Case(
                When(movimiento__tipo='ENTRADA', then=F('movimiento__cantidad')),
                When(movimiento__tipo='AJUSTE', then=F('movimiento__cantidad')),
                When(movimiento__tipo='SALIDA', then=-F('movimiento__cantidad')),
                default=Value(0),
                output_field=IntegerField()
            )
        ),
        Value(0)
    )

    qs = Producto.objects.select_related('categoria').annotate(calc_stock=stock_expr)

    if cat_filtro:
        qs = qs.filter(categoria__nombre=cat_filtro)

    if busqueda:
        qs = qs.filter(Q(sku__icontains=busqueda) | Q(nombre__icontains=busqueda))

    productos = [enriquecer_producto(p, stock=p.calc_stock) for p in qs]

    if estado_filtro == 'critico':
        productos_filtrados = [p for p in productos if p.es_critico]
    elif estado_filtro == 'optimo':
        productos_filtrados = [p for p in productos if not p.es_critico]
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


def detalle_producto(request, codigo):
    """Vista Modo Show: Ficha técnica detallada e historial de movimientos del producto."""
    producto = Producto.objects.select_related('categoria').filter(sku__iexact=codigo).first()

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


def nuevo_movimiento(request):
    
    productos_qs = Producto.objects.all().select_related('categoria').order_by('nombre')
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

        if tipo_form in ['Ingreso', 'ENTRADA']:
            tipo_db = 'ENTRADA'
        elif tipo_form in ['Salida', 'SALIDA']:
            tipo_db = 'SALIDA'
        else:
            messages.error(request, 'El tipo de movimiento debe ser "Ingreso" o "Salida".')
            errores = True
            tipo_db = None

        if not errores and producto and tipo_db == 'SALIDA':
            producto = enriquecer_producto(producto)
            if cantidad > producto.stock_actual:
                messages.error(
                    request,
                    f'Operación rechazada: La cantidad requerida ({cantidad} unidades) excede el stock disponible actual ({producto.stock_actual} unidades) del producto "{producto.nombre}".'
                )
                errores = True

        if errores:
            return render(request, 'movimiento.html', {
                'inventario': inventario,
                'codigo_preseleccionado': codigo,
                'form_data': form_data
            })

        bodega = Bodega.objects.first()
        if not bodega:
            bodega = Bodega.objects.create(
                nombre="Bodega Central Santiago",
                codigo="BOD-STGO-01",
                direccion="Av. Providencia 1234, Santiago"
            )

        observacion_final = glosa
        if responsable:
            observacion_final = f"{glosa} (Resp: {responsable})" if glosa else f"Resp: {responsable}"

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
            f'¡Movimiento de {tipo_form.lower()} registrado con éxito! El stock actualizado de "{producto.nombre}" es de {producto.stock_actual} unidades.'
        )
        return redirect('detalle', codigo=producto.sku)

    return render(request, 'movimiento.html', {
        'inventario': inventario,
        'codigo_preseleccionado': codigo_preseleccionado
    })
