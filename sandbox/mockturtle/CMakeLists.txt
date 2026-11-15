cmake_minimum_required(VERSION 3.16)
project(toffoli_sandbox_mockturtle LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

# mockturtle checkout lives in third_party/ (see sandbox/README.md)
set(MOCKTURTLE_DIR ${CMAKE_CURRENT_SOURCE_DIR}/../../third_party/mockturtle CACHE PATH "mockturtle source tree")
set(MOCKTURTLE_BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
set(MOCKTURTLE_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(MOCKTURTLE_BUILD_EXPERIMENTS OFF CACHE BOOL "" FORCE)
add_subdirectory(${MOCKTURTLE_DIR} mockturtle EXCLUDE_FROM_ALL)

add_executable(mc_flow mc_flow.cpp)
target_link_libraries(mc_flow PRIVATE mockturtle)
