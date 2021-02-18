# -*- coding: utf-8 -*-
"""
chemdataextractor.parse.jsc
~~~~~~~~~~~~~~~~~~~~~~~~~~

Short-circuit current (Jsc, mA/cm2) of photovoltaic devices
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
from ..model import Compound, Jsc
from .actions import merge, join, fix_whitespace
from .base import BaseParser
from .elements import W, I, R, Optional, Any, OneOrMore, Not, ZeroOrMore

log = logging.getLogger(__name__)

#####################################################################
# Customize these patterns and variable names to your custom property
#####################################################################

jsc_specifier = ((I('^Short-circuit current$') | I('^Short circuit current$')) | \
                 (Optional(lbrct) + I('Jsc') + Optional(rbrct)) | \
                 ((I('short') + Optional(I('-')) + I('circuit')) + I('current') + Optional(I('density')))).hide()('jsc')

#keyword matching for phrases that trigger value scraping
prefix = (Optional(Optional('has') + Optional(I('a') | I('an')))).hide() + \
         (Optional(I('the'))).hide() + \
         jsc_specifier + \
         (Optional(I('of') | I('=') | I('equal to') | (I('is') + Optional(I('between'))) | I('is equal to')) | I('was found to be')).hide() + \
         (Optional(I('in') + I('the') + I('range') + Optional(I('of')) | I('about') | ('around') | I('ca') | I('ca.'))).hide()

#Regex to match units of property
units = ((R('A') | R('mA')) + \
             (R('/') | R('per')) + \
             (R('cm2') | R('cm\^2')))('units').add_action(merge)

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
jsc_range = (Optional(R('^[\-–−]$')) + (joined_range | spaced_range | to_range))('value').add_action(merge)

#value instances
jsc_value = (Optional(R('^[~∼˜\<\>\≤\≥]$')) + Optional(R('^[\-\–\–\−±∓⨤⨦±]$')) + R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$'))('value').add_action(merge)

#regex or matching the reporting of a jsc value
value = Optional(lbrct).hide() + (jsc_range | jsc_value) + Optional(rbrct).hide()('value')

#all jsc instances
jsc = (prefix + Optional(delim).hide() + value + units)('jsc')

#phrases that list jsc in parentheses or brackets
bracket_any = lbrct + OneOrMore(Not(jsc) + Not(rbrct) + Any()) + rbrct

#phrases that list an entity having a given jsc
cem_jsc_phrase = (Optional(cem) + Optional(I('having')).hide() + Optional(delim).hide() + Optional(bracket_any).hide() + Optional(delim).hide() + Optional(lbrct) + jsc + Optional(rbrct))('jsc_phrase')

#phrases that culminate in a jsc value after experimental augmentation
to_give_jsc_phrase = ((I('to') + (I('give') | I('afford') | I('yield') | I('obtain')) | I('affording') | I('afforded') | I('gave') | I('yielded')).hide() + Optional(dt).hide() + (cem | chemical_label | lenient_chemical_label) + ZeroOrMore(Not(jsc) + Not(cem) + Any()).hide() + jsc)('jsc_phrase')

#other phrases where experimental changes lead to a jsc value
obtained_jsc_phrase = ((cem | chemical_label) + (I('is') | I('are') | I('was') + Optional(I('found to be'))).hide() + (I('afforded') | I('obtained') | I('yielded')).hide() + ZeroOrMore(Not(jsc) + Not(cem) + Any()).hide() + jsc)('jsc_phrase')

#declaratory CEM phrase (the __ of cem is..)
declaratory_jsc_phrase = (I('the') + jsc + I('of') + (cem | chemical_label | lenient_chemical_label) + (I('is') | I('is equal to') | I('=')) + jsc)('jsc_phrase')

#final, cumulative phrase pattern matching
jsc_phrase = cem_jsc_phrase | to_give_jsc_phrase | obtained_jsc_phrase | declaratory_jsc_phrase

class JscParser(BaseParser):
    """
    
    """
    root = jsc_phrase

    def interpret(self, result, start, end):
        compound = Compound(
            jsc=[
                Jsc(
                    value=first(result.xpath('./jsc/value/text()')),
                    units=first(result.xpath('./jsc/units/text()'))
                )
            ]
        )
        cem_el = first(result.xpath('./cem'))
        if cem_el is not None:
            compound.names = cem_el.xpath('./name/text()')
            compound.labels = cem_el.xpath('./label/text()')
        yield compound


