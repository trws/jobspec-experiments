package main

import (
        "fmt"
        "log"
        "os"
        // "errors"

        // YAML parsing
        "gopkg.in/yaml.v2"

        // Graph library
        "github.com/gonum/graph"
        "github.com/gonum/graph/simple"

        // Graph database
        "github.com/cayleygraph/cayley"
        "github.com/cayleygraph/cayley/quad"
        "github.com/cayleygraph/cayley/exporter"

        // Uuids
        "github.com/satori/go.uuid"
)

var data = `
a: Easy!
b:
  c: 2
  d: [3, 4]
`

var task_data = `
command: [ flux, start, doing, things ]
slot: { level : core }
count: { total : 15 }
distribution: random
attrs:
  stuff: things
  other_stuff: more things
`

var jobspec_data = `
version: 1
walltime: 1h
resources:
  - type: node
    count: 4
    with:
      - type: socket
        count:
            min: 5
            max: 15
        with:
          - type: core
            count: 4
`
type resourceCountInner struct {
    Min int
    Max int
    Operand int
    Operator string
}

type ResourceCount struct {
    resourceCountInner
}

func NewResourceCount() *ResourceCount {
    r := ResourceCount{
        resourceCountInner:
            resourceCountInner{
                Max: 1,
                Min: 1,
                Operator: "+",
                Operand: 1,
            },
    }
    return &r
}

func (r *ResourceCount) UnmarshalYAML(unmarshal func(v interface{}) error) error {
    *r = *NewResourceCount()
    // set defaults
    if err := unmarshal(&r.Max); err == nil{
        // Single number, treat as Max and Min
        r.Min = r.Max
        return nil
    }
    if err := unmarshal(&r.resourceCountInner); err != nil{
        return err
    }
    return nil
}

type Vertex struct {
    Type string
    Count ResourceCount
    Unit string
    Exclusive bool
    With []Vertex
    Id int
    Uuid uuid.UUID
    Tags []string
    Attributes map[string] interface{}
    //Edge non-with or more specific edges
}

func (v *Vertex) ID() int {
    return v.Id
}

type Task struct {
    Command []string
    Slot map[string]string
    Count map[string]uint64
    Distribution string
    Attrs map[string] interface{}
}

type JobSpec struct {
    Resources []Vertex
    Tasks []Task
    Walltime string
    Attrs map[string] interface{}
}

var next_vertex_id = 0

func addQuads(g *cayley.Handle, v *Vertex) error {
    if v.Uuid == uuid.Nil {
        v.Uuid = uuid.NewV4()
    }
    g.AddQuad(quad.Make(v.Uuid, "type", v.Type, nil))
    g.AddQuad(quad.Make(v.Uuid, "id", v.Id, nil))
    g.AddQuad(quad.Make(v.Uuid, "exclusive", v.Exclusive, nil))
    // TODO: tags, attributes, count, unit
    for _, nv := range v.With {
        addQuads(g, &nv)
        g.AddQuad(quad.Make(v.Uuid, "with", nv.Uuid, nil))
    }
    return  nil
}

func fillCayleyGraph(g *cayley.Handle, j *JobSpec) error {
    for _, v := range j.Resources {
        addQuads(g, &v)
    }

    return nil
}

func addVertices(g graph.NodeAdder, v *Vertex) error {
    for _, nv := range v.With {
        addVertices(g, &nv)
    }
    for v.Id == 0 {
        v.Id = g.NewNodeID()
        fmt.Println("adding node id", v.Id)
    }
    g.AddNode(v)
    return  nil
}

func fillGraph(g graph.NodeAdder, j *JobSpec) error {
    for _, v := range j.Resources {
        addVertices(g, &v)
    }

    return nil
}

var hype = `
resources:
    type: Cluster
    name: Hype
    with:
        type: Node
        names: hype[201-354]
        with:
            type: Socket
            count: 2
            with:
                - type: Core
                  count: 8
                - type: Memory
                  count: 15000
                  unit: MB
`

func main() {
    // Create a brand new graph
    store, err := cayley.NewMemoryGraph()
    if err != nil {
        log.Fatalln(err)
    }

    // store.AddQuad(quad.Make("phrase of the day", "is of course", "Hello World!", nil))
    //
    // // Now we create the path, to get to our data
    // p := cayley.StartPath(store, quad.String("phrase of the day")).Out(quad.String("is of course"))
    //
    // // Now we iterate over results. Arguments:
    // // 1. Optional context used for cancellation.
    // // 2. Flag to optimize query before execution.
    // // 3. Quad store, but we can omit it because we have already built path with it.
    // err = p.Iterate(nil).EachValue(nil, func(value quad.Value){
    //     nativeValue := quad.NativeOf(value) // this converts RDF values to normal Go types
    //     fmt.Println(nativeValue)
    // })
    // if err != nil {
    //     log.Fatalln(err)
    // }
    t := JobSpec{}

    if err := yaml.Unmarshal([]byte(jobspec_data), &t); err != nil {
        log.Fatalf("error: %v", err)
    }
    fmt.Printf("--- t:\n%v\n\n", t)

    if false {
        fillCayleyGraph(store, &t)

        w := exporter.NewExporter(os.Stdout, store)
        w.ExportJson()
    }


    g := simple.NewDirectedGraph(0, 1)
    root := Vertex{Type: "root", Id: 0}
    g.AddNode(&root)
    fillGraph(g, &t)


    // p := cayley.StartPath(store).Save("type", "source").Save("exclusive", "exclusive")
    //
    // // Now we iterate over results. Arguments:
    // // 1. Optional context used for cancellation.
    // // 2. Flag to optimize query before execution.
    // // 3. Quad store, but we can omit it because we have already built path with it.
    // err = p.Iterate(nil).EachValue(nil, func(value quad.Value){
    //     // nativeValue := quad.NativeOf(value) // this converts RDF values to normal Go types
    //     // fmt.Println(nativeValue)
    //     fmt.Println(value)
    // })
    // if err != nil {
    //     log.Fatalln(err)
    // }
    //
    // d, err := yaml.Marshal(&t)
    // if err != nil {
    //     log.Fatalf("error: %v", err)
    // }
    // fmt.Printf("--- t dump:\n%s\n\n", string(d))
    //
    // m := make(map[interface{}]interface{})
    //
    // err = yaml.Unmarshal([]byte(jobspec_data), &m)
    // if err != nil {
    //     log.Fatalf("error: %v", err)
    // }
    // fmt.Printf("--- m:\n%v\n\n", m)
    //
    // d, err = yaml.Marshal(&m)
    // if err != nil {
    //     log.Fatalf("error: %v", err)
    // }
    // fmt.Printf("--- m dump:\n%s\n\n", string(d))
}
