#ifndef __FLUX_FIELD_HPP
#define __FLUX_FIELD_HPP

#include "resource.hpp"

#include <boost/graph/adjacency_list.hpp>
#include <list>
#include <map>
#include <set>
#include <string>

namespace flux
{
namespace field
{

using graph_type =
    boost::adjacency_list<boost::listS, boost::vecS, boost::bidirectionalS>;

struct ResourceSpec {
    ResourceSpec () = delete;
    ResourceSpec (const std::string& yaml_string);

   private:
    graph_type graph;
    std::set<ResourceType> types;
};
}
}

#endif /* __FLUX_FIELD_HPP */
