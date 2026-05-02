# ========== LOGIN ==========
if 'logueado' not in st.session_state:
    st.session_state.logueado = False

if not st.session_state.logueado:
    st.markdown('<h1 class="main-title">⛏️ BetaPro Mining</h1>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🔐 Iniciar Sesión", "📝 Registrarse"])
    
    with tab1:
        usuario_login = st.text_input("Usuario", key="login_user")
        password_login = st.text_input("Contraseña", type="password", key="login_pass")
        if st.button("Ingresar", use_container_width=True):
            u = login(usuario_login, password_login)
            if u:
                st.session_state.logueado = True
                st.session_state.usuario = u[1]
                st.session_state.rol = u[3]
                st.session_state.user_id = u[0]
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos")
    
    with tab2:
        nuevo_usuario = st.text_input("Usuario *", key="reg_user")
        nuevo_email = st.text_input("Email", key="reg_email")
        nueva_pass = st.text_input("Contraseña *", type="password", key="reg_pass")
        confirm_pass = st.text_input("Confirmar *", type="password", key="reg_confirm")
        if st.button("Registrarse", use_container_width=True, key="reg_btn"):
            if not nuevo_usuario or not nueva_pass:
                st.error("Usuario y contraseña son obligatorios")
            elif nueva_pass != confirm_pass:
                st.error("Las contraseñas no coinciden")
            else:
                if registrar_usuario(nuevo_usuario, nueva_pass, nuevo_email):
                    st.success("✅ Registrado! Ahora inicia sesión")
                else:
                    st.error("El usuario ya existe")
