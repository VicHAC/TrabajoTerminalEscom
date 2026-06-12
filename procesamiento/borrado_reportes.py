import os
import shutil
import logging
from pathlib import Path
from bd.database import conectar
from utils_rutas import get_resultados_dir, get_app_data_dir

def eliminar_reportes_y_archivos(id_reportes):
    """
    Elimina los reportes especificados de la base de datos (incluyendo registros de
    Microglia, Analisis y ReporteCompartido) y borra físicamente sus carpetas
    de procesamiento localizadas en 'analisis_resultados'.
    Finalmente, limpia los registros de imágenes huérfanas en la tabla Imagen,
    así como sus archivos físicos correspondientes si se encuentran dentro de get_app_data_dir().
    """
    if not id_reportes:
        return
        
    conn = conectar()
    cur = conn.cursor()
    
    try:
        # 1. Obtener las rutas de archivos de imagen asociados a los análisis de estos reportes
        # para conocer los nombres de carpetas a eliminar
        rutas_imagenes = []
        for id_rep in id_reportes:
            cur.execute("""
                SELECT DISTINCT I.ruta_archivo 
                FROM Analisis A 
                JOIN Imagen I ON A.id_imagen = I.id_imagen 
                WHERE A.id_reporte = ?
            """, (id_rep,))
            rows = cur.fetchall()
            for row in rows:
                if row[0]:
                    rutas_imagenes.append(row[0])
                    
        # 2. Borrar físicamente las carpetas de análisis de cada imagen asociada
        for ruta_img in rutas_imagenes:
            stem = Path(ruta_img).stem
            # Ruta de la carpeta de procesamiento local (ej. analisis_resultados/imagen_1)
            folder_path = os.path.join(get_resultados_dir(), stem)
            if os.path.exists(folder_path):
                try:
                    shutil.rmtree(folder_path, ignore_errors=True)
                    logging.info(f"[borrado_reportes] Carpeta física de procesamiento eliminada: {folder_path}")
                except Exception as err_file:
                    logging.error(f"[borrado_reportes] Error al eliminar carpeta {folder_path}: {err_file}")
                    
        # 3. Eliminar de la base de datos registros relacionados en cascada
        for id_rep in id_reportes:
            cur.execute("DELETE FROM ReporteCompartido WHERE id_reporte = ?", (id_rep,))
            cur.execute("""
                DELETE FROM Microglia 
                WHERE id_analisis IN (
                    SELECT id_analisis FROM Analisis WHERE id_reporte = ?
                )
            """, (id_rep,))
            cur.execute("DELETE FROM Analisis WHERE id_reporte = ?", (id_rep,))
            cur.execute("DELETE FROM Reporte WHERE id_reporte = ?", (id_rep,))
            logging.info(f"[borrado_reportes] Registros en BD del reporte {id_rep} eliminados.")
            
        # 4. Obtener rutas de imágenes huérfanas antes de borrarlas
        cur.execute("""
            SELECT ruta_archivo FROM Imagen 
            WHERE id_imagen NOT IN (SELECT DISTINCT id_imagen FROM Analisis)
        """)
        img_huerfanas = [row[0] for row in cur.fetchall() if row[0]]
        
        # Eliminar registros de imágenes huérfanas
        cur.execute("""
            DELETE FROM Imagen 
            WHERE id_imagen NOT IN (SELECT DISTINCT id_imagen FROM Analisis)
        """)
        logging.info("[borrado_reportes] Imágenes huérfanas limpiadas en la base de datos.")
        
        # Borrar físicamente las imágenes huérfanas si están dentro de app_data_dir
        app_data_dir = get_app_data_dir()
        for r_img in img_huerfanas:
            if os.path.isabs(r_img):
                abs_path = os.path.abspath(r_img)
            else:
                abs_path = os.path.abspath(os.path.join(app_data_dir, r_img))
                
            try:
                common_prefix = os.path.commonpath([app_data_dir, abs_path])
                if common_prefix == os.path.abspath(app_data_dir) and os.path.exists(abs_path):
                    os.remove(abs_path)
                    logging.info(f"[borrado_reportes] Archivo de imagen huérfana eliminado: {abs_path}")
            except Exception as file_err:
                logging.error(f"[borrado_reportes] No se pudo borrar archivo de imagen huérfana {abs_path}: {file_err}")
                
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        logging.error(f"[borrado_reportes] Error general al eliminar reportes: {e}")
        raise e
    finally:
        conn.close()
