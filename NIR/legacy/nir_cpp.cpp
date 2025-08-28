#include "nir_cpp.h"
#include <stdexcept>
#include <thread>
#include <chrono>
#include <iostream>
#include <cmath>

NIR8164::NIR8164(int com_port, int gpib_addr, int timeout_ms)
    : com_port_(com_port), gpib_addr_(gpib_addr), timeout_ms_(timeout_ms),
      defaultRM_(VI_NULL), vi_(VI_NULL), is_connected_(false) {}

NIR8164::~NIR8164() {
    disconnect();
}

bool NIR8164::connect() {
    ViStatus status = viOpenDefaultRM(&defaultRM_);
    if (status < VI_SUCCESS) throw std::runtime_error("Failed to open VISA resource manager");

    std::string resource = "ASRL" + std::to_string(com_port_) + "::INSTR";
    status = viOpen(defaultRM_, (ViRsrc)resource.c_str(), VI_NULL, VI_NULL, &vi_);
    if (status < VI_SUCCESS) throw std::runtime_error("Failed to open VISA resource");

    viSetAttribute(vi_, VI_ATTR_TMO_VALUE, timeout_ms_);
    viSetAttribute(vi_, VI_ATTR_TERMCHAR_EN, VI_FALSE);

    write("++mode 1");
    write("++auto 0");
    write("++eos 2");
    write("++eoi 1");
    write("++ifc");
    std::this_thread::sleep_for(std::chrono::milliseconds(50));
    write("++addr " + std::to_string(gpib_addr_));
    write("++clr");
    std::this_thread::sleep_for(std::chrono::milliseconds(50));

    auto idn = query("*IDN?");
    if (idn.empty()) return false;

    configure_units();
    is_connected_ = true;
    return true;
}

bool NIR8164::disconnect() {
    if (vi_ != VI_NULL) {
        viClose(vi_);
        vi_ = VI_NULL;
    }
    if (defaultRM_ != VI_NULL) {
        viClose(defaultRM_);
        defaultRM_ = VI_NULL;
    }
    is_connected_ = false;
    return true;
}

void NIR8164::write(const std::string &cmd) {
    ViUInt32 retCount;
    ViStatus status = viWrite(vi_, (ViBuf)cmd.c_str(), (ViUInt32)cmd.size(), &retCount);
    if (status < VI_SUCCESS) throw std::runtime_error("VISA write failed: " + cmd);
}

std::string NIR8164::query(const std::string &cmd, int sleep_ms) {
    write(cmd);
    std::this_thread::sleep_for(std::chrono::milliseconds(sleep_ms));
    write("++read eoi");

    char buffer[8192] = {0};
    ViUInt32 retCount = 0;
    ViStatus status = viRead(vi_, (ViBuf)buffer, sizeof(buffer)-1, &retCount);
    if (status < VI_SUCCESS) return "";
    return std::string(buffer, retCount);
}

// Laser control
void NIR8164::configure_units() {
    write("SOUR0:POW:UNIT 0");
    write("SENS1:CHAN1:POW:UNIT 0");
    write("SENS1:CHAN2:POW:UNIT 0");
}

void NIR8164::set_wavelength(double nm) {
    write("SOUR0:WAV " + std::to_string(nm*1e-9));
}

double NIR8164::get_wavelength() {
    auto v = query("SOUR0:WAV?");
    double x = std::stod(v);
    return (x < 1e-3) ? x*1e9 : x;
}

void NIR8164::set_power(double dbm) {
    write("SOUR0:POW:UNIT 0");
    write("SOUR0:POW " + std::to_string(dbm));
}

double NIR8164::get_power() {
    write("SOUR0:POW:UNIT 0");
    auto v = query("SOUR0:POW?");
    return std::stod(v);
}

void NIR8164::enable_output(bool on) {
    write("SOUR0:POW:STAT " + std::string(on ? "ON" : "OFF"));
}

bool NIR8164::get_output_state() {
    auto s = query("SOUR0:POW:STAT?");
    return s.find("1") != std::string::npos;
}

// Detector
void NIR8164::set_detector_units(int units) {
    write("SENS1:CHAN1:POW:UNIT " + std::to_string(units));
    write("SENS1:CHAN2:POW:UNIT " + std::to_string(units));
}

std::pair<double,double> NIR8164::read_power() {
    auto p1 = query("FETC1:CHAN1:POW?");
    auto p2 = query("FETC1:CHAN2:POW?");
    return {std::stod(p1), std::stod(p2)};
}

// Sweep
void NIR8164::set_sweep_range_nm(double start_nm, double stop_nm) {
    write("SOUR0:WAV:SWE:STAR " + std::to_string(start_nm*1e-9));
    write("SOUR0:WAV:SWE:STOP " + std::to_string(stop_nm*1e-9));
}

void NIR8164::set_sweep_step_nm(double step_nm) {
    write("SOUR0:WAV:SWE:STEP " + std::to_string(step_nm) + "NM");
}

void NIR8164::arm_sweep_cont_oneway() {
    write("SOUR0:WAV:SWE:MODE CONT");
    write("SOUR0:WAV:SWE:REP ONEW");
    write("SOUR0:WAV:SWE:CYCL 1");
}

void NIR8164::start_sweep() { write("SOUR0:WAV:SWE:STAT START"); }
void NIR8164::stop_sweep()  { write("SOUR0:WAV:SWE:STAT STOP"); }

std::string NIR8164::get_sweep_state() {
    return query("SOUR0:WAV:SWE:STAT?");
}

// Lambda scan
bool NIR8164::configure_and_start_lambda_sweep(double start_nm, double stop_nm, double step_nm,
                                               double laser_power_dbm, double avg_time_s) {
    try {
        set_power(laser_power_dbm);
        enable_output(true);
        set_wavelength(start_nm);

        set_sweep_range_nm(start_nm, stop_nm);
        set_sweep_step_nm(step_nm);
        write("SOUR0:WAV:SWE:SPE " + std::to_string(step_nm/avg_time_s) + "NM/S");
        arm_sweep_cont_oneway();
        write("SOUR0:AM:STAT OFF");

        write("SENS1:FUNC 'POWer'");
        int num_points = (int)((stop_nm - start_nm)/step_nm) + 1;
        std::string logg = std::to_string(num_points) + "," + std::to_string(avg_time_s);
        write("SENS1:FUNC:PAR:LOGG " + logg);
        write("SENS1:CHAN1:FUNC:PAR:LOGG " + logg);
        write("SENS1:CHAN2:FUNC:PAR:LOGG " + logg);

        write("SENS1:FUNC:STAT LOGG,START");
        return true;
    } catch (...) {
        return false;
    }
}

bool NIR8164::execute_lambda_scan(int timeout_s) {
    start_sweep();
    auto t0 = std::chrono::steady_clock::now();
    while (std::chrono::steady_clock::now() - t0 < std::chrono::seconds(timeout_s)) {
        auto swe = query("SOUR0:WAV:SWE:STAT?");
        auto fun = query("SENS1:CHAN1:FUNC:STAT?");
        if (fun.find("COMPLETE") != std::string::npos) return true;
        std::this_thread::sleep_for(std::chrono::seconds(1));
    }
    return false;
}

std::vector<float> NIR8164::query_binary_and_parse(const std::string &command) {
    write(command);
    write("++read eoi");

    char header[2];
    ViUInt32 retCount;
    viRead(vi_, (ViBuf)header, 2, &retCount);
    if (header[0] != '#') throw std::runtime_error("Invalid block header");
    int num_digits = header[1]-'0';

    std::vector<char> lenbuf(num_digits);
    viRead(vi_, (ViBuf)lenbuf.data(), num_digits, &retCount);
    int data_len = std::stoi(std::string(lenbuf.begin(), lenbuf.end()));

    std::vector<char> datablock(data_len);
    int remaining = data_len;
    int offset = 0;
    while (remaining > 0) {
        int chunk = std::min(remaining, 4096);
        viRead(vi_, (ViBuf)(datablock.data()+offset), chunk, &retCount);
        remaining -= retCount;
        offset += retCount;
    }

    int n = data_len/4;
    std::vector<float> arr(n);
    memcpy(arr.data(), datablock.data(), data_len);

    // Convert to dBm if positive
    for (auto &v: arr) {
        if (v > 0) v = 10*log10(v) + 30;
    }
    return arr;
}

std::tuple<std::vector<double>, std::vector<double>, std::vector<double>> NIR8164::retrieve_scan_data() {
    auto ch1 = query_binary_and_parse("SENS1:CHAN1:FUNC:RES?");
    auto ch2 = query_binary_and_parse("SENS1:CHAN2:FUNC:RES?");
    std::vector<double> wl(ch1.size());
    double start = std::stod(query("SOUR0:WAV:SWE:STAR?"))*1e9;
    double stop  = std::stod(query("SOUR0:WAV:SWE:STOP?"))*1e9;
    double step  = (stop-start)/(ch1.size()-1);
    for (size_t i=0; i<wl.size(); i++) wl[i] = start + i*step;
    return {wl, std::vector<double>(ch1.begin(), ch1.end()), std::vector<double>(ch2.begin(), ch2.end())};
}

void NIR8164::cleanup_scan() {
    try { write("SENS1:CHAN1:FUNC:STAT LOGG,STOP"); } catch(...) {}
    try { stop_sweep(); } catch(...) {}
    try { write("SOUR0:POW:STAT OFF"); } catch(...) {}
}
