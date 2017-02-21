//
// Created by Thomas Richard William Scogland on 8/15/16.
//

#include "task.hpp"

#include <exception>
#include <string>
#include <iostream>
#include <sstream>

#include <gtest/gtest.h>


std::string canonical_task = R"(
command: [ flux, start, doing, things ]
slot: { level : core }
count: { total : 15 }
distribution: random
attrs:
  stuff: things
  other_stuff: more things
)";


using namespace flux::field;
using namespace std;

TEST(Task, LoadCanonical) {
  auto y = YAML::Load(canonical_task);
  Task t(y.as<Task>());

  EXPECT_EQ(t.getCommand(), list<string>({"flux", "start", "doing", "things"}));
  EXPECT_EQ(t.getSlot_type(), Task::SlotLevel);
  EXPECT_EQ(t.getSlot(), "core");
  EXPECT_EQ(t.getCount_type(), Task::CountTotal);
  EXPECT_EQ(t.getCount(), 15);
  EXPECT_EQ(t.getDistribution(), "random");
  EXPECT_EQ(t.getAttrs().find("stuff")->second, "things");
  EXPECT_EQ(t.getAttrs().find("other_stuff")->second, "more things");
}

TEST(Task, EmitCanonical) {
  auto y = YAML::Load(canonical_task);
  Task t(y.as<Task>());

  YAML::Node n;
  n["task"] = t;
  ostringstream ss;
  ss << n["task"];
  Task reloaded(YAML::Load(ss.str()).as<Task>());
  EXPECT_EQ(t, reloaded);
}
