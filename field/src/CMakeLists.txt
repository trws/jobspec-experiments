find_package (PkgConfig)
pkg_check_modules ( YAML REQUIRED yaml-cpp )
link_directories (${YAML_LIBRARY_DIRS})
include_directories (${YAML_INCLUDE_DIRS})

add_library(field
        field.cpp
        ${CMAKE_SOURCE_DIR}/include/count.hpp
        ${CMAKE_SOURCE_DIR}/include/task.hpp
        #${CMAKE_SOURCE_DIR}/include/count.hpp
        #${CMAKE_SOURCE_DIR}/include/count.hpp
        )

target_link_libraries(field ${YAML_LIBRARIES})

