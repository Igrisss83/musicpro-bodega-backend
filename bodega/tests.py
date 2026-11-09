from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

from bodega.models import (
    Categoria,
    Proveedor,
    Bodega,
    Sucursal,
    Producto,
    Solicitud,
    DetalleSolicitud,
    Movimiento,
)
from bodega.views import enriquecer_producto


class MusicProBodegaModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='operador', password='password123')
        self.categoria = Categoria.objects.create(nombre='Guitarras Eléctricas', descripcion='Guitarras')
        self.proveedor = Proveedor.objects.create(
            rut='78.111.222-3',
            nombre='Fender Chile SpA',
            contacto='contacto@fender.cl',
            telefono='+56911223344'
        )
        self.bodega = Bodega.objects.create(
            nombre='Bodega Central Santiago',
            codigo='BOD-CENTRAL',
            direccion='Av. Providencia 1234'
        )
        self.sucursal = Sucursal.objects.create(
            codigo='SUC-01',
            nombre='Sucursal Providencia',
            direccion='Av. Providencia 2000',
            activa=True
        )
        self.producto = Producto.objects.create(
            sku='GTR-TEST-001',
            nombre='Fender Stratocaster Test',
            categoria=self.categoria,
            proveedor=self.proveedor,
            precio=Decimal('799990.00'),
            stock_minimo=5,
            activo=True
        )

    def test_stock_dinamico_kardex(self):
        """Verifica que el cálculo dinámico de stock sume entradas/ajustes y reste salidas."""
        # 1. Entrada de 10 unidades
        Movimiento.objects.create(
            producto=self.producto,
            bodega=self.bodega,
            tipo='ENTRADA',
            cantidad=10
        )
        prod = enriquecer_producto(self.producto)
        self.assertEqual(prod.stock_actual, 10)
        self.assertFalse(prod.es_critico)  # 10 > stock_minimo (5)

        # 2. Salida de 6 unidades -> Quedan 4 (Crítico porque 4 <= 5)
        Movimiento.objects.create(
            producto=self.producto,
            bodega=self.bodega,
            tipo='SALIDA',
            cantidad=6
        )
        # Forzar re-cálculo limpiando atributo en caché si existe
        if hasattr(prod, 'stock_actual'):
            delattr(prod, 'stock_actual')
        prod = enriquecer_producto(self.producto)
        self.assertEqual(prod.stock_actual, 4)
        self.assertTrue(prod.es_critico)
        self.assertEqual(prod.estado_label, "Stock Crítico")

        # 3. Ajuste de 2 unidades -> Quedan 6 (Óptimo)
        Movimiento.objects.create(
            producto=self.producto,
            bodega=self.bodega,
            tipo='AJUSTE',
            cantidad=2
        )
        if hasattr(prod, 'stock_actual'):
            delattr(prod, 'stock_actual')
        prod = enriquecer_producto(self.producto)
        self.assertEqual(prod.stock_actual, 6)
        self.assertFalse(prod.es_critico)
        self.assertEqual(prod.estado_label, "Óptimo")


class MusicProBodegaViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='admin', password='admin123')
        self.categoria = Categoria.objects.create(nombre='Audio Profesional')
        self.proveedor = Proveedor.objects.create(
            rut='76.555.444-3',
            nombre='Shure Distribución Chile',
            contacto='ventas@shure.cl',
            telefono='+5622334455'
        )
        self.bodega = Bodega.objects.create(
            nombre='Bodega Central Santiago',
            codigo='BOD-CENTRAL',
            direccion='Av. Providencia 1234'
        )
        self.sucursal = Sucursal.objects.create(
            codigo='SUC-COST-01',
            nombre='Sucursal Costanera Center',
            direccion='Av. Andrés Bello 2425',
            activa=True
        )
        self.producto = Producto.objects.create(
            sku='AUD-SHU-001',
            nombre='Shure SM7B Vocal',
            categoria=self.categoria,
            proveedor=self.proveedor,
            precio=Decimal('429990.00'),
            stock_minimo=4,
            activo=True
        )

    def test_acceso_anonimo_y_proteccion_vistas(self):
        """Verifica que las vistas administrativas requieran inicio de sesión."""
        # Landing es pública
        resp_index = self.client.get(reverse('index'))
        self.assertEqual(resp_index.status_code, 200)

        # Login view es pública
        resp_login = self.client.get(reverse('login'))
        self.assertEqual(resp_login.status_code, 200)

        # Dashboard protegido
        resp_dash = self.client.get(reverse('dashboard'))
        self.assertEqual(resp_dash.status_code, 302)
        self.assertIn('/login/', resp_dash.url)

        # Inventario protegido
        resp_inv = self.client.get(reverse('inventario'))
        self.assertEqual(resp_inv.status_code, 302)

        # Solicitudes protegidas
        resp_sol = self.client.get(reverse('lista_solicitudes'))
        self.assertEqual(resp_sol.status_code, 302)

        # Reportes protegidos
        resp_rep = self.client.get(reverse('reportes_panel'))
        self.assertEqual(resp_rep.status_code, 302)

    def test_login_y_logout(self):
        """Prueba autenticación exitosa y cierre de sesión."""
        login_resp = self.client.post(reverse('login'), {
            'username': 'admin',
            'password': 'admin123'
        })
        self.assertEqual(login_resp.status_code, 302)
        self.assertEqual(login_resp.url, reverse('dashboard'))

        # Ahora el dashboard responde 200
        resp_dash = self.client.get(reverse('dashboard'))
        self.assertEqual(resp_dash.status_code, 200)

        # Logout
        logout_resp = self.client.get(reverse('logout'))
        self.assertEqual(logout_resp.status_code, 302)
        self.assertEqual(logout_resp.url, reverse('login'))

    def test_flujo_aprobacion_solicitud_con_validacion_stock(self):
        """
        Prueba el flujo de aprobación:
        - Si no hay stock suficiente en Bodega Central, rechaza la operación.
        - Si hay stock suficiente, aprueba y genera automáticamente el movimiento de SALIDA.
        """
        self.client.login(username='admin', password='admin123')

        solicitud = Solicitud.objects.create(
            sucursal=self.sucursal,
            usuario_solicitante=self.user,
            estado='PENDIENTE',
            observaciones='Reabastecimiento urgente'
        )
        DetalleSolicitud.objects.create(
            solicitud=solicitud,
            producto=self.producto,
            cantidad_solicitada=5
        )

        # 1. Intentar aprobar sin stock suficiente (stock = 0)
        resp_aprobar_sin_stock = self.client.get(
            reverse('procesar_solicitud', kwargs={'solicitud_id': solicitud.id, 'accion': 'aprobar'})
        )
        self.assertEqual(resp_aprobar_sin_stock.status_code, 302)
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'PENDIENTE')
        self.assertEqual(Movimiento.objects.filter(tipo='SALIDA').count(), 0)

        # 2. Agregar stock en Bodega Central (10 unidades de ENTRADA)
        Movimiento.objects.create(
            producto=self.producto,
            bodega=self.bodega,
            tipo='ENTRADA',
            cantidad=10,
            observacion='Recepción de lote inicial'
        )

        # 3. Intentar aprobar con stock disponible (solicita 5, hay 10)
        resp_aprobar = self.client.get(
            reverse('procesar_solicitud', kwargs={'solicitud_id': solicitud.id, 'accion': 'aprobar'})
        )
        self.assertEqual(resp_aprobar.status_code, 302)
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'APROBADA')

        # Se debe haber creado automáticamente el Movimiento de SALIDA
        mov_salida = Movimiento.objects.filter(tipo='SALIDA').first()
        self.assertIsNotNone(mov_salida)
        self.assertEqual(mov_salida.producto, self.producto)
        self.assertEqual(mov_salida.cantidad, 5)

        # El stock restante del producto debe ser 5
        prod = enriquecer_producto(self.producto)
        self.assertEqual(prod.stock_actual, 5)

        # 4. Despachar solicitud
        resp_despacho = self.client.get(
            reverse('procesar_solicitud', kwargs={'solicitud_id': solicitud.id, 'accion': 'despachar'})
        )
        self.assertEqual(resp_despacho.status_code, 302)
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'DESPACHADA')

    def test_modulo_reportes_20_indicadores(self):
        """Verifica que el panel de reportes calcule y renderice los 20 indicadores sin errores."""
        self.client.login(username='admin', password='admin123')

        # Registrar movimientos para que haya datos en todos los agregados
        Movimiento.objects.create(
            producto=self.producto,
            bodega=self.bodega,
            tipo='ENTRADA',
            cantidad=20
        )
        Movimiento.objects.create(
            producto=self.producto,
            bodega=self.bodega,
            tipo='SALIDA',
            cantidad=3
        )

        response = self.client.get(reverse('reportes_panel'))
        self.assertEqual(response.status_code, 200)

        # Verificar presencia de indicadores clave en el contexto
        self.assertIn('ind1_productos_criticos', response.context)
        self.assertIn('ind2_top10_caros', response.context)
        self.assertIn('ind3_conteo_por_categoria', response.context)
        self.assertIn('ind4_resumen_estados', response.context)
        self.assertIn('ind5_top_sucursales', response.context)
        self.assertIn('ind6_top_solicitados', response.context)
        self.assertIn('ind7_valor_total_inventario', response.context)
        self.assertIn('ind8_salidas_mes', response.context)
        self.assertIn('ind9_entradas_mes', response.context)
        self.assertIn('ind10_top_proveedores', response.context)
        self.assertIn('ind11_productos_agotados', response.context)
        self.assertIn('ind12_productos_optimos', response.context)
        self.assertIn('ind13_promedio_categoria', response.context)
        self.assertIn('ind14_total_unidades_fisicas', response.context)
        self.assertIn('ind15_movimientos_tipo', response.context)
        self.assertIn('ind16_top_rotacion', response.context)
        self.assertIn('ind17_top_usuarios', response.context)
        self.assertIn('ind18_tasa_aprobacion', response.context)
        self.assertIn('ind19_sucursales_estado', response.context)
        self.assertIn('ind20_ultimas_solicitudes', response.context)

