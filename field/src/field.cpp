#include "field.hpp"

#include <yaml-cpp/yaml.h>
#include <iostream>

namespace flux {
namespace field {

ResourceSpec::ResourceSpec(const std::string& yaml_string){
    YAML::Node y = YAML::Load(yaml_string);


}

}
}
