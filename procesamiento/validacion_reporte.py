"""
procesamiento/validacion_reporte.py
====================================
Módulo que centraliza toda la lógica del flujo de validación de reportes compartidos.

Los checkboxes de validación aparecen AL LADO de los botones de proceso existentes
en el menú lateral (Detectar, Filtrar, Ramas, Métricas). Solo se muestran los
checkboxes de pasos que el tesista ya completó.
"""

import logging
from PyQt6.QtWidgets import (
    QPushButton, QWidget, QHBoxLayout, QVBoxLayout,
    QCheckBox, QLabel, QFrame,
)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QSize, Qt


# ---------------------------------------------------------------------------
# 1. OPERACIONES DE BASE DE DATOS
# ---------------------------------------------------------------------------

def db_marcar_validado(id_reporte: int) -> None:
    """Actualiza ReporteCompartido.estado a 'Validado' para el reporte dado."""
    from bd.database import conectar
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE ReporteCompartido SET estado = 'Validado' WHERE id_reporte = ?",
            (id_reporte,)
        )
        conn.commit()
    except Exception as e:
        logging.error(f"[validacion_reporte] Error al marcar validado: {e}")
        raise
    finally:
        conn.close()


def db_guardar_comentarios(id_reporte: int, comentarios: str) -> None:
    """Actualiza ReporteCompartido.comentarios para el reporte dado."""
    from bd.database import conectar
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE ReporteCompartido SET comentarios = ? WHERE id_reporte = ?",
            (comentarios, id_reporte)
        )
        conn.commit()
    except Exception as e:
        logging.error(f"[validacion_reporte] Error al guardar comentarios: {e}")
        raise
    finally:
        conn.close()


def db_actualizar_estado_reporte(id_reporte: int, estado: str) -> None:
    """Actualiza ReporteCompartido.estado para el reporte dado."""
    from bd.database import conectar
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE ReporteCompartido SET estado = ? WHERE id_reporte = ?",
            (estado, id_reporte)
        )
        conn.commit()
    except Exception as e:
        logging.error(f"[validacion_reporte] Error al actualizar estado reporte: {e}")
        raise
    finally:
        conn.close()


def db_resetear_progreso_analisis(id_reporte: int, paso_fallido: int) -> None:
    """Resetea el progreso del análisis asociado al reporte según el paso que falló."""
    from bd.database import conectar
    import json
    import shutil
    import os
    from pathlib import Path
    
    conn = conectar()
    cur = conn.cursor()
    try:
        # 1. Obtener el último análisis de este reporte
        cur.execute("""
            SELECT A.id_analisis, A.datos_persistentes, I.ruta_archivo 
            FROM Analisis A 
            JOIN Imagen I ON A.id_imagen = I.id_imagen 
            WHERE A.id_reporte = ? 
            ORDER BY A.id_analisis DESC LIMIT 1
        """, (id_reporte,))
        res = cur.fetchone()
        if not res:
            return
            
        id_an, dp, ruta_img = res
        
        # Cargar datos persistentes
        boxes = []
        metricas = []
        if dp:
            try:
                datos = json.loads(dp)
                boxes = datos.get("boxes", [])
                metricas = datos.get("metricas_acumuladas", [])
            except:
                pass
                
        stem = Path(ruta_img).stem
        base_dir = os.path.join(os.getcwd(), "analisis_resultados", stem)
        
        # Determinar el nuevo paso_actual y qué limpiar según paso_fallido
        # paso_fallido: 1 = Conteo, 2 = Filtrar, 3 = Esqueletizado, 4 = Métricas
        if paso_fallido == 1:
            # Se equivoco en el conteo -> Borrar TODO (paso_actual = 1)
            nuevo_paso = 1
            boxes = []
            metricas = []
            
            # Borrar de la base de datos las microglias individuales
            cur.execute("DELETE FROM Microglia WHERE id_analisis = ?", (id_an,))
            cur.execute("UPDATE Analisis SET cantidad_microglias = 0 WHERE id_analisis = ?", (id_an,))
            
            # Borrar carpetas físicas de crops, filtradas y esqueletos
            for folder in ["crops", "filtradas", "esqueletos"]:
                p = os.path.join(base_dir, folder)
                if os.path.exists(p):
                    shutil.rmtree(p, ignore_errors=True)
                    
        elif paso_fallido == 2:
            # Se equivoco en el filtrado -> Conservar conteo (paso_actual = 2), borrar filtrado/esqueletos/métricas
            nuevo_paso = 2
            metricas = []
            
            # Borrar carpetas físicas de filtradas y esqueletos
            for folder in ["filtradas", "esqueletos"]:
                p = os.path.join(base_dir, folder)
                if os.path.exists(p):
                    shutil.rmtree(p, ignore_errors=True)
                    
        elif paso_fallido == 3:
            # Se equivoco en el esqueletizado -> Conservar conteo y filtrado (paso_actual = 3), borrar esqueletos/métricas
            nuevo_paso = 3
            metricas = []
            
            # Borrar carpetas físicas de esqueletos
            p = os.path.join(base_dir, "esqueletos")
            if os.path.exists(p):
                shutil.rmtree(p, ignore_errors=True)
                
        elif paso_fallido == 4:
            # Se equivoco en obtener métricas -> Conservar todo menos métricas (paso_actual = 4)
            nuevo_paso = 4
            metricas = []
            
        # Guardar cambios en Analisis
        datos_nuevos = {
            "boxes": boxes,
            "metricas_acumuladas": metricas
        }
        cur.execute(
            "UPDATE Analisis SET paso_actual = ?, datos_persistentes = ? WHERE id_analisis = ?",
            (nuevo_paso, json.dumps(datos_nuevos), id_an)
        )
        conn.commit()
    except Exception as e:
        logging.error(f"[validacion_reporte] Error al resetear progreso: {e}")
        raise
    finally:
        conn.close()


def db_verificar_reporte_completo(id_reporte: int, cur) -> tuple:
    """Devuelve (total_analisis, completados) para un reporte."""
    cur.execute("SELECT COUNT(*) FROM Analisis WHERE id_reporte = ?", (id_reporte,))
    total = cur.fetchone()[0]
    cur.execute(
        "SELECT COUNT(*) FROM Analisis WHERE id_reporte = ? AND paso_actual >= 5",
        (id_reporte,)
    )
    completados = cur.fetchone()[0]
    return total, completados


# ---------------------------------------------------------------------------
# 2. HELPERS PARA DialogoHistorial
# ---------------------------------------------------------------------------

def construir_boton_validar(tree_widget, rep_item, id_rep, reporte_completo,
                             total_analisis, completados, callback_validar):
    """Crea botón de validar en la columna 5 del rep_item."""
    btn = QPushButton()
    btn.setIcon(QIcon("assets/buttons/validar.png"))
    btn.setIconSize(QSize(18, 18))
    btn.setFixedSize(30, 30)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet("""
        QPushButton { background-color: transparent; border: 1px solid transparent; outline: none; }
        QPushButton:hover { background-color: #ddf4ff; border-radius: 15px; }
        QPushButton:disabled { opacity: 0.3; }
    """)
    btn.setEnabled(True)
    btn.setToolTip("Revisar y validar reporte")
    btn.clicked.connect(lambda checked, r=id_rep: callback_validar(r))

    container = QWidget()
    lay = QHBoxLayout(container)
    lay.addWidget(btn)
    lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lay.setContentsMargins(0, 0, 0, 0)
    tree_widget.setItemWidget(rep_item, 5, container)


def construir_boton_descargar(tree_widget, rep_item, col, id_rep,
                               habilitado, tooltip, callback_descargar):
    """Crea botón de descargar en la columna `col` del rep_item."""
    btn = QPushButton()
    btn.setIcon(QIcon("assets/buttons/download.png"))
    btn.setIconSize(QSize(18, 18))
    btn.setFixedSize(30, 30)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet("""
        QPushButton { background-color: transparent; border: 1px solid transparent; outline: none; }
        QPushButton:hover { background-color: #ddf4ff; border-radius: 15px; }
        QPushButton:disabled { opacity: 0.1; }
    """)
    btn.setEnabled(habilitado)
    btn.setToolTip(tooltip)
    btn.clicked.connect(lambda checked, r=id_rep: callback_descargar(r))

    container = QWidget()
    lay = QHBoxLayout(container)
    lay.addWidget(btn)
    lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lay.setContentsMargins(0, 0, 0, 0)
    tree_widget.setItemWidget(rep_item, col, container)


def debe_bloquear_carga(data: dict, id_usuario: int) -> bool:
    """Retorna True si el botón Cargar/Retomar debe bloquearse (propietario + Modificado)."""
    estado = data.get("estado_compartido", "")
    id_prop = data.get("id_prop", -1)
    return id_prop == id_usuario and estado == "Modificado"


# ---------------------------------------------------------------------------
# 3. MIXIN PARA VentanaBaseAnalisis
# ---------------------------------------------------------------------------

class ValidacionReporteMixin:
    """
    Mixin que agrega checkboxes de validación al lado de cada botón de
    proceso en el menú lateral, con lógica de "Validar Progreso" y
    "Enviar Comentarios".
    """

    # ------------------------------------------------------------------
    # Inicialización
    # ------------------------------------------------------------------

    def _init_validacion_estado(self):
        """Inicializa variables de estado del flujo de validación."""
        self.reporte_validado_cargado = False

    # ------------------------------------------------------------------
    # Construcción del sidebar con rows de validación
    # ------------------------------------------------------------------

    def _crear_panel_validacion(self, menu_lateral):
        """
        Crea el layout del sidebar con checkboxes al lado de cada botón de proceso.
        Los checkboxes están ocultos por defecto y solo se muestran en modo validación.

        Orden en el sidebar:
          [lbl_titulo_validacion]  (oculto)
          [btn_cargar]
          [chk ☐ | btn_conteo]
          [chk ☐ | btn_filtrar]
          [chk ☐ | btn_ramas]
          [chk ☐ | btn_obtener_metricas]
          [btn_descargar_reporte]
          [btn_finalizar_reporte]
          [btn_corregir_filtrado]
          [btn_validar_progreso]   (oculto)
          [btn_enviar_comentarios] (oculto)
        """
        # Asegurar check_white.png para que se vea la palomita blanca sobre el fondo verde
        import os
        from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor
        from PyQt6.QtCore import Qt
        os.makedirs("assets/buttons", exist_ok=True)
        img_path = "assets/buttons/check_white.png"
        if not os.path.exists(img_path):
            pix = QPixmap(14, 14)
            pix.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pix)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            pen = QPen(QColor("white"), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.drawLine(3, 7, 6, 10)
            painter.drawLine(6, 10, 11, 4)
            painter.end()
            pix.save(img_path)

        # --- Cargar Imagen (sin checkbox) ---
        menu_lateral.addWidget(self.btn_cargar)

        # --- Título de validación (oculto por defecto) ---
        self.lbl_titulo_validacion = QLabel("Proceso de Validación")
        self.lbl_titulo_validacion.setStyleSheet(
            "font-weight: bold; color: #3a61a0; font-size: 10px; "
            "margin-top: 15px; margin-bottom: 5px; padding-left: 10px;"
        )
        self.lbl_titulo_validacion.hide()
        menu_lateral.addWidget(self.lbl_titulo_validacion)

        # --- Crear checkboxes para cada proceso ---
        estilo_check = """
            QCheckBox { background: transparent; }
            QCheckBox::indicator {
                width: 14px; height: 14px;
                border: 2px solid #d0d7de; border-radius: 3px;
                background: white;
            }
            QCheckBox::indicator:checked {
                background-color: #2da44e; border-color: #2da44e;
                image: url(assets/buttons/check_white.png);
            }
            QCheckBox::indicator:hover { border-color: #0969da; }
        """

        self.chk_val_conteo = QCheckBox()
        self.chk_val_filtrar = QCheckBox()
        self.chk_val_ramas = QCheckBox()

        # Lista: (checkbox, botón, paso_mínimo_para_mostrar)
        self._checks_validacion = [
            (self.chk_val_conteo, self.btn_conteo, 2),
            (self.chk_val_filtrar, self.btn_filtrar, 3),
            (self.chk_val_ramas, self.btn_ramas, 4),
        ]

        for chk, btn, _ in self._checks_validacion:
            chk.setFixedSize(18, 18)
            chk.setStyleSheet(estilo_check)
            chk.setCursor(Qt.CursorShape.PointingHandCursor)
            chk.hide()
            chk.stateChanged.connect(self._on_checkbox_state_changed)

            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(0)
            row.addWidget(chk)
            row.addWidget(btn, stretch=1)
            menu_lateral.addLayout(row)

        # --- Botones de reporte (sin checkbox) ---
        menu_lateral.addWidget(self.btn_obtener_metricas)
        menu_lateral.addWidget(self.btn_descargar_reporte)
        menu_lateral.addWidget(self.btn_finalizar_reporte)
        menu_lateral.addWidget(self.btn_corregir_filtrado)

        # --- Botón "Validar Progreso" (aparece cuando TODOS los checks marcados) ---
        self.btn_validar_progreso = QPushButton("✔  Validar Progreso")
        self.btn_validar_progreso.setStyleSheet("""
            QPushButton {
                background-color: transparent; color: #2da44e; border: 2px solid #2da44e;
                border-radius: 8px; padding: 8px; font-weight: bold;
                font-size: 11px; text-align: center; margin-top: 4px;
            }
            QPushButton:hover { background-color: #2da44e; color: white; }
        """)
        self.btn_validar_progreso.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_validar_progreso.hide()
        self.btn_validar_progreso.clicked.connect(self.confirmar_validacion)
        menu_lateral.addWidget(self.btn_validar_progreso)

        # --- Botón "Enviar comentarios" (aparece cuando NO todos marcados) ---
        self.btn_enviar_comentarios = QPushButton("✉  Enviar comentario(s)")
        self.btn_enviar_comentarios.setStyleSheet("""
            QPushButton {
                background-color: transparent; color: #0969da; border: 2px solid #0969da;
                border-radius: 8px; padding: 8px; font-weight: bold;
                font-size: 11px; text-align: center; margin-top: 4px;
            }
            QPushButton:hover { background-color: #0969da; color: white; }
        """)
        self.btn_enviar_comentarios.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_enviar_comentarios.hide()
        self.btn_enviar_comentarios.clicked.connect(self.agregar_comentario_proceso)
        menu_lateral.addWidget(self.btn_enviar_comentarios)



    # ------------------------------------------------------------------
    # Lógica: actualización de botones según checkboxes
    # ------------------------------------------------------------------

    def _on_checkbox_state_changed(self):
        """Lógica secuencial: si un proceso anterior no está validado,
        todos los posteriores se desmarcan y se deshabilitan.
        """
        # Desconectar señales temporalmente para evitar recursión infinita
        for chk, _, _ in self._checks_validacion:
            try:
                chk.stateChanged.disconnect(self._on_checkbox_state_changed)
            except TypeError:
                pass

        # chk_val_conteo (índice 0) siempre habilitado si es visible
        self.chk_val_conteo.setEnabled(True)

        if not self.chk_val_conteo.isChecked():
            self.chk_val_filtrar.setChecked(False)
            self.chk_val_filtrar.setEnabled(False)
            self.chk_val_ramas.setChecked(False)
            self.chk_val_ramas.setEnabled(False)
        else:
            self.chk_val_filtrar.setEnabled(True)
            if not self.chk_val_filtrar.isChecked():
                self.chk_val_ramas.setChecked(False)
                self.chk_val_ramas.setEnabled(False)
            else:
                self.chk_val_ramas.setEnabled(True)

        # Reconectar señales
        for chk, _, _ in self._checks_validacion:
            chk.stateChanged.connect(self._on_checkbox_state_changed)

        # Actualizar visibilidad de botones
        self._actualizar_botones_validacion()

    def _actualizar_botones_validacion(self):
        """Muestra Validar Progreso si todos marcados, o Enviar comentario(s) si no."""
        checks_visibles = [
            chk for chk, _, _ in self._checks_validacion if chk.isVisible()
        ]
        if not checks_visibles:
            return
        todos = all(chk.isChecked() for chk in checks_visibles)
        self.btn_validar_progreso.setVisible(todos)
        self.btn_enviar_comentarios.setVisible(not todos)

    # ------------------------------------------------------------------
    # Apertura del historial
    # ------------------------------------------------------------------

    def abrir_historial(self):
        """Abre el diálogo de historial y gestiona el flujo de validación."""
        from vistas.base_analisis import DialogoHistorial
        diag = DialogoHistorial(self.id_usuario, self.rol, self)
        if diag.exec() and diag.seleccion:
            sel = diag.seleccion
            ir_a_validacion = sel.get("ir_a_metricas", False)
            self.reporte_validado_cargado = ir_a_validacion
            self.cargar_reporte_especifico(sel)
            if ir_a_validacion:
                self._entrar_modo_validacion()
        else:
            self.reporte_validado_cargado = False

    def _entrar_modo_validacion(self):
        """Configura la UI para el modo de revisión de validación."""
        # Mostrar título
        # Mostrar título
        self.lbl_titulo_validacion.show()

        # Inicializar comentarios por proceso
        self.comentarios_por_proceso = {1: "", 2: "", 3: "", 4: ""}
        if hasattr(self, "btn_comentario_proceso"):
            self.btn_comentario_proceso.setEnabled(True)
            self.btn_comentario_proceso.show()
            self._actualizar_tooltip_comentarios()

        # Reset y mostrar checkboxes solo para los pasos completados
        for chk, btn, paso_min in self._checks_validacion:
            chk.setChecked(False)
            if self.paso_actual >= paso_min:
                chk.show()
            else:
                chk.hide()

        # Mostrar botón de comentarios por defecto
        self.btn_validar_progreso.hide()
        self.btn_enviar_comentarios.show()

        # Forzar ejecución secuencial inicial
        self._on_checkbox_state_changed()

        # Notificación
        from vistas.utilidades import DialogoNotificacion
        DialogoNotificacion(
            "Revisión de Reporte",
            "Revisa los procesos realizados por el colaborador.\n"
            "Usa los botones ‹ › para navegar entre los pasos.\n"
            "Marca las casillas al lado de cada proceso validado.",
            "info", self
        ).exec()

    def _salir_modo_validacion(self):
        """Oculta todos los elementos de validación del sidebar."""
        self.lbl_titulo_validacion.hide()
        for chk, _, _ in self._checks_validacion:
            chk.hide()
            chk.setChecked(False)
        self.btn_validar_progreso.hide()
        self.btn_enviar_comentarios.hide()

    # ------------------------------------------------------------------
    # UI de paso 5 con soporte de modo revisión
    # ------------------------------------------------------------------

    def aplicar_ui_paso5_validacion(self):
        """Configura botones del sidebar en paso 5 según modo normal o revisión."""
        if self.reporte_validado_cargado:
            self.btn_agregar_imagen_reporte.setEnabled(False)
            self.btn_descargar_reporte.setEnabled(False)
            self.btn_finalizar_reporte.setEnabled(False)
            self.btn_cargar.setEnabled(False)
        else:
            self.btn_agregar_imagen_reporte.setEnabled(True)
            self.btn_descargar_reporte.setEnabled(True)
            self.btn_finalizar_reporte.setEnabled(False)
            self._salir_modo_validacion()

    # ------------------------------------------------------------------
    # Navegación libre en modo revisión
    # ------------------------------------------------------------------

    def actualizar_nav_en_validacion(self) -> bool:
        """Si es modo revisión, habilita navegación libre. Retorna True si aplicado."""
        if not self.reporte_validado_cargado:
            return False
        self.btn_sig_global.show()
        self.btn_ant_global.show()
        idx = self.combo_vista.currentIndex()
        self.btn_ant_global.setEnabled(idx > 0)
        self.btn_sig_global.setEnabled(idx < self.combo_vista.count() - 1)
        return True

    # ------------------------------------------------------------------
    # Confirmación de la validación
    # ------------------------------------------------------------------

    def confirmar_validacion(self):
        """Marca el reporte como Validado en la BD tras confirmar."""
        if not self.id_reporte_actual:
            return
        from vistas.utilidades import DialogoConfirmacion, DialogoNotificacion
        msg = "¿Confirmas que todos los procesos fueron revisados correctamente?"
        if not DialogoConfirmacion("Confirmar Validación", msg).exec():
            return
        try:
            db_marcar_validado(self.id_reporte_actual)
            db_guardar_comentarios(self.id_reporte_actual, "Validado sin observaciones.")
            self.reporte_validado_cargado = False
            self._salir_modo_validacion()
            self.cerrar_reporte_actual()
            DialogoNotificacion(
                "Éxito",
                "Reporte validado correctamente.",
                "info", self
            ).exec()
        except Exception as e:
            DialogoNotificacion(
                "Error", f"No se pudo validar: {e}", "error", self
            ).exec()

    # ------------------------------------------------------------------
    # Enviar comentarios
    # ------------------------------------------------------------------

    def _enviar_comentarios(self):
        """Notifica sobre los procesos no validados y guarda comentarios."""
        from vistas.utilidades import DialogoNotificacion, DialogoComentarioGeneral
        
        # Encontrar el primer proceso visible y no validado (raíz del error)
        paso_fallido = None
        mapa_checks = {
            1: self.chk_val_conteo,
            2: self.chk_val_filtrar,
            3: self.chk_val_ramas
        }
        for step_id in [1, 2, 3]:
            chk = mapa_checks[step_id]
            if chk.isVisible() and not chk.isChecked():
                paso_fallido = step_id
                break

        # Obtener comentario previo si existe para este paso fallido
        comentario_previo = ""
        if paso_fallido is not None and hasattr(self, "comentarios_por_proceso"):
            comentario_previo = self.comentarios_por_proceso.get(paso_fallido, "")

        # Pedir un comentario general explicativo
        diag_comentario = DialogoComentarioGeneral(
            "Enviar Retroalimentación",
            "Por favor, ingresa los comentarios u observaciones para el colaborador sobre las correcciones requeridas:",
            comentario_previo,
            self
        )
        if not diag_comentario.exec():
            return # Cancelado
        
        comentario_general = diag_comentario.resultado_texto.strip()
        if not comentario_general:
            return

        try:
            db_guardar_comentarios(self.id_reporte_actual, comentario_general)
            db_actualizar_estado_reporte(self.id_reporte_actual, 'Pendiente')
            if paso_fallido is not None:
                db_resetear_progreso_analisis(self.id_reporte_actual, paso_fallido)
            DialogoNotificacion(
                "Comentarios Enviados",
                "Las observaciones han sido guardadas y el reporte ha sido retornado al colaborador para su corrección.",
                "info", self
            ).exec()
            self.reporte_validado_cargado = False
            self._salir_modo_validacion()
            self.cerrar_reporte_actual()
        except Exception as e:
            DialogoNotificacion(
                "Error", f"No se pudieron guardar los comentarios: {e}", "error", self
            ).exec()

    # ------------------------------------------------------------------
    # Métodos del botón de comentarios por proceso
    # ------------------------------------------------------------------

    def agregar_comentario_proceso(self):
        """Muestra un diálogo de retroalimentación general y devuelve el reporte al colaborador en el paso fallido."""
        if not self.reporte_validado_cargado or not self.id_reporte_actual:
            return
        
        # Determinar el primer paso que no está marcado como correcto
        paso_nom = "Esqueletizado"
        paso_id = 3
        
        mapa_checks = {
            1: (self.chk_val_conteo, "Detectar Microglías"),
            2: (self.chk_val_filtrar, "Filtrar"),
            3: (self.chk_val_ramas, "Esqueletizado"),
        }
        paso_fallido = None
        for step_id in [1, 2, 3]:
            chk, name = mapa_checks[step_id]
            if chk.isVisible() and not chk.isChecked():
                paso_fallido = step_id
                paso_nom = name
                break
                
        if paso_fallido is None:
            # Todos los procesos están marcados como correctos, no hay fallo
            from vistas.utilidades import DialogoNotificacion
            DialogoNotificacion(
                "Atención",
                "Todos los procesos han sido validados como correctos. Utiliza el botón 'Validar Progreso' en el menú lateral para aprobar.",
                "warning", self
            ).exec()
            return

        from vistas.utilidades import DialogoComentarioGeneral, DialogoNotificacion
        # Pedir la retroalimentación explicativa del fallo
        diag_retro = DialogoComentarioGeneral(
            "Enviar Retroalimentación",
            f"Por favor, ingresa las observaciones sobre la fase de '{paso_nom}' que no fue validada:",
            "",
            self
        )
        if not diag_retro.exec():
            return # Cancelado
            
        comentario_general = diag_retro.resultado_texto.strip()
        if not comentario_general:
            return

        try:
            db_guardar_comentarios(self.id_reporte_actual, f"Fallo en fase '{paso_nom}': {comentario_general}")
            db_actualizar_estado_reporte(self.id_reporte_actual, 'Pendiente')
            db_resetear_progreso_analisis(self.id_reporte_actual, paso_fallido)
            
            DialogoNotificacion(
                "Retroalimentación Enviada",
                f"Las observaciones sobre '{paso_nom}' han sido enviadas y el reporte ha sido retornado al colaborador para su corrección.",
                "info", self
            ).exec()
            
            self.reporte_validado_cargado = False
            self._salir_modo_validacion()
            self.cerrar_reporte_actual()
        except Exception as e:
            DialogoNotificacion(
                "Error", f"No se pudo guardar la retroalimentación: {e}", "error", self
            ).exec()

    def _actualizar_tooltip_comentarios(self):
        """Actualiza el tooltip del botón lateral de comentarios según el paso actual fallido."""
        if not hasattr(self, "btn_enviar_comentarios"):
            return
            
        if not getattr(self, "reporte_validado_cargado", False):
            self.btn_enviar_comentarios.hide()
            return
            
        # Determinar el primer paso no validado
        mapa_checks = {
            1: (self.chk_val_conteo, "Detectar Microglías"),
            2: (self.chk_val_filtrar, "Filtrar"),
            3: (self.chk_val_ramas, "Esqueletizado"),
        }
        paso_fallido = None
        paso_nom = ""
        for step_id in [1, 2, 3]:
            chk, name = mapa_checks[step_id]
            if chk.isVisible() and not chk.isChecked():
                paso_fallido = step_id
                paso_nom = name
                break
                
        if paso_fallido is not None:
            self.btn_enviar_comentarios.setToolTip(f"Enviar retroalimentación (Fallo detectado en: {paso_nom})")
            self.btn_enviar_comentarios.setEnabled(True)
        else:
            self.btn_enviar_comentarios.setToolTip("Todos los procesos están validados como correctos.")
            self.btn_enviar_comentarios.setEnabled(False)
