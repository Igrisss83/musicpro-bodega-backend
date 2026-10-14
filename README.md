# 🎸 Bodega Central - Music Pro S.A.
> **Evaluación 1** | Asignatura de Desarrollo Web / Arquitectura de Software  
> **Profesor:** Benjamín Mora  

---

## 📋 Descripción y Alcance del Proyecto

**Music Pro S.A.** es una empresa especializada en la distribución e importación de instrumentos musicales, equipos de audio e iluminación profesional. El módulo **Bodega Central** corresponde al sistema web administrativo desarrollado con el framework **Django**, diseñado para optimizar el control de inventario, la trazabilidad de insumos y la gestión operativa de entradas y salidas de mercadería.

### 🚀 Funcionalidades Clave
- **Dashboard Administrativo (KPIs):** Panel de control con métricas clave en tiempo real: total de productos, unidades físicas almacenadas, alertas de stock crítico e historial de los últimos movimientos.
- **Catálogo de Inventario:** Listado completo con filtros combinables por categoría, estado operativo (*Óptimo*, *Stock Crítico*, *Agotado*) y campo de búsqueda en tiempo real por código o nombre de producto.
- **Ficha Técnica & Trazabilidad ("Modo Show"):** Vista detallada por producto que expone especificaciones técnicas, ubicación física en bodega y la trazabilidad histórica de todas sus entradas y salidas.
- **Gestión de Movimientos:** Formulario operativo para registrar **Ingresos** y **Salidas** de stock con validaciones estrictas en el servidor para evitar descuadres de inventario.

---

## 🤖 Justificación del Uso de Inteligencia Artificial (Criterio 1.1.4)

En conformidad con las pautas de evaluación y el **Criterio 1.1.4**, el desarrollo de esta solución integró el apoyo asistido de herramientas de **Inteligencia Artificial Generativa / Agentic Coding (Antigravity AI)** como par de programación (*Pair Programming*).

### 🛠️ Áreas de Aplicación de la IA en el Proyecto:
1. **Modelamiento de Capa de Datos Mock (JSON Driven):**
   - Asistencia en la estructuración del esquema JSON (`bodega/data/inventario.json`) y la implementación de utilidades Python (`cargar_inventario`, `guardar_inventario`) para garantizar la persistencia de datos y manipulación en memoria sin necesidad de ORM relacional complejo en esta etapa.
2. **Lógica de Negocio y Controladores en Python (`views.py`):**
   - Co-diseño del algoritmo de enriquecimiento dinámico (`enriquecer_producto`), el cual calcula estados de alerta y asigna badges de Bootstrap de manera reactiva según reglas de stock mínimo.
   - Reforzamiento de las validaciones de negocio en el backend (verificación de tipo de movimiento, validación de enteros positivos y prevención de salidas que excedan el stock disponible).
3. **Optimización de UI/UX con Bootstrap 5 y Django Template Language (DTL):**
   - Generación modular de plantillas HTML5 (`base.html`, `dashboard.html`, `inventario.html`, `detalle.html`, `movimiento.html`) garantizando diseño *responsive*, estética profesional (*dark/light contrast*, componentes visuales limpios) y manejo centralizado de alertas (`django.contrib.messages`).

### 📌 Declaración de Integridad y Co-Pilotaje Técnico:
El uso de la IA actuó exclusivamente como un acelerador de prototipado y soporte de buenas prácticas de código. La supervisión técnica, decisiones de arquitectura modular, enrutamiento de Django y verificación de requisitos fueron guiadas por el alumno para cumplir rigurosamente con los objetivos pedagógicos planteados por el docente.

---

## 🗺️ Mapa de Rutas y Endpoints

| Ruta URL | Nombre (Django Name) | Método | Descripción del Componente |
| :--- | :--- | :---: | :--- |
| `/` | `index` | `GET` | Landing pública de presentación de la Bodega Central. |
| `/admin-panel/dashboard/` | `dashboard` | `GET` | Panel de métricas KPI, alertas críticas y últimos movimientos. |
| `/admin-panel/inventario/` | `inventario` | `GET` | Catálogo de productos con filtros por categoría, estado y búsqueda. |
| `/admin-panel/producto/<codigo>/` | `detalle` | `GET` | Ficha técnica ("Modo Show") y trazabilidad histórica del producto. |
| `/admin-panel/movimientos/nuevo/` | `movimiento_nuevo` | `GET / POST` | Formulario de registro e inserción de entradas y salidas de stock. |

---

## 🛠️ Requisitos e Instrucciones de Ejecución

### Prerrequisitos
- **Python:** 3.10 o superior
- **Django:** 5.0+

### Pasos de Instalación y Despliegue Local

1. **Clonar el repositorio:**
   ```bash
   git clone <URL_DE_TU_REPOSITORIO_GITHUB>
   cd progra
   ```

2. **Crear y activar entorno virtual:**
   ```bash
   # En Windows (PowerShell):
   python -m venv .venv
   \.venv\Scripts\Activate.ps1

   # En Linux/macOS:
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Instalar dependencias (Django):**
   ```bash
   pip install django
   ```

4. **Ejecutar el servidor de desarrollo:**
   ```bash
   python manage.py runserver
   ```

5. **Acceder a la aplicación:**
   Abrir el navegador web en `http://127.0.0.1:8000/`.

---

## 📁 Estructura del Proyecto

```text
progra/
├── .gitignore               # Exclusión de entornos virtuales, pycache y SQLite
├── README.md                # Documentación del proyecto (Criterio 1.1.4)
├── manage.py                # Script principal de administración de Django
├── config/                  # Configuración global del proyecto Django
│   ├── __init__.py
│   ├── settings.py          # Ajustes globales y registro de la app 'bodega'
│   ├── urls.py              # Enrutador principal de URLs
│   └── wsgi.py              # Interfaz WSGI para despliegue
└── bodega/                  # Aplicación principal de la Bodega Central
    ├── data/
    │   └── inventario.json  # Base de datos mock en formato JSON
    ├── static/              # Archivos estáticos de la aplicación
    ├── templates/           # Plantillas DTL (base, index, dashboard, inventario, detalle, movimiento)
    ├── urls.py              # Rutas modulares de la aplicación
    └── views.py             # Controladores de vistas y validaciones de negocio
```
