#include "field.hpp"

#include <gtest/gtest.h>

#include <string>

std::string basic_node = R"-yaml-(
type: Node
with:
    type: Socket
    count: 2
    with:
        type: Core
        count: 4
)-yaml-";

TEST (RSpec, Load)
{
    auto r = flux::field::ResourceSpec(basic_node);
}

