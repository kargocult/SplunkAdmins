#!/usr/bin/env python
# coding=utf-8
#
# Copyright © 2011-2015 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import absolute_import, division, print_function, unicode_literals

from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
import sys
from splunklib import six
import types
import re

#Based on the Splunk SDK for python example http://dev.splunk.com/view/python-sdk/SP-CAAAEU2 countmatches.py, searchcommands_app
#with modifications
@Configuration()
class StreamFilterCommand(StreamingCommand):
    """ Returns a field with a list of non-overlapping matches to a regular expression in a set of fields.

    ##Syntax

    .. code-block::
        StreamFilterCommand fieldname=<field> pattern=<field containing regex pattern> <field-list>

    ##Description

    Returns the non-overlapping matches to the regular expression contained in the field specified by `pattern`
    The result is stored in the field specified by `fieldname`. If `fieldname` exists, its value
    is replaced. If `fieldname` does not exist, it is created. Event records are otherwise passed through to the next
    pipeline processor unmodified.

    ##Example

    Return the regular expression matches in the `text` of each tweet in tweets.csv and store the result in `word_count`.

    .. code-block::
        | inputlookup tweets | eval pattern="\\w+" | streamfilter fieldname=word_count pattern=pattern text

    """
    fieldname = Option(
        doc='''
        **Syntax:** **fieldname=***<fieldname>*
        **Description:** Name of the field that will hold the match count''',
        require=True, validate=validators.Fieldname())

    pattern = Option(
        doc='''
        **Syntax:** **pattern=***<fieldname>* 
        **Description:** Field name containign the regular expression pattern to match''',
        require=True, validate=validators.Fieldname())

    #Filtering function created so we can handle multi-value pattern fields
    def thefilter(self, record, pattern):
        values = ""
        for fieldname in self.fieldnames:
            #multivalue fields come through as a ListType, iterate through the list and run the regex against each entry
            #in the multivalued field
            if isinstance(record[fieldname], types.ListType):
                for aRecord in record[fieldname]:
                    matches = pattern.findall(six.text_type(aRecord.decode("utf-8")))
                    for match in matches:
                        values = values + " " + match
            else:
                matches = pattern.findall(six.text_type(record[fieldname].decode("utf-8")))
                for match in matches:
                    values = values + " " + match
        return values

    #stream function to work on each event which may or may not be multi-valued
    def stream(self, records):
        self.logger.debug('StreamFilterCommand: %s', self)  # logs command line
        for record in records:
            values = ""
            pattern = self.pattern
            if not record.has_key(pattern):
               self.logger.warn("StreamFilterCommand: pattern field is %s but cannot find this field" % (pattern), self)
               sys.exit(-1)
            if isinstance(record[pattern], types.ListType):
                for aPattern in record[pattern]:
                    pattern = re.compile(aPattern)
                    values = values + self.thefilter(record, pattern)
            else:
                pattern = re.compile(record[pattern])
                values = values + self.thefilter(record, pattern)

            record[self.fieldname] = values
            yield record

dispatch(StreamFilterCommand, sys.argv, sys.stdin, sys.stdout, __name__)
