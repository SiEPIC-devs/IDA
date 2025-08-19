import ctypes

# Step 1: What is kernel32?
# kernel32 is Windows' core system library that handles memory, files, processes
# Think of it as Windows' "toolbox" for low-level operations
kernel32 = ctypes.windll.kernel32


class ExplainedSharedMemory:
    def __init__(self, name, create=False):
        print(f"Creating shared memory named '{name}'...")
        
        if create:
            print("  -> Asking Windows: 'Give me a shared notebook'")
            # CreateFileMappingW = "Windows, create a shared memory block"
            # Parameters: handle(-1=new), security(None), protection(0x04=read/write), 
            #            size_high(0), size_low(1024), name
            self.handle = kernel32.CreateFileMappingW(-1, None, 0x04, 0, 1024, name)
            print(f"  -> Windows gave us handle: {self.handle}")
            
        else:
            print("  -> Asking Windows: 'Open existing shared notebook'")
            # OpenFileMappingW = "Windows, open existing shared memory"
            self.handle = kernel32.OpenFileMappingW(0xF001F, False, name)
            print(f"  -> Windows gave us handle: {self.handle}")
        
        print("  -> Now mapping it so we can actually use it...")
        # MapViewOfFile = "Let me actually access this memory"
        self.buffer = kernel32.MapViewOfFile(self.handle, 0xF001F, 0, 0, 1024)
        print(f"  -> Memory is now accessible at address: {self.buffer}")
        print()
    
    def write_data(self, text, position):
        print(f"WRITING '{text}' at position {position}")
        
        # Convert text to bytes (computers store text as numbers)
        data_bytes = text.encode('utf-8')
        print(f"  -> '{text}' becomes bytes: {data_bytes}")
        
        # Copy these bytes into shared memory at specific position
        # memmove = "copy data from here to there"
        ctypes.memmove(self.buffer + position, data_bytes, len(data_bytes))
        print(f"  -> Copied {len(data_bytes)} bytes to shared memory")
        print()
    
    def read_data(self, length, position):
        print(f"READING {length} bytes from position {position}")
        
        # Read raw bytes from shared memory
        raw_bytes = ctypes.string_at(self.buffer + position, length)
        print(f"  -> Got raw bytes: {raw_bytes}")
        
        # Convert bytes back to text
        text = raw_bytes.decode('utf-8').rstrip('\x00')  # Remove null terminators
        print(f"  -> Converted to text: '{text}'")
        print()
        return text

def demonstrate_step_by_step():
    print("=== DEMONSTRATION ===")
    print("Let's create shared memory and see what happens...")
    print()
    
    # Create the shared memory "notebook"
    shared_mem = ExplainedSharedMemory("my_notebook", create=True)
    
    # Write some data
    shared_mem.write_data("Hello World", 0)      # Write at position 0
    shared_mem.write_data("Python", 50)         # Write at position 50
    shared_mem.write_data("Instruments", 100)   # Write at position 100
    
    print("Memory now contains:")
    print("  Position 0-10: 'Hello World'")
    print("  Position 50-55: 'Python'")  
    print("  Position 100-110: 'Instruments'")
    print()
    
    # Read it back
    text1 = shared_mem.read_data(20, 0)     # Read 20 bytes from position 0
    text2 = shared_mem.read_data(10, 50)    # Read 10 bytes from position 50
    text3 = shared_mem.read_data(15, 100)   # Read 15 bytes from position 100
    
    print("=== WHAT JUST HAPPENED? ===")
    print("1. We asked Windows for shared memory space")
    print("2. Windows gave us a 'handle' (like a key to access it)")
    print("3. We 'mapped' it so our program can read/write")
    print("4. We copied data into specific positions")
    print("5. We read data back from those positions")
    print()
    print("If another program opened the same 'my_notebook',")
    print("it would see the exact same data!")

if __name__ == "__main__":
    demonstrate_step_by_step()