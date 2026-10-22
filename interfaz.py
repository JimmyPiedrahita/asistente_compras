import tkinter as tk
from tkinter import ttk, messagebox


class InterfazUsuario:
    """
    Vista (GUI) del sistema. Implementa 'actualizar' para responder
    a las notificaciones del Carrito (Observer).
    """
    BG_COLOR = "#f4f4f9"
    PRIMARY_COLOR = "#4a90e2"
    FONT_TITLE = ("Helvetica", 20, "bold")
    FONT_NORMAL = ("Helvetica", 12)

    def __init__(self):
        self._controlador = None
        self.root = None

    def set_controlador(self, controlador):
        self._controlador = controlador

    def actualizar(self, sujeto, mensaje: str):
        print(f"\n[NOTIFICACIÓN VISTA]: {mensaje}")
        print(f"[NUEVO TOTAL EN TIEMPO REAL]: ${sujeto.calcular_total():.2f}")

    def ejecutar(self):
        self.root = tk.Tk()
        self.root.title("Asistente de Compras Inteligente")
        self.root.geometry("850x650")
        style = ttk.Style(self.root)
        style.theme_use('clam')
        self._mostrar_menu_principal()
        self.root.mainloop()

    
    def _limpiar_pantalla(self):
        self.root.unb23ind('<Return>')
        for widget in self.root.winfo_children():
            widget.destroy()
        self.root.configure(bg=self.BG_COLOR)

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

        s = ttk.Style(self.root)
        s.configure("Action.TButton", font=("Helvetica", 12, "bold"), padding=10)

        ttk.Button(cards, text="Ingresar como Usuario",
                command=self._mostrar_menu_usuario,
                style="Action.TButton", width=25).pack(pady=10)
        ttk.Button(cards, text="Administrar Almacenes",
                command=self._mostrar_login_admin,
                style="Action.TButton", width=25).pack(pady=10)

    def _mostrar_menu_usuario(self):
        self._limpiar_pantalla()

        header = tk.Frame(self.root, bg=self.PRIMARY_COLOR)
        header.pack(fill=tk.X)
        tk.Label(header, text="Compras - Usuario", font=self.FONT_TITLE,
                bg=self.PRIMARY_COLOR, fg="white", pady=15).pack()

        body = tk.Frame(self.root, bg=self.BG_COLOR)
        body.pack(expand=True, fill=tk.BOTH, padx=40, pady=20)

        frame_controls = tk.Frame(body, bg=self.BG_COLOR)
        frame_controls.pack(pady=10)
        tk.Label(frame_controls, text="Nuevo Producto:", font=self.FONT_NORMAL,
                bg=self.BG_COLOR).grid(row=0, column=0, padx=5)
        entrada = ttk.Entry(frame_controls, font=self.FONT_NORMAL, width=25)
        entrada.grid(row=0, column=1, padx=10)

        frame_list = tk.Frame(body, bg=self.BG_COLOR)
        frame_list.pack(pady=5, fill=tk.X)
        tk.Label(frame_list, text="Mi Lista de Compras:",
                font=("Helvetica", 14, "bold"), bg=self.BG_COLOR).pack(anchor="w")
        listbox = tk.Listbox(frame_list, font=self.FONT_NORMAL, height=6, bg="white",
                            selectbackground=self.PRIMARY_COLOR)
        listbox.pack(fill=tk.X, pady=5)

        btn_agregar = ttk.Button(frame_controls, text="Agregar")
        btn_agregar.grid(row=0, column=2, padx=5)
        btn_eliminar = ttk.Button(frame_controls, text="Eliminar")
        btn_eliminar.grid(row=0, column=3, padx=5)

        tk.Label(body, text="Resultados de Busqueda:",
                font=("Helvetica", 14, "bold"), bg=self.BG_COLOR).pack(anchor="w", pady=(20, 0))
        btn_buscar = ttk.Button(body, text="Buscar mejores precios")
        btn_buscar.pack(pady=5, anchor="w")

        listbox_resultados = tk.Listbox(body, font=("Consolas", 11), height=8, bg="#eef2f5")
        listbox_resultados.pack(fill=tk.X, pady=5)

        ttk.Button(body, text="Volver al Menu", command=self._mostrar_menu_principal).pack(pady=10)

        def actualizar_lista():
            listbox.delete(0, tk.END)
            for producto in self._controlador.obtener_compras_usuario():
                listbox.insert(tk.END, producto)

        def agregar_producto():
            producto = entrada.get().strip()
            if producto:
                self._controlador.agregar_producto_usuario(producto)
                entrada.delete(0, tk.END)
                actualizar_lista()
            else:
                messagebox.showwarning("Advertencia", "Ingrese el nombre del producto")

        def eliminar_producto():
            seleccion = listbox.curselection()
            if seleccion:
                producto = listbox.get(seleccion[0])
                if self._controlador.eliminar_producto_usuario(producto):
                    actualizar_lista()
            else:
                producto = entrada.get().strip()
                if producto:
                    if self._controlador.eliminar_producto_usuario(producto):
                        entrada.delete(0, tk.END)
                        actualizar_lista()
                    else:
                        messagebox.showwarning("No encontrado", "Ese producto no esta en la lista")
                else:
                    messagebox.showwarning("Advertencia",
                            "Seleccione un producto o nombre para eliminar")

        def buscar_mejor_precio():
            resultados = self._controlador.ejecutar_busqueda_precios()
            listbox_resultados.delete(0, tk.END)
            for almacen, lista_prod in resultados.items():
                if not lista_prod.esta_vacia():
                    listbox_resultados.insert(tk.END, f"--- {almacen.nombre} ---")
                    for p in lista_prod.mostrar():
                        listbox_resultados.insert(tk.END, f"  {p.nombre} - ${p.precio:.2f}")

        btn_agregar.configure(command=agregar_producto)
        btn_eliminar.configure(command=eliminar_producto)
        btn_buscar.configure(command=buscar_mejor_precio)
        actualizar_lista()

    def _mostrar_menu_admin(self):
        self._limpiar_pantalla()

        header = tk.Frame(self.root, bg=self.PRIMARY_COLOR)
        header.pack(fill=tk.X)
        tk.Label(header, text="Panel de Administracion", font=self.FONT_TITLE,
        bg=self.PRIMARY_COLOR, fg="white", pady=15).pack()

        body = tk.Frame(self.root, bg=self.BG_COLOR)
        body.pack(expand=True, fill=tk.BOTH, padx=20, pady=10)

        frame_add = ttk.LabelFrame(body, text="Agregar Nuevo Producto en Almacen")
        frame_add.pack(pady=10, fill=tk.X)

        tk.Label(frame_add, text="Nombre:", font=self.FONT_NORMAL, bg=self.BG_COLOR).grid(row=0, column=0, padx=10, pady=10)
        entry_nombre = ttk.Entry(frame_add, font=self.FONT_NORMAL, width=15)
        entry_nombre.grid(row=0, column=1)

        tk.Label(frame_add, text="Precio:", font=self.FONT_NORMAL, bg=self.BG_COLOR).grid(row=0, column=2, padx=10, pady=10)
        entry_precio = ttk.Entry(frame_add, font=self.FONT_NORMAL, width=8)
        entry_precio.grid(row=0, column=3)

        tk.Label(frame_add, text="Almacen:", font=self.FONT_NORMAL, bg=self.BG_COLOR).grid(row=0, column=4, padx=10, pady=10)
        opciones = ["Almacen 1", "Almacen 2", "Almacen 3"]
        var_almacen = tk.StringVar(value=opciones[0])
        ttk.OptionMenu(frame_add, var_almacen, opciones[0], *opciones).grid(row=0, column=5)

        def actualizar_almacenes():
            listboxes = [listbox_a1, listbox_a2, listbox_a3]
            for lb in listboxes:
                lb.delete(0, tk.END)
            for i, alm in enumerate(self._controlador.gestor_almacenes.obtener_almacenes()):
                if i < len(listboxes):
                    for p in alm.inventario.mostrar():
                        listboxes[i].insert(tk.END, f"{p.nombre} - ${p.precio:.2f}")

        def agregar_producto_admin():
            nombre = entry_nombre.get().strip()
            precio_str = entry_precio.get().strip()
            if not nombre or not precio_str:
                messagebox.showwarning("Advertencia", "Ingrese nombre y precio")
                return
            try:
                precio = float(precio_str)
            except ValueError:
                messagebox.showerror("Error", "Precio numerico")
                return
            id_almacen = int(var_almacen.get().split(" ")[-1])
            self._controlador.agregar_producto_almacen(id_almacen, nombre, precio)
            entry_nombre.delete(0, tk.END)
            entry_precio.delete(0, tk.END)
            actualizar_almacenes()

        ttk.Button(frame_add, text="Guardar", command=agregar_producto_admin).grid(row=0, column=6, padx=15)

        tk.Label(body, text="Inventario de Almacenes:",
            font=("Helvetica", 14, "bold"), bg=self.BG_COLOR).pack(anchor="w", pady=5)

        frame_lists = tk.Frame(body, bg=self.BG_COLOR)
        frame_lists.pack(fill=tk.BOTH, expand=True)
        for col in range(3):
            frame_lists.columnconfigure(col, weight=1)

        listbox_a1 = tk.Listbox(frame_lists, font=("Consolas", 10), height=12)
        listbox_a1.grid(row=1, column=0, padx=5, sticky="nsew")
        listbox_a2 = tk.Listbox(frame_lists, font=("Consolas", 10), height=12)
        listbox_a2.grid(row=1, column=1, padx=5, sticky="nsew")
        listbox_a3 = tk.Listbox(frame_lists, font=("Consolas", 10), height=12)
        listbox_a3.grid(row=1, column=2, padx=5, sticky="nsew")
        tk.Label(frame_lists, text="Almacen 1", bg=self.BG_COLOR, font=self.FONT_NORMAL).grid(row=0, column=0, pady=5)
        tk.Label(frame_lists, text="Almacen 2", bg=self.BG_COLOR, font=self.FONT_NORMAL).grid(row=0, column=1, pady=5)
        tk.Label(frame_lists, text="Almacen 3", bg=self.BG_COLOR, font=self.FONT_NORMAL).grid(row=0, column=2, pady=5)

        actualizar_almacenes()
        ttk.Button(body, text="Volver al Menu", command=self._mostrar_menu_principal).pack(pady=15)

    def _mostrar_login_admin(self):
        self._limpiar_pantalla()

        frame_login = tk.Frame(self.root, bg="white", padx=40, pady=40, relief="groove", bd=2)
        frame_login.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(frame_login, text="Admin", font=self.FONT_TITLE, bg="white").pack(pady=(0, 20))
        tk.Label(frame_login, text="Clave de acceso:", font=self.FONT_NORMAL, bg="white").pack()

        password_entry = ttk.Entry(frame_login, show="*", font=self.FONT_NORMAL)
        password_entry.pack(pady=10)
        password_entry.focus()

        def check_password(event=None):
            if password_entry.get() == "admin123":
                self._mostrar_menu_admin()
            else:
                messagebox.showerror("Error", "Clave incorrecta")

        self.root.bind('<Return>', check_password)

        ttk.Button(frame_login, text="Ingresar", command=check_password).pack(pady=5, fill=tk.X)
        ttk.Button(frame_login, text="Cancelar", command=self._mostrar_menu_principal).pack(fill=tk.X)