import sys
import pyparsing as pp
import os
import fileinput
import pprint
import unittest
import yaml
import hostlist

# define punctuation literals
LPAR, RPAR, LBRK, RBRK, LBRC, RBRC, VBAR, COLON, GT, LT, AT, EQ, DASH, DOLLAR = map(pp.Suppress, "()[]{}|:><@=-$")

ident = pp.alphanums + "_"

# No extra leading 0s allowed
decimal = pp.Regex(r'-?0|[1-9]\d*').setParseAction(lambda t: int(t[0]))

# 0x for hex
hexadecimal = pp.Group("0x" + pp.Word(pp.hexnums)).setParseAction(lambda n: int(n[2:], 16))

# 0* for octal
octal = pp.Group("0" + pp.Word("012345678")).setParseAction(lambda n: int(n[1:], 8))

# 0b* for binary
binary = pp.Group("0b" + pp.Word("01")).setParseAction(lambda n: int(n[2:], 16))

whole_numeric = decimal | hexadecimal | octal | binary

# floats contain a dot, or use scientific notation, or both
real = pp.Regex(r"[+-]?\d+\.\d*([eE][+-]?\d+)?").setParseAction(lambda tokens: float(tokens[0]))

numeric = whole_numeric | real

resource_type = pp.Word(ident)("type")

slice_expr =  whole_numeric("min") + pp.Optional(
                  COLON 
                + pp.Optional( #allow min: notation, python people will expect this to work
                      whole_numeric("max") 
                    + pp.Optional(
                          COLON 
                        + pp.Optional(pp.oneOf("+ - * / ^"), default='+')("stride_operator")
                        + whole_numeric("stride_operand")
                        )
                    )
                )

bare_range = pp.Group(slice_expr)("count")

range_group = LBRK + bare_range + RBRK

# forward declaration of resource and shardto allow this to be recursive
resource = pp.Forward()

def marker(value):
    return pp.Empty().setParseAction(pp.replaceWith(value))

def attribute_type_marker(value):
    return marker(value)('attr_type')

resource_list = pp.delimitedList(resource, delim=',')('resources')
resource_group = LPAR + pp.delimitedList(resource, delim=",") + RPAR | pp.Group(resource)('resources')

link_type = pp.Optional(pp.Word(ident), default='with')("link_type") + pp.Optional(range_group)
link_target = resource_group | pp.Group(resource)

in_link_attribute = marker('in')("direction") + (LT + DASH + link_type + DASH + LT | LT + marker('with')('link_type')) + link_target
out_link_attribute = marker('out')("direction") + marker('with')('link_type') + ((GT + DASH + link_type + DASH + GT | GT ) + link_target)
either_link_attribute = marker('inout')("direction") + LT + DASH + link_type + DASH + GT + link_target

link_attribute = attribute_type_marker('link') + (in_link_attribute | out_link_attribute | either_link_attribute)

tag_attribute = attribute_type_marker('tag') + COLON + pp.Word(ident)("tag")

task_attribute = pp.Group(attribute_type_marker('task') + DOLLAR + pp.Optional(pp.Word(ident))("command") + pp.Optional(range_group))

attribute = pp.Group(link_attribute | tag_attribute )

attribute_list =( pp.Group(LPAR + pp.delimitedList(attribute | task_attribute, delim=",") + RPAR)("attributes") 
                | pp.Group(task_attribute + attribute
                         | attribute
                         | task_attribute)("attributes") 
                    )


resource_id = pp.Word(ident)
resource_id_list = pp.Group(pp.Word(ident) | LPAR + pp.Word(ident + "[]- \t").setParseAction(hostlist.expand_hostlist) + RPAR)("id_list")
id_reference = AT + resource_id_list
id_assignment = EQ + resource_id_list

resource << pp.Group((resource_type | id_reference) #id_reference must match number of elements created!
                  + pp.Optional( 
                     (range_group + pp.Optional(pp.Word(pp.alphas))('unit'))
                    | id_assignment #number of IDs must match number of compound elements created!
                    )
                  + pp.Optional(attribute_list)
                  )

# rspec = resource('top_resource') | resource_group('top_group')
rspec = resource_list
rspec.debug = True

def asDictDeep(parse_results):
    out = {}
    for k, v in parse_results.asDict().iteritems():
        if isinstance(v, pp.ParseResults):
            res = asDictDeep(v)
            if res == {}:
                l = []
                for i in v:
                    l.append(asDictDeep(i))
                out[k] = l
            else:
                out[k] = res
        else:
            out[k] = v
    return out

default_resource = { 'count' : { 'min' : 1},
                     'ftype' : 'resource'
                     }
default_shard = { 'count' : { 'min' : 1},
                  'tasks' : { 'count' : 1 },
                  'type' : 'Shard' }

def assign_if_non_empty(d, key, src, src_key=None):
    if src.get(key, '') != '':
        if src_key is not None:
            d[key] = src[src_key]
        else:
            d[key] = src[key]

def link_name(res):
    ret = res.link_type
    if res.direction == 'in':
        return '<' + ret
    if res.direction == 'out':
        if ret == 'with':
            return 'with'
        else:
            return ret + '>'
    if res.direction == 'inout':
        return '<' + ret + '>'

def process_sub_resource(s, ret, res):
    if ret.get('with', None) is None:
        ret['with'] = []
    ret['with'].append(canonicalize_inner(s, res))

def process_attribute(s, ret, a):
    if a == 'task' or a.attr_type == 'task':
        if ret.get('tasks', None) is None:
            ret['tasks'] = []
        nt = {}
        if a.command:
            nt['command'] = a.command
        if a.count:
            process_range(nt, a)
        if nt != {}:
            ret['tasks'].append(nt)
    elif a.attr_type == 'link':
        #special case the sub-resources case, it's nice to make this easy to read
        if a.link_type == 'with' and a.direction == 'out' and not a.count: 
            for r in a.resources:
                # print r.dump(), 'resource', r.resource, 'here'
                process_sub_resource(s, ret, r)
        elif not a.count:
            ln = link_name(a)
            if ret.get(ln, None) is None:
                ret[ln] = []
            for r in a.resources:
                # print r.dump(), 'resource', r.resource, 'here'
                ret[ln].append(canonicalize_inner(s, r))
        else: # complex link, make it happen
            if ret.get('links', None) is None:
                ret['links'] = []
            link = { 'type' : a.link_type,
                     'direction' : a.direction,
                     'targets' : [], }
            process_range(link, a)
            for r in a.resources:
                # print r.dump(), 'resource', r.resource, 'here'
                link['targets'].append(canonicalize_inner(s, r))
            ret['links'].append(link)
    elif a.attr_type == 'tag':
        if ret.get('tags', None) is None:
            ret['tags'] = []
        ret['tags'].append(a.tag)


def parse_range_into(d, res):
    assign_if_non_empty(d, 'min', res)
    assign_if_non_empty(d, 'max', res)
    assign_if_non_empty(d, 'stride_operator', res)
    assign_if_non_empty(d, 'stride_operand', res)

def process_range(ret, res):
    if res.count:
        if ret.get('count', None) is not None:
            ret['count'] = dict(ret['count']) # make a new dict for the range to update
        else:
            ret['count'] = {}
        parse_range_into(ret['count'], res.count)
        # print "RANGE", res.count.dump()
    # clean out un-necessary range keys
    if cmp(ret['count'], { 'min' : 1 }) == 0:
        del ret['count']

def canonicalize_inner(s, res):
    # print res.dump()
    # print asDictDeep(res)
    if isinstance(res, str):
        return res
    if res.resources:
        l = []
        for r in res.resources:
            l.append (canonicalize_inner(s, r))
        # print "LENGTH:", l
        return l if len(l) > 1 else l[0]
    ret = dict(default_resource)
    # for k,v in res.asDict().iteritems():
    #     ret[k] = v

    if res.ftype:
        ret['ftype'] = res.ftype
    elif res.type == 'Shard':
        ret['ftype'] = 'shard'
        ret['tasks'] = []
    elif res.type == 'Task':
        ret['ftype'] = 'task'
    elif res.type == 'Instance':
        ret['ftype'] = 'Instance'
    elif res.type == 'Program':
        ret['ftype'] = 'Program'
    if res.id_list:
        ret['ids'] = list(res.id_list)
    elif res.type:
        ret['type'] = res.type
    elif res.name:
        ret['type'] = res.name
    assign_if_non_empty(ret, 'unit', res)
    process_range(ret, res)
    for a in res.attributes:
        process_attribute(s, ret, a)
    return ret

def canonicalize(s):
    try:
        return canonicalize_inner(s, rspec.parseString(s, parseAll=True))
    except pp.ParseException as pfe:
        print "Error:", pfe.msg
        print pfe.markInputline('^')
        sys.exit(1)

def parse_bare_range(s):
    try:
        d = {}
        parse_range_into(d, bare_range.parseString(s, parseAll=True).count)
        return d
    except pp.ParseException as pfe:
        print "Error:", pfe.msg
        print pfe.markInputline('^')
        sys.exit(1)

def parse_range(s):
    try:
        d = {}
        parse_range_into(d, range_group.parseString(s, parseAll=True).count)
        return d
    except pp.ParseException as pfe:
        return parse_bare_range(s)

def parse_resource_string(s):
    return canonicalize(s)

def parse(l):
    try:
        print yaml.dump(canonicalize(l), default_flow_style=False)
        # pprint.pprint(canonicalize(l))
        # res =  rspec.parseString(l, parseAll=True)
        # res = range_group.parseString(l)
        # print res.dump()
        # print res.asList()
        # print yaml.dump(asDictDeep(res), default_flow_style=False)
        # pprint.pprint(res.asDict(), width=20)
        # print res.asDict()
    except pp.ParseException as pfe:
        print "Error:", pfe.msg
        print pfe.markInputline('^')
        sys.exit(1)

if __name__ == '__main__':
    for line in fileinput.input():
        parse(line)



class TestResource(unittest.TestCase):
    def test_range_group(self):
        res = range_group.parseString("[1:15:+2]")
        self.assertEqual(res.count.min, 1)
        self.assertEqual(res.count.max, 15)
        self.assertEqual(res.count.stride_operator, "+")
        self.assertEqual(res.count.stride_operand, 2)

    def test_range_group_no_stride(self):
        res = range_group.parseString("[1:15]")
        self.assertEqual(res.count.min, 1)
        self.assertEqual(res.count.max, 15)
        self.assertFalse(res.count.stride_operator)
        self.assertFalse(res.count.stride_operand)

    def test_range_group_no_max(self):
        res = range_group.parseString("[1]")
        self.assertEqual(res.count.min, 1)
        self.assertEqual(res.count.max, '')
        self.assertFalse(res.count.stride_operator)
        self.assertFalse(res.count.stride_operand)

    def test_rspec_single(self):
        r = canonicalize("Node[1:15:+2]")
        self.assertEqual(r['type'], "Node")
        self.assertEqual(r['count']['min'], 1)
        self.assertEqual(r['count']['min'], 1)
        self.assertEqual(r['count']['max'], 15)
        self.assertEqual(r['count']['stride_operator'], "+")
        self.assertEqual(r['count']['stride_operand'], 2)

    def test_rspec_no_range(self):
        res = canonicalize("Node")
        print res
        self.assertEqual(res['type'], "Node")
        self.assertFalse(res.get('count', False))
    def test_everything_together(self):
        res = canonicalize('Rack>>{Node[1:15:*4](>with[2]>Core[15],>>Socket[2],>[1:5]>PU[1]b,:thing)}')
        pprint.pprint( res)
        self.assertEqual(res['type'], 'Rack')
        self.assertEqual(res['resources'][0]['resources'][0]['type'], 'Node')

    # def range_group_no_max(self):

