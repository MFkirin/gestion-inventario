# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date
from dateutil.relativedelta import relativedelta


class Cliente(models.Model):
    _name = 'tienda.cliente'
    _description = 'Clientes de la tienda'

    name = fields.Char(string="Nombre", required=True)
    apellidos = fields.Char(string="Apellidos")
    email = fields.Char(string="Email", required=True)
    telefono = fields.Char(string="Teléfono")
    direccion = fields.Text(string="Dirección")
    birth_date = fields.Date(string="Fecha de Nacimiento", required=True)
    edad = fields.Integer(string="Edad", compute="_compute_edad")
    tutor_nif = fields.Char(string="NIF del Tutor")
    nif = fields.Char(string="NIF", required=True)
    country_id = fields.Many2one('res.country', string="País", required=True)
    saldo = fields.Float(string="Saldo", default=0.0)
    metodo_pago = fields.Selection([
        ('tarjeta', 'Tarjeta de Crédito'),
        ('paypal', 'PayPal'),
        ('transferencia', 'Transferencia Bancaria')
    ], string="Método de Pago")
    saldo_maximo = fields.Float(string="Límite de saldo", default=2000.0)
    dinero_gastado = fields.Float(string="Dinero Gastado", compute="_compute_dinero_gastado")
    cesta_ids = fields.One2many('tienda.cesta', 'cliente_id', string="Cestas")

    _sql_constraints = [
        ('unique_nif', 'unique(nif)', 'El NIF debe ser único.')
    ]

    @api.depends('birth_date')
    def _compute_edad(self):
        for record in self:
            if record.birth_date:
                today = date.today()
                record.edad = relativedelta(today, record.birth_date).years
            else:
                record.edad = 0

    @api.constrains('birth_date', 'tutor_nif')
    def _check_minor(self):
        for record in self:
            if record.edad < 18 and not record.tutor_nif:
                raise ValidationError("Los menores de edad deben proporcionar el NIF de un tutor.")

    @api.depends('cesta_ids.lista_compra_ids.precio_total')
    def _compute_dinero_gastado(self):
        for cliente in self:
            # Calcula el total gastado
            total_gastado = sum(line.precio_total for cesta in cliente.cesta_ids for line in cesta.lista_compra_ids)

            # Resta el total gastado del saldo
            cliente.dinero_gastado = total_gastado
            cliente.saldo = cliente.saldo_maximo - total_gastado

    @api.constrains('saldo')
    def _check_saldo_maximo(self):
        for record in self:
            if record.saldo > record.saldo_maximo:
                raise ValidationError("El saldo no puede exceder el límite establecido.")


class Producto(models.Model):
    _name = 'tienda.producto'
    _description = 'Productos de la tienda'

    name = fields.Char(string="Nombre", required=True)
    descripcion = fields.Text(string="Descripción")
    precio = fields.Float(string="Precio", required=True)
    categoria = fields.Char(string="Categoría")

    _sql_constraints = [
        ('unique_product_name', 'unique(name)', 'El nombre del producto debe ser único.')
    ]


class Inventario(models.Model):
    _name = 'tienda.inventario'
    _description = 'Inventario de productos'

    producto_id = fields.Many2one('tienda.producto', string="Producto", required=True)
    cantidad_disponible = fields.Integer(string="Cantidad Disponible", required=True)
    almacen = fields.Char(string="Almacén")

    _sql_constraints = [
        ('unique_product_in_inventory', 'unique(producto_id)', 'El producto ya está registrado en el inventario.')
    ]

    _order = 'producto_id, cantidad_disponible desc'

    def name_get(self):
        """
        Define cómo se muestran los registros de inventario en los campos Many2one.
        """
        result = []
        for record in self:
            name = f"{record.producto_id.name} "
            result.append((record.id, name))
        return result

    def get_cantidad(self):
        """
        Devuelve una lista de opciones de cantidad basadas en el stock disponible.
        """
        print(f"Stock disponible para {self.producto_id.name}: {self.cantidad_disponible}")
        if self.cantidad_disponible <= 0:
            return []
        opciones = [(str(i), str(i)) for i in range(1, self.cantidad_disponible + 1)]
        print(f"Opciones de cantidad: {opciones}")
        return opciones


class ListaCompra(models.Model):
    _name = 'tienda.lista_compra'
    _description = 'Lista de compras'

    cesta_id = fields.Many2one('tienda.cesta', string="Cesta", required=True)
    inventario_id = fields.Many2one('tienda.inventario', string="Producto", required=True)
    cantidad = fields.Integer(string="Cantidad", required=True)
    precio_total = fields.Float(string="Precio Total", compute="_compute_precio_total", store=True)

    @api.depends('cantidad', 'inventario_id.producto_id.precio')
    def _compute_precio_total(self):
        for record in self:
            record.precio_total = int(record.cantidad or 0) * record.inventario_id.producto_id.precio

    @api.model
    def create(self, vals):
        """
        Valida la cantidad seleccionada contra el stock del inventario y actualiza el inventario.
        """
        inventario = self.env['tienda.inventario'].browse(vals.get('inventario_id'))
        cantidad_solicitada = vals.get('cantidad', 0)

        # Validar stock disponible
        if cantidad_solicitada > inventario.cantidad_disponible:
            raise ValidationError(
                f"No hay suficiente stock del producto '{inventario.producto_id.name}'. "
                f"Disponible: {inventario.cantidad_disponible}, solicitado: {cantidad_solicitada}."
            )

        # Reducir el stock en el inventario
        inventario.cantidad_disponible -= cantidad_solicitada
        return super(ListaCompra, self).create(vals)

    def write(self, vals):
        """
        Valida y actualiza el inventario si se modifica una línea de lista de compras.
        """
        for record in self:
            nueva_cantidad = vals.get('cantidad', record.cantidad)
            diferencia = nueva_cantidad - record.cantidad

            inventario = record.inventario_id

            # Validar si hay suficiente stock disponible
            if diferencia > 0 and diferencia > inventario.cantidad_disponible:
                raise ValidationError(
                    f"No hay suficiente stock del producto '{inventario.producto_id.name}'. "
                    f"Disponible: {inventario.cantidad_disponible}, adicional solicitado: {diferencia}."
                )

            # Actualizar el stock del inventario
            inventario.cantidad_disponible -= diferencia

        return super(ListaCompra, self).write(vals)

    def unlink(self):
        """
        Restaura el stock del inventario cuando se elimina una línea de la lista de compras.
        """
        for record in self:
            inventario = record.inventario_id
            if inventario:
                inventario.cantidad_disponible += record.cantidad
        return super(ListaCompra, self).unlink()


class Cesta(models.Model):
    _name = 'tienda.cesta'
    _description = 'Cestas de compra'
    _order = 'cliente_id, fecha_creacion desc'

    name = fields.Char(string='Nombre', required=False, onlyread=True)
    cliente_id = fields.Many2one('tienda.cliente', string="Cliente", required=True)
    fecha_creacion = fields.Date(string="Fecha de Creación", default=fields.Date.today)
    estado = fields.Selection([
        ('pendiente', 'Pendiente'),
        ('finalizada', 'Finalizada')
    ], string="Estado", default='pendiente')
    lista_compra_ids = fields.One2many('tienda.lista_compra', 'cesta_id', string="Lista de Compras")
    total_cesta = fields.Float(string="Total de la Cesta", compute="_compute_total_cesta", store=True, readonly=True,
                               default=0.0)
    descuento_id = fields.Many2one('tienda.descuento', string="Descuento")
    total_con_descuento = fields.Float(string="Total con Descuento", compute="_compute_total_con_descuento", store=True,
                                       readonly=True)
    codigo_descuento = fields.Char(string="Código de Descuento")

    @api.onchange('codigo_descuento')
    def _onchange_codigo_descuento(self):
        """
        Valida el código de descuento y lo aplica si es válido.
        """
        if self.codigo_descuento:
            descuento = self.env['tienda.descuento'].search([('codigo', '=', self.codigo_descuento)], limit=1)
            if not descuento:
                self.descuento_id = False
                return {
                    'warning': {
                        'title': "Código de Descuento No Válido",
                        'message': "El código ingresado no existe. Por favor, verifique e intente de nuevo."
                    }
                }
            if descuento.fecha_expiracion and descuento.fecha_expiracion < fields.Date.today():
                self.descuento_id = False
                return {
                    'warning': {
                        'title': "Código de Descuento Caducado",
                        'message': f"El código ingresado ha expirado el {descuento.fecha_expiracion}. Intente con otro código."
                    }
                }
            # Asignar el descuento si es válido
            self.descuento_id = descuento
        else:
            self.descuento_id = False

    @api.depends('lista_compra_ids.precio_total')
    def _compute_total_cesta(self):
        """
        Calcula el total de la cesta sumando los precios totales de las líneas de compra.
        """
        for record in self:
            record.total_cesta = sum(line.precio_total for line in record.lista_compra_ids)

    @api.depends('total_cesta', 'descuento_id')
    def _compute_total_con_descuento(self):
        """
        Calcula el total de la cesta aplicando el descuento seleccionado.
        """
        for record in self:
            if record.descuento_id:
                descuento = record.descuento_id.porcentaje / 100
                record.total_con_descuento = record.total_cesta * (1 - descuento)
            else:
                record.total_con_descuento = record.total_cesta

    def confirmar_compra(self):
        for cesta in self:
            if cesta.estado != 'finalizada':
                raise ValidationError("La cesta debe estar en estado 'finalizada' para confirmar la compra.")

            cliente = cesta.cliente_id

            # Calcular el total de la compra con descuento, si aplica
            total_compra = cesta.total_cesta
            if cesta.descuento_id:
                descuento = cesta.descuento_id.porcentaje / 100
                total_compra *= (1 - descuento)

            # Verificar si el cliente tiene saldo suficiente
            if cliente.saldo < total_compra:
                raise ValidationError(
                    f"Saldo insuficiente para completar la compra. "
                    f"Saldo disponible: {cliente.saldo}, Total de la compra con descuento: {total_compra:.2f}."
                )

            # Restar el total de la compra del saldo del cliente
            cliente.saldo -= total_compra

    @api.constrains('descuento_id')
    def _check_descuento_valido(self):
        for record in self:
            if record.descuento_id and record.descuento_id.fecha_expiracion < fields.Date.today():
                raise ValidationError(f"El descuento '{record.descuento_id.codigo}' ha expirado.")

    @api.model
    def create(self, vals):
        cliente_id = vals.get('cliente_id')
        descuento_id = vals.get('descuento_id')
        cesta = super(Cesta, self).create(vals)

        if cliente_id:
            cliente = self.env['tienda.cliente'].browse(cliente_id)
            total_cesta = cesta.total_cesta

            # Aplicar descuento si está definido
            if descuento_id:
                descuento = self.env['tienda.descuento'].browse(descuento_id).porcentaje / 100
                total_cesta *= (1 - descuento)

            # Verificar si el cliente tiene saldo suficiente
            if cliente.saldo < total_cesta:
                raise ValidationError(
                    f"Saldo insuficiente para el cliente '{cliente.name}'. "
                    f"Saldo disponible: {cliente.saldo}, Total con descuento: {total_cesta}."
                )

            # Restar el total con descuento del saldo del cliente
            cliente.saldo -= total_cesta

        return cesta

    def write(self, vals):
        for cesta in self:
            cliente = cesta.cliente_id
            total_cesta = cesta.total_cesta
            descuento_id = vals.get('descuento_id', cesta.descuento_id.id)

            # Aplicar descuento si está definido
            if descuento_id:
                descuento = self.env['tienda.descuento'].browse(descuento_id).porcentaje / 100
                total_cesta *= (1 - descuento)

            # Verificar si el cliente tiene saldo suficiente
            if cliente.saldo < total_cesta:
                raise ValidationError(
                    f"Saldo insuficiente para el cliente '{cliente.name}'. "
                    f"Saldo disponible: {cliente.saldo}, Total con descuento: {total_cesta}."
                )

            # Restar el total con descuento del saldo del cliente
            cliente.saldo -= total_cesta

        return super(Cesta, self).write(vals)


class Pedido(models.Model):
    _name = 'tienda.pedido'
    _description = 'Pedidos'

    cesta_id = fields.Many2one('tienda.cesta', string="Cesta", required=True)
    fecha_pedido = fields.Date(string="Fecha del Pedido", default=fields.Date.today)
    estado = fields.Selection([
        ('en_preparacion', 'En preparación'),
        ('enviado', 'Enviado'),
        ('entregado', 'Entregado')
    ], string="Estado", default='en_preparacion')
    direccion_envio = fields.Char(string="Dirección de Envío")


class Descuento(models.Model):
    _name = 'tienda.descuento'
    _description = 'Descuentos'

    name = fields.Char(string="Nombre", onlyread=False)
    codigo = fields.Char(string="Código", required=True)
    porcentaje = fields.Float(string="Porcentaje de Descuento", required=True)
    fecha_expiracion = fields.Date(string="Fecha de Expiración", required=True)

    _sql_constraints = [
        ('unique_discount_code', 'unique(codigo)', 'El código de descuento debe ser único.')
    ]

    @api.model
    def create(self, vals):
        # Asignar un nombre automáticamente si no tiene
        if 'name' not in vals or not vals['name']:
            vals['name'] = f"Descuento {vals.get('porcentaje')}% - {vals.get('codigo')}"

        return super(Descuento, self).create(vals)
