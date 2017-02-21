#ifndef __FLUX_RESOURCE_HPP
#define __FLUX_RESOURCE_HPP

#include <yaml-cpp/yaml.h>

#include <cmath>
#include <cstdint>
#include <exception>
#include <functional>
#include <string>

namespace flux
{
namespace field
{
struct Count {
    Count (int64_t min = 1, int64_t max = 1, int64_t operand = 1, char op = '+')
        : min (min), max (max > min ? max : min), operand (operand), op (op)
    {
        if (min < 0)
            throw std::invalid_argument (
                "Negative minimum counts are not supported");
        if (max < 0)
            throw std::invalid_argument (
                "Negative maximum counts are not supported");
        if (max <= 0)
            throw std::invalid_argument (
                "Negative or zero count operands are not supported");

        set_fn_from_op (op);
    }

    YAML::Node encode_yaml () const
    {
        YAML::Node node;

        node["min"] = min;
        node["max"] = max;
        node["operand"] = operand;
        node["operator"] = op;

        return node;
    }

    int64_t get_min ()
    {
        return min;
    }

    int64_t get_max ()
    {
        return max;
    };

    int64_t get_operand ()
    {
        return operand;
    };

    char get_op ()
    {
        return op;
    };

   private:
    int64_t min;
    int64_t max;
    int64_t operand;
    char op;
    std::function<int64_t (int64_t, int64_t)> next_fn;

    void set_fn_from_op (char op)
    {
        if (op == '+') {
            next_fn = std::plus<int64_t> ();
        } else if (op == '*') {
            next_fn = std::multiplies<int64_t> ();
        } else if (op == '^') {
            next_fn = [](int64_t b, int64_t exp) -> int64_t {
                return ceil (pow (b, exp));
            };
        } else {
            throw std::invalid_argument ("Operator is not one of +, * or ^");
        }
    }
};
}
}

namespace YAML
{
template <>
struct convert<flux::field::Count> {
    static Node encode (const flux::field::Count& rhs)
    {
        return rhs.encode_yaml ();
    }

    static bool decode (const Node& node, flux::field::Count& rhs)
    {
        if (node.IsScalar ()) {
            rhs = flux::field::Count (node.as<int64_t> ());
            return true;
        }

        if (!node.IsMap () || !node["min"]) {
            return false;
        }

        int64_t min = node["min"].as<int64_t> ();
        rhs = flux::field::Count (min,
                                  node["max"].as<int64_t> (min),
                                  node["operand"].as<int64_t> (1),
                                  node["operator"].as<char> ('+'));

        return true;
    }
};
}

#endif /* __FLUX_RESOURCE_HPP */
