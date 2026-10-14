import random
import time
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from faker import Faker

from bodega.models import Categoria, Bodega, Producto, Movimiento


class Command(BaseCommand):
    help = 'Puebla la base de datos con categorías, bodegas, productos y movimientos para pruebas de carga.'

    def add_arguments(self, parser):
        parser.add_argument(
            'cantidad',
            type=int,
            help='Cantidad de movimientos masivos a generar (ej. 100, 1000, 100000, 1000000)'
        )

    def handle(self, *args, **options):
        total_movimientos = options['cantidad']
        if total_movimientos <= 0:
            self.stdout.write(self.style.ERROR('La cantidad de movimientos debe ser mayor a 0.'))
            return

        fake = Faker('es_CL')
        self.stdout.write(f'=== INICIANDO CARGA CON FAKER (es_CL) — CANTIDAD: {total_movimientos:,} ===')

        # 1. Asegurar categorías, bodegas y productos de prueba si la base de datos está vacía
        self._asegurar_datos_base(fake)

        # 2. Inserción masiva de movimientos por lotes
        self._generar_movimientos_masivos(total_movimientos, fake)

    def _asegurar_datos_base(self, fake):
        """Genera categorías, bodegas y productos de prueba usando Faker('es_CL') si la BD está vacía."""
        if Categoria.objects.count() == 0:
            self.stdout.write('Generando categorías iniciales...')
            nombres_categorias = [
                'Guitarras y Bajos',
                'Audio Profesional',
                'Teclados y Sintetizadores',
                'Baterías y Percusión',
                'Iluminación y Efectos',
                'Accesorios y Conectividad'
            ]
            for nombre in nombres_categorias:
                Categoria.objects.create(
                    nombre=nombre,
                    descripcion=fake.sentence(nb_words=10)
                )
            self.stdout.write(f'OK: {Categoria.objects.count()} categorías registradas.')

        if Bodega.objects.count() == 0:
            self.stdout.write('Generando bodegas iniciales...')
            bodegas_data = [
                ('Bodega Central Santiago', 'BOD-STGO-01', f"{fake.street_name()} {fake.building_number()}, Santiago"),
                ('Bodega Regional Antofagasta', 'BOD-ANTOF-02', f"{fake.street_name()} {fake.building_number()}, Antofagasta"),
                ('Bodega Regional Concepción', 'BOD-CONC-03', f"{fake.street_name()} {fake.building_number()}, Concepción"),
                ('Centro Logístico Pudahuel', 'BOD-PUD-04', f"{fake.street_name()} {fake.building_number()}, Pudahuel"),
            ]
            for nombre, codigo, direccion in bodegas_data:
                Bodega.objects.create(
                    nombre=nombre,
                    codigo=codigo,
                    direccion=direccion
                )
            self.stdout.write(f'OK: {Bodega.objects.count()} bodegas registradas.')

        if Producto.objects.count() == 0:
            self.stdout.write('Generando catálogo de productos iniciales...')
            categorias = list(Categoria.objects.all())
            productos_data = [
                ('GTR-FEN-001', 'Fender Stratocaster Player II - Cherry Sunburst', 'Guitarras y Bajos', Decimal('849990.00'), 5),
                ('AUD-YAM-002', 'Yamaha HS8 Monitor de Estudio Activo (Par)', 'Audio Profesional', Decimal('659980.00'), 4),
                ('KEY-ROL-003', 'Roland RD-88 Piano Digital de Escenario', 'Teclados y Sintetizadores', Decimal('1199990.00'), 2),
                ('DRM-PRL-004', 'Pearl Decade Maple Batería Acústica 5 Cuerpos', 'Baterías y Percusión', Decimal('1299990.00'), 3),
                ('AUD-SHU-005', 'Shure SM7B Micrófono Dinámico Vocal', 'Audio Profesional', Decimal('429990.00'), 8),
                ('GTR-GIB-006', 'Gibson Les Paul Standard 60s - Bourbon Burst', 'Guitarras y Bajos', Decimal('2499990.00'), 2),
                ('KEY-KRG-007', 'Korg Minilogue XD Sintetizador Polifónico', 'Teclados y Sintetizadores', Decimal('649990.00'), 4),
                ('ACC-MOG-008', 'Mogami Gold Studio Cable XLR 6m', 'Accesorios y Conectividad', Decimal('59990.00'), 15),
                ('AUD-FOC-009', 'Focusrite Scarlett 4i4 4ta Gen Interfaz USB', 'Audio Profesional', Decimal('259990.00'), 6),
                ('DRM-ROL-010', 'Roland TD-17KVX2 Batería Electrónica V-Drums', 'Baterías y Percusión', Decimal('1799990.00'), 3),
                ('ILU-CHV-011', 'Chauvet DJ Intimidator Spot 360 Cabezal Móvil', 'Iluminación y Efectos', Decimal('899990.00'), 4),
                ('GTR-IBA-012', 'Ibanez SR505E Bajo Eléctrico 5 Cuerdas', 'Guitarras y Bajos', Decimal('789990.00'), 3),
            ]
            cat_map = {c.nombre: c for c in categorias}
            for sku, nombre, cat_nom, precio, stock_min in productos_data:
                cat = cat_map.get(cat_nom, categorias[0])
                Producto.objects.create(
                    sku=sku,
                    nombre=nombre,
                    categoria=cat,
                    precio=precio,
                    stock_minimo=stock_min
                )
            self.stdout.write(f'OK: {Producto.objects.count()} productos registrados.')

    def _generar_movimientos_masivos(self, total_movimientos, fake):
        """Inserta movimientos por lotes usando bulk_create dentro de transaction.atomic."""
        productos_ids = list(Producto.objects.values_list('id', flat=True))
        bodegas_ids = list(Bodega.objects.values_list('id', flat=True))

        if not productos_ids or not bodegas_ids:
            self.stdout.write(self.style.ERROR('Error: No hay productos o bodegas disponibles.'))
            return

        tipos = ['ENTRADA', 'SALIDA', 'AJUSTE']
        pesos = [0.60, 0.35, 0.05]

        # Glosas comunes generadas con Faker para velocidad óptima
        glosas_pool = [
            f"Recepcion lote importacion #{random.randint(100, 9999)} - Proveedor internacional",
            f"Despacho a sucursal {fake.city()} para gira Music Pro 2026",
            f"Ingreso stock inicial desde centro de distribucion Pudahuel",
            f"Ajuste operativo de inventario por auditoria",
            f"Salida para demostracion tecnica en showroom",
            f"Asignacion escenario principal Music Pro Tour",
            f"Transferencia entre bodegas autorizada",
            f"Reabastecimiento urgente de stock critico"
        ]
        for _ in range(40):
            glosas_pool.append(f"{fake.bs().capitalize()} - Ref: {fake.bothify(text='DOC-####')}")

        batch_size = 10000
        creados = 0
        tiempo_inicio = time.time()

        self.stdout.write(f'Insertando registros en lotes de {batch_size:,} con bulk_create()...')

        with transaction.atomic():
            lote = []
            for i in range(1, total_movimientos + 1):
                tipo = random.choices(tipos, weights=pesos, k=1)[0]
                cantidad = random.randint(1, 40) if tipo != 'AJUSTE' else random.randint(1, 8)

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
                        f' -> Progreso: {creados:,} / {total_movimientos:,} ({progreso:.1f}%) | '
                        f'Tiempo: {tiempo_transcurrido:.2f}s'
                    )

            if lote:
                Movimiento.objects.bulk_create(lote, batch_size=batch_size)
                creados += len(lote)

        tiempo_total = time.time() - tiempo_inicio
        tasa = creados / tiempo_total if tiempo_total > 0 else creados

        self.stdout.write(self.style.SUCCESS(
            f'\n[OK] Carga finalizada: {creados:,} movimientos insertados en {tiempo_total:.2f} segundos '
            f'({tasa:,.0f} registros/segundo).'
        ))
