from django.db import models
from django.contrib.auth.models import User


class Categoria(models.Model):
    """Categoría clasificadora de instrumentos y equipamiento musical."""
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Nombre de Categoría")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Proveedor(models.Model):
    """Empresa proveedora o distribuidora mayorista de insumos musicales."""
    rut = models.CharField(max_length=20, unique=True, verbose_name="RUT Proveedor")
    nombre = models.CharField(max_length=150, verbose_name="Razón Social / Nombre")
    contacto = models.CharField(max_length=150, blank=True, verbose_name="Persona de Contacto / Email")
    telefono = models.CharField(max_length=30, blank=True, verbose_name="Teléfono")

    class Meta:
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.rut})"


class Bodega(models.Model):
    """Instalación física donde se almacena el stock centralizado o regional."""
    nombre = models.CharField(max_length=120, verbose_name="Nombre de Bodega")
    codigo = models.CharField(max_length=20, unique=True, verbose_name="Código")
    direccion = models.CharField(max_length=255, verbose_name="Dirección Física")

    class Meta:
        verbose_name = "Bodega"
        verbose_name_plural = "Bodegas"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} [{self.codigo}]"


class Sucursal(models.Model):
    """Puntos de venta o sucursales de Music Pro que solicitan mercadería a Bodega Central."""
    codigo = models.CharField(max_length=20, unique=True, verbose_name="Código de Sucursal")
    nombre = models.CharField(max_length=150, verbose_name="Nombre de Sucursal")
    direccion = models.CharField(max_length=255, verbose_name="Dirección")
    activa = models.BooleanField(default=True, verbose_name="¿Sucursal Activa?")

    class Meta:
        verbose_name = "Sucursal"
        verbose_name_plural = "Sucursales"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.codigo})"


class Producto(models.Model):
    """Catálogo maestro de instrumentos, equipamiento de audio e iluminación."""
    sku = models.CharField(max_length=50, unique=True, verbose_name="SKU / Código Único")
    nombre = models.CharField(max_length=200, verbose_name="Nombre del Instrumento / Equipo")
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.CASCADE,
        related_name="productos",
        verbose_name="Categoría"
    )
    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="productos",
        verbose_name="Proveedor"
    )
    precio = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Precio Unitario (CLP)")
    stock_minimo = models.PositiveIntegerField(default=5, verbose_name="Stock Mínimo Exigido")
    activo = models.BooleanField(default=True, verbose_name="¿Producto Activo?")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ["sku"]

    def __str__(self):
        return f"[{self.sku}] {self.nombre}"


class Solicitud(models.Model):
    """Requerimientos de abastecimiento emitidos por sucursales a Bodega Central."""
    ESTADOS = [
        ('PENDIENTE', 'Pendiente'),
        ('APROBADA', 'Aprobada'),
        ('RECHAZADA', 'Rechazada'),
        ('DESPACHADA', 'Despachada'),
    ]

    sucursal = models.ForeignKey(
        Sucursal,
        on_delete=models.CASCADE,
        related_name="solicitudes",
        verbose_name="Sucursal Solicitante"
    )
    usuario_solicitante = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="solicitudes",
        verbose_name="Usuario Solicitante"
    )
    fecha_solicitud = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Solicitud")
    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default='PENDIENTE',
        verbose_name="Estado de Solicitud"
    )
    observaciones = models.TextField(blank=True, verbose_name="Observaciones / Justificación")

    class Meta:
        verbose_name = "Solicitud de Sucursal"
        verbose_name_plural = "Solicitudes de Sucursales"
        ordering = ["-fecha_solicitud"]

    def __str__(self):
        return f"Solicitud #{self.id} - {self.sucursal.nombre} ({self.get_estado_display()})"


class DetalleSolicitud(models.Model):
    """Línea de ítem solicitada dentro de una Solicitud."""
    solicitud = models.ForeignKey(
        Solicitud,
        on_delete=models.CASCADE,
        related_name="detalles",
        verbose_name="Solicitud Principal"
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name="detalles_solicitud",
        verbose_name="Producto Requerido"
    )
    cantidad_solicitada = models.PositiveIntegerField(verbose_name="Cantidad Solicitada")

    class Meta:
        verbose_name = "Detalle de Solicitud"
        verbose_name_plural = "Detalles de Solicitud"

    def __str__(self):
        return f"{self.cantidad_solicitada} un. de {self.producto.nombre} (Sol #{self.solicitud_id})"


class Movimiento(models.Model):
    """Kardex de entradas, salidas y ajustes de stock en bodega."""
    TIPOS = [
        ('ENTRADA', 'Entrada'),
        ('SALIDA', 'Salida'),
        ('AJUSTE', 'Ajuste'),
    ]

    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name="movimientos",
        verbose_name="Producto"
    )
    bodega = models.ForeignKey(
        Bodega,
        on_delete=models.CASCADE,
        related_name="movimientos",
        verbose_name="Bodega Asignada"
    )
    tipo = models.CharField(max_length=10, choices=TIPOS, verbose_name="Tipo de Movimiento")
    cantidad = models.IntegerField(default=1, verbose_name="Cantidad de Unidades")
    fecha = models.DateTimeField(auto_now_add=True, verbose_name="Fecha y Hora de Registro")
    observacion = models.CharField(max_length=255, blank=True, verbose_name="Glosa u Observación")

    class Meta:
        verbose_name = "Movimiento de Inventario"
        verbose_name_plural = "Movimientos de Inventario"
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.tipo} ({self.cantidad}) - {self.producto.sku}"
