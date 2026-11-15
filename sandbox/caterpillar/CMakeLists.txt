cmake_minimum_required(VERSION 3.16)
project(toffoli_sandbox_caterpillar LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

# caterpillar (Nov 2020) bundles its own mockturtle/tweedledum/lorina in lib/.
# Its old code warns a lot on GCC 15; silence it, we are only reading it.
set(CATERPILLAR_DIR ${CMAKE_CURRENT_SOURCE_DIR}/../../third_party/caterpillar CACHE PATH "caterpillar source tree")
set(CATERPILLAR_TEST OFF CACHE BOOL "" FORCE)
add_compile_options(-w)
add_subdirectory(${CATERPILLAR_DIR} caterpillar EXCLUDE_FROM_ALL)

add_executable(strategies strategies.cpp)
target_link_libraries(strategies PRIVATE caterpillar)
