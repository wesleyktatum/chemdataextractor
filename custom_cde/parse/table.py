# -*- coding: utf-8 -*-
"""
chemdataextractor.parse.table
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
import logging
import re
from lxml.builder import E
from lxml import etree

from .common import delim, lbrct, rbrct
from ..utils import first
from ..model import Compound, UvvisSpectrum, UvvisPeak, QuantumYield, FluorescenceLifetime, MeltingPoint, GlassTransition
from ..model import ElectrochemicalPotential, IrSpectrum, IrPeak
from ..model import BandGap, FermiEnergy, HOMOLevel, LUMOLevel
from ..model import PCE, FF, Voc, Jsc
from ..model import NumAvgMolecularWeight, WeightAvgMolecularWeight, Dispersity
from ..model import Crystallinity, FusionEnthalpy, SublimationEnthalpy, VaporizationEnthalpy
from ..model import Modulus, CorrosionInhibition, BoilingPoint
from .actions import join, merge, fix_whitespace
from .base import BaseParser
from .cem import chemical_label, label_before_name, chemical_name, chemical_label_phrase, solvent_name, lenient_chemical_label
from .elements import R, I, W, Optional, ZeroOrMore, Any, OneOrMore, Start, End, Group, Not

log = logging.getLogger(__name__)


delims = ZeroOrMore(delim)
minus = R('^[\-–−‒]$')


name_blacklist = R('^([\d\.]+)$')

#: Compound identifier column heading
compound_heading = R('(^|\b)(comp((oun)?d)?|molecule|ligand|oligomer|complex|dye|porphyrin|substance|sample|material|catalyst|acronym|isomer|(co)?polymer|chromophore|species|quinone|ether|diene|adduct|acid|radical|monomer|amine|analyte|product|system|(photo)?sensitiser|phthalocyanine|MPc)(e?s)?($|\b)', re.I)
solvent_heading = R('(^|\b)(solvent)s?($|\b)', re.I)
solvent_in_heading = Group(solvent_name)('cem')
solvent_cell = Group(solvent_name | chemical_name)('cem')
compound_cell = Group(
    (Start() + chemical_label + End())('cem') |
    (Start() + lenient_chemical_label + End())('cem') |
    chemical_label_phrase('cem') |
    (Not(Start() + OneOrMore(name_blacklist) + End()) + OneOrMore(Any())('name').add_action(join).add_action(fix_whitespace) + Optional(W('(').hide() + chemical_label + W(')').hide()))('cem') |
    label_before_name
)('cem_phrase')


uvvis_emi_title = (
    I('emission') + R('max(ima)?') |
    W('λ') + Optional(I('max')) + Optional(W(',')) + R('em(i(ssion)?)?', re.I) |
    R('em(i(ssion)?)?', re.I) + W('λ') + Optional(I('max')) + Optional(W(','))
)
uvvis_abs_title = (
    I('absorption') + R('max(ima)?') |
    W('λ') + OneOrMore(R('^(a|sol)?max$', re.I) | R('abs(or[bp]tion)?', re.I) | I('a') | W(',')) |
    R('uv([-/]?vis)?', re.I)
)
extinction_title = Optional(R('^10\d$') | W('10') + minus + R('^\d$')).hide() + W('ε') + Optional(I('max'))
uvvis_units = (W('nm') | R('^eV[\-–−‒]1$') | W('eV') + minus + W('1'))('uvvis_units').add_action(merge)
multiplier = Optional(I('×')) + (R('^10–?[34]$') | (W('10') + minus + R('^[345]$')))

extinction_units = (
    (Optional(multiplier + delims) + (
        I('M') + minus + I('1') + I('cm') + minus + I('1') |
        I('M') + minus + I('1') + I('cm') + minus + I('1') |
        I('dm3') + I('mol') + minus + I('1') + I('cm') + minus + I('1') |
        I('l') + I('mol') + minus + I('1') + I('cm') + minus + I('1') |
        I('l') + I('cm') + minus + I('1') + I('mol') + minus + I('1')
    )) | multiplier
)('extinction_units').add_action(join)

ir_title = (
    R('^(FT-?)?IR$') + Optional(I('absorption'))
)
ir_units = Optional(W('/')).hide() + (
    R('^\[?cm[-–−]1\]?$') |
    W('cm') + R('^[-–−]$') + W('1')
)('ir_units').add_action(merge)
ir_heading = (OneOrMore(ir_title.hide()) + ZeroOrMore(delims.hide() + ir_units))('ir_heading')
ir_value = (R('^\d{3,5}(\.\d{1,2})?$'))('value')
peak_strength = R('^(sh(oulder)?|br(oad)?)$')('strength')
ir_peak = (
    ir_value + Optional(W('(').hide()) + Optional(peak_strength) + Optional(W(')').hide())
)('ir_peak')
ir_cell = (
    ir_peak + ZeroOrMore(W(',').hide() + ir_peak)
)('ir_cell')

# TODO: (photoluminescence|fluorescence) quantum yield
quantum_yield_title = (R('^(Φ|ϕ)(fl?|pl|ze|t|l|lum)?$', re.I) + Optional(R('^(fl?|pl|ze|t|l|lum)$', re.I)))('quantum_yield_type').add_action(merge)  #  + ZeroOrMore(Any())
quantum_yield_units = W('%')('quantum_yield_units')
quantum_yield_heading = Group(Start() + quantum_yield_title + delims.hide() + Optional(quantum_yield_units) + delims.hide() + End())('quantum_yield_heading')
quantum_yield_value = (Optional(R('^[~∼\<\>]$')) + ((W('10') + minus + R('^\d$')) | R('^(100(\.0+)?|\d\d?(\.\d+)?)$')) + Optional(W('±') + R('^\d+(\.\d+)?$')))('quantum_yield_value').add_action(merge)
quantum_yield_cell = (quantum_yield_value + Optional(quantum_yield_units))('quantum_yield_cell')


def split_uvvis_shape(tokens, start, result):
    """"""
    if result[0].text.endswith('sh') or result[0].text.endswith('br'):
        result.append(E('shape', result[0].text[-2:]))
        result[0].text = result[0].text[:-2]



uvvis_emi_heading = (OneOrMore(uvvis_emi_title.hide()))('uvvis_emi_heading')
uvvis_abs_heading = (OneOrMore(uvvis_abs_title.hide()) + ZeroOrMore(delims.hide() + (uvvis_units | extinction_title.hide() | extinction_units)))('uvvis_abs_heading')
uvvis_abs_disallowed = I('emission')
extinction_heading = (extinction_title.hide() + delims.hide() + Optional(extinction_units))('extinction_heading')
uvvis_value = (R('^\d{3,4}(\.\d{1,2})?(sh|br)?$'))('value').add_action(split_uvvis_shape)
peak_shape = R('^(sh(oulder)?|br(oad)?)$')('shape')
extinction_value = (
    R('^\d+\.\d+$') + Optional(W('±') + R('^\d+\.\d+$')) + Optional(W('×') + R('10\d+')) |  # Scientific notation
    R('^\d{1,3}$') + R('^\d\d\d$') |  # RSC often inserts spaces within values instead of commas
    R('^\d{1,2},?\d{3,3}$')

)('extinction').add_action(merge)


uvvis_abs_emi_quantum_yield_heading = (
    OneOrMore(uvvis_abs_title.hide()) +
    Optional(Optional(delims.hide()) + uvvis_units('uvvis_abs_units') + Optional(delims.hide())) +
    OneOrMore(uvvis_emi_title.hide()) +
    Optional(Optional(delims.hide()) + uvvis_units + Optional(delims.hide())) +
    Optional(delims.hide()) + quantum_yield_title.hide() + Optional(delims.hide()) +
    Optional(Optional(delims.hide()) + quantum_yield_units + Optional(delims.hide()))
)('uvvis_emi_quantum_yield_heading')

uvvis_abs_emi_quantum_yield_cell = (
    uvvis_value('uvvis_abs_value') + delims.hide() + uvvis_value + delims.hide() + quantum_yield_value + Optional(quantum_yield_units)
)('uvvis_emi_quantum_yield_cell')


uvvis_emi_quantum_yield_heading = (
    OneOrMore(uvvis_emi_title.hide()) +
    Optional(Optional(delims.hide()) + uvvis_units + Optional(delims.hide())) +
    Optional(delims.hide()) + quantum_yield_title.hide() + Optional(delims.hide()) +
    Optional(Optional(delims.hide()) + quantum_yield_units + Optional(delims.hide()))
)('uvvis_emi_quantum_yield_heading')

uvvis_emi_quantum_yield_cell = (
    uvvis_value + delims.hide() + quantum_yield_value + Optional(quantum_yield_units)
)('uvvis_emi_quantum_yield_cell')

uvvis_abs_peak = (
    uvvis_value + Optional(peak_shape) + Optional(W('(').hide() + extinction_value + W(')').hide())
)('uvvis_abs_peak')

uvvis_abs_cell = (
    uvvis_abs_peak + ZeroOrMore(W(',').hide() + uvvis_abs_peak)
)('uvvis_abs_cell')

extinction_cell = (
    extinction_value + ZeroOrMore(W(',').hide() + extinction_value)
)('uvvis_abs_cell')

uvvis_emi_peak = (
    uvvis_value + Optional(peak_shape)
)('uvvis_emi_peak')

uvvis_emi_cell = (
    uvvis_emi_peak + ZeroOrMore(W(',').hide() + uvvis_emi_peak)
)('uvvis_emi_cell')


fluorescence_lifetime_title = W('τ') + R('^(e|f|ave|avg|0)$', re.I)
fluorescence_lifetime_units = (W('ns') | W('μ') + W('s'))('fluorescence_lifetime_units').add_action(merge)
fluorescence_lifetime_heading = (fluorescence_lifetime_title.hide() + delims.hide() + Optional(fluorescence_lifetime_units))('fluorescence_lifetime_heading')
fluorescence_lifetime_value = (Optional(R('^[~∼\<\>]$')) + R('^\d+(\.\d+)?$'))('fluorescence_lifetime_value').add_action(merge)
fluorescence_lifetime_cell = (
    fluorescence_lifetime_value + ZeroOrMore(W(',').hide() + fluorescence_lifetime_value)
)('fluorescence_lifetime_cell')

electrochemical_potential_title = ((R('^E(ox|red)1?$', re.I) | W('E') + R('^(ox|red)1?$')) + Optional(W('/') + W('2')))('electrochemical_potential_type').add_action(merge)
electrochemical_potential_units = (W('V'))('electrochemical_potential_units').add_action(merge)
electrochemical_potential_heading = (electrochemical_potential_title + delims.hide() + Optional(electrochemical_potential_units))('electrochemical_potential_heading')
electrochemical_potential_value = (Optional(R('^[~∼\<\>]$')) + Optional(minus) + R('^\d+(\.\d+)?$'))('electrochemical_potential_value').add_action(merge)
electrochemical_potential_cell = (
    electrochemical_potential_value + ZeroOrMore(delims.hide() + electrochemical_potential_value)
)('electrochemical_potential_cell')

subject_phrase = ((I('of') | I('for')) + chemical_name)('subject_phrase')

solvent_phrase = (I('in') + (solvent_name | chemical_name) | \
                  ((solvent_name | chemical_name) + Optional(I('solution'))) | \
                 (Optional(I('thin')) + I('film')))('solvent_phrase')

temp_range = (Optional(R('^[\-–−]$')) + (R('^[\+\-–−]?\d+(\.\d+)?[\-–−]\d+(\.\d+)?$') | (R('^[\+\-–−]?\d+(\.\d+)?$') + R('^[\-–−]$') + R('^[\+\-–−]?\d+(\.\d+)?$'))))('temperature').add_action(merge)
temp_value = (Optional(R('^[\-–−]$')) + R('^[\+\-–−]?\d+(\.\d+)?$') + Optional(W('±') + R('^\d+(\.\d+)?$')))('temperature').add_action(merge)
temp_word = (I('room') + R('^temp(erature)?$') | R('^r\.?t\.?$', re.I))('temperature').add_action(merge)
temp = (temp_range | temp_value | temp_word)('value')
temp_units = ((Optional(R('°')) | Optional(R('º'))) + (R('[C|F|K]') | W('K')))('units').add_action(merge)
temp_with_units = (temp + temp_units)('temp')
temp_with_optional_units = (temp + Optional(temp_units))('temp')

temp_phrase = (I('at') + temp_with_units)('temp_phrase')

melting_point_title = (R('^T(melt|m\.p|m)$', re.I) | W('T') + R('^(melt|m\.p|m)?$') | (I('Melting') + Optional(I('point')) + Optional(I('temperature')) + Optional(I('range'))))

melting_point_heading = (melting_point_title.hide() + delims.hide() + Optional(temp_units))('melting_point_heading')

melting_point_cell = (
    temp_with_optional_units + ZeroOrMore(delims.hide() + temp_with_optional_units)
)('melting_point_cell')

glass_transition_title = (R('^T(g\.)$', re.I) | W('T') + R('^(g\.)?$') | (I('glass') + I('transition') + Optional(I('point')) + Optional(I('temperature')) + Optional(I('range'))))

glass_transition_heading = (glass_transition_title.hide() + delims.hide() + Optional(temp_units))('glass_transition_heading')

glass_transition_cell = (
    temp_with_optional_units + ZeroOrMore(delims.hide() + temp_with_optional_units)
)('glass_transition_cell')

boiling_point_title = (I('Tb') | I('T_b') | I('b\.?p\.?') | (I('Boiling') + Optional(I('point')) + Optional(I('temperature')) + Optional(I('range'))))

boiling_point_heading = (boiling_point_title + delims.hide() + Optional(temp_units))('boiling_point_heading')

boiling_point_cell = (temp_with_optional_units + ZeroOrMore(delims.hide() + temp_with_optional_units))('boiling_point_cell')

caption_context = Group(subject_phrase | solvent_phrase | temp_phrase)('caption_context')

####################################################################
# custom-cde additions
####################################################################

#############################################################
###########   Molecular Energy Level Properties   ###########
#############################################################

################## Bandgap, Fermi Energy, HOMO level, LUMO level

energy_level_range = (Optional(R('[\-–−]')) + (R('[\+\-–−]?\d+(\.\d+)?(\(\d\))?[\-––-−~∼˜]\d+(\.\d+)?(\(\d\))?') | (R('[\+\-–−]?\d+(\.\d+)?') + R('[\-–−]') + R('[\+\-–−]?\d+(\.\d+)?'))))('energy_value').add_action(merge)

energy_level_value = (Optional(R('^[\-–−]$')) + R('^[\+\-–−]?\d+(\.\d+)?$') + Optional(W('±') + Optional(R('^\d+(\.\d+)?$'))))('energy_value').add_action(merge)

energy_value = (energy_level_range | energy_level_value)('energy_value')

energy_level_units = R('eV')('energy_level_units')

energy_level_with_units = (energy_value + Optional(lbrct) + energy_level_units + Optional(rbrct))('energy_level').add_action(merge)

energy_level_with_optional_units = (energy_value + Optional(energy_level_units))('energy_level')

#################
bandgap_title = (R('Eg') | R('Ebandgap') | R('ΔE') | R('Egopt') | R('Egcv') | R('Egap') | (I('band') + I('gap')))

bandgap_heading = (bandgap_title.hide() + Optional(delims).hide() + Optional(lbrct) + energy_level_units + Optional(rbrct))('bandgap_heading')

bandgap_cell = (energy_level_with_optional_units + ZeroOrMore(delims.hide() + energy_level_with_optional_units))('bandgap_cell')
#################

#################
fermi_energy_title = (R('Ef') | R('Efermi') | (I('fermi') + Optional(I('energy')) + Optional(I('level'))))

fermi_energy_heading = (fermi_energy_title.hide() + Optional(delims).hide() + Optional(lbrct) + energy_level_units + Optional(rbrct))('fermi_energy_heading')

fermi_energy_cell = (energy_level_with_optional_units + ZeroOrMore(delims.hide() + energy_level_with_optional_units))('fermi_energy_cell')
#################

#################
homo_level_title = (R('Ehomo') | (I('homo') + Optional(I('energy')) + Optional(I('level'))))

homo_level_heading = (homo_level_title.hide() + Optional(delims).hide() + Optional(lbrct) + energy_level_units + Optional(rbrct))('homo_level_heading')

homo_level_cell = (energy_level_with_optional_units + ZeroOrMore(delims.hide() + energy_level_with_optional_units))('homo_level_cell')
#################

#################
lumo_level_title = (R('Elumo') | (I('lumo') + Optional(I('energy')) + Optional(I('level'))))

lumo_level_heading = (lumo_level_title.hide() + Optional(delims).hide() + Optional(lbrct) + energy_level_units + Optional(rbrct))('lumo_level_heading')

lumo_level_cell = (energy_level_with_optional_units + ZeroOrMore(delims.hide() + energy_level_with_optional_units))('lumo_level_cell')
#################
            
class BandGapHeadingParser(BaseParser):
    """"""
    root = bandgap_heading
            
    def interpret(self, result, start, end):
        """"""
#         print('bg headparser interpret')
#         print(result)
            
        bandgap_units = first(result.xpath('./energy_level_units/text()'))
        c = Compound()
        if bandgap_units:
            c.band_gap.append(
                BandGap(units=bandgap_units)
            )
        yield c


class BandGapCellParser(BaseParser):
    """"""
    root = bandgap_cell
    
    def interpret(self, result, start, end):
        """"""
#         print('bg cellparser interpret')
        
        c = Compound()
#         children = result.getchildren()
#         print(children[0].text())
#         print(etree.tostring(result))
        for band_gap in result.xpath('./energy_level'):
#             print(band_gap)
            c.band_gap.append(
                BandGap(
                    value=first(band_gap.xpath('./energy_value/text()')),
                    units=first(band_gap.xpath('./energy_level_units/text()'))
                )
            )
        if c.band_gap:
#             print("yield c", c.serialize())
            yield c
    

class FermiEnergyHeadingParser(BaseParser):
    """"""
    root = fermi_energy_heading
            
    def interpret(self, result, start, end):
        """"""
            
        fermi_energy_units = first(result.xpath('./energy_level_units/text()'))
        c = Compound()
        if fermi_energy_units:
            c.fermi_energy.append(
                FermiEnergy(units=fermi_energy_units)
            )
        yield c


class FermiEnergyCellParser(BaseParser):
    """"""
    root = fermi_energy_cell
    
    def interpret(self, result, start, end):
        """"""        
        c = Compound()
        for fermi_energy in result.xpath('./energy_level'):
            c.fermi_energy.append(
                FermiEnergy(
                    value=first(fermi_energy.xpath('./energy_value/text()')),
                    units=first(fermi_energy.xpath('./energy_level_units/text()'))
                )
            )
        if c.fermi_energy:
            yield c
            
            
class HOMOLevelHeadingParser(BaseParser):
    """"""
    root = homo_level_heading
            
    def interpret(self, result, start, end):
        """"""
            
        homo_level_units = first(result.xpath('./energy_level_units/text()'))
        c = Compound()
        if homo_level_units:
            c.HOMO_level.append(
                HOMOLevel(units=homo_level_units)
            )
        yield c


class HOMOLevelCellParser(BaseParser):
    """"""
    root = homo_level_cell
    
    def interpret(self, result, start, end):
        """"""        
        c = Compound()
        for homo_level in result.xpath('./energy_level'):
            c.HOMO_level.append(
                HOMOLevel(
                    value=first(homo_level.xpath('./energy_value/text()')),
                    units=first(homo_level.xpath('./energy_level_units/text()'))
                )
            )
        if c.HOMO_level:
            yield c
            
            
class LUMOLevelHeadingParser(BaseParser):
    """"""
    root = lumo_level_heading
            
    def interpret(self, result, start, end):
        """"""
            
        lumo_level_units = first(result.xpath('./energy_level_units/text()'))
        c = Compound()
        if lumo_level_units:
            c.LUMO_level.append(
                LUMOLevel(units=lumo_level_units)
            )
        yield c


class LUMOLevelCellParser(BaseParser):
    """"""
    root = lumo_level_cell
    
    def interpret(self, result, start, end):
        """"""        
        c = Compound()
        for lumo_level in result.xpath('./energy_level'):
            c.LUMO_level.append(
                LUMOLevel(
                    value=first(lumo_level.xpath('./energy_value/text()')),
                    units=first(lumo_level.xpath('./energy_level_units/text()'))
                )
            )
        if c.LUMO_level:
            yield c

#############################################################
###########   Photovoltaic Properties     ###################
#############################################################

##################### PCE, FF, Jsc, Voc

opv_range = (Optional(R('[\-–−]')) + (R('[\+\-–−]?\d+(\.\d+)?(\(\d\))?[\-––-−~∼˜]\d+(\.\d+)?(\(\d\))?') | (R('[\+\-–−]?\d+(\.\d+)?') + R('[\-–−]') + R('[\+\-–−]?\d+(\.\d+)?'))))('opv_value').add_action(merge)

opv_optional_deviation = (Optional(R('^[\-–−]$')) + R('^[\+\-–−]?\d+(\.\d+)?$') + Optional(W('±') + Optional(R('^\d+(\.\d+)?$'))))('opv_value').add_action(merge)

opv_value = (opv_range | opv_optional_deviation)('opv_value')

######## PCE

pce_units = R('%')('pce_units')

pce_with_units = (opv_value + Optional(lbrct) + pce_units + Optional(rbrct))('pce').add_action(merge)

pce_with_optional_units = (opv_value + Optional(pce_units))('pce')

pce_title = (R('PCE') | (I('power') + I('conversion') + I('efficiency')))

pce_heading = (pce_title.hide() + Optional(delims).hide() + Optional(lbrct) + pce_units + Optional(rbrct))('pce_heading')

pce_cell = (pce_with_optional_units + ZeroOrMore(delims.hide() + pce_with_optional_units))('pce_cell')

####### FF

ff_no_units = (opv_value)('ff')

ff_title = (R('FF') | (I('fill') + I('factor')))

ff_heading = (ff_title.hide() + Optional(delims).hide())('ff_heading')

ff_cell = (ff_no_units + ZeroOrMore(delims.hide() + ff_no_units))('ff_cell')

######## Voc

voc_units = (R('V') | R('mV'))('voc_units')

voc_with_units = (opv_value + Optional(lbrct) + voc_units + Optional(rbrct))('voc').add_action(merge)

voc_with_optional_units = (opv_value + Optional(voc_units))('voc')

voc_title = (R('Voc') | (I('open') + Optional(I('-')) + I('circuit') + I('voltage')))

voc_heading = (voc_title.hide() + Optional(delims).hide() + Optional(lbrct) + voc_units + Optional(rbrct))('voc_heading')

voc_cell = (voc_with_optional_units + ZeroOrMore(delims.hide() + voc_with_optional_units))('voc_cell')

######## Jsc

jsc_units = ((R('A') | R('mA')) + \
             (R('/') | R('per')) + \
             (R('cm2') | R('cm\^2')))('jsc_units').add_action(merge)

jsc_with_units = (opv_value + Optional(lbrct) + jsc_units + Optional(rbrct))('jsc').add_action(merge)

jsc_with_optional_units = (opv_value + Optional(jsc_units))('jsc')

jsc_title = (R('Jsc') | (I('short') + Optional(I('-')) + I('circuit') + I('current') + Optional(I('density'))))

jsc_heading = (jsc_title.hide() + Optional(delims).hide() + Optional(lbrct) + jsc_units + Optional(rbrct))('jsc_heading')

jsc_cell = (jsc_with_optional_units + ZeroOrMore(delims.hide() + jsc_with_optional_units))('jsc_cell')


class PCEHeadingParser(BaseParser):
    """"""
    root = pce_heading
            
    def interpret(self, result, start, end):
        """"""
            
        pce_units = first(result.xpath('./pce_units/text()'))
        c = Compound()
        if pce_units:
            c.pce.append(
                PCE(units=pce_units)
            )
        yield c


class PCECellParser(BaseParser):
    """"""
    root = pce_cell
    
    def interpret(self, result, start, end):
        """"""        
        c = Compound()
        for pce in result.xpath('./pce'):
            c.pce.append(
                PCE(
                    value=first(pce.xpath('./opv_value/text()')),
                    units=first(pce.xpath('./pce_units/text()'))
                )
            )
        if c.pce:
            yield c


class FFHeadingParser(BaseParser):
    """"""
    root = ff_heading
            
    def interpret(self, result, start, end):
        """
        unitless property
        """

        c = Compound()
        yield c


class FFCellParser(BaseParser):
    """"""
    root = ff_cell
    
    def interpret(self, result, start, end):
        """"""        
        c = Compound()        
        for ff in result.xpath('./ff'):
            c.ff.append(
                FF(
                    value=first(ff.xpath('./text()')),
                )
            )
        if c.ff:
            yield c
            
            
class VocHeadingParser(BaseParser):
    """"""
    root = voc_heading
            
    def interpret(self, result, start, end):
        """"""
            
        voc_units = first(result.xpath('./voc_units/text()'))
        c = Compound()
        if voc_units:
            c.voc.append(
                Voc(units=voc_units)
            )
        yield c


class VocCellParser(BaseParser):
    """"""
    root = voc_cell
    
    def interpret(self, result, start, end):
        """"""        
        c = Compound()
        for voc in result.xpath('./voc'):
            c.voc.append(
                Voc(
                    value=first(voc.xpath('./opv_value/text()')),
                    units=first(voc.xpath('./voc_units/text()'))
                )
            )
        if c.voc:
            yield c
            
            
class JscHeadingParser(BaseParser):
    """"""
    root = jsc_heading
            
    def interpret(self, result, start, end):
        """"""
            
        jsc_units = first(result.xpath('./jsc_units/text()'))
        c = Compound()
        if jsc_units:
            c.jsc.append(
                Jsc(units=jsc_units)
            )
        yield c


class JscCellParser(BaseParser):
    """"""
    root = jsc_cell
    
    def interpret(self, result, start, end):
        """"""        
        c = Compound()
        for jsc in result.xpath('./jsc'):
            c.jsc.append(
                Jsc(
                    value=first(jsc.xpath('./opv_value/text()')),
                    units=first(jsc.xpath('./jsc_units/text()'))
                )
            )
        if c.jsc:
            yield c
            
#############################################################
###########  Physical/Thermodynamic Properties  #############
#############################################################

# crystallinity, enthalpies, modulus
phys_range = (Optional(R('[\-–−]')) + (R('[\+\-–−]?\d+(\.\d+)?(\(\d\))?[\-––-−~∼˜]\d+(\.\d+)?(\(\d\))?') | (R('[\+\-–−]?\d+(\.\d+)?') + R('[\-–−]') + R('[\+\-–−]?\d+(\.\d+)?'))))('phys_value').add_action(merge)

phys_optional_deviation = (Optional(R('^[\-–−]$')) + R('^[\+\-–−]?\d+(\.\d+)?$') + Optional(W('±') + Optional(R('^\d+(\.\d+)?$'))))('phys_value').add_action(merge)

phys_value = (phys_range | phys_optional_deviation)('phys_value')

######## Crystallinity

xtal_units = (R('%'))('xtal_units')

xtal_with_units = (phys_value + Optional(lbrct) + xtal_units + Optional(rbrct))('xtal').add_action(merge)

xtal_with_optional_units = (phys_value + Optional(xtal_units))('xtal')

xtal_title = (I('Xc') | I('X_c') | I('Χ') | I('Χc') | I('Χ_c') | I('χ') | I('χc') | I('χ_c') | I('RDOC') | I('DOC') | \
              (Optional(I('relative')) + Optional(I('degree')) + Optional(I('of')) + I('crystallinity')))

xtal_heading = (xtal_title.hide() + Optional(delims).hide() + Optional(lbrct) + xtal_units + Optional(rbrct))('xtal_heading')

xtal_cell = (xtal_with_optional_units + ZeroOrMore(delims.hide() + xtal_with_optional_units))('xtal_cell')

######## (Young's) Modulus

modulus_units = (I('Pa') | I('kPa') | I('MPa') | I('GPa'))('modulus_units')

modulus_with_units = (phys_value + Optional(lbrct) + modulus_units + Optional(rbrct))('modulus').add_action(merge)

modulus_with_optional_units = (phys_value + Optional(modulus_units))('modulus')

modulus_title = (I('E') | I('modulus') | I("young's modulus") | I('elastic modulus'))

modulus_heading = (modulus_title.hide() + Optional(delims).hide() + Optional(lbrct) + modulus_units + Optional(rbrct))('modulus_heading')

modulus_cell = (modulus_with_optional_units + ZeroOrMore(delims.hide() + modulus_with_optional_units))('modulus_cell')

######## Enthalpy of...

enthalpy_units = ((I('kJ') | I('J') | I('mJ') | I('Cal') | I('kcal') | I('cal') | I('mcal')) + \
                  (R('/') | I('per')) + \
                  (R('kg') | I('g') | I('mg') | I('mol') | I('mmol')))('units').add_action(merge)

    ######## ...Fusion
fusion_with_units = (phys_value + Optional(lbrct) + enthalpy_units + Optional(rbrct))('fusion').add_action(merge)

fusion_with_optional_units = (phys_value + Optional(enthalpy_units))('fusion')

fusion_title = (I('ΔHf') | I('ΔHm') | I('ΔHc') | I('ΔH_f') | I('ΔH_m') | I('ΔH_c') | I('ΔHfus') | \
                I('ΔH_fus') | I('ΔHcrys') | I('ΔH_crys') | I('ΔHmelt') | I('ΔH_melt') | \
                ((I('enthalpy') | I('heat')) + I('of') + (I('fusion') | I('melting') | I('crystallization') | I('crystalization'))))

fusion_heading = (fusion_title.hide() + Optional(delims).hide() + Optional(lbrct) + enthalpy_units + Optional(rbrct))('fusion_heading')

fusion_cell = (fusion_with_optional_units + ZeroOrMore(delims.hide() + fusion_with_optional_units))('fusion_cell')

    ######## ...Sublimation
sublimation_with_units = (phys_value + Optional(lbrct) + enthalpy_units + Optional(rbrct))('sublimation').add_action(merge)

sublimation_with_optional_units = (phys_value + Optional(enthalpy_units))('sublimation')

sublimation_title = (I('ΔH') | I('ΔHs') | I('ΔH_s') | I('ΔHsub') | I('ΔH_sub') | \
                     ((I('enthalpy') | I('heat')) + I('of') + (I('sublimation'))))

sublimation_heading = (sublimation_title.hide() + Optional(delims).hide() + Optional(lbrct) + enthalpy_units + Optional(rbrct))('sublimation_heading')

sublimation_cell = (sublimation_with_optional_units + ZeroOrMore(delims.hide() + sublimation_with_optional_units))('sublimation_cell')

    ######## ...Vaporization
vaporization_with_units = (phys_value + Optional(lbrct) + enthalpy_units + Optional(rbrct))('vaporization').add_action(merge)

vaporization_with_optional_units = (phys_value + Optional(enthalpy_units))('vaporization')

vaporization_title = (I('ΔHv') | I('ΔHe') | I('ΔH_v') | I('ΔH_e') | I('ΔHvap') | I('ΔH_vap') | \
                     I('ΔHevap') | I('ΔH_evap') | \
                     ((I('enthalpy') | I('heat')) + I('of') + (I('vaporization') | I('evaporation'))))

vaporization_heading = (vaporization_title.hide() + Optional(delims).hide() + Optional(lbrct) + enthalpy_units + Optional(rbrct))('vaporization_heading')

vaporization_cell = (vaporization_with_optional_units + ZeroOrMore(delims.hide() + vaporization_with_optional_units))('vaporization_cell')


class CrystallinityHeadingParser(BaseParser):
    """"""
    root = xtal_heading
            
    def interpret(self, result, start, end):
        """"""
            
        xtal_units = first(result.xpath('./xtal_units/text()'))
        c = Compound()
        if xtal_units:
            c.crystallinity.append(
                Crystallinity(units=xtal_units)
            )
        yield c


class CrystallinityCellParser(BaseParser):
    """"""
    root = xtal_cell
    
    def interpret(self, result, start, end):
        """"""        
        c = Compound()
        for xtal in result.xpath('./xtal'):
            c.crystallinity.append(
                Crystallinity(
                    value=first(xtal.xpath('./phys_value/text()')),
                    units=first(xtal.xpath('./xtal_units/text()'))
                )
            )
        if c.crystallinity:
            yield c
            
            
class ModulusHeadingParser(BaseParser):
    """"""
    root = modulus_heading
            
    def interpret(self, result, start, end):
        """"""
            
        modulus_units = first(result.xpath('./modulus_units/text()'))
        c = Compound()
        if modulus_units:
            c.modulus.append(
                Modulus(units=modulus_units)
            )
        yield c


class ModulusCellParser(BaseParser):
    """"""
    root = modulus_cell
    
    def interpret(self, result, start, end):
        """"""        
        c = Compound()
        for modulus in result.xpath('./modulus'):
            c.modulus.append(
                Modulus(
                    value=first(modulus.xpath('./phys_value/text()')),
                    units=first(modulus.xpath('./modulus_units/text()'))
                )
            )
        if c.modulus:
            yield c
            
            
class FusionEnthalpyHeadingParser(BaseParser):
    """"""
    root = fusion_heading
            
    def interpret(self, result, start, end):
        """"""
            
        fusion_units = first(result.xpath('./enthalpy_units/text()'))
        c = Compound()
        if fusion_units:
            c.enthalpy_of_fusion.append(
                FusionEnthalpy(units=fusion_units)
            )
        yield c


class FusionEnthalpyCellParser(BaseParser):
    """"""
    root = fusion_cell
    
    def interpret(self, result, start, end):
        """"""        
        c = Compound()
        for fusion in result.xpath('./fusion'):
            c.enthalpy_of_fusion.append(
                FusionEnthalpy(
                    value=first(fusion.xpath('./phys_value/text()')),
                    units=first(fusion.xpath('./enthaply_units/text()'))
                )
            )
        if c.enthalpy_of_fusion:
            yield c
            
            
class SublimationEnthalpyHeadingParser(BaseParser):
    """"""
    root = sublimation_heading
            
    def interpret(self, result, start, end):
        """"""
            
        sublimation_units = first(result.xpath('./enthalpy_units/text()'))
        c = Compound()
        if sublimation_units:
            c.enthalpy_of_sublimation.append(
                SublimationEnthalpy(units=sublimation_units)
            )
        yield c


class SublimationEnthalpyCellParser(BaseParser):
    """"""
    root = sublimation_cell
    
    def interpret(self, result, start, end):
        """"""        
        c = Compound()
        for sublimation in result.xpath('./sublimation'):
            c.enthalpy_of_sublimation.append(
                SublimationEnthalpy(
                    value=first(sublimation.xpath('./phys_value/text()')),
                    units=first(sublimation.xpath('./enthaply_units/text()'))
                )
            )
        if c.enthalpy_of_sublimation:
            yield c
            
            
class VaporizationEnthalpyHeadingParser(BaseParser):
    """"""
    root = vaporization_heading
            
    def interpret(self, result, start, end):
        """"""
            
        vaporization_units = first(result.xpath('./enthalpy_units/text()'))
        c = Compound()
        if vaporization_units:
            c.enthalpy_of_vaporization.append(
                VaporizationEnthalpy(units=vaporization_units)
            )
        yield c


class VaporizationEnthalpyCellParser(BaseParser):
    """"""
    root = vaporization_cell
    
    def interpret(self, result, start, end):
        """"""        
        c = Compound()
        for vaporization in result.xpath('./vaporization'):
            c.enthalpy_of_vaporization.append(
                VaporizationEnthalpy(
                    value=first(vaporization.xpath('./phys_value/text()')),
                    units=first(vaporization.xpath('./enthaply_units/text()'))
                )
            )
        if c.enthalpy_of_vaporization:
            yield c


#############################################################
#################    Polymer Properties   ###################
#############################################################

# Dispersity, Mn, Mw

weight_range = (Optional(R('[\-–−]')) + (R('[\+\-–−]?\d+(\.\d+)?(\(\d\))?[\-––-−~∼˜]\d+(\.\d+)?(\(\d\))?') | (R('[\+\-–−]?\d+(\.\d+)?') + R('[\-–−]') + R('[\+\-–−]?\d+(\.\d+)?'))))('weight_value').add_action(merge)

weight_optional_deviation = (Optional(R('^[\-–−]$')) + R('^[\+\-–−]?\d+(\.\d+)?$') + Optional(W('±') + Optional(R('^\d+(\.\d+)?$'))))('weight_value').add_action(merge)

weight_value = (weight_range | weight_optional_deviation)('weight_value')

######## Mn

mn_units = ((I('kDa') | I('Da')) | \
            ((I('g') | I('kg')) + (R('/') | I('per')) + R('mol')) | \
            (I('gmol-1') | I('kgmol-1') | I('g•mol-1') | I('kg•mol-1')))('mn_units').add_action(merge)

mn_with_units = (weight_value + Optional(lbrct) + mn_units + Optional(rbrct))('mn').add_action(merge)

mn_with_optional_units = (weight_value + Optional(mn_units))('mn')

mn_title = (R('Mn') | (Optional(I('number average')) + I('molecular') + I('weight')))

mn_heading = (mn_title.hide() + Optional(delims).hide() + Optional(lbrct) + mn_units + Optional(rbrct))('mn_heading')

mn_cell = (mn_with_optional_units + ZeroOrMore(delims.hide() + mn_with_optional_units))('mn_cell')

######## Mw

mw_units = ((I('kDa') | I('Da')) | \
            ((I('g') | I('kg')) + (R('/') | I('per')) + R('mol')) | \
            (I('gmol-1') | I('kgmol-1') | I('g•mol-1') | I('kg•mol-1')))('mw_units').add_action(merge)

mw_with_units = (weight_value + Optional(lbrct) + mw_units + Optional(rbrct))('mw').add_action(merge)

mw_with_optional_units = (weight_value + Optional(mw_units))('mw')

mw_title = (R('Mw') | (Optional(I('weight average')) + I('molecular') + I('weight')))

mw_heading = (mw_title.hide() + Optional(delims).hide() + Optional(lbrct) + mw_units + Optional(rbrct))('mw_heading')

mw_cell = (mw_with_optional_units + ZeroOrMore(delims.hide() + mw_with_optional_units))('mw_cell')

######## Dispersity

dispersity_no_units = (weight_value)('dispersity')

dispersity_title = (R('Dispersity') | I('Polydispersity index') | I('PDI') | I('Đ') | I('Đm'))

dispersity_heading = (dispersity_title.hide() + Optional(delims).hide())('dispersity_heading')

dispersity_cell = (dispersity_no_units + ZeroOrMore(delims.hide() + dispersity_no_units))('dispersity_cell')

class MnHeadingParser(BaseParser):
    """"""
    root = mn_heading
            
    def interpret(self, result, start, end):
        """"""
            
        mn_units = first(result.xpath('./mn_units/text()'))
        c = Compound()
        if mn_units:
            c.M_n.append(
                NumAvgMolecularWeight(units=mn_units)
            )
        yield c


class MnCellParser(BaseParser):
    """"""
    root = mn_cell
    
    def interpret(self, result, start, end):
        """"""        
        c = Compound()
        for mn in result.xpath('./mn'):
            c.M_n.append(
                NumAvgMolecularWeight(
                    value=first(mn.xpath('./weight_value/text()')),
                    units=first(mn.xpath('./mn_units/text()'))
                )
            )
        if c.M_n:
            yield c
            

class MwHeadingParser(BaseParser):
    """"""
    root = mw_heading
            
    def interpret(self, result, start, end):
        """"""
            
        mw_units = first(result.xpath('./mw_units/text()'))
        c = Compound()
        if mw_units:
            c.M_w.append(
                WeightAvgMolecularWeight(units=mw_units)
            )
        yield c


class MwCellParser(BaseParser):
    """"""
    root = mw_cell
    
    def interpret(self, result, start, end):
        """"""        
        c = Compound()
        for mw in result.xpath('./mw'):
            c.M_w.append(
                WeightAvgMolecularWeight(
                    value=first(mw.xpath('./weight_value/text()')),
                    units=first(mw.xpath('./mw_units/text()'))
                )
            )
        if c.M_w:
            yield c
            
            
class DispersityHeadingParser(BaseParser):
    """"""
    root = dispersity_heading
            
    def interpret(self, result, start, end):
        """
        unitless property
        """

        c = Compound()
        yield c


class DispersityCellParser(BaseParser):
    """"""
    root = dispersity_cell
    
    def interpret(self, result, start, end):
        """"""        
        c = Compound()        
        for dispersity in result.xpath('./dispersity'):
            c.dispersity.append(
                Dispersity(
                    value=first(dispersity.xpath('./text()')),
                )
            )
        if c.dispersity:
            yield c

#############################################################
###############    Performance Properties   #################
#############################################################

############## Corrosion Inhibition
corro_range = (Optional(R('[\-–−]')) + (R('[\+\-–−]?\d+(\.\d+)?(\(\d\))?[\-––-−~∼˜]\d+(\.\d+)?(\(\d\))?') | (R('[\+\-–−]?\d+(\.\d+)?') + R('[\-–−]') + R('[\+\-–−]?\d+(\.\d+)?'))))('corro_value').add_action(merge)

corro_optional_deviation = (Optional(R('^[\-–−]$')) + R('^[\+\-–−]?\d+(\.\d+)?$') + Optional(W('±') + Optional(R('^\d+(\.\d+)?$'))))('corro_value').add_action(merge)

corro_value = (corro_range | corro_optional_deviation)('corro_value')

corro_units = (I('%'))('corro_units')

corro_with_units = (corro_value + Optional(lbrct) + corro_units + Optional(rbrct))('corro').add_action(merge)

corro_with_optional_units = (corro_value + Optional(corro_units))('corro')

corro_title = (I('η') | I('CI') | I('CIE') | (Optional(I('corrosion')) + (I('inhibition') | I('ihibitor')) + Optional(I('efficiency'))))

corro_heading = (corro_title.hide() + Optional(delims).hide() + Optional(lbrct) + corro_units + Optional(rbrct))('corro_heading')

corro_cell = (corro_with_optional_units + ZeroOrMore(delims.hide() + corro_with_optional_units))('corro_cell')


class CorrosionInhibitionHeadingParser(BaseParser):
    """"""
    root = corro_heading
            
    def interpret(self, result, start, end):
        """"""
            
        corro_units = first(result.xpath('./corro_units/text()'))
        c = Compound()
        if corro_units:
            c.corrosion_inhibition.append(
                CorrosionInhibition(units=corro_units)
            )
        yield c


class CorrosionInhibitionCellParser(BaseParser):
    """"""
    root = corro_cell
    
    def interpret(self, result, start, end):
        """"""        
        c = Compound()
        for corro in result.xpath('./corro'):
            c.corrosion_inhibition.append(
                CorrosionInhibition(
                    value=first(corro.xpath('./corro_value/text()')),
                    units=first(corro.xpath('./corro_units/text()'))
                )
            )
        if c.corrosion_inhibition:
            yield c
            
####################################################################
####################################################################


class CompoundHeadingParser(BaseParser):
    """"""
    root = compound_heading

    def interpret(self, result, start, end):
        """"""
        yield Compound()


class SolventHeadingParser(BaseParser):
    """"""
    root = solvent_heading

    def interpret(self, result, start, end):
        """"""
        yield Compound()


class UvvisAbsDisallowedHeadingParser(BaseParser):
    """"""
    root = uvvis_abs_disallowed

    def interpret(self, result, start, end):
        """"""
        yield Compound()


class SolventInHeadingParser(BaseParser):
    """"""
    root = solvent_in_heading

    def interpret(self, result, start, end):
        """"""
        c = Compound()
        solvent = first(result.xpath('./name/text()'))
        if solvent is not None:
            context = {'solvent': solvent}
            c.melting_points = [MeltingPoint(**context)]
            c.glass_transitions = [GlassTransition(**context)]
            c.quantum_yields = [QuantumYield(**context)]
            c.fluorescence_lifetimes = [FluorescenceLifetime(**context)]
            c.electrochemical_potentials = [ElectrochemicalPotential(**context)]
            c.uvvis_spectra = [UvvisSpectrum(**context)]
            c.band_gap = [BandGap(**context)]
        if c.serialize():
            yield c


class TempInHeadingParser(BaseParser):
    """"""
    root = temp_with_units

    def interpret(self, result, start, end):
        """"""
        c = Compound()
        context = {
            'temperature': first(result.xpath('./value/text()')),
            'temperature_units': first(result.xpath('./units/text()'))
        }
        c.quantum_yields = [QuantumYield(**context)]
        c.fluorescence_lifetimes = [FluorescenceLifetime(**context)]
        c.electrochemical_potentials = [ElectrochemicalPotential(**context)]
        c.uvvis_spectra = [UvvisSpectrum(**context)]
        yield c


class SolventCellParser(BaseParser):
    """"""
    root = solvent_cell

    def interpret(self, result, start, end):
        """"""
        c = Compound()
        solvent = first(result.xpath('./name/text()'))
        if solvent is not None:
            context = {'solvent': solvent}
            c.melting_points = [MeltingPoint(**context)]
            c.glass_transitions = [GlassTransition(**context)]
            c.quantum_yields = [QuantumYield(**context)]
            c.fluorescence_lifetimes = [FluorescenceLifetime(**context)]
            c.electrochemical_potentials = [ElectrochemicalPotential(**context)]
            c.uvvis_spectra = [UvvisSpectrum(**context)]
            c.band_gap = [BandGap(**context)]
        if c.serialize():
            yield c


class CompoundCellParser(BaseParser):
    """"""
    root = compound_cell

    def interpret(self, result, start, end):
        for cem_el in result.xpath('./cem'):
            c = Compound(
                names=cem_el.xpath('./name/text()'),
                labels=cem_el.xpath('./label/text()')
            )
            yield c


class UvvisEmiHeadingParser(BaseParser):
    """"""
    root = uvvis_emi_heading

    def interpret(self, result, start, end):
        """"""
        uvvis_units = first(result.xpath('./uvvis_units/text()'))
        c = Compound()
        # TODO: Emission peaks
        yield c


class UvvisAbsHeadingParser(BaseParser):
    """"""
    root = uvvis_abs_heading

    def interpret(self, result, start, end):
        """"""
        uvvis_units = first(result.xpath('./uvvis_units/text()'))
        extinction_units = first(result.xpath('./extinction_units/text()'))
        c = Compound()
        if uvvis_units or extinction_units:
            c.uvvis_spectra.append(
                UvvisSpectrum(peaks=[UvvisPeak(units=uvvis_units, extinction_units=extinction_units)])
            )
        yield c


class ExtinctionHeadingParser(BaseParser):
    """"""
    root = extinction_heading

    def interpret(self, result, start, end):
        """"""
        extinction_units = first(result.xpath('./extinction_units/text()'))
        c = Compound()
        if extinction_units:
            c.uvvis_spectra.append(
                UvvisSpectrum(peaks=[UvvisPeak(extinction_units=extinction_units)])
            )
        yield c


class IrHeadingParser(BaseParser):
    """"""
    root = ir_heading

    def interpret(self, result, start, end):
        """"""
        ir_units = first(result.xpath('./ir_units/text()'))
        c = Compound()
        if ir_units:
            c.ir_spectra.append(
                IrSpectrum(peaks=[IrPeak(units=ir_units)])
            )
        yield c


class IrCellParser(BaseParser):
    """"""
    root = ir_cell

    def interpret(self, result, start, end):
        """"""
        c = Compound()
        ir = IrSpectrum()
        for peak in result.xpath('./ir_peak'):
            ir.peaks.append(
                IrPeak(
                    value=first(peak.xpath('./value/text()')),
                    strength=first(peak.xpath('./strength/text()'))
                )
            )
        if ir.peaks:
            c.ir_spectra.append(ir)
            yield c


class QuantumYieldHeadingParser(BaseParser):
    """"""
    root = quantum_yield_heading

    def interpret(self, result, start, end):
        """"""
        c = Compound(
            quantum_yields=[
                QuantumYield(
                    type=first(result.xpath('./quantum_yield_type/text()')),
                    units=first(result.xpath('./quantum_yield_units/text()'))
                )
            ]
        )
        yield c


class QuantumYieldCellParser(BaseParser):
    """"""
    root = quantum_yield_cell

    def interpret(self, result, start, end):
        """"""
        c = Compound()
        qy = QuantumYield(
            value=first(result.xpath('./quantum_yield_value/text()')),
            units=first(result.xpath('./quantum_yield_units/text()'))
        )
        if qy.value:
            c.quantum_yields.append(qy)
            yield c


class UvvisEmiCellParser(BaseParser):
    """"""
    root = uvvis_emi_cell

    def interpret(self, result, start, end):
        """"""
        # TODO: Emission peaks
        return
        yield


class UvvisAbsCellParser(BaseParser):
    """"""
    root = uvvis_abs_cell

    def interpret(self, result, start, end):
        """"""
        c = Compound()
        uvvis = UvvisSpectrum()
        for peak in result.xpath('./uvvis_abs_peak'):
            uvvis.peaks.append(
                UvvisPeak(
                    value=first(peak.xpath('./value/text()')),
                    extinction=first(peak.xpath('./extinction/text()')),
                    shape=first(peak.xpath('./shape/text()'))
                )
            )
        if uvvis.peaks:
            c.uvvis_spectra.append(uvvis)
            yield c


class ExtinctionCellParser(BaseParser):
    """"""
    root = extinction_cell

    def interpret(self, result, start, end):
        """"""
        c = Compound()
        uvvis = UvvisSpectrum()
        for value in result.xpath('./extinction/text()'):
            uvvis.peaks.append(
                UvvisPeak(
                    extinction=value,
                )
            )
        if uvvis.peaks:
            c.uvvis_spectra.append(uvvis)
            yield c


class UvvisAbsEmiQuantumYieldHeadingParser(BaseParser):
    """"""
    root = uvvis_abs_emi_quantum_yield_heading

    def interpret(self, result, start, end):
        """"""
        c = Compound()
        abs_units = first(result.xpath('./uvvis_abs_units/text()'))
        if abs_units:
            c.uvvis_spectra.append(
                UvvisSpectrum(peaks=[UvvisPeak(units=abs_units)])
            )
        qy_units = first(result.xpath('./quantum_yield_units/text()'))
        if qy_units:
            c.quantum_yields.append(
                QuantumYield(units=qy_units)
            )

        yield c


class UvvisAbsEmiQuantumYieldCellParser(BaseParser):
    """"""
    root = uvvis_abs_emi_quantum_yield_cell

    def interpret(self, result, start, end):
        """"""
        c = Compound()
        uvvis = UvvisSpectrum()
        for value in result.xpath('./uvvis_abs_value/text()'):
            uvvis.peaks.append(
                UvvisPeak(
                    value=value,
                )
            )
        if uvvis.peaks:
            c.uvvis_spectra.append(uvvis)
        qy = QuantumYield(
            value=first(result.xpath('./quantum_yield_value/text()'))
        )
        if qy.value:
            c.quantum_yields.append(qy)

        if c.quantum_yields or c.uvvis_spectra:
            yield c


class UvvisEmiQuantumYieldHeadingParser(BaseParser):
    """"""
    root = uvvis_emi_quantum_yield_heading

    def interpret(self, result, start, end):
        """"""
        # Yield an empty compound to signal that the Parser matched
        yield Compound()


class UvvisEmiQuantumYieldCellParser(BaseParser):
    """"""
    root = uvvis_emi_quantum_yield_cell

    def interpret(self, result, start, end):
        """"""
        c = Compound()
        qy = QuantumYield(
            value=first(result.xpath('./quantum_yield_value/text()'))
        )
        if qy.value:
            c.quantum_yields.append(qy)
            yield c


class FluorescenceLifetimeHeadingParser(BaseParser):
    """"""
    root = fluorescence_lifetime_heading

    def interpret(self, result, start, end):
        """"""
        fluorescence_lifetime_units = first(result.xpath('./fluorescence_lifetime_units/text()'))
        c = Compound()
        if fluorescence_lifetime_units:
            c.fluorescence_lifetimes.append(
                FluorescenceLifetime(units=fluorescence_lifetime_units)
            )
        yield c


class FluorescenceLifetimeCellParser(BaseParser):
    """"""
    root = fluorescence_lifetime_cell

    def interpret(self, result, start, end):
        """"""
        c = Compound()
        fl = FluorescenceLifetime(
            value=first(result.xpath('./fluorescence_lifetime_value/text()'))
        )
        if fl.value:
            c.fluorescence_lifetimes.append(fl)
            yield c


class MeltingPointHeadingParser(BaseParser):
    """"""
    root = melting_point_heading

    def interpret(self, result, start, end):
        """"""
        melting_point_units = first(result.xpath('./units/text()'))
        c = Compound()
        if melting_point_units:
            c.melting_points.append(
                MeltingPoint(units=melting_point_units)
            )
        yield c


class MeltingPointCellParser(BaseParser):
    """"""
    root = melting_point_cell

    def interpret(self, result, start, end):
        """"""
        c = Compound()
        for mp in result.xpath('./temp'):
            c.melting_points.append(
                MeltingPoint(
                    value=first(mp.xpath('./value/text()')),
                    units=first(mp.xpath('./units/text()'))
                )
            )
        if c.melting_points:
            yield c


class GlassTransitionHeadingParser(BaseParser):
    """"""
    root = glass_transition_heading
    
    def interpret(self, result, start, end):
        """"""
        glass_transition_units = first(result.xpath('./units/text()'))
        c = Compound()
        if glass_transition_units:
            c.glass_transitions.append(
                GlassTransition(units=glass_transition_units)
            )
        yield c

class GlassTransitionCellParser(BaseParser):
    """"""
    root = glass_transition_cell

    def interpret(self, result, start, end):
        """"""
        c = Compound()
        for tg in result.xpath('./temp'):
            c.glass_transitions.append(
                GlassTransition(
                    value=first(tg.xpath('./value/text()')),
                    units=first(tg.xpath('./units/text()'))
                )
            )
        if c.glass_transitions:
            yield c
            
            
class BoilingPointHeadingParser(BaseParser):
    """"""
    root = boiling_point_heading

    def interpret(self, result, start, end):
        """"""
#         print(etree.tostring(result))
        boiling_point_units = first(result.xpath('./units/text()'))
        c = Compound()
        if boiling_point_units:
            c.boiling_point.append(
                BoilingPoint(units=boiling_point_units)
            )
        yield c


class BoilingPointCellParser(BaseParser):
    """"""
    root = boiling_point_cell

    def interpret(self, result, start, end):
        """"""
        c = Compound()
        for boil in result.xpath('./temp'):
            c.boiling_point.append(
                BoilingPoint(
                    value=first(boil.xpath('./value/text()')),
                    units=first(boil.xpath('./units/text()'))
                )
            )
        if c.boiling_point:
            yield c
            

class ElectrochemicalPotentialHeadingParser(BaseParser):
    """"""
    root = electrochemical_potential_heading

    def interpret(self, result, start, end):
        """"""
        c = Compound(
            electrochemical_potentials=[
                ElectrochemicalPotential(
                    type=first(result.xpath('./electrochemical_potential_type/text()')),
                    units=first(result.xpath('./electrochemical_potential_units/text()'))
                )
            ]
        )
        yield c


class ElectrochemicalPotentialCellParser(BaseParser):
    """"""
    root = electrochemical_potential_cell

    def interpret(self, result, start, end):
        """"""
        c = Compound()
        for value in result.xpath('./electrochemical_potential_value/text()'):
            c.electrochemical_potentials.append(
                ElectrochemicalPotential(
                    value=value
                )
            )
        if c.electrochemical_potentials:
            yield c


class CaptionContextParser(BaseParser):
    """"""
    root = caption_context

    def __init__(self):
        pass

    def interpret(self, result, start, end):
        name = first(result.xpath('./subject_phrase/name/text()'))
        c = Compound(names=[name]) if name else Compound()
        context = {}
        
        # print(etree.tostring(result[0]))
        solvent = first(result.xpath('./solvent_phrase/name/text()'))
        if solvent is not None:
            context['solvent'] = solvent
            
        # Melting point shouldn't have contextual temperature
        if context:
            c.melting_points = [MeltingPoint(**context)]
            
        temp = first(result.xpath('./temp_phrase'))
        if temp is not None:
            context['temperature'] = first(temp.xpath('./temp/value/text()'))
            context['temperature_units'] = first(temp.xpath('./temp/units/text()'))
            
        # Glass transition temperature shouldn't have contextual temperature
        if context:
            c.glass_transitions = [GlassTransition(**context)]
            
        temp = first(result.xpath('./temp_phrase'))
        if temp is not None:
            context['temperature'] = first(temp.xpath('./temp/value/text()'))
            context['temperature_units'] = first(temp.xpath('./temp/units/text()'))
            
        if context:
            c.quantum_yields = [QuantumYield(**context)]
            c.fluorescence_lifetimes = [FluorescenceLifetime(**context)]
            c.electrochemical_potentials = [ElectrochemicalPotential(**context)]
            c.uvvis_spectra = [UvvisSpectrum(**context)]
            c.band_gap = [BandGap(**context)]
            
        if c.serialize():
            # print(c.to_primitive())
            yield c
            

            
            