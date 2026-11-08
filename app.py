import streamlit as st
import pandas as pd
from supabase import create_client, Client
import datetime

# -----------------------------------------------------------------------------
# CONFIGURACIÓN DE PÁGINA Y TEMA
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Control de Costos - INGECONSPRO",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CONEXIÓN SEGURA A SUPABASE
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# -----------------------------------------------------------------------------
# ESTILOS CSS AVANZADOS (REPLICANDO INDEX.HTML ORIGINAL)
# -----------------------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    .stApp {
        background: linear-gradient(135deg, #090d16 0%, #111827 50%, #0f172a 100%) !important;
        color: #f3f4f6;
    }
    
    /* GLASS CARDS PARA KPIs */
    .glass-card {
        background: rgba(17, 24, 39, 0.7);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2);
    }
    
    /* BORDES DE KPI POR TIPO */
    .kpi-presupuesto { border-left: 5px solid #3b82f6 !important; }
    .kpi-costo-real { border-left: 5px solid #f43f5e !important; }
    .kpi-proyeccion { border-left: 5px solid #06b6d4 !important; }
    .kpi-utilidad { border-left: 5px solid #10b981 !important; }
    
    .kpi-title {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #9ca3af;
        font-weight: 600;
        margin-bottom: 6px;
    }
    
    .kpi-value {
        font-size: 1.6rem;
        font-weight: 800;
        margin: 0;
    }
    
    /* BADGES DE ESTADO EN APU */
    .badge-margen {
        background-color: rgba(16, 185, 129, 0.15);
        color: #10b981;
        padding: 4px 10px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.75rem;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    
    .badge-sobrecosto {
        background-color: rgba(244, 63, 94, 0.15);
        color: #f43f5e;
        padding: 4px 10px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.75rem;
        border: 1px solid rgba(244, 63, 94, 0.3);
    }

    /* BARRA LATERAL ESTILIZADA */
    [data-testid="stSidebar"] {
        background: rgba(15, 23, 42, 0.95) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# FUNCIONES DE FORMATO DE MONEDA Y NÚMEROS (COP)
# -----------------------------------------------------------------------------
def fmt_cop(val):
    try:
        return f"$ {val:,.0f}".replace(",", ".")
    except:
        return "$ 0"

def fmt_num(val, dec=2):
    try:
        return f"{val:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "0"

# -----------------------------------------------------------------------------
# BARRA LATERAL: LOGO Y SELECTOR GLOBAL DE PROYECTO
# -----------------------------------------------------------------------------
st.sidebar.image("https://lh3.googleusercontent.com/d/1GGsI4a9bvY2McOuHmj8NlFC_Vx0HA8VV", width=140)
st.sidebar.markdown("## **INGECONSPRO S.A.S.**")
st.sidebar.caption("Control Operativo & Financiero")

# Cargar lista de proyectos
res_proyectos = supabase.table("proyectos").select("*").execute()
df_proyectos = pd.DataFrame(res_proyectos.data)

if df_proyectos.empty:
    st.error("No hay proyectos en la base de datos.")
    st.stop()

st.sidebar.markdown("---")
st.sidebar.markdown("##### **PROYECTO ACTIVO**")
proyecto_seleccionado = st.sidebar.selectbox(
    "Selecciona la obra a consultar:",
    options=df_proyectos["nombre"].tolist(),
    index=0
)

id_proyecto_activo = df_proyectos[df_proyectos["nombre"] == proyecto_seleccionado]["id_proyecto"].values[0]

st.sidebar.markdown("---")
menu = st.sidebar.radio("Navegación Módulos:", [
    "📊 Dashboard & Presupuesto", 
    "📥 Importar Presupuesto",
    "🧾 Ingreso de Costos", 
    "📐 Registrar Avances", 
    "🚚 Proveedores", 
    "➕ Crear Nuevo Proyecto"
])

# -----------------------------------------------------------------------------
# MÓDULO 1: DASHBOARD CON TARJETAS GLASSMORPHISM Y TABLAS ESTILIZADAS
# -----------------------------------------------------------------------------
if menu == "📊 Dashboard & Presupuesto":
    st.markdown(f"### 🏗️ Obra Activa: **{proyecto_seleccionado}**")
    st.caption("Resumen Ejecutivo Base vs. Costos Reales")
    
    # Cargar actividades
    pres = supabase.table("presupuesto").select("*").eq("id_proyecto", id_proyecto_activo).execute()
    df_pres = pd.DataFrame(pres.data)
    
    if df_pres.empty:
        st.warning(f"El proyecto '{proyecto_seleccionado}' aún no tiene actividades en su presupuesto. Dirígete a '📥 Importar Presupuesto' para cargar su archivo CSV/Excel.")
    else:
        # Cargar Compras y Avances
        comp = supabase.table("compras").select("*").eq("id_proyecto", id_proyecto_activo).execute()
        df_comp = pd.DataFrame(comp.data)
        
        avan = supabase.table("avances").select("*").eq("id_proyecto", id_proyecto_activo).execute()
        df_avan = pd.DataFrame(avan.data)
        
        # Cálculos de Costo Real y Cantidad Ejecutada
        costo_real_map = {}
        if not df_comp.empty:
            df_comp["val_total"] = df_comp["cantidad"] * df_comp["precio_unitario"]
            costo_real_map = df_comp.groupby("id_actividad")["val_total"].sum().to_dict()
            
        cant_ejec_map = {}
        if not df_avan.empty:
            cant_ejec_map = df_avan.groupby("id_actividad")["cant_ejecutada"].sum().to_dict()
            
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
        
        # TARJETAS DE INDICADORES EN CSS GLASSMORPHISM
        tot_pres = df_pres['total_pres'].sum()
        tot_real = df_pres['costo_real'].sum()
        tot_proy = df_pres['proyeccion'].sum()
        tot_util = df_pres['utilidad'].sum()
        
        k1, k2, k3, k4 = st.columns(4)
        
        with k1:
            st.markdown(f"""
            <div class="glass-card kpi-presupuesto">
                <div class="kpi-title">PRESUPUESTO TOTAL</div>
                <div class="kpi-value" style="color:#3b82f6;">{fmt_cop(tot_pres)}</div>
            </div>
            """, unsafe_allow_html=True)
            
        with k2:
            st.markdown(f"""
            <div class="glass-card kpi-costo-real">
                <div class="kpi-title">COSTO REAL EJECUTADO</div>
                <div class="kpi-value" style="color:#f43f5e;">{fmt_cop(tot_real)}</div>
            </div>
            """, unsafe_allow_html=True)
            
        with k3:
            st.markdown(f"""
            <div class="glass-card kpi-proyeccion">
                <div class="kpi-title">COSTO PROYECTADO</div>
                <div class="kpi-value" style="color:#06b6d4;">{fmt_cop(tot_proy)}</div>
            </div>
            """, unsafe_allow_html=True)
            
        with k4:
            color_u = "#10b981" if tot_util >= 0 else "#f43f5e"
            st.markdown(f"""
            <div class="glass-card kpi-utilidad">
                <div class="kpi-title">UTILIDAD PROYECTADA</div>
                <div class="kpi-value" style="color:{color_u};">{fmt_cop(tot_util)}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("Auditoría de APU y Consolidado de Actividades")
        
        # FORMATEAR TABLA PARA INTERFAZ LIMPIA
        df_ver = df_pres.copy()
        df_ver["Cant. Pres."] = df_ver["cant_pres"].apply(lambda v: fmt_num(v, 2))
        df_ver["APU Pres."] = df_ver["apu_pres"].apply(fmt_cop)
        df_ver["Total Pres."] = df_ver["total_pres"].apply(fmt_cop)
        df_ver["Costo Real"] = df_ver["costo_real"].apply(fmt_cop)
        df_ver["Cant. Ejec."] = df_ver["cant_ejec"].apply(lambda v: fmt_num(v, 2))
        df_ver["APU Real"] = df_ver["apu_real"].apply(fmt_cop)
        df_ver["Proyección"] = df_ver["proyeccion"].apply(fmt_cop)
        df_ver["Utilidad"] = df_ver["utilidad"].apply(fmt_cop)
        
        columnas_renombradas = {
            "codigo_item": "Ítem",
            "capitulo": "Capítulo",
            "descripcion": "Descripción",
            "unidad": "Unidad",
            "estado": "Estado APU"
        }
        
        st.dataframe(
            df_ver.rename(columns=columnas_renombradas)[[
                "Ítem", "Capítulo", "Descripción", "Unidad", 
                "Cant. Pres.", "APU Pres.", "Total Pres.", 
                "Costo Real", "Cant. Ejec.", "APU Real", 
                "Proyección", "Utilidad", "Estado APU"
            ]],
            use_container_width=True,
            hide_index=True
        )

# -----------------------------------------------------------------------------
# MÓDULO 2: IMPORTAR PRESUPUESTO AL PROYECTO ACTIVO
# -----------------------------------------------------------------------------
elif menu == "📥 Importar Presupuesto":
    st.title(f"Importar Presupuesto a: {proyecto_seleccionado}")
    
    st.info("Carga el archivo CSV o Excel generado con las actividades de la obra.")
    
    archivo = st.file_uploader("Seleccionar archivo (CSV o XLSX)", type=["csv", "xlsx"])
    
    if archivo is not None:
        try:
            if archivo.name.endswith(".csv"):
                df_cargado = pd.read_csv(archivo)
            else:
                df_cargado = pd.read_excel(archivo)
            
            st.markdown("#### Vista previa de los datos a cargar:")
            st.dataframe(df_cargado.head(10), use_container_width=True, hide_index=True)
            
            if st.button("💾 Cargar Presupuesto a la Obra Activa", type="primary"):
                df_cargado["id_proyecto"] = int(id_proyecto_activo)
                datos_insertar = df_cargado[["id_proyecto", "codigo_item", "capitulo", "descripcion", "unidad", "cant_pres", "apu_pres"]].to_dict(orient="records")
                
                # Limpiar presupuesto previo si existe
                supabase.table("presupuesto").delete().eq("id_proyecto", id_proyecto_activo).execute()
                
                # Insertar nuevos ítems
                supabase.table("presupuesto").insert(datos_insertar).execute()
                st.success(f"¡Se importaron {len(datos_insertar)} actividades correctamente a {proyecto_seleccionado}!")
                st.rerun()
        except Exception as e:
            st.error(f"Error al leer el archivo. Asegúrate de usar la plantilla descargada. Detalle: {e}")

# -----------------------------------------------------------------------------
# MÓDULO 3: INGRESO DE COSTOS (FACTURAS)
# -----------------------------------------------------------------------------
elif menu == "🧾 Ingreso de Costos":
    st.title(f"Imputación de Costos - Obra: {proyecto_seleccionado}")
    
    pres = supabase.table("presupuesto").select("id_actividad, codigo_item, descripcion").eq("id_proyecto", id_proyecto_activo).execute()
    df_act = pd.DataFrame(pres.data)
    
    prov = supabase.table("proveedores").select("id_proveedor, nombre").execute()
    df_prov = pd.DataFrame(prov.data)
    
    if df_act.empty:
        st.warning("Debes cargar primero el presupuesto de esta obra antes de ingresar facturas.")
    else:
        with st.form("form_facturas", clear_on_submit=True):
            st.markdown("##### **1. Encabezado del Documento**")
            f1, f2, f3 = st.columns(3)
            fecha_fac = f1.date_input("Fecha de Factura", datetime.date.today())
            num_fac = f2.text_input("Número de Factura / Remisión", placeholder="Ej: F-1045")
            
            prov_list = df_prov["nombre"].tolist() if not df_prov.empty else ["Sin Proveedores"]
            prov_nom = f3.selectbox("Proveedor", prov_list)
            
            st.markdown("##### **2. Asignación de Costo a Actividad Presupuestada**")
            act_opciones = df_act.apply(lambda r: f"{r['codigo_item']} - {r['descripcion']}", axis=1).tolist()
            act_sel = st.selectbox("Actividad de Obra Target:", act_opciones)
            
            c1, c2, c3, c4 = st.columns(4)
            tipo_c = c1.selectbox("Tipo de Costo", ["Materiales", "Mano de Obra", "Equipos", "Subcontratos"])
            insumo_desc = c2.text_input("Descripción Insumo", placeholder="Ej: Perfil Estructural W10")
            cant_ing = c3.number_input("Cantidad Insumo", min_value=0.001, step=1.0)
            precio_u = c4.number_input("Precio Unitario ($)", min_value=1.0, step=100.0)
            
            val_total_calc = cant_ing * precio_u
            st.markdown(f"**Total Línea:** `{fmt_cop(val_total_calc)}`")
            
            btn_save = st.form_submit_button("💾 Registar Costo en Obra", type="primary")
            
            if btn_save:
                idx = act_opciones.index(act_sel)
                id_act_target = df_act.iloc[idx]["id_actividad"]
                id_prov_target = df_prov[df_prov["nombre"] == prov_nom]["id_proveedor"].values[0] if not df_prov.empty else None
                
                datos_compra = {
                    "id_proyecto": int(id_proyecto_activo),
                    "fecha": str(fecha_fac),
                    "id_proveedor": int(id_prov_target) if id_prov_target else None,
                    "num_factura": num_fac,
                    "id_actividad": int(id_act_target),
                    "insumo": insumo_desc,
                    "tipo_costo": tipo_c,
                    "cantidad": float(cant_ing),
                    "precio_unitario": float(precio_u)
                }
                supabase.table("compras").insert(datos_compra).execute()
                st.success("Costo asignado y guardado correctamente.")
                st.rerun()

# -----------------------------------------------------------------------------
# MÓDULO 4: REGISTRAR AVANCES DE OBRA
# -----------------------------------------------------------------------------
elif menu == "📐 Registrar Avances":
    st.title(f"Avances Físicos - Obra: {proyecto_seleccionado}")
    
    pres = supabase.table("presupuesto").select("id_actividad, codigo_item, descripcion, unidad").eq("id_proyecto", id_proyecto_activo).execute()
    df_act = pd.DataFrame(pres.data)
    
    if not df_act.empty:
        with st.form("form_avances", clear_on_submit=True):
            col_f, col_a = st.columns([1, 3])
            fecha_av = col_f.date_input("Fecha Reporte", datetime.date.today())
            
            act_opciones = df_act.apply(lambda r: f"{r['codigo_item']} - {r['descripcion']} ({r['unidad']})", axis=1).tolist()
            act_sel = col_a.selectbox("Actividad Ejecutada:", act_opciones)
            
            cant_ejec = st.number_input("Cantidad Ejecutada en el Periodo", min_value=0.001, step=0.1)
            memoria = st.text_area("Memoria de Cálculo / Ubicación (Ej: Tramo Eje 1-3, Piso 4)", placeholder="Desglose de dimensiones...")
            
            if st.form_submit_button("💾 Guardar Avance Físico", type="primary"):
                idx = act_opciones.index(act_sel)
                id_act_target = df_act.iloc[idx]["id_actividad"]
                
                supabase.table("avances").insert({
                    "id_proyecto": int(id_proyecto_activo),
                    "fecha": str(fecha_av),
                    "id_actividad": int(id_act_target),
                    "cant_ejecutada": float(cant_ejec),
                    "memoria_detalle": memoria
                }).execute()
                st.success("Avance guardado con éxito.")
                st.rerun()

# -----------------------------------------------------------------------------
# MÓDULO 5: PROVEEDORES
# -----------------------------------------------------------------------------
elif menu == "🚚 Proveedores":
    st.title("Directorio Comercial de Proveedores")
    
    with st.expander("➕ Registrar Nuevo Proveedor"):
        with st.form("form_prov_new", clear_on_submit=True):
            p1, p2 = st.columns(2)
            nit = p1.text_input("NIT / Cédula")
            nombre = p2.text_input("Razón Social")
            tel = p1.text_input("Teléfono")
            dir_p = p2.text_input("Dirección")
            contacto = st.text_input("Nombre de Contacto")
            
            if st.form_submit_button("Guardar Proveedor", type="primary"):
                supabase.table("proveedores").insert({
                    "nit": nit, "nombre": nombre, "telefono": tel, "direccion": dir_p, "contacto": contacto
                }).execute()
                st.success("Proveedor creado con éxito.")
                st.rerun()
                
    prov_res = supabase.table("proveedores").select("*").execute()
    if prov_res.data:
        st.dataframe(pd.DataFrame(prov_res.data)[["nit", "nombre", "telefono", "direccion", "contacto"]], use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# MÓDULO 6: CREAR PROYECTO
# -----------------------------------------------------------------------------
elif menu == "➕ Crear Nuevo Proyecto":
    st.title("Crear Nuevo Proyecto en la Firma")
    
    with st.form("form_new_proy", clear_on_submit=True):
        nom_obra = st.text_input("Nombre del Proyecto / Obra (Ej: Boreal, Torres de San Mateo)")
        cli_obra = st.text_input("Cliente / Constructora / Entidad")
        
        if st.form_submit_button("🚀 Crear Proyecto", type="primary"):
            if nom_obra:
                supabase.table("proyectos").insert({"nombre": nom_obra, "cliente": cli_obra}).execute()
                st.success(f"¡Proyecto '{nom_obra}' registrado en el sistema!")
                st.rerun()
            else:
                st.error("Ingresa el nombre del proyecto.")
