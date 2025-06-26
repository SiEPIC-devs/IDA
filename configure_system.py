import os 
import sys
import subprocess
import time

from multiprocessing import Process,Queue

cwd = os.getcwd()
main_path=os.path.split(cwd)
main_path=main_path[0]

logfile=open("log.txt",'w')
line_estimate=0

def print(string):
    global logfile
    global line_estimate
    max_linecount=500
    trim_size=100

    term=sys.stdout
    term.write(str(string)+"\n")
    term.flush()
    
    if line_estimate>max_linecount:
        #the log file is too large
        logfile.close()
        try:
            logfile=open("log.txt",'r')
            trim=logfile.readlines()
            logfile.close()
        except:
            logfile=open("log.txt",'w')
            logfile.write(str(string)+"\n")
            logfile.flush()
            return
        
        logfile=open("log.txt",'w')
        trim=trim[trim_size:]#remove the first lines
        #term.write(str(trim))
        #term.flush()
        new_line_count=0
        for line in trim:
            line=line.rstrip()
            logfile.write(str(line)+"\n")
            if line=="":
                continue
            new_line_count=new_line_count+1
        trim=[]#free memory
        line_estimate=new_line_count
        
    logfile.write(str(string)+"\n")
    logfile.flush()
    line_estimate=line_estimate+len(str(string).split('\n'))

def read_pipe(output,readQ):
    while True:
        raw=output.readline()
        string=raw.decode("ascii").rstrip()
        readQ.put(string)

def setup_non_block(value):
    readQ=Queue()
    thread = Process(target = read_pipe,args=(value,readQ))
    thread.start()
    return readQ
    
def non_block_read(readQ):
    try:
        return readQ.get(block=False)
    except:
        return ""

print("By Donald Witt")
dir_path = os.path.dirname(os.path.realpath(__file__))
print(sys.executable)
print(dir_path+"/NIR Detector/detector_init.py")

os.chdir(dir_path+"/NIR Detector")
detector_init = subprocess.Popen([sys.executable,"detector_init.py"], 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.STDOUT)

(output,err)=detector_init.communicate()
detector_init_status=detector_init.wait()

print("detector init")
print(output)
print(err)

os.chdir(dir_path+"/NIR laser")
laser_init = subprocess.Popen([sys.executable,"laser_init.py"], 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.STDOUT)

(output,err)=laser_init.communicate()
laser_init_status=laser_init.wait()

print("laser init")
print(output)
print(err)

os.chdir(dir_path+"/MMC 100")
stage_init=subprocess.Popen([sys.executable,"stage_init.py"], 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.STDOUT)

(output,err)=stage_init.communicate()
stage_init_status=stage_init.wait()

print("stage init")
print(output)
print(err)


os.chdir(dir_path+"/LDC Temperature Controller")
ldc_init=subprocess.Popen([sys.executable,"ldc_init.py"], 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.STDOUT)

(output,err)=ldc_init.communicate()
ldc_init_status=ldc_init.wait()

print("temperature control init")
print(output)
print(err)

os.chdir(dir_path+"/Camera")
camera_init=subprocess.Popen([sys.executable,"camera_init.py"], 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.STDOUT)

(output,err)=camera_init.communicate()
camera_init_status=camera_init.wait()

print("camera init")
print(output)
print(err)

#stage gui
print("launching stage gui")
os.chdir(dir_path+"/MMC 100")
stage_gui = subprocess.Popen([sys.executable,"stage_gui.pyc"], 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.STDOUT)

stage_q=(setup_non_block(stage_gui.stdout))
time.sleep(2)

#stage setup gui
print("launching stage setup gui")
os.chdir(dir_path+"/MMC 100")
stage_setup = subprocess.Popen([sys.executable,"stage_setup.pyc"], 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.STDOUT)
stage_setup_q=(setup_non_block(stage_setup.stdout))
time.sleep(2)

#temperature control gui
print("launching temperature gui")
os.chdir(dir_path+"/LDC Temperature Controller")
temperature_gui = subprocess.Popen([sys.executable,"temperature_gui.pyc"], 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.STDOUT)

temperature_q=(setup_non_block(temperature_gui.stdout))
time.sleep(2)

#laser gui
print("launching laser gui")
os.chdir(dir_path+"/NIR laser")
laser_gui = subprocess.Popen([sys.executable,"laser_gui.pyc"], 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.STDOUT)

laser_q=(setup_non_block(laser_gui.stdout))
time.sleep(2)

#detector gui
print("launching detector gui")
os.chdir(dir_path+"/NIR Detector")
detector_gui = subprocess.Popen([sys.executable,"detector_gui.pyc"], 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.STDOUT)

detector_q=(setup_non_block(detector_gui.stdout))
time.sleep(2)

#alignment gui
print("launching alignment gui")
os.chdir(dir_path+"/Alignment NIR")
alignment_gui = subprocess.Popen([sys.executable,"alignment_gui.pyc"], 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.STDOUT)

alignment_q=(setup_non_block(alignment_gui.stdout))
time.sleep(2)

#plot gui
print("launching plot gui")
os.chdir(dir_path+"/Plot")
plot_gui = subprocess.Popen([sys.executable,"plot_gui.pyc"], 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.STDOUT)

plot_q=(setup_non_block(plot_gui.stdout))
time.sleep(2)

#camera gui
print("launching camera gui")
os.chdir(dir_path+"/Camera")
camera_gui = subprocess.Popen([sys.executable,"camera_gui.pyc"], 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.STDOUT)
camera_q=(setup_non_block(camera_gui.stdout))
time.sleep(2)

#terminal gui
print("launching terminal gui")
os.chdir(dir_path+"/Terminal")
terminal_gui = subprocess.Popen([sys.executable,"terminal_gui.pyc"], 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.STDOUT)

terminal_q=(setup_non_block(terminal_gui.stdout))
time.sleep(2)

#files gui
print("launching files gui")
os.chdir(dir_path+"/File Import")
files_gui = subprocess.Popen([sys.executable,"files_gui.pyc"], 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.STDOUT)

file_q=(setup_non_block(files_gui.stdout))
time.sleep(2)

print("launching script gui")
script_gui = subprocess.Popen([sys.executable,"script_gui.pyc"], 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.STDOUT)

script_q=(setup_non_block(script_gui.stdout))
time.sleep(2)

print("launching selection gui")
selection_gui = subprocess.Popen([sys.executable,"selection_gui.pyc"], 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.STDOUT)

selection_q=(setup_non_block(selection_gui.stdout))
time.sleep(2)

print("launching run gui")
run_gui = subprocess.Popen([sys.executable,"run_gui.pyc"], 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.STDOUT)

run_q=(setup_non_block(run_gui.stdout))
time.sleep(2)

#main gui
print("launching main gui")
os.chdir(dir_path)
main = subprocess.Popen([sys.executable,"main_gui.pyc"], 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.STDOUT)

main_q=(setup_non_block(main.stdout))
time.sleep(2)

try:
    while True:
        string=str(non_block_read(stage_q))
        if string:
            print(string)
            
        string=str(non_block_read(stage_setup_q))
        if string:
            print(string)
            
        string=str(non_block_read(temperature_q))
        if string:
            print(string)
            
        string=str(non_block_read(laser_q))
        if string:
            print(string)
            
        string=str(non_block_read(detector_q))
        if string:
            print(string)
            
        string=str(non_block_read(alignment_q))
        if string:
            print(string)
            
        string=str(non_block_read(plot_q))
        if string:
            print(string)
            
        string=str(non_block_read(terminal_q))
        if string:
            print(string)
            
        string=str(non_block_read(file_q))
        if string:
            print(string)
            
        string=str(non_block_read(script_q))
        if string:
            print(string)
        
        string=str(non_block_read(selection_q))
        if string:
            print(string)

        string=str(non_block_read(run_q))
        if string!="":
            print(string)
        
        string=str(non_block_read(camera_q))
        if string!="":
            print(string)

        string=str(non_block_read(main_q))
        if string:
            print(string)
            
        #check if the process are still running (laser and detector)
        if laser_gui.poll() is not None:
            print("Laser process has crashed!!")
            time.sleep(45)
            try:
                laser_gui.kill()
            except:
                pass
            
            try:
                detector_gui.kill()
            except:
                pass
            
            os.chdir(dir_path+"/NIR Detector")
            detector_init = subprocess.Popen([sys.executable,"detector_init.py"], 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.STDOUT)

            (output,err)=detector_init.communicate()
            detector_init_status=detector_init.wait()

            print("detector init")
            print(output)
            print(err)

            os.chdir(dir_path+"/NIR laser")
            laser_init = subprocess.Popen([sys.executable,"laser_init.py"], 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.STDOUT)

            (output,err)=laser_init.communicate()
            laser_init_status=laser_init.wait()

            print("laser init")
            print(output)
            print(err)
            
            #laser gui
            print("launching laser gui")
            os.chdir(dir_path+"/NIR laser")
            laser_gui = subprocess.Popen([sys.executable,"laser_gui.pyc"], 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.STDOUT)

            laser_q=(setup_non_block(laser_gui.stdout))
            time.sleep(2)

            #detector gui
            print("launching detector gui")
            os.chdir(dir_path+"/NIR Detector")
            detector_gui = subprocess.Popen([sys.executable,"detector_gui.pyc"], 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.STDOUT)

            detector_q=(setup_non_block(detector_gui.stdout))


        if detector_gui.poll() is not None:
            print("detector process has crashed!!")
            time.sleep(45)
            try:
                laser_gui.kill()
            except:
                pass
            
            try:
                detector_gui.kill()
            except:
                pass
            
            os.chdir(dir_path+"/NIR Detector")
            detector_init = subprocess.Popen([sys.executable,"detector_init.py"], 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.STDOUT)

            (output,err)=detector_init.communicate()
            detector_init_status=detector_init.wait()

            print("detector init")
            print(output)
            print(err)

            os.chdir(dir_path+"/NIR laser")
            laser_init = subprocess.Popen([sys.executable,"laser_init.py"], 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.STDOUT)

            (output,err)=laser_init.communicate()
            laser_init_status=laser_init.wait()

            print("laser init")
            print(output)
            print(err)
            
            
            #laser gui
            print("launching laser gui")
            os.chdir(dir_path+"/NIR laser")
            laser_gui = subprocess.Popen([sys.executable,"laser_gui.pyc"], 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.STDOUT)

            laser_q=(setup_non_block(laser_gui.stdout))
            time.sleep(2)

            #detector gui
            print("launching detector gui")
            os.chdir(dir_path+"/NIR Detector")
            detector_gui = subprocess.Popen([sys.executable,"detector_gui.pyc"], 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.STDOUT)

            detector_q=(setup_non_block(detector_gui.stdout))
            
        if run_gui.poll() is not None:
            print("run process has crashed!!")
            time.sleep(45)
            try:
                laser_gui.kill()
            except:
                pass
            
            try:
                detector_gui.kill()
            except:
                pass
            
            try:
                run_gui.kill()
            except:
                pass
            
            #reinit the stage
            os.chdir(dir_path+"/MMC 100")
            stage_init=subprocess.Popen([sys.executable,"stage_init.py"], 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.STDOUT)

            (output,err)=stage_init.communicate()
            stage_init_status=stage_init.wait()

            print("stage init")
            print(output)
            print(err)
            
            
            os.chdir(dir_path+"/NIR Detector")
            detector_init = subprocess.Popen([sys.executable,"detector_init.py"], 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.STDOUT)

            (output,err)=detector_init.communicate()
            detector_init_status=detector_init.wait()

            print("detector init")
            print(output)
            print(err)

            os.chdir(dir_path+"/NIR laser")
            laser_init = subprocess.Popen([sys.executable,"laser_init.py"], 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.STDOUT)

            (output,err)=laser_init.communicate()
            laser_init_status=laser_init.wait()

            print("laser init")
            print(output)
            print(err)
            
            
            #laser gui
            print("launching laser gui")
            os.chdir(dir_path+"/NIR laser")
            laser_gui = subprocess.Popen([sys.executable,"laser_gui.pyc"], 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.STDOUT)

            laser_q=(setup_non_block(laser_gui.stdout))
            time.sleep(2)

            #detector gui
            print("launching detector gui")
            os.chdir(dir_path+"/NIR Detector")
            detector_gui = subprocess.Popen([sys.executable,"detector_gui.pyc"], 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.STDOUT)

            detector_q=(setup_non_block(detector_gui.stdout))
            
            #run gui
            print("launching run gui")
            os.chdir(dir_path+"/File Import")
            run_gui = subprocess.Popen([sys.executable,"run_gui.py"], 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.STDOUT)

            run_q=(setup_non_block(run_gui.stdout))
            time.sleep(2)
except:
    pass

print("exit")
main.kill()
stage_gui.kill()
stage_setup.kill()
laser_gui.kill()
detector_gui.kill()
plot_gui.kill()
camera_gui.kill()
terminal_gui.kill()
files_gui.kill()
script_gui.kill()
selection_gui.kill()
run_gui.kill()
