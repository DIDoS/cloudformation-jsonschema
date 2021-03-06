# coding: utf-8
from pyquery import PyQuery as q
from collections import OrderedDict
import tools
from tools import OD
import logging


logging.basicConfig(format='%(levelname)s %(type)s %(href)s\n  %(message)s')
log = logging.LoggerAdapter(logging.getLogger(), {'type': '', 'href': ''})

PROPERTIES_REFERENCE = tools.BASE + 'aws-product-property-reference.html'
this = None


def property_name_from_href(href):
    href = str(href)
    href, _ = href.rsplit(".", 1)
    _, href = href.rsplit("/", 1)
    return href


def property_ref_from_href(href):
    return {
        '$ref':
        '#/definitions/property_types/%s' % property_name_from_href(href)
    }

def property_ref(dt, dd_, dd, t):
    name = dt('.term').text()
    href = dd('a').attr('href')
    #import pdb; pdb.set_trace()
    if name == 'DBSecurityGroupIngress':
        return OD((
            ('oneOf', [
                OD((
                    ('type', 'array'),
                    ('items', property_ref_from_href(href)),
                )),
                {"$ref": "basic_types.json#/definitions/function"},
                property_ref_from_href(href),
            ]),
        ))

    if 'list of' in t or 'tags' in t or name in (
        'Parameters',
        'Stages',
        'Tags',
        'KeySchema',
    ):
        return OD((
            ('oneOf', [
                OD((
                    ('type', 'array'),
                    ('items', property_ref_from_href(href)),
                )),
                {"$ref": "basic_types.json#/definitions/function"},
            ]),
        ))
    return property_ref_from_href(href)


type_patterns = (
    ('type : string',
     {"$ref": "basic_types.json#/definitions/string"}),
    ('type : ref id',
     {"$ref": "basic_types.json#/definitions/string"}),
    ('list of strings',
     {"$ref": "basic_types.json#/definitions/list<string>"}),
    ('type : integer',
     {"$ref": "basic_types.json#/definitions/integer"}),
    ('type : number',
     {"$ref": "basic_types.json#/definitions/integer"}),
    ('type : boolean',
     {"$ref": "basic_types.json#/definitions/boolean"}),
    ('type : json object',
     {"type": "object"}),
    ('type : a list of amazon sns topics arns',
     {"$ref": "basic_types.json#/definitions/list<string>"}),
    ('type : a list of security groups',
     {"$ref": "basic_types.json#/definitions/list<string>"}),
    ('key-value pairs',
     {"$ref": "basic_types.json#/definitions/key-value-pairs"}),
    ('type : time stamp',
     {"$ref": "basic_types.json#/definitions/timestamp"}),
)


def get_type(dt, dd_):
    dd = dd_('p').filter(lambda x: q(this).text().startswith('Type'))
    t = dd.text().lower()
    for pattern, schema_fragment in type_patterns:
        if pattern in t:
            return schema_fragment
    if dd('a'):
        return property_ref(dt, dd_, dd, t)
    if dd_('.type') and len(dd_('.type')):
        if (dd_('.type').text() == 'AWS::EC2::SecurityGroup' and
                'list of' in t):
            return {"$ref": "basic_types.json#/definitions/list<string>"}

    ind = t.find('type :')
    extract = t[ind:ind + 50]
    log.warning('Could not parse resource property type: "%s"\n"%s"', extract, dd_.html())
    return {'description': dd_.html()}

all_properties = tools.all_resource_properties_hrefs()
all_resource_hrefs = tools.all_resource_hrefs()


def pretty_print_element(el):
    from pygments import highlight
    from pygments.lexers import HtmlLexer
    from pygments.formatters import TerminalFormatter

    code = el.html(pretty_print=True)
    print highlight(code, HtmlLexer(), TerminalFormatter())


def set_resource_property_type_properties(schema, res_prop_type):
    schema = schema['definitions']['property_types'][res_prop_type]
    href = schema['descriptionURL']
    log.extra['type'] = res_prop_type
    log.extra['href'] = href
    properties, required = parse_properties_from_href(href)
    schema['properties'] = properties
    if required:
        schema['required'] = required
    schema['additionalProperties'] = False



def parse_properties_from_href(href):
    h = tools.get_pq(href)
    dl = h('#main-col-body .variablelist dl').filter(
        lambda i: 'Type :' in q(this).text()
    )
    #pretty_print_element(dl)
    #import pdb; pdb.set_trace()
    pairs = zip(dl.children('dt'), dl.children('dd'))
    pairs = [(q(dt), q(dd)) for dt, dd in pairs]

    properties = OrderedDict(
        (dt.text().split()[0], get_type(dt, dd))
        for dt, dd in pairs
    )

    required = [
        k.text()
        for k, v
        in pairs
        if v('p').filter(
            lambda i: 'Required : Yes' in q(this).text() and
            not 'Yes, for VPC security groups' in q(this).text()
        )
    ]

    return properties, required


def set_resource_properties(schema, res_type):
    log.extra['type'] = res_type
    type_href = all_resource_hrefs[res_type]
    log.extra['href'] = type_href
    resources = tools.get_resource_types(schema)
    shortcut = resources[res_type]['properties']

    properties, required = parse_properties_from_href(type_href)
    shortcut['Properties']['properties'] = properties
    if required:
        shortcut['Properties']['required'] = required
        resources[res_type]['required'] += ['Properties']
    resources[res_type]['additionalProperties'] = False
    return schema


def all_res_properties():
    h = tools.get_pq(PROPERTIES_REFERENCE)
    res = OrderedDict()
    for a in h('#main-col-body li a'):
        href = q(a).attr("href")
        res[property_name_from_href(href)] = OD((
            ("title", " ".join(a.text.split())),
            ("descriptionURL", href),
            ("type", "object"),
        ))
    return res
