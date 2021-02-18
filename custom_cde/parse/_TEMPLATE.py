# -*- coding: utf-8 -*-
"""
chemdataextractor.parse.<property_name>
~~~~~~~~~~~~~~~~~~~~~~~~~~

This is a template for new properties. Primary changes need to occur between the commented
sections. This is were the property name and abbreviations, as well as the units, are defined.

Below these sections, make sure that the variable names and xpath tags (in parentheses at
the end of the variable definition) are updated to reflect the property of interest. Be sure 
to also update the import statement to include the property class defined in model.py.

If there the property is unitless, erase all references to units in both patterns and the
parser class. For an example of unitless properties, look at `dispersity.py`

Make sure to update model.py and text.py to accomodate the new parser.

This template is pre-filled with the enthalpy_of_sublimation property fields as an example.
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
from ..model import Compound, SublimationEnthalpy
from .actions import merge, join, fix_whitespace
from .base import BaseParser
from .elements import W, I, R, Optional, Any, OneOrMore, Not, ZeroOrMore

log = logging.getLogger(__name__)

#####################################################################
# Customize these patterns and variable names to your custom property
#####################################################################

enthalpy_of_sublimation_specifier = ((I('^Enthalpy of sublimation$')) | \
                                      (Optional(lbrct) + (I('ΔH') | I('ΔHs') | I('ΔH_s') | \
                                                          I('ΔHsub') | I('ΔH_sub')) + Optional(rbrct)) | \
                                      ((I('enthalpy') | I('heat')) + I('of') + (I('sublimation')))).hide()('enthalpy_of_sublimation')

#keyword matching for phrases that trigger value scraping
prefix = (Optional(Optional('has') + Optional(I('a') | I('an')))).hide() + \
         (Optional(I('the'))).hide() + \
         enthalpy_of_sublimation_specifier + \
         (Optional(I('of') | I('=') | I('equal to') | (I('is') + Optional(I('between'))) | I('is equal to')) | I('was found to be')).hide() + \
         (Optional(I('in') + I('the') + I('range') + Optional(I('of')) | I('about') | ('around') | I('ca') | I('ca.'))).hide()

#Regex to match units of property
units = ((I('kJ') | I('J') | I('mJ') | I('Cal') | I('kcal') | I('cal') | I('mcal')) + \
         (R('/') | I('per')) + \
         (R('kg') | I('g') | I('mg') | I('mol') | I('mmol')))('units').add_action(merge)

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
enthalpy_of_sublimation_range = (Optional(R('^[\-–−]$')) + (joined_range | spaced_range | to_range))('value').add_action(merge)

#value instances
enthalpy_of_sublimation_value = (Optional(R('^[~∼˜\<\>\≤\≥]$')) + Optional(R('^[\-\–\–\−±∓⨤⨦±]$')) + R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$'))('value').add_action(merge)

#regex or matching the reporting of a enthalpy_of_sublimation value
value = Optional(lbrct).hide() + (enthalpy_of_sublimation_range | enthalpy_of_sublimation_value) + Optional(rbrct).hide()('value')

#all enthalpy_of_sublimation instances
enthalpy_of_sublimation = (prefix + Optional(delim).hide() + value + units)('enthalpy_of_sublimation')

#phrases that list enthalpy_of_sublimation in parentheses or brackets
bracket_any = lbrct + OneOrMore(Not(enthalpy_of_sublimation) + Not(rbrct) + Any()) + rbrct

#phrases that list an entity having a given enthalpy_of_sublimation
cem_enthalpy_of_sublimation_phrase = (Optional(cem) + Optional(I('having')).hide() + Optional(delim).hide() + Optional(bracket_any).hide() + Optional(delim).hide() + Optional(lbrct) + enthalpy_of_sublimation + Optional(rbrct))('enthalpy_of_sublimation_phrase')

#phrases that culminate in a enthalpy_of_sublimation value after experimental augmentation
to_give_enthalpy_of_sublimation_phrase = ((I('to') + (I('give') | I('afford') | I('yield') | I('obtain')) | I('affording') | I('afforded') | I('gave') | I('yielded')).hide() + Optional(dt).hide() + (cem | chemical_label | lenient_chemical_label) + ZeroOrMore(Not(enthalpy_of_sublimation) + Not(cem) + Any()).hide() + enthalpy_of_sublimation)('enthalpy_of_sublimation_phrase')

#other phrases where experimental changes lead to a enthalpy_of_sublimation value
obtained_enthalpy_of_sublimation_phrase = ((cem | chemical_label) + (I('is') | I('are') | I('was') + Optional(I('found to be'))).hide() + (I('afforded') | I('obtained') | I('yielded')).hide() + ZeroOrMore(Not(enthalpy_of_sublimation) + Not(cem) + Any()).hide() + enthalpy_of_sublimation)('enthalpy_of_sublimation_phrase')

#declaratory CEM phrase (the __ of cem is..)
declaratory_enthalpy_of_sublimation_phrase = (I('the') + enthalpy_of_sublimation + I('of') + (cem | chemical_label | lenient_chemical_label) + (I('is') | I('is equal to') | I('=')) + enthalpy_of_sublimation)('enthalpy_of_sublimation_phrase')

#final, cumulative phrase pattern matching
enthalpy_of_sublimation_phrase = cem_enthalpy_of_sublimation_phrase | to_give_enthalpy_of_sublimation_phrase | obtained_enthalpy_of_sublimation_phrase | declaratory_enthalpy_of_sublimation_phrase

class SublimationEnthalpyParser(BaseParser):
    """
    
    """
    root = enthalpy_of_sublimation_phrase

    def interpret(self, result, start, end):
        compound = Compound(
            enthalpy_of_sublimation=[
                SublimationEnthalpy(
                    #Why won't it work if using xpath('./enthalpy_of_sublimation/value/text()')?
                    value=first(result.xpath('./enthalpy_of_sublimation/value/text()')),
                    units=first(result.xpath('./enthalpy_of_sublimation/units/text()'))
                )
            ]
        )
        cem_el = first(result.xpath('./cem'))
        if cem_el is not None:
            compound.names = cem_el.xpath('./name/text()')
            compound.labels = cem_el.xpath('./label/text()')
        yield compound


