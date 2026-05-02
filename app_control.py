    with tab1:
        usuario_login = st.text_input("Usuario", key="login_user")
        password_login = st.text_input("Contraseña", type="password", key="login_pass")
        if st.button("Ingresar", use_container_width=True, key="login_btn"):
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
        nuevo_usuario = st.text_input("Usuario", key="reg_user")
        nuevo_email = st.text_input("Email", key="reg_email")
        nueva_pass = st.text_input("Contraseña", type="password", key="reg_pass")
        confirmar_pass = st.text_input("Confirmar", type="password", key="reg_confirm")
        if st.button("Registrarse", use_container_width=True, key="reg_btn"):
            if nueva_pass == confirmar_pass:
                if registrar_usuario(nuevo_usuario, nueva_pass, nuevo_email):
                    st.success("Registrado! Ahora inicia sesión")
                else:
                    st.error("Usuario ya existe")
            else:
                st.error("Las contraseñas no coinciden")
