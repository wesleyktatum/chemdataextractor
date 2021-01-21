# -*- coding: utf-8 -*-
"""
chemdataextractor.parse.modulus
~~~~~~~~~~~~~~~~~~~~~~~~~~

Parser for modulus, a.k.a. Young's Modulus or elastic modulus
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
from ..model import Compound, Modulus
from .actions import merge, join, fix_whitespace
from .base import BaseParser
from .elements import W, I, R, Optional, Any, OneOrMore, Not, ZeroOrMore

log = logging.getLogger(__name__)

#####################################################################
# Customize these patterns and variable names to your custom property
#####################################################################


modulus_specifier = ((I('^Modulus$') | I("^Young's Modulus$") | I('^Elastic modulus$')) | \
                 (Optional(lbrct) + (I('E')) + Optional(rbrct)) | \
                 (I('modulus') | I("young's modulus") | I('elastic modulus'))).hide()('modulus')

#keyword matching for phrases that trigger value scraping
prefix = (Optional(Optional('has') + Optional(I('a') | I('an')))).hide() + \
         (Optional(I('the'))).hide() + \
         modulus_specifier + \
         (Optional(I('of') | I('=') | I('equal to') | (I('is') + Optional(I('between'))) | I('is equal to')) | I('was found to be')).hide() + \
         (Optional(I('in') + I('the') + I('range') + Optional(I('of')) | I('about') | ('around') | I('ca') | I('ca.'))).hide()

#Regex to match units of property
units = (I('Pa') | I('kPa') | I('MPa') | I('GPa'))('units')


######################################################
# make sure variable names match up below here
######################################################

#generic list of delimiters
delim = R('^[:;\.,]$')

#Regex to match ranges of values or single values (with or without spaces)
joined_range = R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?[\-––-−~∼˜]\d+(\.\d+)?(\(\d\))?$')('value').add_action(merge)

spaced_range = (R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') + Optional(units).hide() +(R('^[\-±–−~∼˜]$') + R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') | R('^[\+\-–−]\d+(\.\d+)?(\(\d\))?$')))('value').add_action(merge)

to_range = (R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') + Optional(units).hide() + ((I('to') | I('and')) + R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') | R('^[\+\-–−]\d+(\.\d+)?(\(\d\))?$')))('value').add_action(join)

#ranged instances
modulus_range = (Optional(R('^[\-–−]$')) + (joined_range | spaced_range | to_range))('value').add_action(merge)

#value instances
modulus_value = (Optional(R('^[~∼˜\<\>\≤\≥]$')) + Optional(R('^[\-\–\–\−±∓⨤⨦±]$')) + R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$'))('value').add_action(merge)

#regex or matching the reporting of a modulus value
value = Optional(lbrct).hide() + (modulus_range | modulus_value) + Optional(rbrct).hide()('value')

#all modulus instances
modulus = (prefix + Optional(delim).hide() + value + units)('modulus')

#phrases that list modulus in parentheses or brackets
bracket_any = lbrct + OneOrMore(Not(modulus) + Not(rbrct) + Any()) + rbrct

#phrases that list an entity having a given modulus
cem_modulus_phrase = (Optional(cem) + Optional(I('having')).hide() + Optional(delim).hide() + Optional(bracket_any).hide() + Optional(delim).hide() + Optional(lbrct) + modulus + Optional(rbrct))('modulus_phrase')

#phrases that culminate in a modulus value after experimental augmentation
to_give_modulus_phrase = ((I('to') + (I('give') | I('afford') | I('yield') | I('obtain')) | I('affording') | I('afforded') | I('gave') | I('yielded')).hide() + Optional(dt).hide() + (cem | chemical_label | lenient_chemical_label) + ZeroOrMore(Not(modulus) + Not(cem) + Any()).hide() + modulus)('modulus_phrase')

#other phrases where experimental changes lead to a modulus value
obtained_modulus_phrase = ((cem | chemical_label) + (I('is') | I('are') | I('was') + Optional(I('found to be'))).hide() + (I('afforded') | I('obtained') | I('yielded')).hide() + ZeroOrMore(Not(modulus) + Not(cem) + Any()).hide() + modulus)('modulus_phrase')

#declaratory CEM phrase (the __ of cem is..)
declaratory_modulus_phrase = (I('the') + modulus + I('of') + (cem | chemical_label | lenient_chemical_label) + (I('is') | I('is equal to') | I('=')) + modulus)('modulus_phrase')

#final, cumulative phrase pattern matching
modulus_phrase = cem_modulus_phrase | to_give_modulus_phrase | obtained_modulus_phrase | declaratory_modulus_phrase

class ModulusParser(BaseParser):
    """
    
    """
    root = modulus_phrase

    def interpret(self, result, start, end):
        compound = Compound(
            modulus=[
                Modulus(
                    #Why won't it work if using xpath('./modulus/value/text()')?
                    value=first(result.xpath('./modulus/value/text()')),
                    units=first(result.xpath('./modulus/units/text()'))
                )
            ]
        )
        cem_el = first(result.xpath('./cem'))
        if cem_el is not None:
            compound.names = cem_el.xpath('./name/text()')
            compound.labels = cem_el.xpath('./label/text()')
        yield compound


