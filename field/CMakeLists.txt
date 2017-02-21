cmake_minimum_required(VERSION 3.5)
project(field)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED On)

include_directories(include)

enable_testing()

add_subdirectory(external)
add_subdirectory(src)
add_subdirectory(test)

