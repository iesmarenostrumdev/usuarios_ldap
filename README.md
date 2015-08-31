# usuarios_ldap
Script para crear usuarios y actualizar passwords LDAP en el servidor de Centro de Lliurex

## Configuración
1. Renombrar archivo `usuarios.config.example` a `usuarios.config`.
2. Modificar `usuarios.config` con la información adecuada.
3. Dar permisos de escritura al script `usuarios.py` (`chmod u+x usuarios.py`).
4. Modificar archivo `trabajo.cron` para indicar el nombre del usuario que lanzará el script.
5. Programar el trabajo mediante CRON: `crontab trabajo.cron`.
