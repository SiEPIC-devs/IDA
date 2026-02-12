# GUI连接配置流程说明

## 概览
你的GUI界面通过一个配置系统将用户选择的设备驱动连接到实际硬件。以下是完整的数据流程。

---

## 1. 用户界面选择

在 `main_instruments_gui.py` 中，你看到的界面：

```
Laser / Detector: [8164B_NIR ▼]  [Connect]
TEC:             [8164B_NIR ▼]  [Connect]  
SMU:             [Dummy_B   ▼]  [Connect]
```

### 可用选项：

**Laser / Detector (sensor):**
- `8164B_NIR` - HP/Agilent 8164B单个或多个主机
- `luna_controller` - Luna OVA系统
- `Dummy_B` - 测试用虚拟设备

**TEC:**
- `srs_ldc_502` - Stanford Research LDC502
- `srs_ldc_501` - Stanford Research LDC501
- `Dummy_B` - 测试用虚拟设备

**SMU:**
- `keithley_2600` - Keithley 2600系列
- `Dummy_A` / `Dummy_B` - 测试用虚拟设备

---

## 2. GPIB地址配置

点击 **"Configure VISA"** 按钮打开配置窗口 (`sub_connect_config_gui.py`)：

```
Stage:     [COM7 ▼]
TEC:       [GPIB0::7::INSTR ▼]
SMU:       [GPIB0::26::INSTR ▼]
Laser:     [GPIB0::20::INSTR ▼]
Detector:  [None ▼]
           [Confirm]
```

### 工作原理：

1. **自动扫描**: 系统自动扫描所有可用的VISA资源
2. **选择地址**: 从下拉菜单选择对应的GPIB地址
3. **Detector选项**:
   - `None` = 单个主机模式（laser和detector在同一设备）
   - 具体地址 = 多主机模式（laser和detector分开）
4. **保存配置**: 点击"Confirm"保存到 `database/shared_memory.json`

### 配置保存格式：

```json
{
  "Port": {
    "stage": "COM7",
    "tec": "GPIB0::7::INSTR",
    "smu": "GPIB0::26::INSTR",
    "laser_gpib": "GPIB0::20::INSTR",
    "detector_gpib": null
  }
}
```

---

## 3. 连接流程

### Step 1: 选择驱动
用户在主界面选择驱动类型（如 `8164B_NIR`）

### Step 2: 配置地址
点击"Configure VISA"设置GPIB地址

### Step 3: 点击Connect
点击"Connect"按钮后：

```python
# main_instruments_gui.py - onclick_sensor_connect_btn()
self.configuration["sensor"] = "8164B_NIR"  # 从下拉框获取
File("shared_memory", "Configuration", self.configuration).save()
```

保存到JSON：
```json
{
  "Configuration": {
    "stage": "Corvus_controller",
    "sensor": "8164B_NIR",
    "tec": "srs_ldc_501",
    "smu": "keithley_2600"
  }
}
```

### Step 4: 后台连接处理

在 `mainframe_stage_control_gui.py` 的 `after_configuration()` 方法中：

```python
# 检测到configuration["sensor"]不为空
if self.configuration["sensor"] != "" and self.configuration_sensor == 0:
    # 1. 创建NIR配置
    self.nir_configure = NIRConfiguration()
    self.nir_configure.driver_types = "8164B_NIR"  # 从configuration读取
    
    # 2. 读取GPIB地址配置
    laser = self.port.get("laser_gpib")      # "GPIB0::20::INSTR"
    detector = self.port.get("detector_gpib")  # None (单主机模式)
    
    # 3. 根据配置决定模式
    if laser == detector or detector is None:
        # 单主机模式
        self.nir_configure.laser_slot = "GPIB0::20::INSTR"
        self.nir_configure.detector_slots = []
    else:
        # 多主机模式
        self.nir_configure.laser_slot = "GPIB0::20::INSTR"
        self.nir_configure.detector_slots = ["GPIB0::21::INSTR"]
    
    # 4. 创建NIR Manager并初始化
    self.nir_manager = NIRManager(self.nir_configure)
    success = self.nir_manager.initialize()
    
    # 5. 更新连接状态
    if success:
        self.configuration_check["sensor"] = 2  # 连接成功
    else:
        self.configuration_check["sensor"] = 1  # 连接失败
```

---

## 4. 驱动注册系统

### NIR驱动注册（在 `nir_controller.py`）：

```python
# 底部注册所有驱动
register_driver("8164B_NIR", NIR8164)
register_driver("MF_NIR", MF_NIR_controller)
register_driver("luna_controller", LunaController)
```

### 驱动工厂（在 `nir_manager.py`）：

```python
def nir_factory(driver_type: str):
    """根据driver_types字符串创建对应的controller"""
    if driver_type == "8164B_NIR":
        return NIR8164()
    elif driver_type == "MF_NIR":
        return MF_NIR_controller()
    elif driver_type == "luna_controller":
        return LunaController()
    # ...
```

### NIRManager初始化：

```python
class NIRManager:
    def __init__(self, config: NIRConfiguration):
        self.config = config
        # 使用工厂创建controller
        self.controller = nir_factory(config.driver_types)
    
    def initialize(self):
        # 调用controller的connect方法
        return self.controller.connect(
            gpib_addr=self.config.laser_slot,
            detector_addrs=self.config.detector_slots
        )
```

---

## 5. 完整数据流图

```
用户界面
   ↓
[选择驱动: 8164B_NIR] → Configuration.sensor = "8164B_NIR"
   ↓
[Configure VISA] → Port.laser_gpib = "GPIB0::20::INSTR"
   ↓                Port.detector_gpib = None
[Click Connect]
   ↓
mainframe_stage_control_gui.after_configuration()
   ↓
NIRConfiguration(
    driver_types = "8164B_NIR",
    laser_slot = "GPIB0::20::INSTR",
    detector_slots = []
)
   ↓
NIRManager(config)
   ↓
nir_factory("8164B_NIR") → NIR8164 controller实例
   ↓
controller.connect("GPIB0::20::INSTR", [])
   ↓
pyvisa.ResourceManager().open_resource("GPIB0::20::INSTR")
   ↓
✓ 连接成功 → 更新UI显示"Disconnect"
```

---

## 6. 你的当前配置

根据你的系统：

### 设备配置：
- **Laser/Detector**: HP8164A @ GPIB0::20::INSTR (单主机)
- **TEC**: Stanford LDC501 @ GPIB0::7::INSTR
- **SMU**: Keithley 2604B @ GPIB0::26::INSTR

### 驱动选择：
```python
Configuration = {
    "sensor": "8164B_NIR",      # 使用NIR8164 controller
    "tec": "srs_ldc_501",       # 使用SRS controller
    "smu": "keithley_2600"      # 使用Keithley controller
}
```

### Port配置：
```python
Port = {
    "laser_gpib": "GPIB0::20::INSTR",    # HP8164A
    "detector_gpib": None,                # 单主机模式
    "tec": "GPIB0::7::INSTR",            # Stanford LDC
    "smu": "GPIB0::26::INSTR"            # Keithley SMU
}
```

### 结果：
```python
# 系统创建的配置
nir_configure = NIRConfiguration(
    driver_types="8164B_NIR",           # → NIR8164 controller class
    laser_slot="GPIB0::20::INSTR",      # → 连接HP8164A
    detector_slots=[]                   # → 单主机模式（detector在同一设备）
)
```

---

## 7. 常用操作示例

### 测试laser控制：

```python
from NIR.nir_manager import NIRManager
from NIR.config.nir_config import NIRConfiguration

# 创建配置（使用GUI中选择的值）
config = NIRConfiguration(
    driver_types="8164B_NIR",           # 从下拉框选择
    laser_slot="GPIB0::20::INSTR",      # Configure VISA配置
    detector_slots=[]                   # None = 单主机
)

# 创建manager并连接
manager = NIRManager(config)
manager.initialize()

# 控制laser
manager.enable_laser(True)              # 开laser
manager.set_wavelength(1550.0)          # 设置波长
manager.set_power(-5.0)                 # 设置功率
manager.enable_laser(False)             # 关laser
```

### 读取detector：

```python
# 单主机模式
power = manager.read_power(slot=0, head=1, mf=0)
print(f"Power: {power} dBm")

# 多主机模式（如果detector_gpib有值）
# detector在第二个主机的slot 2
power = manager.read_power(slot=2, head=1, mf=1)
```

---

## 8. 故障排查

### 问题1: 找不到设备
**检查**:
1. 设备电源是否打开
2. GPIB地址是否正确
3. 点击"Configure VISA"查看扫描到的设备

### 问题2: 连接失败
**检查**:
1. `Configuration.sensor` 是否设置正确
2. `Port.laser_gpib` 是否匹配实际地址
3. 查看 `database/shared_memory.json` 确认配置保存

### 问题3: Detector读取无效值
**检查**:
1. 是否为单主机模式（`detector_gpib = None`）
2. Slot/head参数是否正确
3. 是否有物理光纤连接到detector端口

---

## 9. 文件位置总结

| 功能 | 文件位置 |
|------|---------|
| 主界面UI | `GUI/main_instruments_gui.py` |
| VISA配置界面 | `GUI/sub_connect_config_gui.py` |
| 连接处理逻辑 | `GUI/mainframe_stage_control_gui.py` |
| NIR Manager | `NIR/nir_manager.py` |
| NIR Controller | `NIR/nir_controller.py` |
| 配置数据类 | `NIR/config/nir_config.py` |
| 配置存储 | `GUI/database/shared_memory.json` |

---

## 总结

你的系统使用了一个三层配置系统：

1. **驱动层** (`Configuration.sensor = "8164B_NIR"`)
   - 决定使用哪个controller类

2. **地址层** (`Port.laser_gpib = "GPIB0::20::INSTR"`)
   - 决定连接到哪个物理设备

3. **模式层** (`detector_gpib = None`)
   - 决定单主机还是多主机模式

这些配置通过JSON文件持久化，GUI读取并使用这些配置创建正确的controller实例来控制硬件。
