# -*- coding: utf-8 -*-
{
    'name': "Gestion inventario",
    'summary': "Módulo para gestionar clientes, productos, inventarios, cestas, compras y descuentos.",
    'description': """
        Este módulo implementa:
        - Gestión completa de Clientes.
        - Productos y control de inventarios.
        - Gestión de cestas y lista de compras.
        - Pedidos y aplicación de descuentos.
    """,
    'author': "Hugo",
    'category': 'Sales',
    'version': '1.0',
    'depends': ['base'],
    'data': [
        'views/views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': True,
}