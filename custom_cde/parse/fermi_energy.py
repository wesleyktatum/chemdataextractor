# -*- coding: utf-8 -*-
"""
chemdataextractor.parse.fermi_energy
~~~~~~~~~~~~~~~~~~~~~~~~~~

Fermi energy level parser.

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
import logging
import re

from .cem import cem, chemical_label, lenient_chemical_label, solvent_name
from .common import lbrct, dt, rbrct, hyphen
from ..utils import first
from ..model import Compound, FermiEnergy
from .actions import merge, join
from .base import BaseParser
from .elements import W, I, R, Optional, Any, OneOrMore, Not, ZeroOrMore

log = logging.getLogger(__name__)

fermi_energy_specifier = (I('^Fermi Energy$') | (I('Fermi') + Optional(I('energy')) + Optional(I('level'))) | (Optional(lbrct) + (I('EF') | I('Ef') | I('E_f') | I('EFermi')) + Optional(rbrct)))('fermi_energy').add_action(join)

#keyword matching for phrases that trigger value scraping
prefix = (Optional(Optional('has') + Optional(I('a') | I('an')))).hide() + \
         (Optional(I('the'))).hide() + \
         fermi_energy_specifier + \
         (Optional(I('of') | I('=') | I('equal to') | (I('is') + Optional(I('between'))) | I('is equal to')) | I('was found to be')).hide() + \
         (Optional(I('in') + I('the') + I('range') + Optional(I('of')) | I('about') | ('around') | I('ca') | I('ca.'))).hide()

#generic list of delimiters
delim = R('^[:;\.,]$')

#Regex to match units of property
units = (R('eV'))('units')

#Regex to match ranges of values or single values (with or without spaces)
joined_range = R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?[\-––-−~∼˜]\d+(\.\d+)?(\(\d\))?$')('value').add_action(merge)

spaced_range = (R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') + Optional(units).hide() +(R('^[\-±–−~∼˜]$') + R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') | R('^[\+\-–−]\d+(\.\d+)?(\(\d\))?$')))('value').add_action(merge)

to_range = (R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') + Optional(units).hide() + ((I('to') | I('and')) + R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') | R('^[\+\-–−]\d+(\.\d+)?(\(\d\))?$')))('value').add_action(join)

#ranged instances
fermi_energy_range = (Optional(R('^[\-–−]$')) + (joined_range | spaced_range | to_range))('value').add_action(merge)

#value instances
fermi_energy_value = (Optional(R('^[~∼˜\<\>\≤\≥]$')) + Optional(R('^[\-\–\–\−±∓⨤⨦±]$')) + R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$'))('value').add_action(merge)

#regex or matching the reporting of a Fermi energy
energy = Optional(lbrct).hide() + (fermi_energy_range | fermi_energy_value)('value') + Optional(rbrct).hide()

#all fermi_energy instances
fermi_energy = (prefix + Optional(delim).hide() + energy + units)('fermi_energy')

#phrases that list fermi_energy level in parentheses or brackets
bracket_any = lbrct + OneOrMore(Not(fermi_energy) + Not(rbrct) + Any()) + rbrct

#phrases that list an entity having a given fermi_energy level
cem_fermi_energy_phrase = (Optional(cem) + Optional(I('having')).hide() + Optional(delim).hide() + Optional(bracket_any).hide() + Optional(delim).hide() + Optional(lbrct) + fermi_energy + Optional(rbrct))('fermi_energy_phrase')

#phrases that culminate in a fermi_energy level after experimental augmentation
to_give_fermi_energy_phrase = ((I('to') + (I('give') | I('afford') | I('yield') | I('obtain')) | I('affording') | I('afforded') | I('gave') | I('yielded')).hide() + Optional(dt).hide() + (cem | chemical_label | lenient_chemical_label) + ZeroOrMore(Not(fermi_energy) + Not(cem) + Any()).hide() + fermi_energy)('fermi_energy_phrase')

#other phrases where experimental changes lead to a fermi energy level
obtained_fermi_energy_phrase = ((cem | chemical_label) + (I('is') | I('are') | I('was')).hide() + (I('afforded') | I('obtained') | I('yielded')).hide() + ZeroOrMore(Not(fermi_energy) + Not(cem) + Any()).hide() + fermi_energy)('fermi_energy')

#final, cumulative phrase pattern matching
fermi_energy_phrase = cem_fermi_energy_phrase | to_give_fermi_energy_phrase | obtained_fermi_energy_phrase


class FermiEnergyParser(BaseParser):
    """
    
    """
    root = fermi_energy_phrase

    def interpret(self, result, start, end):
        compound = Compound(
            fermi_energy=[
                FermiEnergy(
                    value=first(result.xpath('./fermi_energy/value/text()')),
                    units=first(result.xpath('./fermi_energy/units/text()'))
                )
            ]
        )
        cem_el = first(result.xpath('./cem'))
        if cem_el is not None:
            compound.names = cem_el.xpath('./name/text()')
            compound.labels = cem_el.xpath('./label/text()')
        yield compound


