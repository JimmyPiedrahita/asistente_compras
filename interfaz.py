import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk


class InterfazUsuario:
    """
    Vista (GUI) del sistema. Implementa 'actualizar' para responder
    a las notificaciones del Carrito (Observer).
    """

    BG_COLOR = "#f4f4f9"
    PRIMARY_COLOR = "#4a90e2"
    FONT_TITLE = ("Helvetica", 20, "bold")
    FONT_NORMAL = ("Helvetica", 12)
    FONT_SMALL = ("Helvetica", 10)

    MODOS_BUSQUEDA = ("Mejor precio por almacén", "Catálogo completo",
                      "Mejor precio global")
    OPCIONES_DESCUENTO = ("Sin descuento", "Porcentaje (%)", "Monto fijo ($)")

    def __init__(self):
        self._controlador = None
        self.root = None
        self._refrescar_carrito = None
        self._resultados_actuales = []

    def set_controlador(self, controlador):
        self._controlador = controlador

    # = CALLBACKS DEL OBSERVER =

    def actualizar(self, sujeto, mensaje: str):
        print(f"\n[NOTIFICACIÓN VISTA]: {mensaje}")
        print(f"[NUEVO TOTAL EN TIEMPO REAL]: ${sujeto.calcular_total():.2f}")
        if (self._refrescar_carrito is not None and self.root is not None
                and self.root.winfo_exists()):
            try:
                self._refrescar_carrito()
            except tk.TclError:
                pass

    def notificar_denegado(self, permiso: str):
        print(f"[PERMISO DENEGADO]: {permiso}")
        if self.root is not None and self.root.winfo_exists():
            messagebox.showwarning(
                "Permiso denegado",
                f"Su rol actual no permite la acción '{permiso}'.")

    def mostrar_carrito(self, productos, subtotal, total, descuento="Sin descuento"):
        """Salida de carrito para el modo consola."""
        if not productos:
            print("\nEl carrito está vacío.")
            return
        print("\n--- CARRITO ---")
        for indice, producto in enumerate(productos, start=1):
            print(f" {indice}. {producto}")
        print(f" Subtotal:  ${subtotal:.2f}")
        print(f" Descuento: {descuento}")
        print(f" TOTAL:     ${total:.2f}")

    # = VENTANA PRINCIPAL =

    def ejecutar(self):
        self.root = tk.Tk()
        self.root.title("Asistente de Compras Inteligente")
        self.root.geometry("1000x700")
        self.root.minsize(900, 640)
        style = ttk.Style(self.root)
        style.theme_use('clam')
        style.configure("Action.TButton", font=("Helvetica", 12, "bold"), padding=10)
        self._mostrar_menu_principal()
        self.root.mainloop()

    def _limpiar_pantalla(self):
        self._refrescar_carrito = None
        self._resultados_actuales = []
        if self.root is None:
            return
        self.root.unbind("<Return>")
        for widget in self.root.winfo_children():
            widget.destroy()
        self.root.configure(bg=self.BG_COLOR)

    def _cabecera(self, titulo: str, subtitulo: str = None):
        header = tk.Frame(self.root, bg=self.PRIMARY_COLOR)
        header.pack(fill=tk.X)
        tk.Label(header, text=titulo, font=self.FONT_TITLE,
                 bg=self.PRIMARY_COLOR, fg="white").pack(pady=(12, 0))
        tk.Label(header, text=subtitulo or " ", font=self.FONT_SMALL,
                 bg=self.PRIMARY_COLOR, fg="#e8f0fb").pack(pady=(0, 10))
        return header

    def _volver_al_menu(self):
        if self._controlador is not None:
            self._controlador.cerrar_sesion()
        self._mostrar_menu_principal()

    # = MENÚ PRINCIPAL =

    def _mostrar_menu_principal(self):
        self._limpiar_pantalla()

        hero = tk.Frame(self.root, bg=self.PRIMARY_COLOR, height=150)
        hero.pack(fill=tk.X)
        hero.pack_propagate(False)
        tk.Label(hero, text="Asistente de Compras", font=("Helvetica", 28, "bold"),
                 fg="white", bg=self.PRIMARY_COLOR).pack(expand=True)

        body = tk.Frame(self.root, bg=self.BG_COLOR)
        body.pack(expand=True, fill=tk.BOTH)

        cards = tk.Frame(body, bg=self.BG_COLOR)
        cards.place(relx=0.5, rely=0.4, anchor="center")
        tk.Label(cards, text="Seleccione su Perfil", font=("Helvetica", 16),
                 bg=self.BG_COLOR).pack(pady=20)

        ttk.Button(cards, text="Ingresar como Usuario",
                   command=self._entrar_como_usuario,
                   style="Action.TButton", width=25).pack(pady=10)
        ttk.Button(cards, text="Administrar Almacenes",
                   command=self._mostrar_login_admin,
                   style="Action.TButton", width=25).pack(pady=10)

        rol = self._controlador.obtener_rol() if self._controlador else "INVITADO"
        tk.Label(cards, text=f"Rol actual: {rol}", font=self.FONT_SMALL,
                 bg=self.BG_COLOR, fg="#555555").pack(pady=(15, 0))

    def _entrar_como_usuario(self):
        nombre = simpledialog.askstring(
            "Iniciar sesión", "Ingrese su nombre de usuario:", parent=self.root)
        if nombre is None:
            return
        nombre = nombre.strip()
        if not nombre:
            messagebox.showwarning("Advertencia", "Ingrese un nombre válido.")
            return
        # Si ya existe, registrar_usuario devuelve False y el login sigue siendo válido.
        self._controlador.registrar_usuario(nombre)
        if self._controlador.iniciar_sesion(nombre):
            self._mostrar_menu_usuario()
        else:
            messagebox.showerror("Error", "No se pudo iniciar sesión.")

    # = MENÚ DE USUARIO =

    def _mostrar_menu_usuario(self):
        self._limpiar_pantalla()
        usuario = self._controlador.obtener_usuario_actual() or "Invitado"
        self._cabecera("Compras - Usuario", f"Sesión: {usuario}  |  "
                       f"Rol: {self._controlador.obtener_rol()}")

        body = tk.Frame(self.root, bg=self.BG_COLOR)
        body.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        body.columnconfigure(0, weight=1, uniform="col")
        body.columnconfigure(1, weight=1, uniform="col")
        body.rowconfigure(0, weight=3)
        body.rowconfigure(1, weight=2)

        # --- Lista de compras ---
        frame_lista = ttk.LabelFrame(body, text="Mi lista de compras")
        frame_lista.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 8))
        frame_lista.columnconfigure(0, weight=1)
        frame_lista.rowconfigure(1, weight=1)

        controles = ttk.Frame(frame_lista)
        controles.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=8)
        ttk.Label(controles, text="Producto:").pack(side=tk.LEFT)
        entrada = ttk.Entry(controles, width=20)
        entrada.pack(side=tk.LEFT, padx=6)
        btn_agregar = ttk.Button(controles, text="Agregar")
        btn_agregar.pack(side=tk.LEFT)
        btn_eliminar = ttk.Button(controles, text="Eliminar")
        btn_eliminar.pack(side=tk.LEFT, padx=4)

        listbox = tk.Listbox(frame_lista, font=self.FONT_NORMAL, height=8,
                             bg="white", selectbackground=self.PRIMARY_COLOR)
        listbox.grid(row=1, column=0, sticky="nsew", padx=(8, 0), pady=(0, 8))
        scroll = ttk.Scrollbar(frame_lista, orient=tk.VERTICAL, command=listbox.yview)
        scroll.grid(row=1, column=1, sticky="ns", padx=(0, 8), pady=(0, 8))
        listbox.configure(yscrollcommand=scroll.set)

        # --- Carrito ---
        frame_carrito = ttk.LabelFrame(body, text="Mi carrito")
        frame_carrito.grid(row=0, column=1, sticky="nsew", pady=(0, 8))
        frame_carrito.columnconfigure(0, weight=1)
        frame_carrito.rowconfigure(0, weight=1)

        lb_carrito = tk.Listbox(frame_carrito, font=self.FONT_SMALL, height=7,
                                bg="white", selectbackground=self.PRIMARY_COLOR)
        lb_carrito.grid(row=0, column=0, sticky="nsew", padx=(8, 0), pady=(8, 0))
        scroll_carrito = ttk.Scrollbar(frame_carrito, orient=tk.VERTICAL,
                                       command=lb_carrito.yview)
        scroll_carrito.grid(row=0, column=1, sticky="ns", padx=(0, 8), pady=(8, 0))
        lb_carrito.configure(yscrollcommand=scroll_carrito.set)

        resumen = ttk.Frame(frame_carrito)
        resumen.grid(row=1, column=0, columnspan=2, sticky="ew", padx=8, pady=4)
        lbl_subtotal = ttk.Label(resumen, text="Subtotal: $0.00")
        lbl_subtotal.pack(anchor="w")
        lbl_descuento = ttk.Label(resumen, text="Descuento: Sin descuento")
        lbl_descuento.pack(anchor="w")
        lbl_total = ttk.Label(resumen, text="Total: $0.00",
                              font=("Helvetica", 13, "bold"))
        lbl_total.pack(anchor="w", pady=(2, 0))

        descuento = ttk.Frame(frame_carrito)
        descuento.grid(row=2, column=0, columnspan=2, sticky="ew", padx=8, pady=4)
        combo_descuento = ttk.Combobox(descuento, state="readonly", width=15,
                                       values=self.OPCIONES_DESCUENTO)
        combo_descuento.current(0)
        combo_descuento.pack(side=tk.LEFT)
        entrada_descuento = ttk.Entry(descuento, width=8)
        entrada_descuento.pack(side=tk.LEFT, padx=6)
        btn_descuento = ttk.Button(descuento, text="Aplicar")
        btn_descuento.pack(side=tk.LEFT)

        btn_quitar = ttk.Button(frame_carrito, text="Quitar del carrito")
        btn_quitar.grid(row=3, column=0, sticky="ew", padx=(8, 4), pady=(0, 8))
        btn_vaciar = ttk.Button(frame_carrito, text="Vaciar")
        btn_vaciar.grid(row=3, column=1, sticky="ew", padx=(0, 8), pady=(0, 8))

        # --- Búsqueda ---
        frame_busqueda = ttk.LabelFrame(body, text="Buscar en almacenes")
        frame_busqueda.grid(row=1, column=0, columnspan=2, sticky="nsew")
        frame_busqueda.columnconfigure(0, weight=1)
        frame_busqueda.rowconfigure(1, weight=1)

        barra = ttk.Frame(frame_busqueda)
        barra.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=8)
        ttk.Label(barra, text="Modo:").pack(side=tk.LEFT)
        combo_modo = ttk.Combobox(barra, state="readonly", width=26,
                                  values=self.MODOS_BUSQUEDA)
        combo_modo.current(0)
        combo_modo.pack(side=tk.LEFT, padx=6)
        btn_buscar = ttk.Button(barra, text="Buscar")
        btn_buscar.pack(side=tk.LEFT)
        btn_al_carrito = ttk.Button(barra, text="Agregar al carrito")
        btn_al_carrito.pack(side=tk.LEFT, padx=8)
        ttk.Label(barra, text="(seleccione un producto del resultado)",
                  font=self.FONT_SMALL).pack(side=tk.LEFT)

        lb_resultados = tk.Listbox(frame_busqueda, font=("Consolas", 10), height=7,
                                   bg="#eef2f5", selectbackground=self.PRIMARY_COLOR)
        lb_resultados.grid(row=1, column=0, sticky="nsew", padx=(8, 0), pady=(0, 8))
        scroll_res = ttk.Scrollbar(frame_busqueda, orient=tk.VERTICAL,
                                   command=lb_resultados.yview)
        scroll_res.grid(row=1, column=1, sticky="ns", padx=(0, 8), pady=(0, 8))
        lb_resultados.configure(yscrollcommand=scroll_res.set)

        pie = ttk.Frame(body)
        pie.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        ttk.Button(pie, text="Exportar lista", command=self._exportar_lista).pack(side=tk.LEFT)
        ttk.Button(pie, text="Exportar carrito",
                   command=self._exportar_carrito).pack(side=tk.LEFT, padx=8)
        ttk.Button(pie, text="Cerrar sesión y volver",
                   command=self._volver_al_menu).pack(side=tk.RIGHT)

        # --- Lógica de la pantalla ---

        def actualizar_lista():
            listbox.delete(0, tk.END)
            for producto in self._controlador.obtener_compras_usuario():
                listbox.insert(tk.END, producto)

        def agregar_producto():
            estado = self._controlador.agregar_producto_usuario(entrada.get())
            if estado == "ok":
                entrada.delete(0, tk.END)
                actualizar_lista()
            elif estado == "duplicado":
                messagebox.showwarning("Duplicado",
                                       "Ese producto ya está en su lista.")
            elif estado == "vacio":
                messagebox.showwarning("Advertencia",
                                       "Ingrese el nombre del producto.")

        def eliminar_producto():
            seleccion = listbox.curselection()
            if seleccion:
                nombre = listbox.get(seleccion[0])
            else:
                nombre = entrada.get().strip()
            if not nombre:
                messagebox.showwarning(
                    "Advertencia", "Seleccione un producto o escriba su nombre.")
                return
            estado = self._controlador.eliminar_producto_usuario(nombre)
            if estado == "ok":
                entrada.delete(0, tk.END)
                actualizar_lista()
            elif estado == "no_encontrado":
                messagebox.showwarning("No encontrado",
                                       "Ese producto no está en la lista.")

        def refrescar_carrito():
            resumen_carrito = self._controlador.obtener_resumen_carrito()
            lb_carrito.delete(0, tk.END)
            for producto in resumen_carrito["productos"]:
                lb_carrito.insert(
                    tk.END,
                    f"{producto.nombre} ({producto.marca})  "
                    f"${producto.obtener_precio_final():.2f}")
            lbl_subtotal.configure(
                text=f"Subtotal: ${resumen_carrito['subtotal']:.2f}")
            lbl_descuento.configure(
                text=f"Descuento: {resumen_carrito['descuento']}")
            lbl_total.configure(text=f"Total: ${resumen_carrito['total']:.2f}")

        def quitar_del_carrito():
            seleccion = lb_carrito.curselection()
            if not seleccion:
                messagebox.showwarning("Advertencia",
                                       "Seleccione un producto del carrito.")
                return
            self._controlador.quitar_producto_carrito(seleccion[0])

        def vaciar_carrito():
            self._controlador.vaciar_carrito()

        def aplicar_descuento():
            mapa = {"Sin descuento": "sin", "Porcentaje (%)": "porcentaje",
                    "Monto fijo ($)": "fijo"}
            opcion = mapa.get(combo_descuento.get(), "sin")
            valor = entrada_descuento.get().strip() or None
            estado = self._controlador.establecer_descuento(opcion, valor)
            if estado == "invalido":
                messagebox.showerror(
                    "Descuento inválido",
                    "Ingrese un porcentaje entre 0 y 100 o un monto positivo.")

        def insertar_resultado(texto, meta=None):
            lb_resultados.insert(tk.END, texto)
            self._resultados_actuales.append(meta)

        def buscar():
            lb_resultados.delete(0, tk.END)
            self._resultados_actuales = []
            modo = combo_modo.get()
            if modo == "Mejor precio global":
                filas = self._controlador.ejecutar_comparacion_global()
                for fila in filas:
                    insertar_resultado(
                        f"{fila['nombre']} ({fila['producto'].marca})  "
                        f"${fila['precio']:.2f}  ->  {fila['almacen'].nombre}",
                        (fila["producto"], fila["almacen"]))
                if not filas:
                    insertar_resultado("Sin coincidencias para su lista.")
                return

            if modo == "Catálogo completo":
                resultados = self._controlador.ejecutar_catalogo()
            else:
                resultados = self._controlador.ejecutar_busqueda_precios()

            hubo = False
            for almacen, lista_productos in resultados.items():
                if lista_productos.esta_vacia():
                    continue
                insertar_resultado(f"--- {almacen.nombre} ---")
                for producto in lista_productos.mostrar():
                    insertar_resultado(
                        f"  {producto.nombre} ({producto.marca}) - "
                        f"${producto.obtener_precio_final():.2f}",
                        (producto, almacen))
                    hubo = True
            if not hubo:
                insertar_resultado("Sin coincidencias para su lista.")

        def agregar_al_carrito():
            seleccion = lb_resultados.curselection()
            if not seleccion:
                messagebox.showwarning("Advertencia",
                                       "Seleccione un producto del resultado.")
                return
            indice = seleccion[0]
            if indice >= len(self._resultados_actuales):
                return
            meta = self._resultados_actuales[indice]
            if meta is None:
                messagebox.showinfo("Sugerencia",
                                    "Seleccione un producto, no una cabecera.")
                return
            producto, almacen = meta
            if not self._controlador.agregar_seleccion_al_carrito(
                    producto, almacen.id_almacen):
                messagebox.showwarning(
                    "No disponible",
                    "El producto ya no está disponible en ese almacén.")

        btn_agregar.configure(command=agregar_producto)
        btn_eliminar.configure(command=eliminar_producto)
        btn_quitar.configure(command=quitar_del_carrito)
        btn_vaciar.configure(command=vaciar_carrito)
        btn_descuento.configure(command=aplicar_descuento)
        btn_buscar.configure(command=buscar)
        btn_al_carrito.configure(command=agregar_al_carrito)
        entrada.bind("<Return>", lambda event: agregar_producto())

        self._refrescar_carrito = refrescar_carrito
        actualizar_lista()
        refrescar_carrito()

    # = EXPORTACIÓN DESDE EL MENÚ DE USUARIO =

    def _exportar_lista(self):
        ruta = filedialog.asksaveasfilename(
            parent=self.root, title="Exportar lista de compras",
            defaultextension=".csv", initialfile="lista_compras.csv",
            filetypes=[("CSV", "*.csv")])
        if not ruta:
            return
        resultado = self._controlador.exportar_lista(ruta)
        if resultado["ok"]:
            messagebox.showinfo("Exportación",
                                f"Se exportaron {resultado['filas']} filas.")
        else:
            messagebox.showerror("Error", "No se pudo exportar la lista.")

    def _exportar_carrito(self):
        ruta = filedialog.asksaveasfilename(
            parent=self.root, title="Exportar carrito",
            defaultextension=".csv", initialfile="carrito.csv",
            filetypes=[("CSV", "*.csv")])
        if not ruta:
            return
        resultado = self._controlador.exportar_carrito(ruta)
        if resultado["ok"]:
            messagebox.showinfo("Exportación",
                                f"Se exportaron {resultado['filas']} ítems.")
        else:
            messagebox.showerror("Error", "No se pudo exportar el carrito.")

    # = LOGIN Y PANEL DE ADMINISTRACIÓN =

    def _mostrar_login_admin(self):
        self._limpiar_pantalla()

        frame_login = tk.Frame(self.root, bg="white", padx=40, pady=40,
                               relief="groove", bd=2)
        frame_login.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(frame_login, text="Admin", font=self.FONT_TITLE,
                 bg="white").pack(pady=(0, 20))
        tk.Label(frame_login, text="Clave de acceso:", font=self.FONT_NORMAL,
                 bg="white").pack()

        password_entry = ttk.Entry(frame_login, show="*", font=self.FONT_NORMAL)
        password_entry.pack(pady=10)
        password_entry.focus()

        def check_password(event=None):
            if self._controlador.login_admin(password_entry.get()):
                self._mostrar_menu_admin()
            else:
                messagebox.showerror("Error", "Clave incorrecta")

        password_entry.bind("<Return>", check_password)

        ttk.Button(frame_login, text="Ingresar",
                   command=check_password).pack(pady=5, fill=tk.X)
        ttk.Button(frame_login, text="Cancelar",
                   command=self._mostrar_menu_principal).pack(fill=tk.X)

    def _mostrar_menu_admin(self):
        self._limpiar_pantalla()
        self._cabecera("Panel de Administración", "Rol: ADMIN")

        body = tk.Frame(self.root, bg=self.BG_COLOR)
        body.pack(fill=tk.BOTH, expand=True, padx=16, pady=8)

        almacenes = self._controlador.gestor_almacenes.obtener_almacenes()
        listboxes = []

        # --- Formulario de alta ---
        frame_add = ttk.LabelFrame(body, text="Agregar producto a un almacén")
        frame_add.pack(fill=tk.X, pady=(0, 8))

        campos = (("Nombre", 0), ("Marca", 1), ("Categoría", 2),
                  ("Tipo", 3), ("Almacén", 4))
        for texto, columna in campos:
            ttk.Label(frame_add, text=texto).grid(
                row=0, column=columna, sticky="w", padx=6, pady=(6, 0))

        entry_nombre = ttk.Entry(frame_add, width=18)
        entry_nombre.grid(row=1, column=0, sticky="ew", padx=6)
        entry_marca = ttk.Entry(frame_add, width=16)
        entry_marca.grid(row=1, column=1, sticky="ew", padx=6)
        entry_categoria = ttk.Entry(frame_add, width=16)
        entry_categoria.grid(row=1, column=2, sticky="ew", padx=6)

        combo_tipo = ttk.Combobox(frame_add, state="readonly", width=14,
                                  values=("normal", "fisico", "digital",
                                          "suscripcion"))
        combo_tipo.current(0)
        combo_tipo.grid(row=1, column=3, sticky="ew", padx=6)

        nombres_almacenes = [almacen.nombre for almacen in almacenes]
        combo_almacen = ttk.Combobox(frame_add, state="readonly", width=14,
                                     values=nombres_almacenes or ("Almacen 1",))
        combo_almacen.current(0)
        combo_almacen.grid(row=1, column=4, sticky="ew", padx=6)

        ttk.Label(frame_add, text="Precio").grid(
            row=2, column=0, sticky="w", padx=6, pady=(6, 0))
        entry_precio = ttk.Entry(frame_add, width=18)
        entry_precio.grid(row=3, column=0, sticky="ew", padx=6, pady=(0, 6))

        ttk.Label(frame_add, text="Extra (envío / meses)").grid(
            row=2, column=1, sticky="w", padx=6, pady=(6, 0))
        entry_extra = ttk.Entry(frame_add, width=16)
        entry_extra.grid(row=3, column=1, sticky="ew", padx=6, pady=(0, 6))

        for columna in range(5):
            frame_add.columnconfigure(columna, weight=1)

        def actualizar_almacenes():
            for lb in listboxes:
                lb.delete(0, tk.END)
            for indice, almacen in enumerate(almacenes):
                if indice >= len(listboxes):
                    break
                for producto in almacen.inventario.mostrar():
                    listboxes[indice].insert(
                        tk.END,
                        f"{producto.nombre} ({producto.marca})  "
                        f"${producto.precio:.2f}")

        def guardar_producto():
            nombre = entry_nombre.get().strip()
            try:
                precio = float(entry_precio.get().strip())
            except ValueError:
                messagebox.showerror("Error", "El precio debe ser numérico.")
                return
            tipo = combo_tipo.get()
            extra_txt = entry_extra.get().strip()
            kwargs = {}
            try:
                if tipo == "fisico":
                    kwargs["costo_envio"] = float(extra_txt) if extra_txt else 5.0
                elif tipo == "suscripcion":
                    kwargs["meses"] = int(extra_txt) if extra_txt else 1
            except ValueError:
                messagebox.showerror(
                    "Error", "El extra debe ser el costo de envío o los meses.")
                return
            if not almacenes:
                messagebox.showerror("Error", "No hay almacenes disponibles.")
                return
            indice_almacen = combo_almacen.current()
            id_almacen = almacenes[indice_almacen].id_almacen
            if self._controlador.agregar_producto_almacen(
                    id_almacen, nombre, precio,
                    marca=entry_marca.get().strip() or "Generica",
                    categoria=entry_categoria.get().strip() or "General",
                    tipo=tipo, **kwargs):
                entry_nombre.delete(0, tk.END)
                entry_precio.delete(0, tk.END)
                entry_extra.delete(0, tk.END)
                actualizar_almacenes()
            else:
                messagebox.showwarning(
                    "No se pudo agregar",
                    "Revise el nombre, el precio y sus permisos.")

        def editar(indice_almacen, listbox, entrada_precio):
            seleccion = listbox.curselection()
            if not seleccion:
                messagebox.showwarning(
                    "Advertencia", "Seleccione un producto del inventario.")
                return
            try:
                nuevo_precio = float(entrada_precio.get().strip())
            except ValueError:
                messagebox.showerror("Error", "El nuevo precio debe ser numérico.")
                return
            almacen = almacenes[indice_almacen]
            if self._controlador.editar_precio(
                    almacen.id_almacen, seleccion[0], nuevo_precio):
                actualizar_almacenes()
                entrada_precio.delete(0, tk.END)
            else:
                messagebox.showwarning(
                    "No se pudo actualizar",
                    "Revise el precio o sus permisos.")

        def cargar_csv():
            ruta = filedialog.askopenfilename(
                parent=self.root, title="Seleccionar CSV",
                filetypes=[("CSV", "*.csv"), ("Todos", "*.*")])
            if not ruta:
                return
            resultado = self._controlador.cargar_csv(ruta)
            mensaje = (f"Importados: {resultado['importados']}\n"
                       f"Rechazados: {resultado['rechazados']}")
            if resultado["errores"]:
                mensaje += "\n\n" + "\n".join(resultado["errores"][:6])
            if resultado["importados"]:
                messagebox.showinfo("Carga CSV", mensaje)
            else:
                messagebox.showwarning("Carga CSV", mensaje)
            actualizar_almacenes()

        ttk.Button(frame_add, text="Guardar producto",
                   command=guardar_producto).grid(
            row=3, column=3, columnspan=2, sticky="ew", padx=6, pady=(0, 6))

        barra = ttk.Frame(body)
        barra.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(barra, text="Cargar CSV...",
                   command=cargar_csv).pack(side=tk.LEFT)
        ttk.Label(barra,
                  text="Cabecera: almacen,nombre,marca,categoria,tipo,precio,extra",
                  font=self.FONT_SMALL).pack(side=tk.LEFT, padx=10)

        # --- Inventario ---
        frame_inv = ttk.LabelFrame(body, text="Inventario de almacenes")
        frame_inv.pack(fill=tk.BOTH, expand=True)

        for columna, almacen in enumerate(almacenes):
            frame_inv.columnconfigure(columna, weight=1)
            ttk.Label(frame_inv, text=almacen.nombre,
                      font=("Helvetica", 11, "bold")).grid(
                row=0, column=columna, pady=(6, 2), padx=6)

            lb = tk.Listbox(frame_inv, font=("Consolas", 10), height=10,
                            bg="white", selectbackground=self.PRIMARY_COLOR)
            lb.grid(row=1, column=columna, sticky="nsew", padx=6)
            frame_inv.rowconfigure(1, weight=1)
            listboxes.append(lb)

            edicion = ttk.Frame(frame_inv)
            edicion.grid(row=2, column=columna, sticky="ew", padx=6, pady=6)
            ttk.Label(edicion, text="Nuevo $").pack(side=tk.LEFT)
            entrada_precio = ttk.Entry(edicion, width=9)
            entrada_precio.pack(side=tk.LEFT, padx=4)
            ttk.Button(
                edicion, text="Actualizar",
                command=lambda i=columna, l=lb, e=entrada_precio:
                editar(i, l, e)).pack(side=tk.LEFT)

        actualizar_almacenes()

        ttk.Button(body, text="Cerrar sesión y volver",
                   command=self._volver_al_menu).pack(pady=10)
