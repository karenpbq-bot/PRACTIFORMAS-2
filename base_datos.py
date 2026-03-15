import streamlit as st
import pandas as pd
from datetime import date
from supabase import create_client

# =========================================================
# 1. CONEXIÓN Y CONFIGURACIÓN
# =========================================================

def conectar():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

def inicializar_bd():
    """Función mantenida para evitar errores de importación."""
    pass

# =========================================================
# 2. GESTIÓN DE USUARIOS
# =========================================================

def validar_usuario(usuario, clave):
    supabase = conectar()
    res = supabase.table("usuarios").select("*").eq("nombre_usuario", usuario).eq("contrasena", clave).execute()
    return res.data[0] if res.data else None

def obtener_supervisores():
    supabase = conectar()
    res = supabase.table("usuarios").select("id, nombre_real, rol").in_("rol", ['Administrador', 'Gerente', 'Supervisor']).execute()
    return pd.DataFrame(res.data)

# =========================================================
# 3. GESTIÓN DE PROYECTOS (ACTUALIZADA V2)
# =========================================================

def obtener_proyectos(palabra_clave=""):
    """Buscador Universal: Filtra por Código, Nombre o Cliente."""
    supabase = conectar()
    query = supabase.table("proyectos").select("id, codigo, proyecto_text, cliente, estatus, avance, partida")
    
    if palabra_clave:
        # Lógica OR para palabras clave en múltiples campos
        query = query.or_(f"codigo.ilike.%{palabra_clave}%,proyecto_text.ilike.%{palabra_clave}%,cliente.ilike.%{palabra_clave}%")
    
    res = query.execute()
    df = pd.DataFrame(res.data)
    
    if not df.empty:
        # Crea la etiqueta para los selectbox: [PTF-001] Proyecto Ejemplo
        df['proyecto_display'] = "[" + df['codigo'].astype(str) + "] " + df['proyecto_text']
        
    return df

def crear_proyecto(codigo, nombre, cliente, partida):
    """Inserta un nuevo proyecto con su DNI/Código único."""
    try:
        supabase = conectar()
        data = {
            "codigo": codigo,
            "proyecto_text": nombre,
            "cliente": cliente,
            "partida": partida,
            "estatus": "Activo",
            "avance": 0
        }
        return supabase.table("proyectos").insert(data).execute()
    except Exception as e:
        st.error(f"Error al crear: {e}")
        return None

def eliminar_proyecto(id_p):
    """Borra un proyecto y sus datos asociados (Cascada)."""
    return conectar().table("proyectos").delete().eq("id", id_p).execute()
    
# =========================================================
# 4. GESTIÓN DE PRODUCTOS Y SEGUIMIENTO (AJUSTES)
# =========================================================

def obtener_productos_por_proyecto(id_proyecto):
    """Recupera los productos asociados a un proyecto específico."""
    supabase = conectar()
    res = supabase.table("productos").select("*").eq("proyecto_id", id_proyecto).execute()
    return pd.DataFrame(res.data)

def obtener_seguimiento(id_producto):
    """Obtiene el historial de hitos de un producto."""
    supabase = conectar()
    res = supabase.table("seguimiento").select("*").eq("producto_id", id_producto).execute()
    return pd.DataFrame(res.data)

def guardar_seguimiento(id_producto, hito, fecha):
    """Guarda o actualiza un hito. Maneja el formato de fecha para la DB."""
    try:
        supabase = conectar()
        # Intentamos convertir DD/MM/YYYY a YYYY-MM-DD para la base de datos
        try:
            fecha_db = datetime.strptime(fecha, '%d/%m/%Y').strftime('%Y-%m-%d')
        except:
            fecha_db = fecha # Si falla, enviamos el texto original
            
        data = {
            "producto_id": id_producto,
            "hito": hito,
            "fecha": fecha_db
        }
        # upsert: inserta si no existe, actualiza si existe (requiere UNIQUE en producto_id y hito)
        res = supabase.table("seguimiento").upsert(data).execute()
        
        # Actualizamos el avance del proyecto automáticamente
        res_prod = supabase.table("productos").select("proyecto_id").eq("id", id_producto).execute()
        if res_prod.data:
            actualizar_avance_real(res_prod.data[0]['proyecto_id'])
            
        return res
    except Exception as e:
        st.error(f"Error al guardar hito: {e}")
        return None
# =========================================================
# 5. GESTIÓN DE INCIDENCIAS
# =========================================================

def registrar_incidencia_detallada(proy_id, tipo_inc, motivo, piezas, materiales, user_id):
    supabase = conectar()
    inc = supabase.table("incidencias").insert({
        "proyecto_id": proy_id, "tipo_requerimiento": tipo_inc, 
        "categoria": motivo, "fecha_reporte": date.today().isoformat(), "usuario_id": user_id
    }).execute()
    inc_id = inc.data[0]['id']
    if piezas:
        for p in piezas:
            p['incidencia_id'] = inc_id
            supabase.table("detalles_piezas").insert(p).execute()
    if materiales:
        for m in materiales:
            m['incidencia_id'] = inc_id
            supabase.table("detalles_materiales").insert(m).execute()

def obtener_incidencias_resumen():
    supabase = conectar()
    res = supabase.table("incidencias").select("*, proyectos(proyecto_text), usuarios(nombre_real)").execute()
    df = pd.DataFrame(res.data)
    if not df.empty:
        df['proyecto_text'] = df['proyectos'].apply(lambda x: x['proyecto_text'] if x else "")
        df['nombre_real'] = df['usuarios'].apply(lambda x: x['nombre_real'] if x else "")
    return df

def crear_proyecto(codigo, nombre, cliente, partida):
    """Inserta un nuevo proyecto en la base de datos PTF-2."""
    try:
        supabase = conectar()
        data = {
            "codigo": codigo,
            "proyecto_text": nombre,
            "cliente": cliente,
            "partida": partida,
            "estatus": "Activo",
            "avance": 0
        }
        res = supabase.table("proyectos").insert(data).execute()
        return res
    except Exception as e:
        st.error(f"Error en base_datos.crear_proyecto: {e}")
        return None


