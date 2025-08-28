#pragma once
#include <visa.h>
#include <string>
#include <vector>

class NIR8164 {
public:
    NIR8164(int com_port = 3, int gpib_addr = 20, int timeout_ms = 30000);
    ~NIR8164();

    bool connect();
    bool disconnect();
    bool is_connected() const { return is_connected_; }

    // Core communication
    void write(const std::string &cmd);
    std::string query(const std::string &cmd, int sleep_ms = 20);

    // Laser functions
    void configure_units();
    void set_wavelength(double nm);
    double get_wavelength();
    void set_power(double dbm);
    double get_power();
    void enable_output(bool on);
    bool get_output_state();

    // Detector
    void set_detector_units(int units = 0);
    std::pair<double,double> read_power();

    // Sweep
    void set_sweep_range_nm(double start_nm, double stop_nm);
    void set_sweep_step_nm(double step_nm);
    void arm_sweep_cont_oneway();
    void start_sweep();
    void stop_sweep();
    std::string get_sweep_state();

    // Lambda scan
    bool configure_and_start_lambda_sweep(double start_nm, double stop_nm, double step_nm,
                                          double laser_power_dbm = -10, double avg_time_s = 0.01);
    bool execute_lambda_scan(int timeout_s = 300);
    std::tuple<std::vector<double>, std::vector<double>, std::vector<double>> retrieve_scan_data();

    void cleanup_scan();

private:
    int com_port_;
    int gpib_addr_;
    int timeout_ms_;
    ViSession defaultRM_;
    ViSession vi_;
    bool is_connected_;

    std::vector<float> query_binary_and_parse(const std::string &command);
};
