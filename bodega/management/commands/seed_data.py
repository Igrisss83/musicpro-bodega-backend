"""
Comando de Gestión de Django: seed_data
Music Pro Bodega Central — Evaluación N°3 (INACAP)
Poblado masivo de datos iniciales con Faker('es_CL'), creación de superusuario,
catálogos base y movimientos por lotes mediante bulk_create() y transaction.atomic().
"""

import random
import time
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
from faker import Faker

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


class Command(BaseCommand):
    help = (
        'Puebla la base de datos de Bodega Central con superusuario admin, '
        'categorías, proveedores, bodegas, sucursales, catálogo de productos, '
        'solicitudes de ejemplo y generación masiva de movimientos mediante lotes.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            'cantidad',
            nargs='?',
            type=int,
            default=500,
            help='Cantidad de movimientos masivos a generar (por defecto: 500, ej: 100, 1000, 50000)'
        )

    def handle(self, *args, **options):
        total_movimientos = options['cantidad']
        if total_movimientos <= 0:
            self.stdout.write(self.style.ERROR('La cantidad de movimientos debe ser un entero positivo > 0.'))
            return

        fake = Faker('es_CL')
        self.stdout.write(self.style.MIGRATE_HEADING(
            f'\n========================================================================\n'
            f'   INICIANDO SEED_DATA: MUSIC PRO BODEGA CENTRAL (Faker: es_CL)\n'
            f'   MOVIMIENTOS MASIVOS SOLICITADOS: {total_movimientos:,}\n'
            f'========================================================================'
        ))

        # 1. Superusuario y usuarios de sucursales
        self._crear_usuarios(fake)

        # 2. Categorías
        categorias_map = self._crear_categorias(fake)

        # 3. Proveedores
        proveedores_list = self._crear_proveedores(fake)

        # 4. Bodegas
        bodega_central = self._crear_bodegas(fake)

        # 5. Sucursales
        sucursales_list = self._crear_sucursales(fake)

        # 6. Catálogo de Productos
        productos_list = self._crear_productos(categorias_map, proveedores_list)

        # 7. Stock inicial garantizado (Entradas base para cada producto)
        self._asegurar_stock_inicial(productos_list, bodega_central)

        # 8. Solicitudes y DetalleSolicitud de ejemplo
        self._crear_solicitudes_ejemplo(sucursales_list, productos_list)

        # 9. Inserción masiva de movimientos con bulk_create() y transaction.atomic()
        self._generar_movimientos_masivos(total_movimientos, productos_list, bodega_central, fake)

        self.stdout.write(self.style.SUCCESS(
            '\n[OK] Poblado y pruebas de carga finalizadas con éxito total.\n'
            'Credenciales de acceso: admin / admin123\n'
        ))

    def _crear_usuarios(self, fake):
        """Crea el superusuario admin y usuarios de prueba para sucursales."""
        self.stdout.write('-> Verificando superusuario y cuentas de personal...')
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@musicpro.cl',
                'first_name': 'Administrador',
                'last_name': 'Bodega Central',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        admin_user.set_password('admin123')
        admin_user.is_superuser = True
        admin_user.is_staff = True
        admin_user.save()
        if created:
            self.stdout.write(self.style.SUCCESS('   [+] Superusuario "admin" creado con clave "admin123".'))
        else:
            self.stdout.write(self.style.SUCCESS('   [*] Superusuario "admin" verificado y actualizado con clave "admin123".'))

        # Usuarios de sucursal para generar solicitudes
        usuarios_sucursal = [
            ('jefe_costanera', 'Carlos', 'Mendoza', 'costanera@musicpro.cl'),
            ('jefe_vina', 'Valeria', 'Rojas', 'vina@musicpro.cl'),
            ('jefe_concepcion', 'Gonzalo', 'Silva', 'conce@musicpro.cl'),
        ]
        for usr, fname, lname, email in usuarios_sucursal:
            u, c = User.objects.get_or_create(
                username=usr,
                defaults={
                    'first_name': fname,
                    'last_name': lname,
                    'email': email,
                    'is_staff': False,
                }
            )
            if c:
                u.set_password('admin123')
                u.save()

    def _crear_categorias(self, fake):
        """Puebla las categorías de instrumentos y equipamiento musical."""
        self.stdout.write('-> Verificando categorías del catálogo...')
        nombres_categorias = [
            ('Guitarras y Bajos', 'Guitarras eléctricas, electroacústicas, bajos de 4 y 5 cuerdas y amplificación.'),
            ('Audio Profesional', 'Monitores de estudio, interfaces de audio USB, microfonía y consolas de mezcla.'),
            ('Teclados y Sintetizadores', 'Pianos digitales de escenario, sintetizadores polifónicos y controladores MIDI.'),
            ('Baterías y Percusión', 'Baterías acústicas, módulos electrónicos V-Drums, platillos y herrajes.'),
            ('Iluminación y Efectos', 'Cabezales móviles DMX, efectos LED, láseres y máquinas de humo.'),
            ('Accesorios y Conectividad', 'Cables profesionales XLR/TRS, pedestales, cuerdas y fundas de transporte.'),
        ]
        categorias_map = {}
        for nombre, desc in nombres_categorias:
            cat, _ = Categoria.objects.get_or_create(
                nombre=nombre,
                defaults={'descripcion': desc or fake.sentence(nb_words=10)}
            )
            categorias_map[nombre] = cat
        self.stdout.write(f'   [OK] {len(categorias_map)} categorías disponibles.')
        return categorias_map

    def _crear_proveedores(self, fake):
        """Puebla proveedores chilenos de marcas musicales con RUTs válidos."""
        self.stdout.write('-> Verificando proveedores oficiales...')
        proveedores_data = [
            ('76.123.456-7', 'Audiomúsica SpA', 'Patricio Valenzuela (p.valenzuela@audiomusica.cl)', '+56 2 2456 7890'),
            ('77.234.567-8', 'Yamaha Music Latin America Chile', 'Lorena Castillo (contacto@yamaha.cl)', '+56 2 2345 6789'),
            ('78.345.678-9', 'Fender Musical Instruments Chile Ltda.', 'Rodrigo Morales (rmorales@fender.com)', '+56 9 8765 4321'),
            ('79.456.789-0', 'Roland Corporation Chile SpA', 'Marcela Díaz (ventas@roland.cl)', '+56 2 2890 1234'),
            ('80.567.890-1', 'Shure Distribución Chile S.A.', 'Cristián Alarcón (solarcon@shure-chile.cl)', '+56 9 7654 3210'),
            ('81.678.901-2', 'Korg & Vox Chile Ltda.', 'Daniela Vera (dvera@korgchile.cl)', '+56 2 2789 4561'),
        ]
        proveedores = []
        for rut, nombre, contacto, fono in proveedores_data:
            prov, _ = Proveedor.objects.get_or_create(
                rut=rut,
                defaults={
                    'nombre': nombre,
                    'contacto': contacto,
                    'telefono': fono,
                }
            )
            proveedores.append(prov)
        self.stdout.write(f'   [OK] {len(proveedores)} proveedores registrados.')
        return proveedores

    def _crear_bodegas(self, fake):
        """Crea la Bodega Central y centros de distribución."""
        self.stdout.write('-> Verificando bodegas físicas...')
        bodega_central, _ = Bodega.objects.get_or_create(
            codigo='BOD-CENTRAL',
            defaults={
                'nombre': 'Bodega Central Santiago - Music Pro',
                'direccion': 'Av. Providencia 1234, Providencia, Región Metropolitana',
            }
        )
        Bodega.objects.get_or_create(
            codigo='BOD-PUD-02',
            defaults={
                'nombre': 'Centro Logístico Pudahuel',
                'direccion': 'Camino San Pedro 800, Pudahuel, Santiago',
            }
        )
        self.stdout.write(f'   [OK] Bodega Central configurada: {bodega_central.nombre}')
        return bodega_central

    def _crear_sucursales(self, fake):
        """Puebla las sucursales que emiten solicitudes a Bodega Central."""
        self.stdout.write('-> Verificando sucursales de venta...')
        sucursales_data = [
            ('SUC-COST-01', 'Sucursal Costanera Center', 'Av. Andrés Bello 2425, Local 320, Providencia', True),
            ('SUC-VESP-02', 'Sucursal Mall Plaza Vespucio', 'Av. Vicuña Mackenna 7110, Local 110, La Florida', True),
            ('SUC-VINA-03', 'Sucursal Viña del Mar', 'Av. Libertad 1348, Viña del Mar, Región de Valparaíso', True),
            ('SUC-CONC-04', 'Sucursal Concepción Centro', 'Barros Arana 650, Concepción, Región del Biobío', True),
            ('SUC-ANTOF-05', 'Sucursal Antofagasta Mall', 'Av. Balmaceda 2355, Antofagasta', True),
            ('SUC-TEM-06', 'Sucursal Temuco Outlet', 'Av. Alemania 0850, Temuco (En remodelación)', False),
        ]
        sucursales = []
        for codigo, nombre, direccion, activa in sucursales_data:
            suc, _ = Sucursal.objects.get_or_create(
                codigo=codigo,
                defaults={
                    'nombre': nombre,
                    'direccion': direccion,
                    'activa': activa,
                }
            )
            sucursales.append(suc)
        self.stdout.write(f'   [OK] {len(sucursales)} sucursales registradas.')
        return sucursales

    def _crear_productos(self, categorias_map, proveedores_list):
        """Puebla el catálogo de productos con proveedores, categorías y precios."""
        self.stdout.write('-> Verificando catálogo de productos...')
        prov_map = {p.rut: p for p in proveedores_list}

        # SKU, Nombre, Categoria, RUT Proveedor, Precio CLP, Stock Minimo
        catalogo = [
            ('GTR-FEN-001', 'Fender Stratocaster Player II - Cherry Sunburst', 'Guitarras y Bajos', '78.345.678-9', Decimal('849990.00'), 5),
            ('AUD-YAM-002', 'Yamaha HS8 Monitor de Estudio Activo (Par)', 'Audio Profesional', '77.234.567-8', Decimal('659980.00'), 4),
            ('KEY-ROL-003', 'Roland RD-88 Piano Digital de Escenario', 'Teclados y Sintetizadores', '79.456.789-0', Decimal('1199990.00'), 2),
            ('DRM-PRL-004', 'Pearl Decade Maple Batería Acústica 5 Cuerpos', 'Baterías y Percusión', '76.123.456-7', Decimal('1299990.00'), 3),
            ('AUD-SHU-005', 'Shure SM7B Micrófono Dinámico Vocal', 'Audio Profesional', '80.567.890-1', Decimal('429990.00'), 8),
            ('GTR-GIB-006', 'Gibson Les Paul Standard 60s - Bourbon Burst', 'Guitarras y Bajos', '76.123.456-7', Decimal('2499990.00'), 2),
            ('KEY-KRG-007', 'Korg Minilogue XD Sintetizador Polifónico', 'Teclados y Sintetizadores', '81.678.901-2', Decimal('649990.00'), 4),
            ('ACC-MOG-008', 'Mogami Gold Studio Cable XLR 6m', 'Accesorios y Conectividad', '76.123.456-7', Decimal('59990.00'), 15),
            ('AUD-FOC-009', 'Focusrite Scarlett 4i4 4ta Gen Interfaz USB', 'Audio Profesional', '76.123.456-7', Decimal('259990.00'), 6),
            ('DRM-ROL-010', 'Roland TD-17KVX2 Batería Electrónica V-Drums', 'Baterías y Percusión', '79.456.789-0', Decimal('1799990.00'), 3),
            ('ILU-CHV-011', 'Chauvet DJ Intimidator Spot 360 Cabezal Móvil', 'Iluminación y Efectos', '76.123.456-7', Decimal('899990.00'), 4),
            ('GTR-IBA-012', 'Ibanez SR505E Bajo Eléctrico 5 Cuerdas', 'Guitarras y Bajos', '76.123.456-7', Decimal('789990.00'), 3),
            ('AUD-SEN-013', 'Sennheiser EW-D SKM-S Sistema Inalámbrico', 'Audio Profesional', '76.123.456-7', Decimal('749990.00'), 4),
            ('KEY-NOR-014', 'Nord Stage 4 88 Teclas Contrapesadas', 'Teclados y Sintetizadores', '76.123.456-7', Decimal('3899990.00'), 2),
            ('DRM-ZIL-015', 'Zildjian K Custom Dark Set de Platillos', 'Baterías y Percusión', '76.123.456-7', Decimal('1099990.00'), 3),
        ]

        productos = []
        for sku, nombre, cat_nom, rut_prov, precio, stock_min in catalogo:
            cat = categorias_map.get(cat_nom, list(categorias_map.values())[0])
            prov = prov_map.get(rut_prov, proveedores_list[0] if proveedores_list else None)

            prod, created = Producto.objects.get_or_create(
                sku=sku,
                defaults={
                    'nombre': nombre,
                    'categoria': cat,
                    'proveedor': prov,
                    'precio': precio,
                    'stock_minimo': stock_min,
                    'activo': True,
                }
            )
            # Asegurar relación si ya existía de una migración previa
            if not created:
                prod.proveedor = prov
                prod.activo = True
                prod.save()
            productos.append(prod)

        self.stdout.write(f'   [OK] {len(productos)} productos listados en catálogo.')
        return productos

    def _asegurar_stock_inicial(self, productos_list, bodega_central):
        """Garantiza que cada producto posea movimientos base de ENTRADA para stock operativo."""
        movs_base = []
        for prod in productos_list:
            tiene_mov = Movimiento.objects.filter(producto=prod).exists()
            if not tiene_mov:
                movs_base.append(
                    Movimiento(
                        producto=prod,
                        bodega=bodega_central,
                        tipo='ENTRADA',
                        cantidad=random.randint(25, 70),
                        observacion=f"Recepción lote inicial importación #{random.randint(100, 999)} - Proveedor oficial"
                    )
                )
        if movs_base:
            Movimiento.objects.bulk_create(movs_base)
            self.stdout.write(f'   [OK] {len(movs_base)} entradas base registradas para stock inicial.')

    def _crear_solicitudes_ejemplo(self, sucursales_list, productos_list):
        """Crea solicitudes de ejemplo en distintos estados con sus DetalleSolicitud."""
        if Solicitud.objects.count() > 0:
            self.stdout.write('   [*] Solicitudes de sucursales ya existen.')
            return

        self.stdout.write('-> Generando solicitudes de ejemplo para sucursales...')
        admin_user = User.objects.get(username='admin')
        sucursales_activas = [s for s in sucursales_list if s.activa]

        # 1. Solicitud PENDIENTE - Sucursal Costanera
        sol1 = Solicitud.objects.create(
            sucursal=sucursales_activas[0],
            usuario_solicitante=admin_user,
            estado='PENDIENTE',
            observaciones='Reabastecimiento urgente de microfonía y guitarras para fin de semana.'
        )
        DetalleSolicitud.objects.create(solicitud=sol1, producto=productos_list[4], cantidad_solicitada=3)
        DetalleSolicitud.objects.create(solicitud=sol1, producto=productos_list[0], cantidad_solicitada=2)

        # 2. Solicitud PENDIENTE - Sucursal Viña del Mar
        sol2 = Solicitud.objects.create(
            sucursal=sucursales_activas[2],
            usuario_solicitante=admin_user,
            estado='PENDIENTE',
            observaciones='Reposición para evento Music Pro Show Viña del Mar.'
        )
        DetalleSolicitud.objects.create(solicitud=sol2, producto=productos_list[2], cantidad_solicitada=1)
        DetalleSolicitud.objects.create(solicitud=sol2, producto=productos_list[7], cantidad_solicitada=8)

        # 3. Solicitud APROBADA - Sucursal Concepción
        sol3 = Solicitud.objects.create(
            sucursal=sucursales_activas[3],
            usuario_solicitante=admin_user,
            estado='APROBADA',
            observaciones='Pedido quincenal de accesorios y conectividad aprobado.'
        )
        DetalleSolicitud.objects.create(solicitud=sol3, producto=productos_list[7], cantidad_solicitada=5)

        # 4. Solicitud DESPACHADA - Sucursal Vespucio
        sol4 = Solicitud.objects.create(
            sucursal=sucursales_activas[1],
            usuario_solicitante=admin_user,
            estado='DESPACHADA',
            observaciones='Despacho completado por transporte express Music Pro.'
        )
        DetalleSolicitud.objects.create(solicitud=sol4, producto=productos_list[1], cantidad_solicitada=2)

        # 5. Solicitud RECHAZADA - Sucursal Antofagasta
        sol5 = Solicitud.objects.create(
            sucursal=sucursales_activas[4],
            usuario_solicitante=admin_user,
            estado='RECHAZADA',
            observaciones='Rechazada temporalmente por límite de capacidad en transporte norte.'
        )
        DetalleSolicitud.objects.create(solicitud=sol5, producto=productos_list[3], cantidad_solicitada=4)

        self.stdout.write(f'   [OK] {Solicitud.objects.count()} solicitudes de ejemplo configuradas.')

    def _generar_movimientos_masivos(self, total_movimientos, productos_list, bodega_central, fake):
        """
        Inserta movimientos por lotes optimizados usando bulk_create()
        dentro de un bloque transaction.atomic() para máximo rendimiento.
        """
        self.stdout.write(f'-> Generando {total_movimientos:,} movimientos por lotes en bulk_create()...')

        productos_ids = [p.id for p in productos_list]
        bodegas_ids = list(Bodega.objects.values_list('id', flat=True))

        tipos = ['ENTRADA', 'SALIDA', 'AJUSTE']
        pesos = [0.55, 0.40, 0.05]

        glosas_pool = [
            f"Recepción lote importación #{random.randint(1000, 9999)} - Proveedor oficial",
            f"Despacho regular a sucursal {fake.city()} para Music Pro Tour",
            f"Ingreso stock desde centro de distribución Pudahuel",
            f"Ajuste operativo de inventario por auditoría periódica",
            f"Salida para demostración técnica en showroom central",
            f"Preparación de equipamiento escenario principal Music Pro",
            f"Transferencia entre bodegas autorizada por jefatura",
            f"Reabastecimiento preventivo de stock mínimo",
        ]
        for _ in range(30):
            glosas_pool.append(f"{fake.bs().capitalize()} - Ref: {fake.bothify(text='DOC-####')}")

        batch_size = 10000
        creados = 0
        tiempo_inicio = time.time()

        with transaction.atomic():
            lote = []
            for i in range(1, total_movimientos + 1):
                tipo = random.choices(tipos, weights=pesos, k=1)[0]
                cantidad = random.randint(1, 15) if tipo != 'AJUSTE' else random.randint(1, 4)

                lote.append(
                    Movimiento(
                        producto_id=random.choice(productos_ids),
                        bodega_id=random.choice(bodegas_ids),
                        tipo=tipo,
                        cantidad=cantidad,
                        observacion=random.choice(glosas_pool)
                    )
                )

                if len(lote) >= batch_size:
                    Movimiento.objects.bulk_create(lote, batch_size=batch_size)
                    creados += len(lote)
                    lote = []
                    progreso = (creados / total_movimientos) * 100
                    tiempo_transcurrido = time.time() - tiempo_inicio
                    self.stdout.write(
                        f'   -> Lote procesado: {creados:,} / {total_movimientos:,} ({progreso:.1f}%) | '
                        f'Tiempo: {tiempo_transcurrido:.2f}s'
                    )

            if lote:
                Movimiento.objects.bulk_create(lote, batch_size=batch_size)
                creados += len(lote)

        tiempo_total = time.time() - tiempo_inicio
        tasa = creados / tiempo_total if tiempo_total > 0 else creados

        self.stdout.write(self.style.SUCCESS(
            f'   [OK] Inserción finalizada: {creados:,} movimientos insertados en {tiempo_total:.2f}s '
            f'({tasa:,.0f} registros/segundo).'
        ))
