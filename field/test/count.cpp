#include "count.hpp"

#include <gtest/gtest.h>

#include <exception>
#include <string>

std::string canonical_count = R"-yaml-(
min: 1
max: 10
operand: 1
operator: +
)-yaml-";

TEST (Count, LoadCanonical)
{
    auto y = YAML::Load (canonical_count);
    flux::field::Count c = y.as<flux::field::Count> ();
    EXPECT_EQ (c.get_min (), 1);
    EXPECT_EQ (c.get_max (), 10);
    EXPECT_EQ (c.get_operand (), 1);
    EXPECT_EQ (c.get_op (), '+');
}

TEST (Count, LoadScalar)
{
    auto y = YAML::Load ("15");
    flux::field::Count c = y.as<flux::field::Count> ();
    EXPECT_EQ (c.get_min (), 15);
    EXPECT_EQ (c.get_max (), 15);
    EXPECT_EQ (c.get_operand (), 1);
    EXPECT_EQ (c.get_op (), '+');
}

TEST (Count, LoadInvalidScalarString)
{
    auto y = YAML::Load ("hello");
    flux::field::Count c;
    ASSERT_THROW (c = y.as<flux::field::Count> (), YAML::BadConversion);
}

TEST (Count, LoadInvalidScalarNegative)
{
    auto y = YAML::Load ("-15");
    flux::field::Count c;
    ASSERT_THROW (c = y.as<flux::field::Count> (), std::invalid_argument);
}
