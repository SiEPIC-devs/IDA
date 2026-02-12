# Software Developers Guide to the Repo

This document will detail specifications on how to understand the repo, and some design decisions made. Please read this alogn-side the HAL architercture documentation and adding drivers guide before writting any code. This will be breadth rather than depth focused, as an overview.

## GUI

### Structure

"sub" modules correspond to pop out windows on the GUI. 

"main" modules correspond to tabs on the primary display window.

"mainframe" modules correspond to control modules relating to state instructions from the user to the managers.

"lib" modules correspond to libraries with helper functions related tools used in the mainframe modules and others

the runner is an access point that launches all sub processes, and tracks them as well such that when the software is closed, there are no stray PIDs.

UserData stores Configuration profiles and measurement data.

res stores temporary misc data like heat map sweeps, and automated measurement pathing (TSP)

Database stores information at runtime that is accessed by our modules. In particular, shared_memory.json is incredibly useful while debugging, as it shares 

### Important Notes

Each GUI window is hosted on a local distinct port. All processes run in the background upon initialization, and buttons on open unhid windows. The main controller for the whole system is based on the mainframe_stage_control_gui module, it intializes configurations, managers and keeps the state through shared_memory. Furthermore, this window keeps track of detector status, stage positioning and operational state for automated measurements, or any command. This allows the system to know whether the stage is active or not. 

