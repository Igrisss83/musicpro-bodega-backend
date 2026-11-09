# 🎸 Bodega Central - Music Pro S.A.
> **Evaluación N°3** | Tecnologías del Lado del Servidor / Arquitectura Web  
> **Institución:** INACAP  

---

## 📋 Descripción y Alcance del Proyecto

**Music Pro S.A.** es una empresa especializada en la distribución e importación de instrumentos musicales, equipos de audio e iluminación profesional. El módulo **Bodega Central** corresponde al backend administrativo integral desarrollado con **Django** y **Python**, diseñado para la administración centralizada de inventario físico, trazabilidad mediante Kardex ORM, atención y flujo de aprobación de **Solicitudes de Sucursales**, control de **Proveedores** y un **Módulo de Reportes con 20 indicadores analíticos**.

---

### 🚀 Funcionalidades Principales Implementadas

1. **Capa de Modelos ORM Relacional:**
   - `Categoria`: Clasificación de equipamiento.
   - `Proveedor`: Proveedores con RUT chileno, razón social y contacto.
   - `Bodega`: Bodega Central y centros logísticos.
   - `Sucursal`: Red de sucursales activas e inactivas.
   - `Producto`: Catálogo con SKU único, FK a categoría y proveedor, precio CLP, stock mínimo y estado activo.
   - `Solicitud`: Requerimientos emitidos por sucursales a Bodega Central con estados `PENDIENTE`, `APROBADA`, `RECHAZADA`, `DESPACHADA`.
   - `DetalleSolicitud`: Ítems y cantidades solicitadas vinculadas a la solicitud y producto (`related_name='detalles'`).
   - `Movimiento`: Kardex de inventario (`ENTRADA`, `SALIDA`, `AJUSTE`) con `related_name='movimientos'`.

2. **Autenticación y Seguridad:**
   - Vistas independientes `login_view` y `logout_view` basadas en `django.contrib.auth`.
   - Protección de todas las vistas administrativas mediante `@login_required`.
   - Superusuario preconfigurado: `admin` / `admin123`.

3. **Cálculo de Stock Dinámico en Tiempo Real:**
   - Función auxiliar `enriquecer_producto(prod)` con agregaciones ORM (`Sum`, `Case`, `When`, `Coalesce`) para calcular el stock exacto:
     $$\text{Stock Actual} = \sum \text{ENTRADA} + \sum \text{AJUSTE} - \sum \text{SALIDA}$$
   - Determinación automática de alertas: *Óptimo*, *Stock Crítico* y *Agotado*.

4. **Flujo de Solicitudes y Control de Despachos:**
   - Vista `lista_solicitudes` con filtros por estado y sucursal, visualización de stock disponible en bodega central y modal para emitir solicitudes.
   - Vista `procesar_solicitud`:
     - **Aprobar:** Valida atómicamente la disponibilidad de stock de todos los ítems. Si hay quiebre, rechaza la operación informando los productos faltantes. Si hay stock suficiente, cambia el estado a `APROBADA` y genera automáticamente los registros de `Movimiento` tipo `SALIDA`.
     - **Rechazar:** Cambia el estado a `RECHAZADA`.
     - **Despachar:** Marca la solicitud aprobada como `DESPACHADA`.

5. **Módulo de Reportes y Analítica (20 Indicadores ORM):**
   - Panel ejecutivo (`reportes_panel`) con 20 consultas ORM optimizadas:
     1. Productos con stock bajo el mínimo exigido.
     2. Top 10 productos más caros.
     3. Distribución y conteo de productos por categoría.
     4. Conteo de solicitudes por estado (Pendientes, Aprobadas, etc.).
     5. Top 5 sucursales con mayor cantidad de solicitudes.
     6. Top 5 productos más solicitados por las sucursales.
     7. Valor monetario total del inventario en bodega (CLP).
     8. Total de unidades despachadas (salidas) en los últimos 30 días.
     9. Total de unidades ingresadas (entradas) en los últimos 30 días.
     10. Top 5 proveedores con más productos en catálogo.
     11. Conteo y detalle de productos agotados (Stock = 0).
     12. Conteo de productos en nivel óptimo de inventario.
     13. Precio promedio de productos por categoría.
     14. Total de unidades físicas almacenadas en Bodega Central.
     15. Movimientos históricos clasificados por tipo (`ENTRADA`, `SALIDA`, `AJUSTE`).
     16. Top 5 productos con mayor rotación / salidas de bodega.
     17. Top usuarios con más solicitudes generadas.
     18. Tasa porcentual de aprobación de solicitudes.
     19. Relación de sucursales activas vs en remodelación/inactivas.
     20. Trazabilidad de las últimas 10 solicitudes registradas.

6. **Poblado Masivo y Pruebas de Carga (`seed_data`):**
   - Comando `python manage.py seed_data [cantidad]` con `Faker('es_CL')`.
   - Inserción por lotes usando `bulk_create()` y `transaction.atomic()` a tasas de más de 9.000 registros por segundo.

---

## 🗺️ Mapa de Rutas y Endpoints

| Ruta URL | Nombre (Django Name) | Método | Descripción del Componente |
| :--- | :--- | :---: | :--- |
| `/` | `index` | `GET` | Landing pública de presentación institucional. |
| `/login/` | `login` | `GET / POST` | Inicio de sesión con autenticación Django. |
| `/logout/` | `logout` | `GET` | Cierre de sesión y redirección. |
| `/admin-panel/dashboard/` | `dashboard` | `GET` | Panel de métricas KPI, alertas y accesos rápidos. |
| `/admin-panel/inventario/` | `inventario` | `GET` | Catálogo de productos con filtros y búsqueda. |
| `/admin-panel/producto/<codigo>/` | `detalle` | `GET` | Ficha técnica y trazabilidad histórica del producto. |
| `/admin-panel/movimientos/nuevo/` | `movimiento_nuevo` | `GET / POST` | Formulario de registro de entradas, salidas y ajustes. |
| `/admin-panel/solicitudes/` | `lista_solicitudes` | `GET / POST` | Listado, creación y monitoreo de solicitudes de sucursales. |
| `/admin-panel/solicitudes/<id>/<accion>/` | `procesar_solicitud` | `GET` | Controlador de aprobación, rechazo y despacho de solicitudes. |
| `/admin-panel/reportes/` | `reportes_panel` | `GET` | Panel de 20 indicadores analíticos ORM. |

---

## 🛠️ Instrucciones de Ejecución

### 1. Migraciones de Base de Datos
```bash
python manage.py makemigrations
python manage.py migrate
```

### 2. Poblar Datos Iniciales y Pruebas de Carga
```bash
# Poblar datos base + 500 movimientos masivos (por defecto)
python manage.py seed_data 500

# O generar pruebas de alta concurrencia / carga
python manage.py seed_data 10000
```

### 3. Ejecutar Pruebas Automatizadas
```bash
python manage.py test
```

### 4. Iniciar Servidor de Desarrollo
```bash
python manage.py runserver
```
Acceder en el navegador a `http://127.0.0.1:8000/`.  
**Credenciales:** Usuario: `admin` | Contraseña: `admin123`
