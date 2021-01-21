# -*- coding: utf-8 -*-
"""
chemdataextractor.parse.boiling_point
~~~~~~~~~~~~~~~~~~~~~~~~~~

boiling point (Tb) parser.

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
from ..model import Compound, BoilingPoint
from .actions import merge, join, fix_whitespace
from .base import BaseParser
from .elements import W, I, R, Optional, Any, OneOrMore, Not, ZeroOrMore

log = logging.getLogger(__name__)

boiling_point_specifier = (I('^Tb$') | (Optional(lbrct) + (I('Tb') | I('T_b') | I('b\.?p\.?')) + Optional(rbrct)) | I('boiling') + Optional((I('point')) + Optional(I('temperature')) + Optional(I('range'))))('boiling_point').add_action(merge)

#keyword matching for phrases that trigger value scraping
prefix = (Optional(Optional('has') + Optional(I('a') | I('an')))).hide() + \
         (Optional(I('the'))).hide() + \
         boiling_point_specifier + \
         (Optional(I('of') | I('=') | I('equal to') | (I('is') + Optional(I('between'))) | I('is equal to')) | I('was found to be')).hide() + \
         (Optional(I('in') + I('the') + I('range') + Optional(I('of')) | I('about') | ('around') | I('ca') | I('ca.'))).hide()

#generic list of delimiters
delim = R('^[:;\.,]$')

#Regex to match units of property
units = (Optional(W('°') | W('º')) + Optional(R('^[CFK]\.?$')) | W('K\.?'))('units').add_action(merge)

#Regex to match ranges of values or single values (with or without spaces)
joined_range = R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?[\-––-−~∼˜]\d+(\.\d+)?(\(\d\))?$')('value').add_action(merge)

spaced_range = (R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') + Optional(units).hide() +(R('^[\-±–−~∼˜]$') + R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') | R('^[\+\-–−]\d+(\.\d+)?(\(\d\))?$')))('value').add_action(merge)

to_range = (R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') + Optional(units).hide() + ((I('to') | I('and')) + R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') | R('^[\+\-–−]\d+(\.\d+)?(\(\d\))?$')))('value').add_action(join)

#ranged instances
boiling_point_range = (Optional(R('^[\-–−]$')) + (joined_range | spaced_range | to_range))('value').add_action(merge)

#value instances
boiling_point_value = (Optional(R('^[~∼˜\<\>\≤\≥]$')) + Optional(R('^[\-\–\–\−±∓⨤⨦±]$')) + R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$'))('value').add_action(merge)

#regex or matching the reporting of a boiling_point temperature
value = Optional(lbrct).hide() + (boiling_point_range | boiling_point_value)('value') + Optional(rbrct).hide()

#all boiling_point instances
boiling_point = (prefix + Optional(delim).hide() + value + units)('boiling_point')

#phrases that list boiling_point level in parentheses or brackets
bracket_any = lbrct + OneOrMore(Not(boiling_point) + Not(rbrct) + Any()) + rbrct

#phrases that list an entity having a given boiling_point level
solvent_phrase = (R('^(re)?crystalli[sz](ation|ed)$', re.I) + (I('with') | I('from')) + cem | solvent_name)

cem_boiling_point_phrase = (Optional(solvent_phrase).hide() + Optional(cem) + Optional(I('having')).hide() + Optional(delim).hide() + Optional(bracket_any).hide() + Optional(delim).hide() + Optional(lbrct) + boiling_point + Optional(rbrct))('boiling_point_phrase')

#phrases that culminate in a boiling_point value after experimental augmentation
to_give_boiling_point_phrase = ((I('to') + (I('give') | I('afford') | I('yield') | I('obtain')) | I('affording') | I('afforded') | I('gave') | I('yielded')).hide() + Optional(dt).hide() + (cem | chemical_label | lenient_chemical_label) + ZeroOrMore(Not(boiling_point) + Not(cem) + Any()).hide() + boiling_point)('boiling_point_phrase')

#other phrases where experimental changes lead to a boiling_point value
obtained_boiling_point_phrase = ((cem | chemical_label) + (I('is') | I('are') | I('was') + Optional(I('found to be'))).hide() + (I('afforded') | I('obtained') | I('yielded')).hide() + ZeroOrMore(Not(boiling_point) + Not(cem) + Any()).hide() + boiling_point)('boiling_point_phrase')

#declaratory CEM phrase (the __ of cem is..)
declaratory_boiling_point_phrase = (I('the') + boiling_point + I('of') + (cem | chemical_label | lenient_chemical_label) + (I('is') | I('is equal to') | I('=')) + boiling_point)('boiling_point_phrase')

#final, cumulative phrase pattern matching
boiling_point_phrase = cem_boiling_point_phrase | to_give_boiling_point_phrase | obtained_boiling_point_phrase | declaratory_boiling_point_phrase

class BoilingPointParser(BaseParser):
    """
    
    """
    root = boiling_point_phrase

    def interpret(self, result, start, end):
        compound = Compound(
            boiling_point=[
                BoilingPoint(
                    #Why won't it work if using xpath('./boiling_point/value/text()')?
                    value=first(result.xpath('./boiling_point/value/text()')),
                    units=first(result.xpath('./boiling_point/units/text()'))
                )
            ]
        )
        cem_el = first(result.xpath('./cem'))
        if cem_el is not None:
            compound.names = cem_el.xpath('./name/text()')
            compound.labels = cem_el.xpath('./label/text()')
        yield compound


