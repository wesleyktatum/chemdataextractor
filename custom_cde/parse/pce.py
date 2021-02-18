# -*- coding: utf-8 -*-
"""
chemdataextractor.parse.pce
~~~~~~~~~~~~~~~~~~~~~~~~~~

Power Conversion Efficiency (PCE, %) of photovoltaic devices
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
from ..model import Compound, PCE
from .actions import merge, join, fix_whitespace
from .base import BaseParser
from .elements import W, I, R, Optional, Any, OneOrMore, Not, ZeroOrMore

log = logging.getLogger(__name__)

#####################################################################
# Customize these patterns and variable names to your custom property
#####################################################################

pce_specifier = ((I('^Power conversion efficiency$') | I('^PCE$')) | \
                 (Optional(lbrct) + I('PCE') + Optional(rbrct)) | \
                 (I('power') + I('conversion') + I('efficiency'))).hide()('pce')

#keyword matching for phrases that trigger value scraping
prefix = (Optional(Optional('has') + Optional(I('a') | I('an')))).hide() + \
         (Optional(I('the'))).hide() + \
         pce_specifier + \
         (Optional(I('of') | I('=') | I('equal to') | (I('is') + Optional(I('between'))) | I('is equal to')) | I('was found to be')).hide() + \
         (Optional(I('in') + I('the') + I('range') + Optional(I('of')) | I('about') | ('around') | I('ca') | I('ca.'))).hide()

#Regex to match units of property
units = (I('%'))('units')

#############################################################
# make sure variable names and xpath tags match up below here
#############################################################

#generic list of delimiters
delim = R('^[:;\.,]$')

#Regex to match ranges of values or single values (with or without spaces)
joined_range = R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?[\-––-−~∼˜]\d+(\.\d+)?(\(\d\))?$')('value').add_action(merge)

spaced_range = (R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') + Optional(units).hide() +(R('^[\-±–−~∼˜]$') + R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') | R('^[\+\-–−]\d+(\.\d+)?(\(\d\))?$')))('value').add_action(merge)

to_range = (R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') + Optional(units).hide() + ((I('to') | I('and')) + R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') | R('^[\+\-–−]\d+(\.\d+)?(\(\d\))?$')))('value').add_action(join)

#ranged instances
pce_range = (Optional(R('^[\-–−]$')) + (joined_range | spaced_range | to_range))('value').add_action(merge)

#value instances
pce_value = (Optional(R('^[~∼˜\<\>\≤\≥]$')) + Optional(R('^[\-\–\–\−±∓⨤⨦±]$')) + R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$'))('value').add_action(merge)

#regex or matching the reporting of a pce value
value = Optional(lbrct).hide() + (pce_range | pce_value) + Optional(rbrct).hide()('value')

#all pce instances
pce = (prefix + Optional(delim).hide() + value + units)('pce')

#phrases that list pce in parentheses or brackets
bracket_any = lbrct + OneOrMore(Not(pce) + Not(rbrct) + Any()) + rbrct

#phrases that list an entity having a given pce
cem_pce_phrase = (Optional(cem) + Optional(I('having')).hide() + Optional(delim).hide() + Optional(bracket_any).hide() + Optional(delim).hide() + Optional(lbrct) + pce + Optional(rbrct))('pce_phrase')

#phrases that culminate in a pce value after experimental augmentation
to_give_pce_phrase = ((I('to') + (I('give') | I('afford') | I('yield') | I('obtain')) | I('affording') | I('afforded') | I('gave') | I('yielded')).hide() + Optional(dt).hide() + (cem | chemical_label | lenient_chemical_label) + ZeroOrMore(Not(pce) + Not(cem) + Any()).hide() + pce)('pce_phrase')

#other phrases where experimental changes lead to a pce value
obtained_pce_phrase = ((cem | chemical_label) + (I('is') | I('are') | I('was') + Optional(I('found to be'))).hide() + (I('afforded') | I('obtained') | I('yielded')).hide() + ZeroOrMore(Not(pce) + Not(cem) + Any()).hide() + pce)('pce_phrase')

#declaratory CEM phrase (the __ of cem is..)
declaratory_pce_phrase = (I('the') + pce + I('of') + (cem | chemical_label | lenient_chemical_label) + (I('is') | I('is equal to') | I('=')) + pce)('pce_phrase')

#final, cumulative phrase pattern matching
pce_phrase = cem_pce_phrase | to_give_pce_phrase | obtained_pce_phrase | declaratory_pce_phrase

class PCEParser(BaseParser):
    """
    
    """
    root = pce_phrase

    def interpret(self, result, start, end):
        compound = Compound(
            pce=[
                PCE(
                    value=first(result.xpath('./pce/value/text()')),
                    units=first(result.xpath('./pce/units/text()'))
                )
            ]
        )
        cem_el = first(result.xpath('./cem'))
        if cem_el is not None:
            compound.names = cem_el.xpath('./name/text()')
            compound.labels = cem_el.xpath('./label/text()')
        yield compound


