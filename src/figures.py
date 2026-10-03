"""Figuras estáticas del informe y del notebook."""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from .pipeline import ROOT

def build(root=ROOT):
    d=pd.read_csv(root/'data/procesados/produccion_limpia.csv',parse_dates=['fecha'])
    m=pd.read_csv(root/'reportes/serie_mensual.csv',parse_dates=['fecha'])
    ch=pd.read_csv(root/'reportes/cambios_mensuales.csv')
    co=pd.read_csv(root/'reportes/comparacion_interanual.csv')
    out=root/'reportes/figuras';out.mkdir(exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.labelcolor':'#264b40','text.color':'#264b40','figure.facecolor':'white','savefig.facecolor':'white'})
    def save(name):
        plt.tight_layout();plt.savefig(out/name,dpi=170,bbox_inches='tight');plt.close()
    fig,ax=plt.subplots(figsize=(9,3.6));ax.hist(d.crudo.dropna()/1e6,bins=28,color='#337d65',edgecolor='white')
    ax.axvline(d.crudo.mean()/1e6,color='#b87822',label=f'Media: {d.crudo.mean()/1e6:.3f} M')
    ax.axvline(d.crudo.median()/1e6,color='#253f52',linestyle='--',label=f'Mediana: {d.crudo.median()/1e6:.3f} M')
    ax.set(xlabel='Crudo por activo-mes (millones de barriles)',ylabel='Registros',title=f'Distribución del crudo observado · n={d.crudo.count()}');ax.legend(frameon=False);save('01_distribucion.png')
    fig,(ax,bx)=plt.subplots(2,1,figsize=(9,5),sharex=True)
    ax.plot(m.fecha,m.crudo/1e6,color='#337d65',linewidth=2);ax.set(ylabel='Millones de barriles',title='Totales mensuales observados y cobertura variable')
    bx.plot(m.fecha,m.n_crudo,color='#b87822',marker='.',linewidth=1);bx.set(ylabel='Activos con crudo válido',xlabel='Mes');bx.set_yticks(range(10,17));save('02_serie_cobertura.png')
    q=d[d.anio.eq(2026)].groupby('activo').crudo.sum().sort_values()
    fig,ax=plt.subplots(figsize=(9,4.8));ax.barh(q.index,q/1e6,color=['#b87822' if a in ['SA','AU','SH'] else '#337d65' for a in q.index]);ax.set(xlabel='Millones de barriles observados',title='Concentración por activo · enero-agosto 2026 · n=8 meses/activo');save('03_concentracion.png')
    fig,ax=plt.subplots(figsize=(9,4));ax.scatter(ch.cambio_precio_pct,ch.cambio_crudo_pct,color='#337d65',alpha=.7)
    ax.axhline(0,color='#d0d6d2',zorder=0);ax.axvline(0,color='#d0d6d2',zorder=0);ax.set(xlabel='Cambio mensual del precio (%)',ylabel='Cambio mensual del crudo diario (%)',title=f'Cohorte constante de 11 activos · n={len(ch)} pares mensuales');save('04_cambios.png')
    fig,ax=plt.subplots(figsize=(9,4.5));ax.barh(co.activo,co.cambio_pct,color=['#b87822' if v<0 else '#337d65' for v in co.cambio_pct]);ax.axvline(0,color='#9ba9a1');ax.set(xlabel='Cambio de tasa diaria (%)',title='Enero-agosto 2026 vs. 2025 · 14 activos comparables · n=8+8 meses');save('05_comparacion.png')
    return out

if __name__=='__main__':print(build())
