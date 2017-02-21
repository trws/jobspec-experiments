#ifndef __FLUX_TASK_HPP
#define __FLUX_TASK_HPP

#include <yaml-cpp/yaml.h>

#include <cmath>
#include <cstdint>
#include <exception>
#include <functional>
#include <list>
#include <map>
#include <string>

namespace flux
{
namespace field
{
class Task
{
   public:
    enum SlotType { SlotLevel, SlotLabel };

    enum CountType { CountPerSlot, CountTotal };

    Task (std::list<std::string> command = {"flux", "start"},
          SlotType slot_type = SlotLevel,
          std::string slot = "node",
          CountType count_type = CountPerSlot,
          int64_t count = 1,
          std::string distribution = "???",
          std::map<std::string, std::string> attrs = {})
        : command (command),
          slot_type (slot_type),
          slot (slot),
          count_type (count_type),
          count (count),
          distribution (distribution),
          attrs (attrs)
    {
        if (command.size () == 0 || command.front ().size () == 0)
            throw std::invalid_argument (
                "An empty command is not allowed when creating a task");
    }

    YAML::Node encode_yaml () const
    {
        YAML::Node node;

        node["command"] = command;

        if (slot_type == SlotLabel)
            node["slot"]["label"] = slot;
        else
            node["slot"] =
                std::map<std::string, std::string> ({{"level", slot}});

        if (count_type == CountPerSlot)
            node["count"]["per_slot"] = count;
        else
            node["count"]["total"] = count;

        node["distribution"] = distribution;
        if (attrs.size () > 0)
            node["attrs"] = attrs;

        return node;
    }

    bool operator== (const Task &rhs) const
    {
        return command == rhs.command && slot_type == rhs.slot_type
               && slot == rhs.slot && count_type == rhs.count_type
               && count == rhs.count && distribution == rhs.distribution
               && attrs == rhs.attrs;
    }

    bool operator!= (const Task &rhs) const
    {
        return !(rhs == *this);
    }

   private:
    std::list<std::string> command;
    SlotType slot_type;
    std::string slot;
    CountType count_type;
    int64_t count;
    std::string distribution;
    std::map<std::string, std::string> attrs;

   public:
    SlotType getSlot_type () const
    {
        return slot_type;
    }

    CountType getCount_type () const
    {
        return count_type;
    }

    const std::list<std::string, std::allocator<std::string>> &getCommand ()
        const
    {
        return command;
    }

    const std::string &getSlot () const
    {
        return slot;
    }

    const int64_t &getCount () const
    {
        return count;
    }

    const std::string &getDistribution () const
    {
        return distribution;
    }

    const std::map<std::string, std::string> &getAttrs () const
    {
        return attrs;
    }
};
}
}

namespace YAML
{
template <>
struct convert<flux::field::Task> {
    static Node encode (const flux::field::Task &rhs)
    {
        return rhs.encode_yaml ();
    }

    static bool decode (const Node &node, flux::field::Task &rhs)
    {
        // Validity checks
        if (!node.IsMap ()) {
            return false;
        }

        if (!node["command"]
            || !(node["command"] && node["command"].IsSequence ())
            || !(node["count"] && node["count"].IsMap ())
            || !(node["slot"] && node["slot"].IsMap ())
            || !node["distribution"]) {
            return false;
        }

        using namespace flux::field;
        using namespace std;
        rhs = Task (node["command"].as<list<string>> (list<string> ()),
                    node["slot"]["level"] ? Task::SlotLevel : Task::SlotLabel,
                    node["slot"]["level"]
                        ? node["slot"]["level"].as<std::string> ("")
                        : node["slot"]["label"].as<std::string> (""),
                    node["count"]["total"] ? Task::CountTotal
                                           : Task::CountPerSlot,
                    (node["count"]["total"] ? node["count"]["total"]
                                            : node["count"]["per_slot"])
                        .as<int64_t> (),
                    node["distribution"].as<std::string> ("???"),
                    node["attrs"].as<std::map<std::string, std::string>> ());

        return true;
    }
};
}

#endif /* __FLUX_TASK_HPP */
