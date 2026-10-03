"""Un solo comando reconstruye los entregables desde las fuentes conservadas."""
import argparse
from .pipeline import run
from .figures import build as figures
from .build_dashboard import build as dashboard
from .notebook import build as notebook
from .report import build as report

def main():
    p=argparse.ArgumentParser();p.add_argument('--sin-notebook',action='store_true',help='Regenerar salidas sin ejecutar el notebook (opcional).');args=p.parse_args()
    run();print('1/5 Datos, auditoría y análisis listos.')
    figures();print('2/5 Figuras listas.')
    dashboard();print('3/5 Dashboard listo.')
    if not args.sin_notebook:notebook();print('4/5 Notebook ejecutado sin errores.')
    report();print('5/5 PDF generado en docs/Proyecto_Final_EDA_Grupo_5.pdf.')

if __name__=='__main__':main()
