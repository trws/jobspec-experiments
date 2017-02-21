#ifndef __FLUX_FIELD_EDGE_HPP
#define __FLUX_FIELD_EDGE_HPP

namespace flux
{
namespace field
{
struct EdgeType {
    std::string name;
};

struct Edge {
    ResourceType *type;
};
}
}

#endif /* __FLUX_FIELD_EDGE_HPP */
