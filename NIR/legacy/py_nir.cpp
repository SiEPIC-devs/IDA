// py_nir.cpp
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>   // for std::string, std::vector, std::pair
#include "nir_controller.h"

namespace py = pybind11;

PYBIND11_MODULE(nir_cpp, m) {
    m.doc() = "Python bindings for NIR8164 controller (Keysight 8164B)";

    py::class_<NIR8164>(m, "NIR8164")
        .def(py::init<int,int,int>(),
             py::arg("com_port")=3,
             py::arg("gpib_addr")=20,
             py::arg("timeout_ms")=30000)

        // lifecycle
        .def("connect", &NIR8164::connect)
        .def("disconnect", &NIR8164::disconnect)
        .def("is_connected", &NIR8164::is_connected)

        // laser
        .def("set_wavelength", &NIR8164::set_wavelength)
        .def("get_wavelength", &NIR8164::get_wavelength)
        .def("set_power", &NIR8164::set_power)
        .def("get_power", &NIR8164::get_power)
        .def("enable_output", &NIR8164::enable_output)
        .def("get_output_state", &NIR8164::get_output_state)

        // detector
        .def("set_detector_units", &NIR8164::set_detector_units)
        .def("read_power", &NIR8164::read_power)

        // sweep / scan
        .def("configure_and_start_lambda_sweep", &NIR8164::configure_and_start_lambda_sweep)
        .def("execute_lambda_scan", &NIR8164::execute_lambda_scan)
        .def("retrieve_scan_data", &NIR8164::retrieve_scan_data)
        .def("cleanup_scan", &NIR8164::cleanup_scan);
}
