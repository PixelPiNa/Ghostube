import os
import re

def aplicar_puertos():
    print("==================================================")
    print(" [DOORMAN] INICIANDO RECONFIGURACION DE PUERTOS")
    print("==================================================")

    # Leer el archivo puertos.txt
    if not os.path.exists('puertos.txt'):
        print("[ERROR] No se encontro 'puertos.txt'. Se aborta la operacion.")
        return

    puertos = {}
    with open('puertos.txt', 'r', encoding='utf-8') as f:
        for linea in f:
            if '=' in linea:
                clave, valor = linea.strip().split('=')
                puertos[clave.strip()] = valor.strip()

    p_caddy = puertos.get('CADDY', '9090')
    p_flask = puertos.get('FLASK', '9091')
    p_admin = puertos.get('CADDY_ADMIN', '2019')

    # El nuevo bloque que inyectaremos en el código
    nuevo_bloque = f"""# --- CONFIGURACION DE RED ---
PUERTO_CADDY = {p_caddy}
PUERTO_FLASK = {p_flask}
PUERTO_CADDY_ADMIN = {p_admin}
# --- FIN CONFIGURACION ---"""

    # Inyectar en app.py y configuraciones.py usando Expresiones Regulares
    archivos_objetivo = ['app.py', 'configuraciones.py']
    
    for archivo in archivos_objetivo:
        if os.path.exists(archivo):
            with open(archivo, 'r', encoding='utf-8') as f:
                contenido = f.read()

            # Busca todo lo que esté entre nuestras etiquetas y lo reemplaza
            contenido_modificado = re.sub(
                r"# --- CONFIGURACION DE RED ---.*?# --- FIN CONFIGURACION ---",
                nuevo_bloque,
                contenido,
                flags=re.DOTALL
            )

            with open(archivo, 'w', encoding='utf-8') as f:
                f.write(contenido_modificado)
            print(f"[+] Codigo actualizado exitosamente: {archivo}")

    # 4. Actualizar el Caddyfile Base
    caddyfile_base = f"""{{
    admin localhost:{p_admin}
}}

:{p_caddy} {{
    # Todo lo que este en la carpeta static lo sirve Caddy
    handle_path /static/* {{
        root * "static"
        file_server
    }}

    # Todo lo demas se lo envía a Flask
    reverse_proxy 127.0.0.1:{p_flask}
}}
"""
    with open('Caddyfile', 'w', encoding='utf-8') as f:
        f.write(caddyfile_base)
    print(f"[+] Caddyfile base reescrito exitosamente.")

    print("==================================================")
    print(f" [OK] PUERTOS ASIGNADOS: Caddy({p_caddy}) | Flask({p_flask}) | Admin({p_admin})")
    print("==================================================")

if __name__ == '__main__':
    aplicar_puertos()