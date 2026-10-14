from django.db import models


class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)

    def __str__(self):
        return self.nombre


class Bodega(models.Model):
    nombre = models.CharField(max_length=120)
    codigo = models.CharField(max_length=20, unique=True)
    direccion = models.CharField(max_length=255)

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    sku = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=200)
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)
    precio = models.DecimalField(max_digits=12, decimal_places=2)
    stock_minimo = models.PositiveIntegerField(default=5)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre


class Movimiento(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    bodega = models.ForeignKey(Bodega, on_delete=models.CASCADE)
    tipo = models.CharField(
        max_length=10,
        choices=[
            ('ENTRADA', 'Entrada'),
            ('SALIDA', 'Salida'),
            ('AJUSTE', 'Ajuste'),
        ]
    )
    cantidad = models.PositiveIntegerField()
    fecha = models.DateTimeField(auto_now_add=True)
    observacion = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.tipo} - {self.producto.nombre}"
