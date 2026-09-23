"""Lectura de las adjudicaciones de la sindicación de PLACSP.

QUÉ SE PUEDE SACAR DEL FEED Y QUÉ NO. Esto es lo primero que hay que saber,
porque el plan original daba por hecho algo que no está:

  SÍ está      el adjudicatario con su NIF, el organismo, el objeto, el
               importe, el CPV, la duración, cuántas ofertas se
               presentaron y el enlace al expediente.

  NO está      LOS CRITERIOS DE ADJUDICACIÓN. Ni AwardingCriteria, ni
               WeightNumeric, ni AwardingCriteriaTypeCode. Cero apariciones
               en las 439 entradas del feed del 25/08/2026. Lo único que
               trae TenderingTerms es FundingProgramCode y
               ProcurementNationalLegislationCode.

Consecuencia: el filtro de "al menos un 20 % de la puntuación no depende
del precio" NO se puede calcular desde aquí. Eso vive en el PCAP, que es un
PDF aparte. Así que este módulo produce la LISTA DE CANDIDATOS con lo que
sí es comprobable, y el peso de lo no-precio se mira al abrir el pliego,
que es justo el trabajo que se cobra.

Regla de siempre: aquí no se inventa ni se estima nada. Lo que no viene en
el XML sale vacío, no aproximado.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

ATOM = "{http://www.w3.org/2005/Atom}"

# ResultCode de CODICE. Solo nos interesan los contratos que se adjudicaron
# de verdad: un desierto o un renunciado no tiene adjudicatario a quien
# escribir.
ADJUDICADOS = {"8", "9"}          # 8 adjudicado · 9 formalizado
NO_ADJUDICADOS = {"1", "2", "3"}  # desierto, renuncia, desistimiento

# Primera letra del NIF, que dice qué clase de entidad ganó.
#
# Escribimos a ORGANIZACIONES, no a personas. Una P es un ayuntamiento y
# una Q un organismo público: ésos son el cliente de nuestro cliente. Un
# NIF que empieza por número es una persona física, y ahí no entramos: es
# un dato personal y Sara solo escribe a direcciones genéricas de sociedad.
#
# La U son las UTE, uniones temporales de empresas. La primera versión de
# esto las tiraba, y eran 88 de 787 en un solo día: justo el perfil que
# buscamos, porque una UTE gana contratos grandes y con más obligaciones
# que justificar. Cuestan más de localizar, pero no se descartan: salen
# marcadas para que se decida con ellas delante.
NIF_SOCIEDAD = set("ABCDEFJNRW")
NIF_UTE = set("U")
NIF_ASOCIACION = set("G")          # asociaciones y algunas fundaciones
NIF_PUBLICO = set("PQSV")

TIPOS = [(NIF_SOCIEDAD, "Sociedad"), (NIF_UTE, "UTE"),
         (NIF_ASOCIACION, "Asociacion"), (NIF_PUBLICO, "Organismo publico")]

# Familias de CPV con ejecución continuada, que es donde el mapa tiene
# sentido: si el contrato se agota en una entrega, no hay nada que
# justificar mes a mes.
CPV_INTERESANTES = ("50", "90", "85", "79", "45259", "55", "98")


@dataclass
class Adjudicacion:
    expediente: str = ""
    objeto: str = ""
    organismo: str = ""
    organismo_padre: str = ""
    lote: str = ""
    objeto_lote: str = ""
    adjudicatario: str = ""
    nif: str = ""
    importe: float | None = None
    presupuesto: float | None = None
    cpv: str = ""
    ofertas: int | None = None
    fecha_contrato: str = ""
    inicio: str = ""
    fin: str = ""
    region: str = ""
    enlace: str = ""
    resultado: str = ""

    @property
    def tipo_entidad(self) -> str:
        """Sociedad, UTE, Asociacion, Organismo publico o Persona fisica."""
        if not self.nif:
            return ""
        inicial = self.nif[0].upper()
        for letras, nombre in TIPOS:
            if inicial in letras:
                return nombre
        return "Persona fisica" if inicial.isdigit() else "Otra"

    @property
    def es_escribible(self) -> bool:
        """Una organización a la que se le puede escribir a una dirección
        de empresa. Excluye a la persona física, que es un dato personal."""
        return self.tipo_entidad in ("Sociedad", "UTE", "Asociacion")

    @property
    def es_publico(self) -> bool:
        return self.tipo_entidad == "Organismo publico"

    @property
    def cpv_interesante(self) -> bool:
        return self.cpv.startswith(CPV_INTERESANTES)


def _t(nodo, etiqueta: str) -> str:
    """Primer descendiente con ese nombre local, ignorando el namespace."""
    if nodo is None:
        return ""
    for n in nodo.iter():
        if n.tag.split("}")[-1] == etiqueta:
            return (n.text or "").strip()
    return ""


def _hijo(nodo, etiqueta: str):
    if nodo is None:
        return None
    for n in nodo:
        if n.tag.split("}")[-1] == etiqueta:
            return n
    return None


def _num(texto: str) -> float | None:
    """Importe. El feed usa punto decimal; el 0 es un dato, no un vacío."""
    if not texto:
        return None
    try:
        return float(texto)
    except ValueError:
        return None


def _organismos(estado) -> tuple[str, str]:
    """Organismo que contrata y el de encima, si lo hay."""
    lcp = _hijo(estado, "LocatedContractingParty")
    if lcp is None:
        return "", ""
    propio = _t(_hijo(lcp, "Party"), "Name")
    padre = _t(_hijo(lcp, "ParentLocatedParty"), "Name")
    return propio, padre


def _enlace(entrada) -> str:
    for l in entrada.findall(ATOM + "link"):
        if l.get("href"):
            return l.get("href")
    return (_t(entrada, "id") or "").strip()


def leer(ruta: Path | str) -> list[Adjudicacion]:
    """Todas las adjudicaciones del fichero. Una por lote adjudicado."""
    raiz = ET.parse(str(ruta)).getroot()
    salida: list[Adjudicacion] = []

    for entrada in raiz.findall(ATOM + "entry"):
        estado = _hijo(entrada, "ContractFolderStatus")
        if estado is None:
            continue

        proyecto = _hijo(estado, "ProcurementProject")
        organismo, padre = _organismos(estado)
        comun = dict(
            expediente=_t(estado, "ContractFolderID"),
            objeto=_t(proyecto, "Name"),
            organismo=organismo,
            organismo_padre=padre,
            presupuesto=_num(_t(_hijo(proyecto, "BudgetAmount"),
                                "EstimatedOverallContractAmount")),
            cpv=_t(_hijo(proyecto, "RequiredCommodityClassification"),
                   "ItemClassificationCode"),
            region=_t(_hijo(proyecto, "RealizedLocation"), "CountrySubentityCode"),
            inicio=_t(_hijo(proyecto, "PlannedPeriod"), "StartDate"),
            fin=_t(_hijo(proyecto, "PlannedPeriod"), "EndDate"),
            enlace=_enlace(entrada),
        )

        # el nombre de cada lote, para poder decir de cuál hablamos
        lotes = {}
        for lote in estado:
            if lote.tag.split("}")[-1] != "ProcurementProjectLot":
                continue
            lotes[_t(_hijo(lote, "ID"), "ID") or (_hijo(lote, "ID").text or "").strip()
                  if _hijo(lote, "ID") is not None else ""] = \
                _t(_hijo(lote, "ProcurementProject"), "Name")

        for res in estado:
            if res.tag.split("}")[-1] != "TenderResult":
                continue
            codigo = _t(_hijo(res, "ResultCode"), "ResultCode") or \
                     ((_hijo(res, "ResultCode").text or "").strip()
                      if _hijo(res, "ResultCode") is not None else "")
            ganador = _hijo(res, "WinningParty")
            adjudicado = _hijo(res, "AwardedTenderedProject")
            lote_id = _t(adjudicado, "ProcurementProjectLotID")
            ofertas = _t(res, "ReceivedTenderQuantity")

            salida.append(Adjudicacion(
                **comun,
                lote=lote_id,
                objeto_lote=lotes.get(lote_id, ""),
                adjudicatario=_t(_hijo(ganador, "PartyName"), "Name") if ganador is not None else "",
                nif=_t(_hijo(ganador, "PartyIdentification"), "ID") if ganador is not None else "",
                importe=_num(_t(_hijo(adjudicado, "LegalMonetaryTotal"), "TaxExclusiveAmount")),
                ofertas=int(ofertas) if ofertas.isdigit() else None,
                fecha_contrato=_t(_hijo(res, "Contract"), "IssueDate"),
                resultado=codigo,
            ))

    return salida
