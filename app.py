import streamlit as st
import pandas as pd
from supabase import create_client, Client
import datetime

# CONFIGURACIÓN DE PÁGINA (ESTILO INGECONSPRO)
st.set_page_config(
    page_title="Control de Costos - INGECONSPRO",
    page_icon="🏗️",
    layout="wide"
)

# CONEXIÓN SEGURA A SUPABASE
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# ESTILOS CSS PERSONALIZADOS (DARK GLASSmorphism)
st.markdown("""
<style>
    .main { background: linear-gradient(135deg, #090d16 0%, #111827 50%, #0f172a 100%); }
    .stMetric { background: rgba(17, 24, 39, 0.7); border: 1px solid rgba(255, 255, 255, 0.08); padding: 15px; border-radius: 12px; }
    h1, h2, h3, h4 { color: #f3f4f6; }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# BARRA LATERAL: SELECTOR DE PROYECTO GLOBAL
# -----------------------------------------------------------------------------
st.sidebar.image("https://lh3.googleusercontent.com/d/1GGsI4a9bvY2McOuHmj8NlFC_Vx0HA8VV", width=50)
st.sidebar.title("INGECONSPRO S.A.S.")
st.sidebar.caption("Control de Costos Multiproyecto")

# Cargar lista de proyectos
res_proyectos = supabase.table("proyectos").select("*").execute()
df_proyectos = pd.DataFrame(res_proyectos.data)

if df_proyectos.empty:
    st.error("No hay proyectos registrados. Crea uno en el menú lateral.")
    st.stop()

# Dropdown global de selección de obra
proyecto_seleccionado = st.sidebar.selectbox(
    "🏗️ SELECCIONAR PROYECTO ACTIVO:",
    options=df_proyectos["nombre"].tolist(),
    index=0
)

# Obtener ID del proyecto activo
id_proyecto_activo = df_proyectos[df_proyectos["nombre"] == proyecto_seleccionado]["id_proyecto"].values[0]

# Pestañas de Navegación
menu = st.sidebar.radio("Navegación:", [
    "📊 Dashboard & Presupuesto", 
    "📥 Cargar / Importar Presupuesto",
    "🚚 Proveedores", 
    "🧾 Ingreso de Costos", 
    "📐 Registrar Avances", 
    "➕ Crear Nuevo Proyecto"
])

# -----------------------------------------------------------------------------
# MÓDULO 1: DASHBOARD & CONSOLIDADO DE PRESUPUESTO
# -----------------------------------------------------------------------------
if menu == "📊 Dashboard & Presupuesto":
    st.title(f"Dashboard - {proyecto_seleccionado}")
    
    # Cargar actividades del proyecto activo
    pres = supabase.table("presupuesto").select("*").eq("id_proyecto", id_proyecto_activo).execute()
    df_pres = pd.DataFrame(pres.data)
    
    if df_pres.empty:
        st.warning(f"El proyecto '{proyecto_seleccionado}' aún no tiene actividades en su presupuesto. Ve al menú '📥 Cargar / Importar Presupuesto' para subir el despiece en Excel/CSV.")
    else:
        # Cargar compras del proyecto
        comp = supabase.table("compras").select("*").eq("id_proyecto", id_proyecto_activo).execute()
        df_comp = pd.DataFrame(comp.data)
        
        # Cargar avances del proyecto
        avan = supabase.table("avances").select("*").eq("id_proyecto", id_proyecto_activo).execute()
        df_avan = pd.DataFrame(avan.data)
        
        # CÁLCULOS FINANCIEROS (APU REAL)
        costo_real_map = df_comp.groupby("id_actividad")["cantidad"].apply(lambda x: (x * df_comp.loc[x.index, "precio_unitario"]).sum()).to_dict() if not df_comp.empty else {}
        cant_ejec_map = df_avan.groupby("id_actividad")["cant_ejecutada"].sum().to_dict() if not df_avan.empty else {}
        
        df_pres["cant_pres"] = df_pres["cant_pres"].astype(float)
        df_pres["apu_pres"] = df_pres["apu_pres"].astype(float)
        df_pres["total_pres"] = df_pres["cant_pres"] * df_pres["apu_pres"]
        
        df_pres["costo_real"] = df_pres["id_actividad"].map(costo_real_map).fillna(0)
        df_pres["cant_ejec"] = df_pres["id_actividad"].map(cant_ejec_map).fillna(0)
        df_pres["apu_real"] = df_pres.apply(lambda r: r["costo_real"] / r["cant_ejec"] if r["cant_ejec"] > 0 else 0, axis=1)
        
        df_pres["proyeccion"] = df_pres.apply(
            lambda r: r["apu_real"] * r["cant_pres"] if r["cant_ejec"] > 0 and r["apu_real"] > 0 else r["total_pres"], axis=1
        )
        df_pres["utilidad"] = df_pres["total_pres"] - df_pres["proyeccion"]
        df_pres["estado"] = df_pres.apply(lambda r: "Sobrecosto en APU" if r["apu_real"] > r["apu_pres"] else ("Pérdida Proyectada" if r["utilidad"] < 0 else "En Margen"), axis=1)
        
        # KPIs SUPERIORES
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Presupuesto Total", f"${df_pres['total_pres'].sum():,.0f}")
        col2.metric("Costo Real Ejecutado", f"${df_pres['costo_real'].sum():,.0f}")
        col3.metric("Costo Proyectado", f"${df_pres['proyeccion'].sum():,.0f}")
        col4.metric("Utilidad Estimada", f"${df_pres['utilidad'].sum():,.0f}", delta=f"${df_pres['utilidad'].sum():,.0f}")
        
        st.subheader("Consolidado General de Actividades")
        st.dataframe(
            df_pres[["codigo_item", "capitulo", "descripcion", "unidad", "cant_pres", "apu_pres", "total_pres", "costo_real", "cant_ejec", "apu_real", "proyeccion", "utilidad", "estado"]],
            use_container_width=True
        )

# -----------------------------------------------------------------------------
# MÓDULO NUEVO: CARGAR / IMPORTAR PRESUPUESTO AL PROYECTO ACTIVO
# -----------------------------------------------------------------------------
elif menu == "📥 Cargar / Importar Presupuesto":
    st.title(f"Importar Presupuesto a: {proyecto_seleccionado}")
    
    st.info("Sube un archivo Excel (.xlsx) o CSV con el listado de actividades del proyecto.")
    st.markdown("""
    **Estructura obligatoria de columnas en el archivo:**
    - `codigo_item` (Ej: 1.1, 1.2, 2.1)
    - `capitulo` (Ej: Estructura, Cubierta, Acabados)
    - `descripcion` (Ej: Suministro de perfil W10x30)
    - `unidad` (Ej: m2, kg, ml, gl)
    - `cant_pres` (Cantidad presupuestada)
    - `apu_pres` (Valor unitario o APU)
    """)
    
    archivo = st.file_uploader("Seleccionar archivo Excel o CSV", type=["xlsx", "csv"])
    
    if archivo is not None:
        try:
            if archivo.name.endswith(".csv"):
                df_cargado = pd.read_csv(archivo)
            else:
                df_cargado = pd.read_excel(archivo)
            
            st.subheader("Vista previa de los datos a importar:")
            st.dataframe(df_cargado.head(10), use_container_width=True)
            
            if st.button("💾 Confirmar e Importar Presupuesto"):
                df_cargado["id_proyecto"] = int(id_proyecto_activo)
                datos_insertar = df_cargado[["id_proyecto", "codigo_item", "capitulo", "descripcion", "unidad", "cant_pres", "apu_pres"]].to_dict(orient="records")
                
                supabase.table("presupuesto").insert(datos_insertar).execute()
                st.success(f"¡Se importaron {len(datos_insertar)} actividades al proyecto {proyecto_seleccionado} correctamente!")
                st.rerun()
        except Exception as e:
            st.error(f"Error al procesar el archivo. Revisa que los nombres de las columnas sean exactos. Detalle: {e}")

# -----------------------------------------------------------------------------
# MÓDULO 3: INGRESO DE COSTOS Y FACTURAS
# -----------------------------------------------------------------------------
elif menu == "🧾 Ingreso de Costos":
    st.title(f"Ingreso de Facturas - Obra: {proyecto_seleccionado}")
    
    pres = supabase.table("presupuesto").select("id_actividad, codigo_item, descripcion").eq("id_proyecto", id_proyecto_activo).execute()
    df_act = pd.DataFrame(pres.data)
    
    prov = supabase.table("proveedores").select("id_proveedor, nombre").execute()
    df_prov = pd.DataFrame(prov.data)
    
    if df_act.empty or df_prov.empty:
        st.warning("Debes tener actividades en el presupuesto e importar proveedores antes de registrar facturas.")
    else:
        with st.form("form_factura", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            fecha = col1.date_input("Fecha", datetime.date.today())
            num_factura = col2.text_input("Número de Factura / Remisión")
            proveedor_nombre = col3.selectbox("Proveedor", df_prov["nombre"].tolist())
            
            st.markdown("---")
            act_desc = st.selectbox("Actividad de Obra Imputada:", df_act.apply(lambda r: f"{r['codigo_item']} - {r['descripcion']}", axis=1))
            
            c1, c2, c3 = st.columns(3)
            tipo_costo = c1.selectbox("Tipo de Costo", ["Materiales", "Mano de Obra", "Equipos", "Subcontratos"])
            insumo = c2.text_input("Descripción del Insumo", placeholder="Ej: Aceros W10x30")
            cantidad = c3.number_input("Cantidad", min_value=0.01, step=1.0)
            
            precio_unitario = st.number_input("Precio Unitario ($)", min_value=1.0, step=100.0)
            
            if st.form_submit_button("💾 Guardar Compra"):
                id_actividad_sel = df_act.iloc[df_act.apply(lambda r: f"{r['codigo_item']} - {r['descripcion']}", axis=1).tolist().index(act_desc)]["id_actividad"]
                id_prov_sel = df_prov[df_prov["nombre"] == proveedor_nombre]["id_proveedor"].values[0]
                
                datos = {
                    "id_proyecto": int(id_proyecto_activo),
                    "fecha": str(fecha),
                    "id_proveedor": int(id_prov_sel),
                    "num_factura": num_factura,
                    "id_actividad": int(id_actividad_sel),
                    "insumo": insumo,
                    "tipo_costo": tipo_costo,
                    "cantidad": float(cantidad),
                    "precio_unitario": float(precio_unitario)
                }
                supabase.table("compras").insert(datos).execute()
                st.success("Factura registrada exitosamente.")
                st.rerun()

# -----------------------------------------------------------------------------
# MÓDULO 4: PROVEEDORES
# -----------------------------------------------------------------------------
elif menu == "🚚 Proveedores":
    st.title("Gestión de Proveedores Centralizada")
    
    with st.expander("➕ Registrar Nuevo Proveedor"):
        with st.form("form_prov", clear_on_submit=True):
            col1, col2 = st.columns(2)
            nit = col1.text_input("NIT / Cédula")
            nombre = col2.text_input("Nombre / Razón Social")
            tel = col1.text_input("Teléfono")
            dir = col2.text_input("Dirección")
            contacto = st.text_input("Nombre de Contacto")
            
            if st.form_submit_button("Guardar Proveedor"):
                supabase.table("proveedores").insert({
                    "nit": nit, "nombre": nombre, "telefono": tel, "direccion": dir, "contacto": contacto
                }).execute()
                st.success("Proveedor creado con éxito.")
                st.rerun()
                
    prov_res = supabase.table("proveedores").select("*").execute()
    st.dataframe(pd.DataFrame(prov_res.data), use_container_width=True)

# -----------------------------------------------------------------------------
# MÓDULO 5: REGISTRAR AVANCES
# -----------------------------------------------------------------------------
elif menu == "📐 Registrar Avances":
    st.title(f"Avances de Obra - {proyecto_seleccionado}")
    
    pres = supabase.table("presupuesto").select("id_actividad, codigo_item, descripcion, unidad").eq("id_proyecto", id_proyecto_activo).execute()
    df_act = pd.DataFrame(pres.data)
    
    if not df_act.empty:
        with st.form("form_avance", clear_on_submit=True):
            fecha_av = st.date_input("Fecha del Avance", datetime.date.today())
            act_sel = st.selectbox("Actividad", df_act.apply(lambda r: f"{r['codigo_item']} - {r['descripcion']} ({r['unidad']})", axis=1))
            cant_ejec = st.number_input("Cantidad Ejecutada en el Periodo", min_value=0.01, step=0.1)
            memoria = st.text_area("Memoria de Cálculo / Localización (Ej: Eje A 1-5)")
            
            if st.form_submit_button("💾 Guardar Avance"):
                idx = df_act.apply(lambda r: f"{r['codigo_item']} - {r['descripcion']} ({r['unidad']})", axis=1).tolist().index(act_sel)
                id_act = df_act.iloc[idx]["id_actividad"]
                
                supabase.table("avances").insert({
                    "id_proyecto": int(id_proyecto_activo),
                    "fecha": str(fecha_av),
                    "id_actividad": int(id_act),
                    "cant_ejecutada": float(cant_ejec),
                    "memoria_detalle": memoria
                }).execute()
                st.success("Avance guardado con éxito.")
                st.rerun()

# -----------------------------------------------------------------------------
# MÓDULO 6: CREAR NUEVO PROYECTO
# -----------------------------------------------------------------------------
elif menu == "➕ Crear Nuevo Proyecto":
    st.title("Crear Nueva Obra")
    
    with st.form("form_nuevo_proyecto"):
        nombre_obra = st.text_input("Nombre de la Obra (Ej: Boreal / Palo de Agua)")
        cliente = st.text_input("Cliente / Entidad")
        
        if st.form_submit_button("🚀 Crear Proyecto"):
            if nombre_obra:
                supabase.table("proyectos").insert({"nombre": nombre_obra, "cliente": cliente}).execute()
                st.success(f"¡Proyecto '{nombre_obra}' creado exitosamente!")
                st.rerun()
            else:
                st.error("Ingresa el nombre del proyecto.")
