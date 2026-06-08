import os
import sys

def get_app_data_dir():
    if getattr(sys, 'frozen', False):
        app_data = os.getenv('LOCALAPPDATA', os.path.expanduser('~'))
        base_dir = os.path.join(app_data, 'AVA_Image_Analytics')
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    
    os.makedirs(base_dir, exist_ok=True)
    return base_dir

def get_resultados_dir():
    d = os.path.join(get_app_data_dir(), "analisis_resultados")
    os.makedirs(d, exist_ok=True)
    return d

def get_bd_dir():
    d = os.path.join(get_app_data_dir(), "bd")
    os.makedirs(d, exist_ok=True)
    return d
