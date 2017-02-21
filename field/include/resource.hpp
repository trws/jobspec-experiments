#ifndef __FLUX_RESOURCE_HPP
#define __FLUX_RESOURCE_HPP

#include <string>
#include <cstdint>
#include <boost/uuid/uuid.hpp>

namespace flux
{
namespace field
{

struct ResourceType {
    std::string name;
};

struct Resource {
    std::string name;
    uint64_t id;
    boost::uuids::uuid uuid;
    ResourceType *type;
};

}
}

#endif /* __FLUX_RESOURCE_HPP */
