# -*- coding: utf-8 -*-
"""
chemdataextractor.parse.tg
~~~~~~~~~~~~~~~~~~~~~~~~~~

LUMO energy level parser.

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
from ..model import Compound, LUMOLevel
from .actions import merge, join
from .base import BaseParser
from .elements import W, I, R, Optional, Any, OneOrMore, Not, ZeroOrMore

log = logging.getLogger(__name__)

lumo_specifier = (I('^LUMO$') | (Optional(lbrct) + (I('ELUMO') | I('E_LUMO')) + Optional(rbrct)) | (I('LUMO') + Optional(I('energy')) + Optional(I('level'))))('lumo').add_action(merge)

#keyword matching for phrases that trigger value scraping
prefix = (Optional(Optional('has') + Optional(I('a') | I('an')))).hide() + \
         (Optional(I('the'))).hide() + \
         lumo_specifier + \
         (Optional(I('of') | I('=') | I('equal to') | I('is') | I('is equal to'))).hide() + \
         (Optional(I('in') + I('the') + I('range') + Optional(I('of')) | I('about') | ('around') | I('ca') | I('ca.'))).hide()

#generic list of delimiters
delim = R('^[:;\.,]$')

#Regex to match units of property
units = (R('eV'))('units')

#Regex to match ranges of values or single values (with or without spaces)
joined_range = R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?[\-––-−~∼˜]\d+(\.\d+)?(\(\d\))?$')('value').add_action(merge)

spaced_range = (R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') + Optional(units).hide() +(R('^[\-±–−~∼˜]$') + R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') | R('^[\+\-–−]\d+(\.\d+)?(\(\d\))?$')))('value').add_action(merge)

to_range = (R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') + Optional(units).hide() + (I('to') + R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') | R('^[\+\-–−]\d+(\.\d+)?(\(\d\))?$')))('value').add_action(join)

#ranged instances
lumo_range = (Optional(R('^[\-–−]$')) + (joined_range | spaced_range | to_range))('value').add_action(merge)

#value instances
lumo_value = (Optional(R('^[~∼˜\<\>\≤\≥]$')) + Optional(R('^[\-\–\–\−±∓⨤⨦±]$')) + R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$'))('value').add_action(merge)

#regex or matching the reporting of a lumo energy
energy = Optional(lbrct).hide() + (lumo_range | lumo_value)('value') + Optional(rbrct).hide()

#all lumo instances
lumo = (prefix + Optional(delim).hide() + energy + units)('lumo')

#phrases that list lumo level in parentheses or brackets
bracket_any = lbrct + OneOrMore(Not(lumo) + Not(rbrct) + Any()) + rbrct

#phrases that list an entity having a given lumo level
cem_lumo_phrase = (Optional(cem) + Optional(I('having')).hide() + Optional(delim).hide() + Optional(bracket_any).hide() + Optional(delim).hide() + Optional(lbrct) + lumo + Optional(rbrct))('lumo_phrase')

#phrases that culminate in a lumo level after experimental augmentation
to_give_lumo_phrase = ((I('to') + (I('give') | I('afford') | I('yield') | I('obtain')) | I('affording') | I('afforded') | I('gave') | I('yielded')).hide() + Optional(dt).hide() + (cem | chemical_label | lenient_chemical_label) + ZeroOrMore(Not(lumo) + Not(cem) + Any()).hide() + lumo)('lumo_phrase')

#other phrases where experimental changes lead to a lumo level
obtained_lumo_phrase = ((cem | chemical_label) + (I('is') | I('are') | I('was')).hide() + (I('afforded') | I('obtained') | I('yielded')).hide() + ZeroOrMore(Not(lumo) + Not(cem) + Any()).hide() + lumo)('lumo')

#final, cumulative phrase pattern matching
lumo_phrase = cem_lumo_phrase | to_give_lumo_phrase | obtained_lumo_phrase


class LUMOParser(BaseParser):
    """
    
    """
    root = lumo_phrase

    def interpret(self, result, start, end):
        compound = Compound(
            LUMO_level=[
                LUMOLevel(
                    value=first(result.xpath('./lumo/value/text()')),
                    units=first(result.xpath('./lumo/units/text()'))
                )
            ]
        )
        cem_el = first(result.xpath('./cem'))
        if cem_el is not None:
            compound.names = cem_el.xpath('./name/text()')
            compound.labels = cem_el.xpath('./label/text()')
        yield compound


