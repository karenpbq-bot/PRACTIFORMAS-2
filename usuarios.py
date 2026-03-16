import streamlit as st
import pandas as pd
from base_datos import conectar

def mostrar():
    st.header("👤 Gestión de Usuarios y Perfil")
    supabase = conectar()
    
    # --- DIAGNÓSTICO DE ROL (Solo para ti en consola/pantalla) ---
    # Esto nos dirá qué valor exacto tiene tu rol en la base de datos
    rol_actual = str(st.session_state.get('rol', 'Invitado')).strip()
    
    # 1. PERFIL PERSONAL (Siempre visible)
    with st.expander("👤 Mi Perfil y Seguridad", expanded=False):
        st.write(f"**Usuario:** {st.session_state.get('usuario')}")
        st.write(f"**Nombre:** {st.session_state.get('nombre_real')}")
        st.write(f"**Nivel de Acceso:** {rol_actual}")
        
        st.divider()
        with st.form("form_auto_cambio"):
            st.subheader("Cambiar mi contraseña")
            clave_act = st.text_input("Contraseña Actual:", type="password")
            nueva_cl = st.text_input("Nueva Contraseña:", type="password")
            conf_cl = st.text_input("Confirmar Nueva Contraseña:", type="password")
            
            if st.form_submit_button("Actualizar mi contraseña"):
                res = supabase.table("usuarios").select("contrasena").eq("nombre_usuario", st.session_state.usuario).execute()
                if res.data and res.data[0]['contrasena'] == clave_act:
                    if nueva_cl == conf_cl and nueva_cl != "":
                        supabase.table("usuarios").update({"contrasena": nueva_cl}).eq("nombre_usuario", st.session_state.usuario).execute()
                        st.success("✅ Contraseña actualizada.")
                    else: st.error("❌ Las contraseñas no coinciden.")
                else: st.error("❌ Contraseña actual incorrecta.")

    # --- CAMBIO CRÍTICO: VALIDACIÓN FLEXIBLE ---
    # Usamos .lower() para evitar errores si en la DB dice 'administrador' o 'Administrador'
    if rol_actual.lower() == "administrador":
        st.markdown("---")
        st.subheader("⚙️ Panel de Administración de Equipo")
        
        tab1, tab2 = st.tabs(["➕ Crear Usuario", "👥 Lista de Equipo"])
            
        with tab1:
            with st.form("nuevo_usuario", clear_on_submit=True):
                st.write("### Datos del Nuevo Colaborador")
                u_real = st.text_input("Nombre Completo (Ej: Juan Pérez)")
                u_nombre = st.text_input("Nombre de Usuario (Login)")
                u_pass = st.text_input("Contraseña Temporal", type="password")
                u_rol = st.selectbox("Rol y Permisos", ["Supervisor", "Gerente", "Administrador"])
                
                if st.form_submit_button("🚀 Registrar en el Sistema"):
                    if u_nombre and u_pass and u_real:
                        try:
                            # Inserción directa con columna correcta
                            supabase.table("usuarios").insert({
                                "nombre_usuario": u_nombre,
                                "contrasena": u_pass,
                                "rol": u_rol,
                                "nombre_completo": u_real 
                            }).execute()
                            st.success(f"✅ {u_real} ha sido registrado.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error técnico: {e}")
                    else:
                        st.warning("⚠️ Rellene todos los campos.")

        with tab2:
            try:
                res_u = supabase.table("usuarios").select("nombre_completo, nombre_usuario, rol").execute()
                if res_u.data:
                    df_u = pd.DataFrame(res_u.data)
                    df_u.columns = ['Nombre', 'Usuario', 'Rol']
                    st.dataframe(df_u, use_container_width=True, hide_index=True)
            except:
                st.error("No se pudo cargar la lista de equipo.")

        # RESET MAESTRO
        st.markdown("---")
        with st.expander("🛡️ Reset de Contraseñas (Uso Administrativo)"):
            with st.form("reset_maestro"):
                u_reset = st.text_input("Usuario a resetear:")
                p_reset = st.text_input("Nueva contraseña:", type="password")
                if st.form_submit_button("Ejecutar Cambio"):
                    if u_reset and p_reset:
                        supabase.table("usuarios").update({"contrasena": p_reset}).eq("nombre_usuario", u_reset).execute()
                        st.success("✅ Contraseña reseteada.")
    else:
        # Esto te dirá por qué no entras
        st.warning(f"Acceso Restringido. Tu rol registrado es: '{rol_actual}'. Se requiere 'Administrador'.")
