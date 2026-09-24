# -*- coding: utf-8 -*-
"""Saca de cada expediente del ATOM lo que sirve para un hallazgo.

El parseo de ayer (radar/placsp.py) solo miraba quien gano y por cuanto.
El feed trae mucho mas: el PRESUPUESTO BASE, cuantos licitadores se
presentaron, la duracion, la fecha de fin y el enlace al pliego. Con el
presupuesto y el importe adjudicado sale la BAJA, que es el dato que de
verdad le duele a una empresa: cuanto margen se dejo por ganar.
"""
import csv
import glob
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

RAIZ = Path(__file__).parent

# Los .atom los baja CoWork a mano (el proxy no deja salir a la Plataforma)
# y los deja aqui. Se puede apuntar a otra carpeta con un argumento.
CARPETA = sys.argv[1] if len(sys.argv) > 1 else str(RAIZ / 'datos' / 'placsp')
NS = {
 'atom': 'http://www.w3.org/2005/Atom',
 'cfs': 'urn:dgpe:names:draft:codice-place-ext:schema:xsd:CommonAggregateComponents-2',
 'cbcx': 'urn:dgpe:names:draft:codice-place-ext:schema:xsd:CommonBasicComponents-2',
 'cac': 'urn:dgpe:names:draft:codice:schema:xsd:CommonAggregateComponents-2',
 'cbc': 'urn:dgpe:names:draft:codice:schema:xsd:CommonBasicComponents-2',
}

def txt(nodo, ruta):
    e = nodo.find(ruta, NS)
    return (e.text or '').strip() if e is not None and e.text else ''

def num(nodo, ruta):
    v = txt(nodo, ruta)
    try: return float(v)
    except ValueError: return None

filas = []
for fp in sorted(glob.glob(CARPETA + '/*.atom')):
    raiz = ET.parse(fp).getroot()
    for entry in raiz.findall('atom:entry', NS):
        cfs = entry.find('cfs:ContractFolderStatus', NS)
        if cfs is None:
            continue
        pp = cfs.find('cac:ProcurementProject', NS)
        org = cfs.find('.//cfs:LocatedContractingParty/cac:Party', NS)
        base = num(pp, 'cac:BudgetAmount/cbc:TaxExclusiveAmount') if pp is not None else None
        techo = num(pp, 'cac:BudgetAmount/cbc:EstimatedOverallContractAmount') if pp is not None else None

        for tr in cfs.findall('cac:TenderResult', NS):
            if txt(tr, 'cbc:ResultCode') not in ('8', '9'):
                continue
            wp = tr.find('cac:WinningParty', NS)
            if wp is None:
                continue
            adjud = num(tr, 'cac:AwardedTenderedProject/cac:LegalMonetaryTotal/cbc:TaxExclusiveAmount')
            filas.append(dict(
                nif=txt(wp, 'cac:PartyIdentification/cbc:ID'),
                empresa=txt(wp, 'cac:PartyName/cbc:Name'),
                expediente=txt(cfs, 'cbc:ContractFolderID'),
                objeto=txt(pp, 'cbc:Name') if pp is not None else '',
                organismo=txt(org, 'cac:PartyName/cbc:Name') if org is not None else '',
                tipo=txt(pp, 'cbc:TypeCode') if pp is not None else '',
                cpv=txt(pp, 'cac:RequiredCommodityClassification/cbc:ItemClassificationCode') if pp is not None else '',
                base=base, techo=techo, adjudicado=adjud,
                licitadores=txt(tr, 'cbc:ReceivedTenderQuantity'),
                procedimiento=txt(cfs, 'cac:TenderingProcess/cbc:ProcedureCode'),
                sistema=txt(cfs, 'cac:TenderingProcess/cbc:ContractingSystemCode'),
                urgencia=txt(cfs, 'cac:TenderingProcess/cbc:UrgencyCode'),
                duracion=txt(pp, 'cac:PlannedPeriod/cbc:DurationMeasure') if pp is not None else '',
                duracion_ud=(pp.find('cac:PlannedPeriod/cbc:DurationMeasure', NS).get('unitCode','')
                             if pp is not None and pp.find('cac:PlannedPeriod/cbc:DurationMeasure', NS) is not None else ''),
                fin=txt(pp, 'cac:PlannedPeriod/cbc:EndDate') if pp is not None else '',
                lote=txt(tr, 'cac:AwardedTenderedProject/cbc:ProcurementProjectLotID'),
                fecha=txt(tr, 'cbc:AwardDate') or txt(cfs, 'cbc:ContractFolderStatusCode'),
                pcap=txt(cfs, 'cac:TenderingTerms/cac:CallForTendersDocumentReference/cac:Attachment/cac:ExternalReference/cbc:URI'),
                enlace=(entry.find('atom:link', NS).get('href') if entry.find('atom:link', NS) is not None else ''),
            ))

SALIDA = RAIZ / 'datos' / 'expedientes.csv'
if not filas:
    sys.exit(f'No hay ningun .atom en {CARPETA}. Los baja CoWork a mano.')
with SALIDA.open('w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=filas[0].keys()); w.writeheader(); w.writerows(filas)
print(f'{len(filas)} adjudicaciones extraidas -> {SALIDA}')

# Cuanto de esto esta relleno de verdad
for c in ('base', 'techo', 'adjudicado', 'licitadores', 'duracion', 'fin', 'lote', 'pcap'):
    n = sum(1 for r in filas if r[c] not in ('', None))
    print(f'  {c:<13} {n:>4}/{len(filas)}  ({100*n//len(filas)}%)')
