cmake_minimum_required(VERSION 3.14)
project(nir_cpp LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)

find_package(pybind11 REQUIRED)

add_library(nir_cpp MODULE nir_controller.cpp py_nir.cpp)
target_link_libraries(nir_cpp PRIVATE pybind11::module visa)

if (WIN32)
    set_target_properties(nir_cpp PROPERTIES SUFFIX ".pyd")
endif()
