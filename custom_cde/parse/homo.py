# -*- coding: utf-8 -*-
"""
chemdataextractor.parse.tg
~~~~~~~~~~~~~~~~~~~~~~~~~~

HOMO energy level parser.

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
from ..model import Compound, HOMOLevel
from .actions import merge, join, fix_whitespace
from .base import BaseParser
from .elements import W, I, R, Optional, Any, OneOrMore, Not, ZeroOrMore

log = logging.getLogger(__name__)

homo_specifier = (I('^HOMO$') | (Optional(lbrct) + (I('EHOMO') | I('E_HOMO')) + Optional(rbrct)) | (I('HOMO') + Optional(I('energy')) + Optional(I('level'))))('homo').add_action(merge)

#keyword matching for phrases that trigger value scraping
prefix = (Optional(Optional('has') + Optional(I('a') | I('an')))).hide() + \
         (Optional(I('the'))).hide() + \
         homo_specifier + \
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
homo_range = (Optional(R('^[\-–−]$')) + (joined_range | spaced_range | to_range))('value').add_action(merge)

#value instances
homo_value = (Optional(R('^[~∼˜\<\>\≤\≥]$')) + Optional(R('^[\-\–\–\−±∓⨤⨦±]$')) + R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$'))('value').add_action(merge)

#regex or matching the reporting of a homo energy
energy = Optional(lbrct).hide() + (homo_range | homo_value)('value') + Optional(rbrct).hide()

#all homo instances
homo = (prefix + Optional(delim).hide() + energy + units)('homo')

#phrases that list homo level in parentheses or brackets
bracket_any = lbrct + OneOrMore(Not(homo) + Not(rbrct) + Any()) + rbrct

#phrases that list an entity having a given homo level
cem_homo_phrase = (Optional(cem) + Optional(I('having')).hide() + Optional(delim).hide() + Optional(bracket_any).hide() + Optional(delim).hide() + Optional(lbrct) + homo + Optional(rbrct))('homo_phrase')

#phrases that culminate in a homo level after experimental augmentation
to_give_homo_phrase = ((I('to') + (I('give') | I('afford') | I('yield') | I('obtain')) | I('affording') | I('afforded') | I('gave') | I('yielded')).hide() + Optional(dt).hide() + (cem | chemical_label | lenient_chemical_label) + ZeroOrMore(Not(homo) + Not(cem) + Any()).hide() + homo)('homo_phrase')

#other phrases where experimental changes lead to a homo level
obtained_homo_phrase = ((cem | chemical_label) + (I('is') | I('are') | I('was')).hide() + (I('afforded') | I('obtained') | I('yielded')).hide() + ZeroOrMore(Not(homo) + Not(cem) + Any()).hide() + homo)('homo_phrase')

#final, cumulative phrase pattern matching
homo_phrase = cem_homo_phrase | to_give_homo_phrase | obtained_homo_phrase

class HOMOParser(BaseParser):
    """
    
    """
    root = homo_phrase

    def interpret(self, result, start, end):
        compound = Compound(
            HOMO_level=[
                HOMOLevel(
                    #Why won't it work if using xpath('./homo/value/text()')?
                    value=first(result.xpath('./homo/value/text()')),
                    units=first(result.xpath('./homo/units/text()'))
                )
            ]
        )
        cem_el = first(result.xpath('./cem'))
        if cem_el is not None:
            compound.names = cem_el.xpath('./name/text()')
            compound.labels = cem_el.xpath('./label/text()')
        yield compound


