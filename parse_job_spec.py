import glob
import uuid
import sys
import pyparsing as pp
import os
import fileinput
import pprint
import unittest
import yaml
import parse_resource_string as prs
import pytoml
import axon
import json
import sexpdata
import networkx as nx
from networkx.algorithms import isomorphism
from networkx.readwrite import json_graph
import copy
import matplotlib.pyplot as plt
import collections
import hostlist
import cmd

# drawing
import matplotlib.pyplot as plt
import matplotlib.cm as cm

import graph_tool as gt
import graph_tool.draw as gt_draw

NodeType = collections.namedtuple('NodeType', ['type','instances'])
EdgeType = collections.namedtuple('EdgeType', ['type','instances'])
# Task = collections.namedtuple('Program', ['type', 'command', 'walltime'])
# Resource = collections.namedtuple('Resource', ['type', 'pool', 'units'])

types = {
        'program' : NodeType('program', []),
        }

def add_with_type(g, t):
    v = g.add_vertex()
    # print t
    if types.get(t, None) is None:
        types[t] = NodeType(t, [])
    tgt = types[t]
    g.vp.type[v] = tgt.type
    g.vp.data[v] = {}
    g.vp.label[v] = t + '-' + str(len(tgt.instances))
    tgt.instances.append(v)
    return v

def add_edge_type(g, f, to, t='with'):
    # print f
    e = g.add_edge(f, to)
    if types.get(t, None) is None:
        types[t] = EdgeType(t, [])
    tgt = types[t]
    g.ep.type[e] = tgt.type
    tgt.instances.append(e)
    return e

def add_typed_and_attach(g, t, parent, edge_type='with'):
    v = add_with_type(g, t)
    add_edge_type(g, parent, v, edge_type)
    return v


# leave room for root
next_id = 1


def get_id():
    global next_id
    # return str(uuid.uuid4())
    i = next_id
    next_id += 1
    return i


def get_node_type(node):
    # Need to work it out
    t = node.get('ftype', None)
    if t is None:
        if node.get('task', False):
            t = 'slot'
        elif node.get('resources', False):
            t = 'program'
        elif node.get('programs', False):
            t = 'instance'
        elif node.get('command', False):
            t = 'task'
        else:
            t = 'resource'
            # raise RuntimeError("indiscernable resource object type: " + str(node))
    return t


def canonicalize_list(l):
    new_list = []
    for n in l:
        new_list.append(canonicalize_inner(n))
    return new_list


def canonicalize_inner(node, node_type=None):
    # print "NODE", node
    if isinstance(node, str):  # bare string, it's a resource, should use tags for this
        return prs.parse_resource_string(node)
    elif isinstance(node, dict):  # a program, instance, slot or resource that isn't tagged
        ret = dict(node)
        t = node_type
        if t is None:
            t = get_node_type(node)
        ret['ftype'] = t
        if t == 'instance':  # required keys [programs]
            ret['programs'] = canonicalize_inner(
                node['programs'], node_type='program')
        elif t == 'program':
            ret['resources'] = canonicalize_inner(
                node['resources'], node_type='resource')
        elif t in ('resource', 'slot'):
            for name in ('with', 'name', 'type', 'tasks'):
                if node.get(name, False):
                    if name in ('with', 'with'):
                        ret[name] = canonicalize_inner(node[name], 'resource')
                    elif name == 'tasks':
                        ret[name] = canonicalize_inner(node[name], 'task')
                    elif name == 'type':
                        ret[name] = node[name].lower()
                    else:
                        ret[name] = canonicalize_inner(node[name])

            for k in node:
                if k in ('with', 'name', 'type', 'count'):
                    continue
                ret[k] = node[k]
            if  ret.get('executable', None) is None:
                ret['executable'] = ret['type'].lower() in ('core', 'node', 'pu')
        if node.get('count', False):
            rng = node['count']
            if not isinstance(rng, str):
                rng = str(rng)

            new_range = False
            ret['count'] = prs.parse_range(rng)
        return ret
    elif isinstance(node, list):
        new_list = canonicalize_list(node)
        return new_list
    return node


def canonicalize(yaml_conf):
    """ Generate a complete canonical program list from the input spec"""
    ret = []
    for c in yaml.load_all(yaml_conf):
        ret.append(canonicalize_inner(c))
    return ret if len(ret) > 1 else ret[0]


def parse(spec):
    ret = []
    for c in yaml.load_all(spec):
        ret.append((canonicalize_inner(c), c))
    return ret if len(ret) > 1 else ret[0]



def add_resource(g, r, node, parent):
    vtx = add_typed_and_attach(g, node['type'], parent)
    if node['type'] == 'task':
        print "adding task"
        g.vp.data[vtx]['command'] = node.get('command', ['flux', 'start'])
        connect_task(g, node, vtx)
    else:
        g.vp.pool[vtx] = node['pool']
        g.vp.unit[vtx] = node['unit']
        g.vp.slot_id[vtx] = node.get('slot_id', "")
        g.vp.executable[vtx] = node.get('executable', False)
        print node
        print g.vp.executable[vtx], node.get('executable', 15)
    sl = r.get('with', None)
    if sl is not None:
        add_level_to_graph(g, sl, vtx)


def add_resources_to_graph(g, r, t, parent):
    # print r
    if isinstance(r, str):
        r = prs.parse_resource_string(r)
        # print "parsed:", r
        if isinstance(r, str):
            add_typed_and_attach(g, r, parent)
        else:
            add_resources_to_graph(g, r, t, parent)
    elif type(r) in (list, set, tuple):
        for sr in r:
            add_resources_to_graph(g, sr, t, parent)
    elif isinstance(r, dict):
        t = r.get('type', t)
        # vtx = add_typed_and_attach(g, t, parent)
        # g.vp.unit[vtx] = r.get('unit', 'units')
        # g.vp.pool[vtx] = r.get('unit', 'units') != 'units'
        # node.tags = set(r.get('tags', ()))
        node = {'id': get_id(),
                'type': t,
                'unit': r.get('unit', 'units'),
                'executable':r.get('executable', False)}
        node['pool'] = r.get('unit', 'units') != 'units'
        r_min = 0
        r_max = 1
        rng = r.get('count', None)
        if rng is None:
            ids = r.get('ids', False)
            if ids:
                c_node = copy.deepcopy(node)
                for res_id in hostlist.expand_hostlist(ids):
                    c_node['id'] = res_id
                    add_resource(g, r, c_node, parent)
                return
            names = r.get('names', False)
            if names:
                c_node = copy.deepcopy(node)
                for res_id in hostlist.expand_hostlist(names):
                    c_node['id'] = get_id()
                    c_node['name'] = res_id
                    add_resource(g, r, c_node, parent)
                return
        else:
            if r.get('ids', False) or r.get('names', False):
                raise AttributeError(
                    "ids and names must not be specified with count!")

        if isinstance(rng, int):
            r_max = rng
        else:
            if isinstance(rng, str):
                rng = prs.process_range(rng)
            if isinstance(rng, dict):
                r_min = rng.get('min', 1)
                r_max = rng.get('max', None)
                if r_max is None:
                    r_max = r_min
                    r_min = 0
        if node['pool']:  # only one, but with a size
            r_max = r_min + 1

        c_node = copy.deepcopy(node)
        for i in range(r_min, r_max):
            c_node['id'] = get_id()
            add_resource(g, r, c_node, parent)

        for attr in ('name', 'tags'):
            try:
                node[attr] = r[attr]
            except KeyError:
                pass

    else:
        raise RuntimeError("Invalid resource:" + str(r))


def add_tasks_to_graph(g, t, parent):
    if t is None:
        return
    elif type(t) in (list, tuple, set):
        for each in t:
            add_tasks_to_graph(g, each, parent)
    elif isinstance(t, str):
        tn = {'id': get_id(),
              'type': 'task',
              'command': t}
        g.add_node(tn['id'], **tn)
        g.add_edge(tn['id'], parent['id'])  # allocate
    else:
        raise RuntimeError("Bad task spec: " + t)

    return

def connect_task(graph, task, task_vtx):
    target = task.get('slot_id', False)
    if target:
        for v in graph.vertices():
            if graph.vp.slot_id[v] == target:
                add_edge_type(graph, task_vtx, v, 'slot')
            else:
                raise RuntimeError("no matching slot-id found")
    else:
        # print 'deriving task slot'
        executable = gt.GraphView(graph, vfilt=graph.vp.executable)
        # print executable
        e_leaves = gt.GraphView(executable, vfilt=lambda v: v.in_degree() == 1 and v.out_degree() == 0)
        # print e_leaves
        for v in e_leaves.vertices():
            add_edge_type(graph, task_vtx, v, 'slot')


def add_level_to_graph(g, n, parent, query=False):
    # print n
    try:
        t = n.get('ftype', 'Group')
    except AttributeError:
        t = 'Group'
    if t == 'program':
        p = add_with_type(g, 'program')
        g.vp.data[p]['walltime'] = n.get('walltime', '1h')
        add_edge_type(g, parent, p)
        try:
            for r in n['resources']:
                add_level_to_graph(g, r, p)
        except:
            pass
    elif t == 'task':
        print "adding task"
        p = add_with_type(g, 'task')
        g.vp.data[p]['command'] = n.get('command', ['flux', 'start'])
        add_edge_type(g, parent, p)
        connect_task(g, n, p)
    else:
        add_resources_to_graph(g, n, t, parent)
    # else:
    #     raise RuntimeError("unknown node type:" + t)


def to_resource_graph(tree):
    g = gt.Graph()
    g.ep.type = g.new_ep("string")
    g.vp.type = g.new_vp("string")
    g.vp.type = g.new_vp("string")
    g.ep.data = g.new_ep("object")
    g.vp.data = g.new_vp("object")
    g.vp.count_min = g.new_vp("int")
    g.vp.count_max = g.new_vp("int")
    g.vp.unit = g.new_vp("string")
    g.vp.label = g.new_vp("string")
    g.vp.pool = g.new_vp("bool")
    g.vp.slot_id = g.new_vp("string")
    g.vp.executable = g.new_vp("bool")
    root = add_with_type(g, 'root')
    add_level_to_graph(g, tree, root)
    return g


def print_res(n, s):
    print '-' * 20, n, '-' * 20
    print '-' * 20, 'size=', len(s), '-' * 20
    print s

def flatten(root):
    nodes = []
    links = []
    i = 0

    def recurse(node, ancestors):
        node['ancestors'] = ancestors
        nodes.append(node)
        node_id = len(nodes) - 1
        if (node.get('children', False)):
            for n in node['children']:
                links.append({
                    'source': node_id,
                    'target': recurse(n, list(ancestors) + [node, ]),
                })
        return node_id
    recurse(root, [])
    return (nodes, links)


def query(graph, match, limit=1):

    m = isomorphism.DiGraphMatcher(
        graph, match, node_match=isomorphism.categorical_node_match('type', 'resource'))
    print m.subgraph_is_isomorphic()
    # for i in  list(m.subgraph_isomorphisms_iter()):
    # for db, q in i.items():

    for db, q in m.mapping.items():
        print graph.node[db], '==', match.node[q]
    sys.exit(1)
    # for n in graph.successors_iter(0):
    #     print graph.node[n]
    #     print graph[n]
    return ""


class Interactive(cmd.Cmd):
    """Simple load/query interface"""

    def do_load(self, yaml_path):
        """
        load <yaml_path>
        Load jobspec information from the specified file.
        """
        with open(yaml_path) as f:
            self.canonical = canonicalize(f)
            # print self.canonical
            # sys.exit(1)
        self.graph = to_resource_graph(self.canonical)

        print "Successfully loaded", yaml_path

    def complete_load(self, text, line, begidx, endidx):
        completions = glob.glob(text + '*')
        return completions

    def do_draw(self, line):
        g = self.graph

        spectral = plt.get_cmap('spectral')
        n_levels = len(types)
        val = 0.0
        step = 1.0 / n_levels
        colors = {}
        for k in types.keys():
            colors[k] = spectral(val)
            val += step
        g.vp.v_colors = g.new_vp('vector<float>')
        for v in g.vertices():
            g.vp.v_colors[v] = colors[g.vp.type[v]]

        if line:
            gt_draw.graph_draw(self.graph,
                               pos=gt_draw.arf_layout(g),
                               output_size=(2400,2400),
                               vertex_text=g.vp.type,
                               vertex_fill_color=g.vp.v_colors,
                               vertex_size=10,
                               output=line)
        else:
            gt_draw.interactive_window(self.graph,
                                       vertex_fill_color=g.vp.v_colors,
                                       vertex_size=10,
                                       display_props=[g.vp.type,
                                                      g.vp.data,
                                                      g.vp.pool,
                                                      g.vp.unit ])
        # nx.draw_networkx(self.graph)
        # plt.show()
        # completions = glob.glob(text + '*')
        # return completions

    def do_export(self, line):
        """
        export [format] [path]
        Export the graph representation in <format> to a file at [path] or stdout
        """
        args = line.split()
        if 'graphml' == args[0]:
            self.graph.save(args[1] if len( args) > 1 else './meh.graphml')
            return
        # prepare for use with d3 TODO: needs to be fixed after GT conversion
        # gt = json_graph.tree_data(self.graph, 0)
        # (nodes, links) = flatten(gt)
        # gj = {'directed': True,
        #       'links': links,
        #       'nodes': nodes,
        #       'multigraph': True,
        #       'tree': gt,
        #       }
        # # print gt
        # # gj['edges'] = gj['links']
        # for v in gj['links']:
        #     v['id'] = get_id()
        #     # v['target'] = gj['nodes'][v['target']]['id']
        #     # v['source'] = gj['nodes'][v['source']]['id']
        #     v['to'] = v['target']
        #     v['from'] = v['source']
        # for v in gj['nodes']:
        #     v['size'] = 1
        #     v['r'] = 10
        #     v['x'] = 1
        #     v['y'] = 1
        #     v['label'] = v.get('Name', v['type'])
        #     # v['depth'] = nx.shortest_path_length(g, '0', v['id']) + 1
        # if len(args) > 1:
        #     f = open(args[1], 'w')
        # else:
        #     f = sys.stdout
        # if len(args) == 0 or args[0] == 'yaml':
        #     print >> f, yaml.dump(gj, indent=4)
        # elif args[0] == 'json':
        #     print >> f, json.dumps(gj, indent=4)
        # else:
        #     raise "crud"

    def do_export_canonical(self, path):
        """
        export_canonical  [path]
        Export the canonicalized yaml to a file at [path] or on stdout
        """
        if path:
            f = open(path, 'w')
        else:
            f = sys.stdout

        print
        print >> f, yaml.dump(self.canonical)

    def do_query(self, line):
        with open(line) as f:
            print query(self.graph, canonicalize(f))

    def do_EOF(self, line):
        return True

    def postloop(self):
        print

if __name__ == '__main__':
    Interactive().cmdloop()

    # for i, (doc, orig) in enumerate(parse(open(sys.argv[1]))):
    #     print '-' * 50
    #     print '-' * 20, "example", i, '-' * 20
    #     print '-' * 50
    #     print_res("YAML", yaml.dump(doc))
    #     print_res("YAML - no-inline", yaml.dump(doc, default_flow_style=False))
    #     try:
    #         print_res( "TOML", pytoml.dumps(doc))
    #     except:
    #         print "TOML FAILED TO SERIALIZE THIS..."
    #     print_res("SEXP", sexpdata.dumps(doc, false_as='F', true_as='T'))
    #     print_res("AXON - compact", axon.dumps(doc, crossref=1))
    #     print_res("AXON - statement", axon.dumps(doc, pretty=1, crossref=1))
    #     print_res("AXON - expression", axon.dumps(doc, pretty=1, braces=1, crossref=1))
    #     print_res("JSON - dense", json.dumps(doc, sort_keys=True))
    #     print_res("JSON - 'pretty'", json.dumps(doc, indent=2, sort_keys=True))
    # print yaml.dump_all(, default_flow_style=False)
