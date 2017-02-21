add_executable(unit count.cpp rspec.cpp task.cpp)
target_link_libraries(unit field gtest gtest_main)

add_test(NAME unit_tests COMMAND unit)

