# Gestión de Inventario

## Descripción
Este módulo de Odoo permite gestionar clientes, productos, inventarios, cestas de compra y descuentos. Es ideal para pequeñas y medianas empresas que deseen administrar eficientemente sus ventas y compras.

### Funcionalidades principales:
- Gestión de clientes y sus cuentas asociadas.
- Control de inventarios y productos.
- Creación y administración de cestas de compra con líneas detalladas.
- Cálculo automático de subtotales, totales y descuentos aplicados.
- Gestión de pedidos.

## Instalación

### Requisitos previos
- Tener una instancia de Odoo instalada (versión compatible: Odoo 13).
- Acceso como administrador para instalar módulos personalizados.

### Pasos para instalar el módulo
1. Clonar o descargar el módulo en la carpeta de addons personalizada de tu instalación de Odoo:
  git clone https://github.com/MFkirin/gestion-inventario.git

2. Asegúrate de que los permisos del módulo sean correctos:
  sudo chown -R odoo:odoo /ruta/a/gestion-inventario

3. Reinicia el servidor de Odoo para cargar los nuevos módulos:
  sudo systemctl restart odoo
4. Inicia sesión en tu instancia de Odoo como administrador.

5. Ve al menú Aplicaciones y actualiza la lista de módulos haciendo clic en el botón Actualizar lista de aplicaciones.
6. Busca "Gestión de Inventario" en la barra de búsqueda.
7. Haz clic en Instalar para agregar el módulo a tu sistema.
