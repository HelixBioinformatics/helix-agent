#!/usr/bin/env python3
"""Standalone plot from audited actual resource contrasts; no experiment mutation."""
import argparse,hashlib,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
HERE=Path(__file__).resolve().parent
MIB=2**20

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
 p=argparse.ArgumentParser();p.add_argument('--summary',type=Path,default=HERE/'summary.json');p.add_argument('--output',type=Path,default=HERE/'figures');a=p.parse_args()
 data=json.loads(a.summary.read_text());a.output.mkdir(parents=True,exist_ok=True)
 plt.rcParams.update({'font.family':'DejaVu Sans','font.size':12,'axes.labelsize':12,'xtick.labelsize':11.5,'ytick.labelsize':11.5,'legend.fontsize':11.5,'figure.dpi':300,'savefig.dpi':300,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'svg.fonttype':'none'})
 fig,axes=plt.subplots(2,1,figsize=(7.4,9.3),sharey=True)
 for ax,key,label in zip(axes,['original','boundary'],['A. Cuarenta contrastes originales','B. Seis contrastes de frontera']):
  group=data[key];rows=group['rows'];counts=group['counts'];observed=[r for r in rows if r.get('allocatedBlockBytesObservedPeak')is not None]
  allvalues=[r['predictedWorkBytes']/MIB for r in observed if r.get('predictedWorkBytes')is not None]
  lo,hi=(1/16,128)if key=='original'else(36,44)
  # y=x is curved in screen coordinates when the x axis is logarithmic.
  # Sample the identity itself instead of connecting only its end points.
  identity=[lo*(hi/lo)**(i/256)for i in range(257)]
  ax.plot(identity,identity,color='#77808a',lw=1.1,linestyle=':',label='Cuota = bloques asignados')
  if allvalues:
   low,high=min(allvalues),max(allvalues)
   ax.axhline(low,color='#39434d',lw=1.1,linestyle='--')
   if high!=low:ax.axhspan(low,high,color='#39434d',alpha=.1)
  for row in observed:
   decision=row.get('actualDecision');physical=row.get('physicalFeasibilityLabel')
   color='#0072B2'if decision and decision['accepted']else('#D55E00'if decision else'#606870')
   marker='o'if physical is True else('x'if physical is False else'?')
   if marker=='?':ax.annotate('?',(row['budgetWorkBytes']/MIB,row['allocatedBlockBytesObservedPeak']/MIB),color=color,ha='center',va='center',fontsize=12)
   else:ax.scatter(row['budgetWorkBytes']/MIB,row['allocatedBlockBytesObservedPeak']/MIB,c=color,marker=marker,s=55,linewidths=1.3,alpha=.82,zorder=3)
  if key=='original':
   ax.set_xscale('log',base=2);ticks=[.0625,.25,1,4,16,128];ax.set_xticks(ticks,[str(v).replace('.',',')for v in ticks]);ax.set_xlim(.05,155)
  else:ax.set_xlim(lo,hi);ax.set_xticks([37,39,41,43])
  ax.set_ylim(-1.5,46);ax.set_yticks([0,10,20,30,40]);ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
  ax.set_ylabel('Pico muestreado de bloques\nasignados (MiB)');ax.set_xlabel('Cuota de trabajo aprobada por el operador (MiB)')
  ax.text(0,1.055,label,transform=ax.transAxes,fontweight='bold',fontsize=12)
  ax.text(0,1.005,f"{counts['observed']}/{counts['planned']} observados; {counts['feasible']} factibles, {counts['infeasible']} inviables; {counts['unknownObserved']} sin etiqueta",transform=ax.transAxes,fontsize=11.5)
  if key=='boundary':ax.text(.03,.09,f"Falsos rechazos: {counts['falseRejections']}/{counts['feasible']}\nUmbral previsto: ≤ 5 %",transform=ax.transAxes,fontsize=11.5,color='#39434d')
  if not observed:ax.text(.5,.4,'Sin observaciones todavía',transform=ax.transAxes,ha='center',color='#606870')
 handles=[Line2D([],[],color='#0072B2',marker='o',lw=0,label='Admisión real: acepta'),Line2D([],[],color='#D55E00',marker='o',lw=0,label='Admisión real: rechaza'),Line2D([],[],color='#606870',marker='o',lw=0,label='Flujo completo verificado'),Line2D([],[],color='#606870',marker='x',lw=0,label='Fallo terminal causal'),Line2D([],[],color='#606870',marker='$?$',lw=0,label='Factibilidad desconocida'),Line2D([],[],color='#39434d',linestyle='--',lw=1.1,label='Predicción de almacenamiento'),Line2D([],[],color='#77808a',linestyle=':',lw=1.1,label='Igualdad con la cuota')]
 fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.5,.015),ncol=2,frameon=False,handlelength=1.8,columnspacing=1.2)
 fig.subplots_adjust(left=.15,right=.985,top=.945,bottom=.255,hspace=.55)
 for extension in ['png','pdf','svg']:fig.savefig(a.output/('aggregate-storage.'+extension),dpi=300)
 caption=('Contraste de almacenamiento de Helix bajo una única cuota XFS de proyecto para el cliente real, SQLite, cachés, temporales, controlador y exportación portátil. Los cuarenta casos originales (A) y los seis de frontera (B) se congelaron por separado. El color representa la decisión original del módulo de admisión; la forma representa la observación independiente. En una ejecución completa se verificaron cuatro trabajos nativos, el resultado de referencia de su propia entrada, SQLite persistente y la exportación. En un fallo causal, el pico corresponde al trabajo incompleto y no estima todo el almacenamiento necesario para completar el flujo. Los picos se muestrearon cada 0,5 s. Algunos puntos coinciden; no se alteraron sus coordenadas para separarlos. Los tres flujos con cuota de 39 MiB de la frontera completaron el cálculo pese al rechazo de Helix. El suplemento posterior de cuatro casos se informa por separado y no está representado. La infraestructura de software preinstalada, las cachés compartidas de Docker y la telemetría experimental del observador están fuera de la cuota. Todos los casos derivan de una proteína de desarrollo; esta figura no estima desempeño biológico ni sustituye la evaluación reservada. ' + f"Observados al generar la figura: {data['originalCounts']['observed']}/40 y {data['boundaryCounts']['observed']}/6.")
 (a.output/'aggregate-storage-caption.txt').write_text(caption+'\n')
 records={str(p.relative_to(a.output)):{'bytes':p.stat().st_size,'sha256':sha(p)}for p in sorted(a.output.glob('aggregate-storage*'))if p.is_file()}
 (a.output/'figure-manifest.json').write_text(json.dumps({'schema':'helix-derived-resource-figure/1.0','summarySha256':sha(a.summary),'generatorSha256':sha(Path(__file__)),'specificationSha256':sha(HERE/'figure_specification.json'),'files':records,'all46Observed':data['all46Observed'],'scientificR24Rate':None},indent=2)+'\n')
 print(json.dumps({'output':str(a.output),'originalObserved':data['originalCounts']['observed'],'boundaryObserved':data['boundaryCounts']['observed']}))
if __name__=='__main__':main()
